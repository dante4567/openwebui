"""
CalDAV/CardDAV Tool Server for OpenWebUI
Provides calendar and contact management via CalDAV/CardDAV protocols
"""

from fastapi import FastAPI, HTTPException, Query, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import caldav
from caldav.elements import dav
import vobject
import requests
from requests.auth import HTTPBasicAuth
import os
import sys
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
import time
from functools import wraps
from zoneinfo import ZoneInfo
import hashlib
import json
import threading

# Redis import (optional, graceful fallback)
try:
    from redis import Redis
    from redis.exceptions import RedisError
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    Redis = None
    RedisError = Exception

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("caldav-tool")


def retry_on_failure(max_retries=3, base_delay=1.0):
    """
    Retry decorator with exponential backoff for transient failures

    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay: Base delay in seconds, doubles with each retry (default: 1.0)

    Retries on:
        - Network errors (requests.exceptions.RequestException, caldav exceptions)
        - Server errors (status code >= 500)

    Does NOT retry on:
        - Client errors (status code 4xx) - these won't succeed on retry
        - Successful responses (2xx, 3xx)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries <= max_retries:
                try:
                    return func(*args, **kwargs)
                except (requests.exceptions.RequestException, caldav.lib.error.DAVError) as e:
                    retries += 1
                    if retries > max_retries:
                        logger.error(f"Max retries ({max_retries}) exceeded for {func.__name__}", extra={
                            "error": str(e),
                            "retries": retries - 1
                        })
                        raise

                    delay = base_delay * (2 ** (retries - 1))
                    logger.warning(f"Retrying {func.__name__} after {delay}s", extra={
                        "attempt": retries,
                        "max_retries": max_retries,
                        "error": str(e)
                    })
                    time.sleep(delay)
                except HTTPException as e:
                    # Don't retry on client errors (4xx) or successful responses
                    if e.status_code < 500:
                        raise

                    # Retry on server errors (5xx)
                    retries += 1
                    if retries > max_retries:
                        logger.error(f"Max retries ({max_retries}) exceeded for {func.__name__}", extra={
                            "status_code": e.status_code,
                            "retries": retries - 1
                        })
                        raise

                    delay = base_delay * (2 ** (retries - 1))
                    logger.warning(f"Retrying {func.__name__} after {delay}s", extra={
                        "attempt": retries,
                        "max_retries": max_retries,
                        "status_code": e.status_code
                    })
                    time.sleep(delay)
        return wrapper
    return decorator

app = FastAPI(
    title="CalDAV/CardDAV Tool",
    description="Calendar and contact management via CalDAV/CardDAV",
    version="1.0.0"
)

# Get credentials from environment
CALDAV_URL = os.getenv("CALDAV_URL")
CALDAV_USERNAME = os.getenv("CALDAV_USERNAME")
CALDAV_PASSWORD = os.getenv("CALDAV_PASSWORD")

CARDDAV_URL = os.getenv("CARDDAV_URL", CALDAV_URL)  # Often same server
CARDDAV_USERNAME = os.getenv("CARDDAV_USERNAME", CALDAV_USERNAME)
CARDDAV_PASSWORD = os.getenv("CARDDAV_PASSWORD", CALDAV_PASSWORD)

if not all([CALDAV_URL, CALDAV_USERNAME, CALDAV_PASSWORD]):
    logger.error("Required environment variables not set")
    raise ValueError("CALDAV_URL, CALDAV_USERNAME, and CALDAV_PASSWORD are required")

logger.info("CalDAV tool initialized", extra={
    "caldav_url": CALDAV_URL,
    "carddav_url": CARDDAV_URL,
    "username": CALDAV_USERNAME
})

# API Key authentication
TOOL_API_KEY = os.getenv("TOOL_API_KEY")
security = HTTPBearer(auto_error=False)  # Don't auto-error for backwards compatibility


def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Verify API key authentication (optional if TOOL_API_KEY not set)"""
    if not TOOL_API_KEY:
        # No auth required if TOOL_API_KEY not configured
        return None

    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Missing authentication credentials"
        )

    if credentials.credentials != TOOL_API_KEY:
        raise HTTPException(
            status_code=403,
            detail="Invalid authentication credentials"
        )

    return credentials.credentials

# Cache configuration
CACHE_TYPE = os.getenv("CACHE_TYPE", "memory")  # "memory" or "redis"
CACHE_TTL = int(os.getenv("CACHE_TTL", "60"))

# In-memory cache (fallback or default)
_memory_cache: Dict[str, tuple[Any, float]] = {}
_cache_lock = threading.Lock()  # Thread-safe cache access

# Redis cache (optional)
_redis_client: Optional[Redis] = None


def get_redis_client() -> Optional[Redis]:
    """Initialize Redis client (lazy initialization)"""
    global _redis_client
    if _redis_client is None and CACHE_TYPE == "redis" and REDIS_AVAILABLE:
        try:
            _redis_client = Redis(
                host=os.getenv("REDIS_HOST", "redis"),
                port=int(os.getenv("REDIS_PORT", "6379")),
                db=int(os.getenv("REDIS_DB", "2")),  # DB 2 for caldav
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2
            )
            # Test connection
            _redis_client.ping()
            logger.info(f"Redis connected: {_redis_client.info('server')['redis_version']}")
        except (RedisError, Exception) as e:
            logger.error(f"Redis connection failed: {e}, falling back to memory cache")
            _redis_client = None
    return _redis_client


def get_cache_key(prefix: str, **kwargs) -> str:
    """Generate cache key from prefix and parameters"""
    key_data = f"{prefix}:{json.dumps(kwargs, sort_keys=True)}"
    return hashlib.md5(key_data.encode()).hexdigest()


def get_cached(key: str) -> Optional[Any]:
    """Get value from cache (Redis or memory, thread-safe)"""
    # Try Redis first if enabled
    if CACHE_TYPE == "redis" and REDIS_AVAILABLE:
        redis = get_redis_client()
        if redis:
            try:
                value = redis.get(key)
                if value:
                    logger.debug("Redis cache hit", extra={"key": key})
                    return json.loads(value)
                logger.debug("Redis cache miss", extra={"key": key})
                return None
            except (RedisError, Exception) as e:
                logger.warning(f"Redis get failed: {e}, trying memory cache")
                # Fall through to memory cache

    # Memory cache (fallback or default) - thread-safe
    with _cache_lock:
        if key in _memory_cache:
            value, expiry = _memory_cache[key]
            if time.time() < expiry:
                logger.debug("Memory cache hit", extra={"key": key})
                return value
            else:
                logger.debug("Memory cache expired", extra={"key": key})
                del _memory_cache[key]
    return None


def set_cached(key: str, value: Any, ttl: int = CACHE_TTL):
    """Set value in cache (Redis or memory, thread-safe)"""
    # Try Redis first if enabled
    if CACHE_TYPE == "redis" and REDIS_AVAILABLE:
        redis = get_redis_client()
        if redis:
            try:
                redis.setex(key, ttl, json.dumps(value))
                logger.debug("Redis cache set", extra={"key": key, "ttl": ttl})
                return
            except (RedisError, Exception) as e:
                logger.warning(f"Redis set failed: {e}, using memory cache")
                # Fall through to memory cache

    # Memory cache (fallback or default) - thread-safe
    with _cache_lock:
        expiry = time.time() + ttl
        _memory_cache[key] = (value, expiry)
        logger.debug("Memory cache set", extra={"key": key, "ttl": ttl})


def get_cache_stats() -> dict:
    """Get cache statistics"""
    if CACHE_TYPE == "redis" and REDIS_AVAILABLE:
        redis = get_redis_client()
        if redis:
            try:
                info = redis.info("stats")
                return {
                    "type": "redis",
                    "keys": redis.dbsize(),
                    "hits": info.get("keyspace_hits", 0),
                    "misses": info.get("keyspace_misses", 0),
                    "hit_rate": round(
                        info.get("keyspace_hits", 0) /
                        max(1, info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0)) * 100,
                        2
                    ) if (info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0)) > 0 else 0,
                    "ttl_seconds": CACHE_TTL
                }
            except (RedisError, Exception):
                pass

    # Memory cache stats - thread-safe
    with _cache_lock:
        return {
            "type": "memory",
            "entries": len(_memory_cache),
            "ttl_seconds": CACHE_TTL
        }


class Event(BaseModel):
    summary: str
    start: str  # ISO 8601 format
    end: str  # ISO 8601 format
    description: Optional[str] = None
    location: Optional[str] = None
    timezone: Optional[str] = Field(
        default="UTC",
        description="Timezone for event display (e.g., 'Europe/Berlin', 'America/New_York')"
    )


class EventUpdate(BaseModel):
    summary: Optional[str] = None
    start: Optional[str] = None
    end: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None


class Contact(BaseModel):
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    organization: Optional[str] = None


class Calendar(BaseModel):
    name: str = Field(..., description="Calendar ID/name (e.g., 'work', 'personal')")
    displayname: Optional[str] = Field(None, description="Display name for the calendar")
    description: Optional[str] = Field(None, description="Calendar description")


def get_caldav_client():
    """Create CalDAV client connection"""
    return caldav.DAVClient(
        url=CALDAV_URL,
        username=CALDAV_USERNAME,
        password=CALDAV_PASSWORD
    )


def get_carddav_auth():
    """Get CardDAV authentication"""
    return HTTPBasicAuth(CARDDAV_USERNAME, CARDDAV_PASSWORD)


def get_addressbook_url():
    """Build CardDAV addressbook URL for Nextcloud"""
    # Nextcloud CardDAV format: https://server/remote.php/dav/addressbooks/users/USERNAME/
    if CARDDAV_URL.endswith('/remote.php/dav'):
        base_url = CARDDAV_URL[:-len('/remote.php/dav')]
    elif CARDDAV_URL.endswith('/remote.php/dav/'):
        base_url = CARDDAV_URL[:-len('/remote.php/dav/')]
    else:
        base_url = CARDDAV_URL.rstrip('/')
    return f"{base_url}/remote.php/dav/addressbooks/users/{CARDDAV_USERNAME}/"


@app.get("/")
def root():
    """Health check endpoint"""
    logger.debug("Health check requested")
    return {"status": "healthy", "service": "caldav-tool"}


@app.get("/health")
def health_check():
    """
    Enhanced health check with CalDAV connectivity test
    Returns cache statistics and basic metrics
    """
    start_time = time.time()

    # Test CalDAV connectivity
    caldav_status = "unknown"
    caldav_latency_ms = None
    calendar_count = 0

    try:
        client = get_caldav_client()
        principal = client.principal()
        calendars = principal.calendars()
        calendar_count = len(calendars)
        caldav_status = "healthy"
        caldav_latency_ms = round((time.time() - start_time) * 1000, 2)
    except Exception as e:
        caldav_status = "unhealthy"
        logger.error("Health check failed", extra={"error": str(e)})

    # Test CardDAV connectivity (optional)
    carddav_status = "unknown"
    try:
        url = get_addressbook_url()
        auth = get_carddav_auth()
        response = requests.get(url, auth=auth, timeout=5)
        carddav_status = "healthy" if response.status_code in [200, 207] else "degraded"
    except:
        carddav_status = "degraded"

    return {
        "status": caldav_status,
        "service": "caldav-tool",
        "caldav": {
            "status": caldav_status,
            "latency_ms": caldav_latency_ms,
            "calendar_count": calendar_count,
            "url": CALDAV_URL
        },
        "carddav": {
            "status": carddav_status,
            "url": CARDDAV_URL
        },
        "cache": get_cache_stats(),
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================================================
# CALENDAR OPERATIONS (CalDAV)
# ============================================================================

@app.get("/calendars")
@retry_on_failure(max_retries=3, base_delay=1.0)
def list_calendars(token: str = Depends(verify_token)):
    """List all available calendars"""
    start_time = time.time()
    logger.info("Fetching calendars")

    try:
        client = get_caldav_client()
        principal = client.principal()
        calendars = principal.calendars()

        latency = time.time() - start_time
        result = [
            {
                "name": cal.name,
                "url": str(cal.url),
                "id": cal.id
            }
            for cal in calendars
        ]

        logger.info("Calendars fetched successfully", extra={
            "calendar_count": len(result),
            "latency_ms": round(latency * 1000, 2)
        })
        return result

    except Exception as e:
        logger.error("Failed to fetch calendars", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"CalDAV error: {str(e)}")


@app.post("/calendars")
@retry_on_failure(max_retries=3, base_delay=1.0)
def create_calendar(calendar: Calendar, token: str = Depends(verify_token)):
    """
    Create a new calendar

    Args:
        calendar: Calendar details (name, displayname, description)

    Returns:
        Dictionary with calendar details including URL and ID
    """
    start_time = time.time()
    logger.info("Creating calendar", extra={
        "calendar_name": calendar.name,
        "calendar_displayname": calendar.displayname
    })

    try:
        client = get_caldav_client()
        principal = client.principal()

        # Use displayname if provided, otherwise use name
        display = calendar.displayname if calendar.displayname else calendar.name

        # Create the calendar
        new_calendar = principal.make_calendar(
            name=calendar.name,
            cal_id=calendar.name,
            supported_calendar_component_set=['VEVENT']
        )

        # Set displayname and description if caldav library supports it
        # Note: Some CalDAV servers may not support all properties
        try:
            if calendar.displayname:
                new_calendar.set_properties([dav.DisplayName(calendar.displayname)])
            if calendar.description:
                # Description property varies by server implementation
                pass
        except Exception as prop_error:
            logger.warning("Could not set all calendar properties", extra={
                "error": str(prop_error)
            })

        latency = time.time() - start_time
        result = {
            "status": "success",
            "message": "Calendar created",
            "name": calendar.name,
            "displayname": display,
            "url": str(new_calendar.url),
            "id": new_calendar.id if hasattr(new_calendar, 'id') else calendar.name
        }

        logger.info("Calendar created successfully", extra={
            "calendar_name": calendar.name,
            "calendar_url": str(new_calendar.url),
            "latency_ms": round(latency * 1000, 2)
        })

        return result

    except Exception as e:
        logger.error("Failed to create calendar", extra={
            "calendar_name": calendar.name,
            "error": str(e)
        })
        raise HTTPException(status_code=500, detail=f"CalDAV error: {str(e)}")


def parse_relative_date(date_str: str) -> datetime:
    """
    Parse relative date strings like 'today', 'tomorrow', 'yesterday'
    or ISO format dates like '2025-10-14'
    """
    if not date_str:
        return None

    date_str_lower = date_str.lower().strip()
    now = datetime.now()

    # Handle relative dates
    if date_str_lower == "today":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif date_str_lower == "tomorrow":
        return (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    elif date_str_lower == "yesterday":
        return (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    elif date_str_lower == "next week":
        return (now + timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
    elif date_str_lower == "last week":
        return (now - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        # Try to parse as ISO format
        try:
            return datetime.fromisoformat(date_str)
        except ValueError:
            raise ValueError(f"Invalid date format: '{date_str}'. Use ISO format (YYYY-MM-DD) or relative terms (today, tomorrow, yesterday, next week, last week)")


@app.get("/events")
@retry_on_failure(max_retries=3, base_delay=1.0)
def list_events(
    calendar_name: Optional[str] = Query(None, description="Specific calendar name"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format or 'today', 'tomorrow', etc.)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format or relative)"),
    days_ahead: int = Query(30, ge=1, le=365, description="Days to look ahead from start_date"),
    timezone: Optional[str] = Query("UTC", description="Timezone for event display (e.g., 'Europe/Berlin')"),
    use_cache: bool = Query(True, description="Use cached results if available"),
    limit: Optional[int] = Query(None, ge=1, le=500, description="Limit number of results"),
    token: str = Depends(verify_token)
):
    """
    List events from calendar with enhanced filtering

    Args:
        calendar_name: Specific calendar name (default: first calendar)
        start_date: Start date in ISO format (YYYY-MM-DD) or relative ('today', 'tomorrow', 'yesterday', 'next week', 'last week'). Default: today
        end_date: End date in ISO format (YYYY-MM-DD) or relative. Default: 30 days from start_date
        days_ahead: Number of days to look ahead (if end_date not specified). Default: 30
        timezone: Timezone to convert event times (default: UTC)
        use_cache: Whether to use cached results (default: true)
        limit: Maximum number of events to return

    Examples:
        - /events?start_date=today&days_ahead=7 - Next 7 days
        - /events?start_date=tomorrow&timezone=Europe/Berlin - Tomorrow in Berlin time
        - /events?calendar_name=Work&limit=10 - Next 10 work events
    """
    start_time = time.time()

    # Check cache first
    cache_key = get_cache_key(
        "events",
        calendar_name=calendar_name,
        start_date=start_date,
        end_date=end_date,
        days_ahead=days_ahead,
        timezone=timezone,
        limit=limit
    )

    if use_cache:
        cached = get_cached(cache_key)
        if cached is not None:
            logger.info("Returning cached events", extra={
                "event_count": len(cached),
                "cache_hit": True
            })
            return cached

    logger.info("Fetching events", extra={
        "calendar_name": calendar_name,
        "start_date": start_date,
        "end_date": end_date,
        "days_ahead": days_ahead,
        "timezone": timezone,
        "limit": limit,
        "cache_hit": False
    })

    try:
        client = get_caldav_client()
        principal = client.principal()
        calendars = principal.calendars()

        if not calendars:
            logger.error("No calendars found")
            raise HTTPException(status_code=404, detail="No calendars found")

        # Select calendar
        if calendar_name:
            calendar = next((c for c in calendars if c.name == calendar_name), None)
            if not calendar:
                logger.error("Calendar not found", extra={"calendar_name": calendar_name})
                raise HTTPException(status_code=404, detail=f"Calendar '{calendar_name}' not found")
        else:
            calendar = calendars[0]

        # Date range - support relative dates
        try:
            start = parse_relative_date(start_date) if start_date else datetime.now()
            end = parse_relative_date(end_date) if end_date else start + timedelta(days=days_ahead)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Fetch events
        events = calendar.date_search(start=start, end=end)

        # Parse target timezone
        try:
            target_tz = ZoneInfo(timezone) if timezone else ZoneInfo("UTC")
        except Exception:
            logger.warning(f"Invalid timezone '{timezone}', defaulting to UTC")
            target_tz = ZoneInfo("UTC")

        results = []
        for event in events:
            try:
                vcal = vobject.readOne(event.data)
                vevent = vcal.vevent

                # Parse start/end times with timezone conversion
                start_dt = None
                end_dt = None

                if hasattr(vevent, 'dtstart'):
                    start_val = vevent.dtstart.value
                    if isinstance(start_val, datetime):
                        # Convert to target timezone if datetime has timezone info
                        if start_val.tzinfo is not None:
                            start_dt = start_val.astimezone(target_tz).isoformat()
                        else:
                            # Assume UTC if no timezone
                            start_dt = start_val.replace(tzinfo=ZoneInfo("UTC")).astimezone(target_tz).isoformat()
                    else:
                        # Date only (no time component)
                        start_dt = start_val.isoformat()

                if hasattr(vevent, 'dtend'):
                    end_val = vevent.dtend.value
                    if isinstance(end_val, datetime):
                        if end_val.tzinfo is not None:
                            end_dt = end_val.astimezone(target_tz).isoformat()
                        else:
                            end_dt = end_val.replace(tzinfo=ZoneInfo("UTC")).astimezone(target_tz).isoformat()
                    else:
                        end_dt = end_val.isoformat()

                results.append({
                    "summary": str(vevent.summary.value) if hasattr(vevent, 'summary') else "No title",
                    "start": start_dt,
                    "end": end_dt,
                    "description": str(vevent.description.value) if hasattr(vevent, 'description') else None,
                    "location": str(vevent.location.value) if hasattr(vevent, 'location') else None,
                    "uid": str(vevent.uid.value) if hasattr(vevent, 'uid') else None,
                    "timezone": timezone
                })
            except Exception as e:
                logger.warning("Skipping malformed event during list", extra={
                    "error": str(e),
                    "event_url": event.url if hasattr(event, 'url') else None
                })
                continue

        # Apply limit if specified
        if limit and len(results) > limit:
            results = results[:limit]

        # Cache the results
        set_cached(cache_key, results)

        latency = time.time() - start_time
        logger.info("Events fetched successfully", extra={
            "event_count": len(results),
            "calendar": calendar.name,
            "latency_ms": round(latency * 1000, 2),
            "timezone": timezone
        })
        return results

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to fetch events", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"CalDAV error: {str(e)}")


@app.post("/events")
@retry_on_failure(max_retries=3, base_delay=1.0)
def create_event(event: Event, calendar_name: Optional[str] = None, token: str = Depends(verify_token)):
    """
    Create a new calendar event

    Args:
        event: Event details
        calendar_name: Target calendar (default: first calendar)
    """
    start_time = time.time()
    logger.info("Creating event", extra={
        "summary": event.summary,
        "calendar_name": calendar_name,
        "start": event.start,
        "end": event.end
    })

    try:
        client = get_caldav_client()
        principal = client.principal()
        calendars = principal.calendars()

        if not calendars:
            logger.error("No calendars found")
            raise HTTPException(status_code=404, detail="No calendars found")

        # Select calendar
        if calendar_name:
            calendar = next((c for c in calendars if c.name == calendar_name), None)
            if not calendar:
                logger.error("Calendar not found", extra={"calendar_name": calendar_name})
                raise HTTPException(status_code=404, detail=f"Calendar '{calendar_name}' not found")
        else:
            calendar = calendars[0]

        # Create vCalendar object with required fields
        cal = vobject.iCalendar()

        # Add required VERSION and PRODID
        if not hasattr(cal, 'version'):
            cal.add('version')
            cal.version.value = '2.0'
        if not hasattr(cal, 'prodid'):
            cal.add('prodid')
            cal.prodid.value = '-//OpenWebUI//CalDAV Tool//EN'

        # Add event
        cal.add('vevent')
        cal.vevent.add('summary').value = event.summary
        cal.vevent.add('dtstart').value = datetime.fromisoformat(event.start)
        cal.vevent.add('dtend').value = datetime.fromisoformat(event.end)

        # Add DTSTAMP (required by RFC 5545)
        cal.vevent.add('dtstamp').value = datetime.now()

        # Generate UID
        import uuid
        uid = str(uuid.uuid4())
        cal.vevent.add('uid').value = uid

        # Optional fields
        if event.description:
            cal.vevent.add('description').value = event.description
        if event.location:
            cal.vevent.add('location').value = event.location

        # Log the iCalendar data being sent
        ical_data = cal.serialize()
        logger.info("Sending iCalendar data to Nextcloud", extra={
            "uid": uid,
            "summary": event.summary,
            "ical_length": len(ical_data)
        })

        # Save to calendar
        saved_event = calendar.save_event(ical_data)

        # Verify the event was saved by trying to fetch it immediately
        try:
            # Wait a moment for sync
            import time as time_module
            time_module.sleep(0.5)

            # Try to fetch the event we just created
            search_start = datetime.fromisoformat(event.start) - timedelta(hours=1)
            search_end = datetime.fromisoformat(event.end) + timedelta(hours=1)
            verify_events = calendar.date_search(start=search_start, end=search_end)

            found = False
            for ve in verify_events:
                try:
                    vcal_check = vobject.readOne(ve.data)
                    if hasattr(vcal_check.vevent, 'uid') and str(vcal_check.vevent.uid.value) == uid:
                        found = True
                        break
                except:
                    pass

            if not found:
                logger.error("Event creation verification failed - event not found after save", extra={
                    "uid": uid,
                    "summary": event.summary
                })
        except Exception as verify_error:
            logger.warning("Could not verify event creation", extra={
                "error": str(verify_error),
                "uid": uid
            })

        latency = time.time() - start_time
        logger.info("Event created successfully", extra={
            "uid": uid,
            "calendar": calendar.name,
            "latency_ms": round(latency * 1000, 2)
        })
        return {"status": "success", "message": "Event created", "uid": uid}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create event", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"CalDAV error: {str(e)}")


@app.delete("/events/{uid}")
@retry_on_failure(max_retries=3, base_delay=1.0)
def delete_event(uid: str, calendar_name: Optional[str] = None, token: str = Depends(verify_token)):
    """
    Delete a calendar event by UID

    Args:
        uid: Unique identifier of the event
        calendar_name: Target calendar (default: search all calendars)
    """
    start_time = time.time()
    logger.info("Deleting event", extra={"uid": uid, "calendar_name": calendar_name})

    try:
        client = get_caldav_client()
        principal = client.principal()
        calendars = principal.calendars()

        if not calendars:
            logger.error("No calendars found")
            raise HTTPException(status_code=404, detail="No calendars found")

        # Select calendar(s) to search
        search_calendars = []
        if calendar_name:
            calendar = next((c for c in calendars if c.name == calendar_name), None)
            if not calendar:
                logger.error("Calendar not found", extra={"calendar_name": calendar_name})
                raise HTTPException(status_code=404, detail=f"Calendar '{calendar_name}' not found")
            search_calendars = [calendar]
        else:
            search_calendars = calendars

        # Search for event by UID
        event_found = False
        for calendar in search_calendars:
            try:
                # Search for events in a wide date range
                start = datetime.now() - timedelta(days=365)
                end = datetime.now() + timedelta(days=365)
                events = calendar.date_search(start=start, end=end)

                for event in events:
                    try:
                        vcal = vobject.readOne(event.data)
                        if hasattr(vcal.vevent, 'uid') and str(vcal.vevent.uid.value) == uid:
                            # Found the event, delete it
                            event.delete()
                            event_found = True
                            logger.info("Event deleted successfully", extra={
                                "uid": uid,
                                "calendar": calendar.name
                            })
                            latency = time.time() - start_time
                            return {
                                "status": "success",
                                "message": "Event deleted",
                                "uid": uid,
                                "latency_ms": round(latency * 1000, 2)
                            }
                    except Exception as parse_error:
                        logger.debug("Skipping event during delete search", extra={
                            "error": str(parse_error)
                        })
                        continue
            except Exception as calendar_error:
                logger.warning("Error searching calendar", extra={
                    "calendar": calendar.name,
                    "error": str(calendar_error)
                })
                continue

        if not event_found:
            logger.error("Event not found", extra={"uid": uid})
            raise HTTPException(status_code=404, detail=f"Event with UID '{uid}' not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete event", extra={"error": str(e), "uid": uid})
        raise HTTPException(status_code=500, detail=f"CalDAV error: {str(e)}")


@app.patch("/events/{uid}")
@retry_on_failure(max_retries=3, base_delay=1.0)
def update_event(uid: str, updates: EventUpdate, calendar_name: Optional[str] = None, token: str = Depends(verify_token)):
    """
    Update an existing calendar event (partial update)

    Args:
        uid: Unique identifier of the event
        updates: Fields to update (only specified fields will be changed)
        calendar_name: Target calendar (default: search all calendars)

    Examples:
        - PATCH /events/abc123 {"summary": "Updated title"}
        - PATCH /events/abc123 {"start": "2025-10-20T14:00:00", "end": "2025-10-20T15:00:00"}
        - PATCH /events/abc123 {"location": "New location", "description": "Updated description"}
    """
    start_time = time.time()
    logger.info("Updating event", extra={"uid": uid, "updates": updates.dict(exclude_none=True)})

    try:
        client = get_caldav_client()
        principal = client.principal()
        calendars = principal.calendars()

        if not calendars:
            logger.error("No calendars found")
            raise HTTPException(status_code=404, detail="No calendars found")

        # Select calendar(s) to search
        search_calendars = []
        if calendar_name:
            calendar = next((c for c in calendars if c.name == calendar_name), None)
            if not calendar:
                logger.error("Calendar not found", extra={"calendar_name": calendar_name})
                raise HTTPException(status_code=404, detail=f"Calendar '{calendar_name}' not found")
            search_calendars = [calendar]
        else:
            search_calendars = calendars

        # Search for event by UID
        event_found = False
        for calendar in search_calendars:
            try:
                # Search for events in a wide date range
                start_search = datetime.now() - timedelta(days=365)
                end_search = datetime.now() + timedelta(days=365)
                events = calendar.date_search(start=start_search, end=end_search)

                for event in events:
                    try:
                        vcal = vobject.readOne(event.data)
                        if hasattr(vcal.vevent, 'uid') and str(vcal.vevent.uid.value) == uid:
                            # Found the event, update it
                            vevent = vcal.vevent

                            # Update fields if provided
                            if updates.summary is not None:
                                vevent.summary.value = updates.summary

                            if updates.start is not None:
                                vevent.dtstart.value = datetime.fromisoformat(updates.start)

                            if updates.end is not None:
                                vevent.dtend.value = datetime.fromisoformat(updates.end)

                            if updates.description is not None:
                                if hasattr(vevent, 'description'):
                                    vevent.description.value = updates.description
                                else:
                                    vevent.add('description').value = updates.description

                            if updates.location is not None:
                                if hasattr(vevent, 'location'):
                                    vevent.location.value = updates.location
                                else:
                                    vevent.add('location').value = updates.location

                            # Update DTSTAMP
                            if hasattr(vevent, 'dtstamp'):
                                vevent.dtstamp.value = datetime.now()
                            else:
                                vevent.add('dtstamp').value = datetime.now()

                            # Save updated event
                            event.data = vcal.serialize()
                            event.save()

                            event_found = True
                            latency = time.time() - start_time
                            logger.info("Event updated successfully", extra={
                                "uid": uid,
                                "calendar": calendar.name,
                                "latency_ms": round(latency * 1000, 2)
                            })
                            return {
                                "status": "success",
                                "message": "Event updated",
                                "uid": uid,
                                "latency_ms": round(latency * 1000, 2)
                            }
                    except Exception as parse_error:
                        logger.debug("Skipping event during update search", extra={
                            "error": str(parse_error)
                        })
                        continue
            except Exception as calendar_error:
                logger.warning("Error searching calendar", extra={
                    "calendar": calendar.name,
                    "error": str(calendar_error)
                })
                continue

        if not event_found:
            logger.error("Event not found", extra={"uid": uid})
            raise HTTPException(status_code=404, detail=f"Event with UID '{uid}' not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update event", extra={"error": str(e), "uid": uid})
        raise HTTPException(status_code=500, detail=f"CalDAV error: {str(e)}")


# ============================================================================
# CONTACT OPERATIONS (CardDAV)
# ============================================================================

@app.get("/addressbooks")
@retry_on_failure(max_retries=3, base_delay=1.0)
def list_addressbooks(token: str = Depends(verify_token)):
    """List all available addressbooks"""
    start_time = time.time()
    logger.info("Fetching addressbooks")

    try:
        url = get_addressbook_url()
        auth = get_carddav_auth()

        # PROPFIND request to discover addressbooks
        propfind_xml = '''<?xml version="1.0" encoding="utf-8"?>
        <d:propfind xmlns:d="DAV:" xmlns:card="urn:ietf:params:xml:ns:carddav">
            <d:prop>
                <d:displayname/>
                <d:resourcetype/>
            </d:prop>
        </d:propfind>'''

        response = requests.request(
            'PROPFIND',
            url,
            auth=auth,
            data=propfind_xml,
            headers={'Content-Type': 'application/xml', 'Depth': '1'},
            timeout=10
        )

        latency = time.time() - start_time

        if response.status_code not in [200, 207]:
            logger.error("Failed to fetch addressbooks", extra={
                "status_code": response.status_code,
                "response": response.text[:200],
                "latency_ms": round(latency * 1000, 2)
            })
            raise HTTPException(status_code=response.status_code, detail=response.text)

        # Parse XML response
        root = ET.fromstring(response.content)
        ns = {'d': 'DAV:', 'card': 'urn:ietf:params:xml:ns:carddav'}

        addressbooks = []
        for prop_response in root.findall('.//d:response', ns):
            href = prop_response.find('d:href', ns)
            displayname = prop_response.find('.//d:displayname', ns)
            resourcetype = prop_response.find('.//d:resourcetype', ns)

            # Check if it's an addressbook (not the parent collection)
            if resourcetype is not None and resourcetype.find('card:addressbook', ns) is not None:
                addressbooks.append({
                    "name": displayname.text if displayname is not None else "Unnamed",
                    "url": href.text if href is not None else "",
                    "id": href.text.split('/')[-2] if href is not None else ""
                })

        logger.info("Addressbooks fetched successfully", extra={
            "addressbook_count": len(addressbooks),
            "latency_ms": round(latency * 1000, 2)
        })
        return addressbooks

    except HTTPException:
        raise
    except requests.exceptions.RequestException as e:
        logger.error("Network error fetching addressbooks", extra={"error": str(e)})
        raise HTTPException(status_code=503, detail=f"CardDAV API unreachable: {str(e)}")
    except Exception as e:
        logger.error("Failed to fetch addressbooks", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"CardDAV error: {str(e)}")


@app.get("/contacts")
@retry_on_failure(max_retries=3, base_delay=1.0)
def list_contacts(addressbook_name: Optional[str] = "contacts", token: str = Depends(verify_token)):
    """
    List contacts from addressbook

    Args:
        addressbook_name: Specific addressbook (default: "contacts")
    """
    start_time = time.time()

    # Handle None case - default to "contacts" addressbook
    if addressbook_name is None or addressbook_name == "None":
        addressbook_name = "contacts"

    logger.info("Fetching contacts", extra={"addressbook_name": addressbook_name})

    try:
        base_url = get_addressbook_url()
        auth = get_carddav_auth()

        # Build addressbook URL
        addressbook_url = f"{base_url}{addressbook_name}/"

        # REPORT request to get all vcards
        report_xml = '''<?xml version="1.0" encoding="utf-8"?>
        <card:addressbook-query xmlns:d="DAV:" xmlns:card="urn:ietf:params:xml:ns:carddav">
            <d:prop>
                <d:getetag/>
                <card:address-data/>
            </d:prop>
        </card:addressbook-query>'''

        response = requests.request(
            'REPORT',
            addressbook_url,
            auth=auth,
            data=report_xml,
            headers={'Content-Type': 'application/xml', 'Depth': '1'},
            timeout=10
        )

        latency = time.time() - start_time

        if response.status_code not in [200, 207]:
            logger.error("Failed to fetch contacts", extra={
                "addressbook_name": addressbook_name,
                "status_code": response.status_code,
                "response": response.text[:200],
                "latency_ms": round(latency * 1000, 2)
            })
            raise HTTPException(status_code=response.status_code, detail=f"CardDAV error: {response.text}")

        # Parse XML response
        root = ET.fromstring(response.content)
        ns = {'d': 'DAV:', 'card': 'urn:ietf:params:xml:ns:carddav'}

        results = []
        for prop_response in root.findall('.//d:response', ns):
            address_data = prop_response.find('.//card:address-data', ns)
            if address_data is not None and address_data.text:
                try:
                    vcard = vobject.readOne(address_data.text)
                    results.append({
                        "full_name": str(vcard.fn.value) if hasattr(vcard, 'fn') else "Unknown",
                        "email": str(vcard.email.value) if hasattr(vcard, 'email') else None,
                        "phone": str(vcard.tel.value) if hasattr(vcard, 'tel') else None,
                        "organization": str(vcard.org.value[0]) if hasattr(vcard, 'org') and vcard.org.value else None,
                        "uid": str(vcard.uid.value) if hasattr(vcard, 'uid') else None
                    })
                except Exception:
                    continue

        logger.info("Contacts fetched successfully", extra={
            "contact_count": len(results),
            "addressbook": addressbook_name,
            "latency_ms": round(latency * 1000, 2)
        })
        return results

    except HTTPException:
        raise
    except requests.exceptions.RequestException as e:
        logger.error("Network error fetching contacts", extra={"error": str(e)})
        raise HTTPException(status_code=503, detail=f"CardDAV API unreachable: {str(e)}")
    except Exception as e:
        logger.error("Failed to fetch contacts", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"CardDAV error: {str(e)}")


@app.post("/contacts")
@retry_on_failure(max_retries=3, base_delay=1.0)
def create_contact(contact: Contact, addressbook_name: Optional[str] = "contacts", token: str = Depends(verify_token)):
    """
    Create a new contact

    Args:
        contact: Contact details
        addressbook_name: Target addressbook (default: "contacts")
    """
    start_time = time.time()

    # Handle None case - default to "contacts" addressbook
    if addressbook_name is None or addressbook_name == "None":
        addressbook_name = "contacts"

    logger.info("Creating contact", extra={
        "full_name": contact.full_name,
        "addressbook_name": addressbook_name
    })

    try:
        import uuid

        base_url = get_addressbook_url()
        auth = get_carddav_auth()

        # Create vCard object
        vcard = vobject.vCard()
        vcard.add('fn')
        vcard.fn.value = contact.full_name

        if contact.email:
            vcard.add('email')
            vcard.email.value = contact.email
            vcard.email.type_param = 'INTERNET'

        if contact.phone:
            vcard.add('tel')
            vcard.tel.value = contact.phone

        if contact.organization:
            vcard.add('org')
            vcard.org.value = [contact.organization]

        # Generate UID
        uid = str(uuid.uuid4())
        vcard.add('uid')
        vcard.uid.value = uid

        # Build contact URL
        contact_url = f"{base_url}{addressbook_name}/{uid}.vcf"

        # PUT request to create contact
        response = requests.put(
            contact_url,
            auth=auth,
            data=vcard.serialize(),
            headers={'Content-Type': 'text/vcard'},
            timeout=10
        )

        latency = time.time() - start_time

        if response.status_code not in [200, 201, 204]:
            logger.error("Failed to create contact", extra={
                "status_code": response.status_code,
                "response": response.text[:200],
                "latency_ms": round(latency * 1000, 2)
            })
            raise HTTPException(status_code=response.status_code, detail=f"CardDAV error: {response.text}")

        logger.info("Contact created successfully", extra={
            "uid": uid,
            "addressbook": addressbook_name,
            "latency_ms": round(latency * 1000, 2)
        })
        return {"status": "success", "message": "Contact created", "uid": uid}

    except HTTPException:
        raise
    except requests.exceptions.RequestException as e:
        logger.error("Network error creating contact", extra={"error": str(e)})
        raise HTTPException(status_code=503, detail=f"CardDAV API unreachable: {str(e)}")
    except Exception as e:
        logger.error("Failed to create contact", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"CardDAV error: {str(e)}")
