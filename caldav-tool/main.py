"""
CalDAV/CardDAV Tool Server for OpenWebUI
Provides calendar and contact management via CalDAV/CardDAV protocols
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import caldav
from caldav.elements import dav
import vobject
import requests
from requests.auth import HTTPBasicAuth
import os
import sys
import logging
from typing import Optional, List
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
import time

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("caldav-tool")

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


class Event(BaseModel):
    summary: str
    start: str  # ISO 8601 format
    end: str  # ISO 8601 format
    description: Optional[str] = None
    location: Optional[str] = None


class Contact(BaseModel):
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    organization: Optional[str] = None


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


# ============================================================================
# CALENDAR OPERATIONS (CalDAV)
# ============================================================================

@app.get("/calendars")
def list_calendars():
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


@app.get("/events")
def list_events(
    calendar_name: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    days_ahead: int = 30
):
    """
    List events from calendar

    Args:
        calendar_name: Specific calendar name (default: first calendar)
        start_date: Start date in ISO format (default: today)
        end_date: End date in ISO format (default: 30 days from now)
        days_ahead: Number of days to look ahead (if end_date not specified)
    """
    start_time = time.time()
    logger.info("Fetching events", extra={
        "calendar_name": calendar_name,
        "start_date": start_date,
        "end_date": end_date,
        "days_ahead": days_ahead
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

        # Date range
        start = datetime.fromisoformat(start_date) if start_date else datetime.now()
        end = datetime.fromisoformat(end_date) if end_date else start + timedelta(days=days_ahead)

        # Fetch events
        events = calendar.date_search(start=start, end=end)

        results = []
        for event in events:
            try:
                vcal = vobject.readOne(event.data)
                vevent = vcal.vevent
                results.append({
                    "summary": str(vevent.summary.value) if hasattr(vevent, 'summary') else "No title",
                    "start": vevent.dtstart.value.isoformat() if hasattr(vevent, 'dtstart') else None,
                    "end": vevent.dtend.value.isoformat() if hasattr(vevent, 'dtend') else None,
                    "description": str(vevent.description.value) if hasattr(vevent, 'description') else None,
                    "location": str(vevent.location.value) if hasattr(vevent, 'location') else None,
                    "uid": str(vevent.uid.value) if hasattr(vevent, 'uid') else None
                })
            except Exception:
                continue

        latency = time.time() - start_time
        logger.info("Events fetched successfully", extra={
            "event_count": len(results),
            "calendar": calendar.name,
            "latency_ms": round(latency * 1000, 2)
        })
        return results

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to fetch events", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"CalDAV error: {str(e)}")


@app.post("/events")
def create_event(event: Event, calendar_name: Optional[str] = None):
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

        # Create vCalendar object
        cal = vobject.iCalendar()
        cal.add('vevent')
        cal.vevent.add('summary').value = event.summary
        cal.vevent.add('dtstart').value = datetime.fromisoformat(event.start)
        cal.vevent.add('dtend').value = datetime.fromisoformat(event.end)

        if event.description:
            cal.vevent.add('description').value = event.description
        if event.location:
            cal.vevent.add('location').value = event.location

        # Generate UID
        import uuid
        uid = str(uuid.uuid4())
        cal.vevent.add('uid').value = uid

        # Save to calendar
        calendar.save_event(cal.serialize())

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


# ============================================================================
# CONTACT OPERATIONS (CardDAV)
# ============================================================================

@app.get("/addressbooks")
def list_addressbooks():
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
def list_contacts(addressbook_name: Optional[str] = "contacts"):
    """
    List contacts from addressbook

    Args:
        addressbook_name: Specific addressbook (default: "contacts")
    """
    start_time = time.time()
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
def create_contact(contact: Contact, addressbook_name: Optional[str] = "contacts"):
    """
    Create a new contact

    Args:
        contact: Contact details
        addressbook_name: Target addressbook (default: "contacts")
    """
    start_time = time.time()
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
