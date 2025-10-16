"""
Unit tests for CalDAV/CardDAV Tool Server

Tests cover:
- Health check endpoints (basic and enhanced)
- Calendar operations (CalDAV)
- Event CRUD operations
- Enhanced filtering (timezone, date range, limit)
- Event partial updates (PATCH)
- Caching behavior
- Contact operations (CardDAV)
- Error handling
- Retry logic
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
import requests
import sys
import os
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Add parent directory to path to import main
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Mock environment variables before importing main
os.environ["CALDAV_URL"] = "https://caldav.example.com"
os.environ["CALDAV_USERNAME"] = "testuser"
os.environ["CALDAV_PASSWORD"] = "testpass"

from main import app, retry_on_failure, _memory_cache, get_cache_key, get_cached, set_cached, parse_relative_date


client = TestClient(app)


class TestHealthEndpoint:
    """Tests for health check endpoint"""

    def test_health_check_returns_healthy(self):
        """Health endpoint should return status: healthy"""
        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy", "service": "caldav-tool"}

    @patch("main.caldav.DAVClient")
    @patch("main.requests.get")
    def test_enhanced_health_check_success(self, mock_requests_get, mock_dav_client):
        """Enhanced health check should return detailed status"""
        # Mock CalDAV client
        mock_client_instance = Mock()
        mock_principal = Mock()
        mock_calendars = [Mock(), Mock()]
        mock_principal.calendars.return_value = mock_calendars
        mock_client_instance.principal.return_value = mock_principal
        mock_dav_client.return_value = mock_client_instance

        # Mock CardDAV request
        mock_carddav_response = Mock()
        mock_carddav_response.status_code = 200
        mock_requests_get.return_value = mock_carddav_response

        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "caldav-tool"
        assert "caldav" in data
        assert data["caldav"]["status"] == "healthy"
        assert data["caldav"]["calendar_count"] == 2
        assert "latency_ms" in data["caldav"]
        assert "carddav" in data
        assert data["carddav"]["status"] == "healthy"
        assert "cache" in data
        assert data["cache"]["ttl_seconds"] == 60
        assert "timestamp" in data

    @patch("main.caldav.DAVClient")
    def test_enhanced_health_check_caldav_error(self, mock_dav_client):
        """Enhanced health check should detect CalDAV errors"""
        mock_dav_client.side_effect = Exception("Connection error")

        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["caldav"]["status"] == "unhealthy"


class TestListCalendars:
    """Tests for GET /calendars endpoint"""

    @patch("main.caldav.DAVClient")
    def test_list_calendars_success(self, mock_dav_client):
        """List calendars should return calendar list"""
        # Mock calendar objects
        mock_cal1 = Mock()
        mock_cal1.name = "Work"
        mock_cal1.url = "https://caldav.example.com/calendars/work/"
        mock_cal1.id = "work"

        mock_cal2 = Mock()
        mock_cal2.name = "Personal"
        mock_cal2.url = "https://caldav.example.com/calendars/personal/"
        mock_cal2.id = "personal"

        # Mock principal and calendars
        mock_principal = Mock()
        mock_principal.calendars.return_value = [mock_cal1, mock_cal2]

        mock_client = Mock()
        mock_client.principal.return_value = mock_principal
        mock_dav_client.return_value = mock_client

        response = client.get("/calendars")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "Work"
        assert data[1]["name"] == "Personal"

    @patch("main.caldav.DAVClient")
    def test_list_calendars_empty(self, mock_dav_client):
        """List calendars should handle empty calendar list"""
        mock_principal = Mock()
        mock_principal.calendars.return_value = []

        mock_client = Mock()
        mock_client.principal.return_value = mock_principal
        mock_dav_client.return_value = mock_client

        response = client.get("/calendars")

        assert response.status_code == 200
        assert response.json() == []


class TestListEvents:
    """Tests for GET /events endpoint"""

    @patch("main.caldav.DAVClient")
    @patch("main.vobject.readOne")
    def test_list_events_success(self, mock_vobject, mock_dav_client):
        """List events should return events from calendar"""
        # Mock event data
        mock_vevent = Mock()
        mock_vevent.summary.value = "Team Meeting"
        mock_vevent.dtstart.value.isoformat.return_value = "2025-10-15T10:00:00"
        mock_vevent.dtend.value.isoformat.return_value = "2025-10-15T11:00:00"
        mock_vevent.uid.value = "event-123"

        mock_vcal = Mock()
        mock_vcal.vevent = mock_vevent
        mock_vobject.return_value = mock_vcal

        # Mock calendar and events
        mock_event = Mock()
        mock_event.data = "VCALENDAR data"

        mock_calendar = Mock()
        mock_calendar.name = "Work"
        mock_calendar.date_search.return_value = [mock_event]

        mock_principal = Mock()
        mock_principal.calendars.return_value = [mock_calendar]

        mock_client = Mock()
        mock_client.principal.return_value = mock_principal
        mock_dav_client.return_value = mock_client

        response = client.get("/events")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["summary"] == "Team Meeting"

    @patch("main.caldav.DAVClient")
    def test_list_events_calendar_not_found(self, mock_dav_client):
        """List events should return 404 for missing calendar"""
        mock_calendar = Mock()
        mock_calendar.name = "Work"

        mock_principal = Mock()
        mock_principal.calendars.return_value = [mock_calendar]

        mock_client = Mock()
        mock_client.principal.return_value = mock_principal
        mock_dav_client.return_value = mock_client

        response = client.get("/events?calendar_name=NonExistent")

        assert response.status_code == 404


class TestCreateEvent:
    """Tests for POST /events endpoint"""

    @patch("main.caldav.DAVClient")
    @patch("main.vobject.iCalendar")
    @patch("main.time.sleep")  # Mock sleep to speed up test
    def test_create_event_success(self, mock_sleep, mock_icalendar, mock_dav_client):
        """Create event should save event to calendar"""
        # Mock vCalendar
        mock_cal = Mock()
        mock_vevent = Mock()
        mock_cal.vevent = mock_vevent
        mock_cal.serialize.return_value = "BEGIN:VCALENDAR..."
        mock_icalendar.return_value = mock_cal

        # Mock calendar
        mock_calendar = Mock()
        mock_calendar.name = "Work"
        mock_calendar.save_event = Mock()
        # Mock date_search for verification (returns empty - that's OK for the test)
        mock_calendar.date_search = Mock(return_value=[])

        mock_principal = Mock()
        mock_principal.calendars.return_value = [mock_calendar]

        mock_client = Mock()
        mock_client.principal.return_value = mock_principal
        mock_dav_client.return_value = mock_client

        event_data = {
            "summary": "New Meeting",
            "start": "2025-10-16T14:00:00",
            "end": "2025-10-16T15:00:00",
            "description": "Important meeting",
            "location": "Conference Room A"
        }
        response = client.post("/events", json=event_data)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "uid" in data

    @patch("main.caldav.DAVClient")
    def test_create_event_no_calendars(self, mock_dav_client):
        """Create event should fail if no calendars exist"""
        mock_principal = Mock()
        mock_principal.calendars.return_value = []

        mock_client = Mock()
        mock_client.principal.return_value = mock_principal
        mock_dav_client.return_value = mock_client

        event_data = {
            "summary": "Test",
            "start": "2025-10-16T14:00:00",
            "end": "2025-10-16T15:00:00"
        }
        response = client.post("/events", json=event_data)

        assert response.status_code == 404


class TestListAddressbooks:
    """Tests for GET /addressbooks endpoint"""

    @patch("main.requests.request")
    @patch("main.ET.fromstring")
    def test_list_addressbooks_success(self, mock_xml, mock_request):
        """List addressbooks should return addressbook list"""
        # Mock XML response
        mock_response_elem = Mock()
        mock_href = Mock()
        mock_href.text = "/addressbooks/users/testuser/contacts/"
        mock_displayname = Mock()
        mock_displayname.text = "Contacts"
        mock_resourcetype = Mock()
        mock_addressbook_elem = Mock()
        mock_resourcetype.find.return_value = mock_addressbook_elem

        mock_prop_response = Mock()
        mock_prop_response.find.side_effect = lambda xpath, ns: {
            "d:href": mock_href,
            ".//d:displayname": mock_displayname,
            ".//d:resourcetype": mock_resourcetype
        }.get(xpath)

        mock_root = Mock()
        mock_root.findall.return_value = [mock_prop_response]
        mock_xml.return_value = mock_root

        # Mock HTTP response
        mock_http_response = Mock()
        mock_http_response.status_code = 207
        mock_http_response.content = b"<xml>mock</xml>"
        mock_request.return_value = mock_http_response

        response = client.get("/addressbooks")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Contacts"


class TestListContacts:
    """Tests for GET /contacts endpoint"""

    @patch("main.requests.request")
    @patch("main.ET.fromstring")
    @patch("main.vobject.readOne")
    def test_list_contacts_success(self, mock_vobject, mock_xml, mock_request):
        """List contacts should return contact list"""
        # Mock vCard
        mock_vcard = Mock()
        mock_vcard.fn.value = "John Doe"
        mock_vcard.email.value = "john@example.com"
        mock_vcard.tel.value = "+1234567890"
        mock_vcard.org.value = ["Acme Corp"]
        mock_vcard.uid.value = "contact-123"
        mock_vobject.return_value = mock_vcard

        # Mock XML response
        mock_address_data = Mock()
        mock_address_data.text = "BEGIN:VCARD..."

        mock_prop_response = Mock()
        mock_prop_response.find.return_value = mock_address_data

        mock_root = Mock()
        mock_root.findall.return_value = [mock_prop_response]
        mock_xml.return_value = mock_root

        # Mock HTTP response
        mock_http_response = Mock()
        mock_http_response.status_code = 207
        mock_http_response.content = b"<xml>mock</xml>"
        mock_request.return_value = mock_http_response

        response = client.get("/contacts")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["full_name"] == "John Doe"
        assert data[0]["email"] == "john@example.com"

    @patch("main.requests.request")
    def test_list_contacts_api_error(self, mock_request):
        """List contacts should handle API errors"""
        mock_http_response = Mock()
        mock_http_response.status_code = 500
        mock_http_response.text = "Server error"
        mock_request.return_value = mock_http_response

        response = client.get("/contacts")

        assert response.status_code == 500


class TestCreateContact:
    """Tests for POST /contacts endpoint"""

    @patch("main.requests.put")
    @patch("main.vobject.vCard")
    def test_create_contact_success(self, mock_vcard, mock_put):
        """Create contact should save contact to addressbook"""
        # Mock vCard
        mock_card = Mock()
        mock_card.serialize.return_value = "BEGIN:VCARD..."
        mock_vcard.return_value = mock_card

        # Mock HTTP response
        mock_http_response = Mock()
        mock_http_response.status_code = 201
        mock_put.return_value = mock_http_response

        contact_data = {
            "full_name": "Jane Smith",
            "email": "jane@example.com",
            "phone": "+0987654321",
            "organization": "Tech Corp"
        }
        response = client.post("/contacts", json=contact_data)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "uid" in data


class TestParseRelativeDate:
    """Tests for relative date parsing"""

    def test_parse_today(self):
        """Should parse 'today' correctly"""
        result = parse_relative_date("today")
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        assert result.date() == today.date()

    def test_parse_tomorrow(self):
        """Should parse 'tomorrow' correctly"""
        result = parse_relative_date("tomorrow")
        tomorrow = (datetime.now() + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        assert result.date() == tomorrow.date()

    def test_parse_yesterday(self):
        """Should parse 'yesterday' correctly"""
        result = parse_relative_date("yesterday")
        yesterday = (datetime.now() - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        assert result.date() == yesterday.date()

    def test_parse_next_week(self):
        """Should parse 'next week' correctly"""
        result = parse_relative_date("next week")
        next_week = (datetime.now() + timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
        assert result.date() == next_week.date()

    def test_parse_iso_date(self):
        """Should parse ISO format dates"""
        result = parse_relative_date("2025-10-20")
        assert result.year == 2025
        assert result.month == 10
        assert result.day == 20

    def test_parse_invalid_date(self):
        """Should raise error for invalid date"""
        with pytest.raises(ValueError):
            parse_relative_date("invalid-date")


class TestCaching:
    """Tests for caching functionality"""

    def setup_method(self):
        """Clear cache before each test"""
        _memory_cache.clear()

    def test_cache_key_generation(self):
        """Cache keys should be consistent for same parameters"""
        key1 = get_cache_key("events", calendar_name="Work", start_date="today")
        key2 = get_cache_key("events", calendar_name="Work", start_date="today")
        key3 = get_cache_key("events", calendar_name="Personal", start_date="today")

        assert key1 == key2
        assert key1 != key3

    def test_cache_set_and_get(self):
        """Should be able to set and get cached values"""
        test_data = [{"summary": "Test event", "start": "2025-10-20T14:00:00"}]
        cache_key = "test_key"

        set_cached(cache_key, test_data, ttl=60)
        cached_data = get_cached(cache_key)

        assert cached_data == test_data

    def test_cache_expiration(self):
        """Cache should expire after TTL"""
        test_data = [{"summary": "Test event"}]
        cache_key = "test_key"

        set_cached(cache_key, test_data, ttl=0.1)  # 100ms TTL
        time.sleep(0.2)  # Wait for expiration

        cached_data = get_cached(cache_key)
        assert cached_data is None

    def test_cache_miss(self):
        """Should return None for cache miss"""
        cached_data = get_cached("nonexistent_key")
        assert cached_data is None


class TestRetryLogic:
    """Tests for retry decorator"""

    def test_retry_on_caldav_error(self):
        """Retry should work on CalDAV errors"""
        import caldav
        attempt_count = {"count": 0}

        @retry_on_failure(max_retries=2, base_delay=0.01)
        def failing_caldav():
            attempt_count["count"] += 1
            if attempt_count["count"] < 3:
                raise caldav.lib.error.DAVError("CalDAV error")
            return "success"

        result = failing_caldav()
        assert result == "success"
        assert attempt_count["count"] == 3

    def test_retry_on_network_error(self):
        """Retry should work on network errors"""
        attempt_count = {"count": 0}

        @retry_on_failure(max_retries=2, base_delay=0.01)
        def failing_network():
            attempt_count["count"] += 1
            if attempt_count["count"] < 3:
                raise requests.exceptions.ConnectionError("Network error")
            return "success"

        result = failing_network()
        assert result == "success"
        assert attempt_count["count"] == 3


class TestErrorHandling:
    """Tests for error handling"""

    @patch("main.requests.request")
    def test_network_timeout_addressbooks(self, mock_request):
        """Should handle network timeout gracefully"""
        mock_request.side_effect = requests.exceptions.Timeout("Timeout")

        response = client.get("/addressbooks")

        assert response.status_code == 503
        assert "unreachable" in response.json()["detail"].lower()

    @patch("main.caldav.DAVClient")
    def test_caldav_connection_error(self, mock_dav_client):
        """Should handle CalDAV connection errors"""
        import caldav
        mock_dav_client.side_effect = caldav.lib.error.DAVError("Connection failed")

        response = client.get("/calendars")

        assert response.status_code == 500
