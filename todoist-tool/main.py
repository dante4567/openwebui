"""
Todoist Tool Server for OpenWebUI
Provides task management capabilities via Todoist API
"""

from fastapi import FastAPI, HTTPException, Query, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import requests
import os
import sys
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import time
from functools import wraps, lru_cache
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
logger = logging.getLogger("todoist-tool")


def retry_on_failure(max_retries=3, base_delay=1.0):
    """
    Retry decorator with exponential backoff for transient failures

    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay: Base delay in seconds, doubles with each retry (default: 1.0)

    Retries on:
        - Network errors (requests.exceptions.RequestException)
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
                except requests.exceptions.RequestException as e:
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
    title="Todoist Tool",
    description="Task management via Todoist API",
    version="1.0.0"
)

TODOIST_API_KEY = os.getenv("TODOIST_API_KEY")
TODOIST_API_URL = "https://api.todoist.com/rest/v2"

if not TODOIST_API_KEY:
    logger.error("TODOIST_API_KEY environment variable not set")
    raise ValueError("TODOIST_API_KEY environment variable is required")

logger.info("Todoist tool initialized", extra={"api_url": TODOIST_API_URL})

headers = {
    "Authorization": f"Bearer {TODOIST_API_KEY}",
    "Content-Type": "application/json"
}

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
                db=int(os.getenv("REDIS_DB", "1")),
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


class Task(BaseModel):
    content: str
    description: Optional[str] = None
    project_id: Optional[str] = None
    due_string: Optional[str] = None
    priority: Optional[int] = 1
    labels: Optional[List[str]] = None


class TaskUpdate(BaseModel):
    content: Optional[str] = None
    description: Optional[str] = None
    due_string: Optional[str] = None
    priority: Optional[int] = None


@app.get("/")
def root():
    """Health check endpoint"""
    logger.debug("Health check requested")
    return {"status": "healthy", "service": "todoist-tool"}


@app.get("/health")
def health_check():
    """
    Enhanced health check with API connectivity test
    Returns cache statistics and basic metrics
    """
    start_time = time.time()

    # Test Todoist API connectivity
    try:
        response = requests.get(
            f"{TODOIST_API_URL}/projects",
            headers=headers,
            timeout=5
        )
        api_status = "healthy" if response.status_code == 200 else "degraded"
        api_latency_ms = round((time.time() - start_time) * 1000, 2)
    except Exception as e:
        api_status = "unhealthy"
        api_latency_ms = None
        logger.error("Health check failed", extra={"error": str(e)})

    return {
        "status": api_status,
        "service": "todoist-tool",
        "todoist_api": {
            "status": api_status,
            "latency_ms": api_latency_ms,
            "url": TODOIST_API_URL
        },
        "cache": get_cache_stats(),
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/tasks")
@retry_on_failure(max_retries=3, base_delay=1.0)
def list_tasks(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    label: Optional[str] = Query(None, description="Filter by label name"),
    filter: Optional[str] = Query(None, description="Todoist filter string (e.g., 'today', 'overdue', '@work')"),
    priority: Optional[int] = Query(None, ge=1, le=4, description="Filter by priority (1=normal, 2=high, 3=very high, 4=urgent)"),
    limit: Optional[int] = Query(None, ge=1, le=500, description="Limit number of results"),
    token: str = Depends(verify_token),
    use_cache: bool = Query(True, description="Use cached results if available")
):
    """
    List tasks with enhanced filtering

    Args:
        project_id: Filter by project ID
        label: Filter by label name
        filter: Todoist filter string (e.g., "today", "overdue", "@work")
        priority: Filter by priority (1-4, where 4 is most urgent)
        limit: Maximum number of tasks to return (1-500)
        use_cache: Whether to use cached results (default: true)

    Returns:
        List of tasks matching the filters

    Examples:
        - /tasks?filter=today - Get today's tasks
        - /tasks?priority=4&limit=10 - Get 10 most urgent tasks
        - /tasks?label=work&filter=overdue - Get overdue work tasks
    """
    start_time = time.time()

    # Check cache first
    cache_key = get_cache_key(
        "tasks",
        project_id=project_id,
        label=label,
        filter=filter,
        priority=priority,
        limit=limit
    )

    if use_cache:
        cached = get_cached(cache_key)
        if cached is not None:
            logger.info("Returning cached tasks", extra={
                "task_count": len(cached),
                "cache_hit": True
            })
            return cached

    # Build query parameters
    params = {}
    if project_id:
        params["project_id"] = project_id
    if filter:
        params["filter"] = filter

    logger.info("Fetching tasks", extra={
        "project_id": project_id,
        "label": label,
        "filter": filter,
        "priority": priority,
        "limit": limit,
        "cache_hit": False
    })

    try:
        response = requests.get(f"{TODOIST_API_URL}/tasks", headers=headers, params=params, timeout=10)
        latency = time.time() - start_time

        if response.status_code != 200:
            logger.error("Failed to fetch tasks", extra={
                "status_code": response.status_code,
                "response": response.text[:200],
                "latency_ms": round(latency * 1000, 2)
            })
            raise HTTPException(status_code=response.status_code, detail=response.text)

        tasks = response.json()

        # Apply client-side filters (label, priority)
        filtered_tasks = tasks

        if label:
            filtered_tasks = [t for t in filtered_tasks if label in t.get("labels", [])]

        if priority:
            filtered_tasks = [t for t in filtered_tasks if t.get("priority") == priority]

        if limit:
            filtered_tasks = filtered_tasks[:limit]

        # Cache the results
        set_cached(cache_key, filtered_tasks)

        logger.info("Tasks fetched successfully", extra={
            "task_count": len(tasks),
            "filtered_count": len(filtered_tasks),
            "latency_ms": round(latency * 1000, 2)
        })
        return filtered_tasks

    except requests.exceptions.RequestException as e:
        logger.error("Network error fetching tasks", extra={"error": str(e)})
        raise HTTPException(status_code=503, detail=f"Todoist API unreachable: {str(e)}")


@app.post("/tasks")
@retry_on_failure(max_retries=3, base_delay=1.0)
def create_task(task: Task, token: str = Depends(verify_token)):
    """
    Create a new task

    Args:
        task: Task details (content is required)

    Returns:
        Created task object
    """
    start_time = time.time()
    logger.info("Creating task", extra={"content": task.content, "priority": task.priority})

    try:
        response = requests.post(
            f"{TODOIST_API_URL}/tasks",
            headers=headers,
            json=task.dict(exclude_none=True),
            timeout=10
        )
        latency = time.time() - start_time

        if response.status_code != 200:
            logger.error("Failed to create task", extra={
                "status_code": response.status_code,
                "response": response.text[:200],
                "latency_ms": round(latency * 1000, 2)
            })
            raise HTTPException(status_code=response.status_code, detail=response.text)

        created_task = response.json()
        logger.info("Task created successfully", extra={
            "task_id": created_task.get("id"),
            "latency_ms": round(latency * 1000, 2)
        })
        return created_task

    except requests.exceptions.RequestException as e:
        logger.error("Network error creating task", extra={"error": str(e)})
        raise HTTPException(status_code=503, detail=f"Todoist API unreachable: {str(e)}")


@app.get("/tasks/{task_id}")
@retry_on_failure(max_retries=3, base_delay=1.0)
def get_task(task_id: str, token: str = Depends(verify_token)):
    """Get a specific task by ID"""
    start_time = time.time()
    logger.info("Fetching task", extra={"task_id": task_id})

    try:
        response = requests.get(f"{TODOIST_API_URL}/tasks/{task_id}", headers=headers, timeout=10)
        latency = time.time() - start_time

        if response.status_code != 200:
            logger.error("Failed to fetch task", extra={
                "task_id": task_id,
                "status_code": response.status_code,
                "latency_ms": round(latency * 1000, 2)
            })
            raise HTTPException(status_code=response.status_code, detail=response.text)

        logger.info("Task fetched successfully", extra={
            "task_id": task_id,
            "latency_ms": round(latency * 1000, 2)
        })
        return response.json()

    except requests.exceptions.RequestException as e:
        logger.error("Network error fetching task", extra={"task_id": task_id, "error": str(e)})
        raise HTTPException(status_code=503, detail=f"Todoist API unreachable: {str(e)}")


@app.post("/tasks/{task_id}/close")
@retry_on_failure(max_retries=3, base_delay=1.0)
def complete_task(task_id: str, token: str = Depends(verify_token)):
    """Mark a task as completed"""
    start_time = time.time()
    logger.info("Completing task", extra={"task_id": task_id})

    try:
        response = requests.post(f"{TODOIST_API_URL}/tasks/{task_id}/close", headers=headers, timeout=10)
        latency = time.time() - start_time

        if response.status_code != 204:
            logger.error("Failed to complete task", extra={
                "task_id": task_id,
                "status_code": response.status_code,
                "latency_ms": round(latency * 1000, 2)
            })
            raise HTTPException(status_code=response.status_code, detail=response.text)

        logger.info("Task completed successfully", extra={
            "task_id": task_id,
            "latency_ms": round(latency * 1000, 2)
        })
        return {"status": "success", "message": f"Task {task_id} completed"}

    except requests.exceptions.RequestException as e:
        logger.error("Network error completing task", extra={"task_id": task_id, "error": str(e)})
        raise HTTPException(status_code=503, detail=f"Todoist API unreachable: {str(e)}")


@app.post("/tasks/{task_id}/reopen")
@retry_on_failure(max_retries=3, base_delay=1.0)
def reopen_task(task_id: str, token: str = Depends(verify_token)):
    """Reopen a completed task"""
    start_time = time.time()
    logger.info("Reopening task", extra={"task_id": task_id})

    try:
        response = requests.post(f"{TODOIST_API_URL}/tasks/{task_id}/reopen", headers=headers, timeout=10)
        latency = time.time() - start_time

        if response.status_code != 204:
            logger.error("Failed to reopen task", extra={
                "task_id": task_id,
                "status_code": response.status_code,
                "latency_ms": round(latency * 1000, 2)
            })
            raise HTTPException(status_code=response.status_code, detail=response.text)

        logger.info("Task reopened successfully", extra={
            "task_id": task_id,
            "latency_ms": round(latency * 1000, 2)
        })
        return {"status": "success", "message": f"Task {task_id} reopened"}

    except requests.exceptions.RequestException as e:
        logger.error("Network error reopening task", extra={"task_id": task_id, "error": str(e)})
        raise HTTPException(status_code=503, detail=f"Todoist API unreachable: {str(e)}")


@app.post("/tasks/{task_id}")
@retry_on_failure(max_retries=3, base_delay=1.0)
def update_task(task_id: str, updates: TaskUpdate, token: str = Depends(verify_token)):
    """Update an existing task"""
    start_time = time.time()
    logger.info("Updating task", extra={"task_id": task_id, "updates": updates.dict(exclude_none=True)})

    try:
        response = requests.post(
            f"{TODOIST_API_URL}/tasks/{task_id}",
            headers=headers,
            json=updates.dict(exclude_none=True),
            timeout=10
        )
        latency = time.time() - start_time

        if response.status_code != 200:
            logger.error("Failed to update task", extra={
                "task_id": task_id,
                "status_code": response.status_code,
                "latency_ms": round(latency * 1000, 2)
            })
            raise HTTPException(status_code=response.status_code, detail=response.text)

        logger.info("Task updated successfully", extra={
            "task_id": task_id,
            "latency_ms": round(latency * 1000, 2)
        })
        return response.json()

    except requests.exceptions.RequestException as e:
        logger.error("Network error updating task", extra={"task_id": task_id, "error": str(e)})
        raise HTTPException(status_code=503, detail=f"Todoist API unreachable: {str(e)}")


@app.delete("/tasks/{task_id}")
@retry_on_failure(max_retries=3, base_delay=1.0)
def delete_task(task_id: str, token: str = Depends(verify_token)):
    """Delete a task"""
    start_time = time.time()
    logger.info("Deleting task", extra={"task_id": task_id})

    try:
        response = requests.delete(f"{TODOIST_API_URL}/tasks/{task_id}", headers=headers, timeout=10)
        latency = time.time() - start_time

        if response.status_code != 204:
            logger.error("Failed to delete task", extra={
                "task_id": task_id,
                "status_code": response.status_code,
                "latency_ms": round(latency * 1000, 2)
            })
            raise HTTPException(status_code=response.status_code, detail=response.text)

        logger.info("Task deleted successfully", extra={
            "task_id": task_id,
            "latency_ms": round(latency * 1000, 2)
        })
        return {"status": "success", "message": f"Task {task_id} deleted"}

    except requests.exceptions.RequestException as e:
        logger.error("Network error deleting task", extra={"task_id": task_id, "error": str(e)})
        raise HTTPException(status_code=503, detail=f"Todoist API unreachable: {str(e)}")


@app.get("/projects")
@retry_on_failure(max_retries=3, base_delay=1.0)
def list_projects(token: str = Depends(verify_token)):
    """List all projects"""
    start_time = time.time()
    logger.info("Fetching projects")

    try:
        response = requests.get(f"{TODOIST_API_URL}/projects", headers=headers, timeout=10)
        latency = time.time() - start_time

        if response.status_code != 200:
            logger.error("Failed to fetch projects", extra={
                "status_code": response.status_code,
                "latency_ms": round(latency * 1000, 2)
            })
            raise HTTPException(status_code=response.status_code, detail=response.text)

        projects = response.json()
        logger.info("Projects fetched successfully", extra={
            "project_count": len(projects),
            "latency_ms": round(latency * 1000, 2)
        })
        return projects

    except requests.exceptions.RequestException as e:
        logger.error("Network error fetching projects", extra={"error": str(e)})
        raise HTTPException(status_code=503, detail=f"Todoist API unreachable: {str(e)}")
