"""
Unit tests for Todoist Tool Server

Tests cover:
- Health check endpoints (basic and enhanced)
- Task CRUD operations
- Enhanced filtering (priority, label, limit)
- Caching behavior
- Quick add endpoint
- Error handling
- Retry logic
- Network failure scenarios
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
import requests
import sys
import os
import time

# Add parent directory to path to import main
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Mock environment variables before importing main
os.environ["TODOIST_API_KEY"] = "test-api-key"

from main import app, retry_on_failure, _memory_cache, get_cache_key, get_cached, set_cached


client = TestClient(app)


class TestHealthEndpoint:
    """Tests for health check endpoint"""

    def test_health_check_returns_healthy(self):
        """Health endpoint should return status: healthy"""
        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy", "service": "todoist-tool"}

    @patch("main.requests.get")
    def test_enhanced_health_check_success(self, mock_get):
        """Enhanced health check should return detailed status"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "todoist-tool"
        assert "todoist_api" in data
        assert data["todoist_api"]["status"] == "healthy"
        assert "latency_ms" in data["todoist_api"]
        assert "cache" in data
        assert "entries" in data["cache"]
        assert data["cache"]["ttl_seconds"] == 60
        assert "timestamp" in data

    @patch("main.requests.get")
    def test_enhanced_health_check_degraded(self, mock_get):
        """Enhanced health check should detect degraded API"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["todoist_api"]["status"] == "degraded"

    @patch("main.requests.get")
    def test_enhanced_health_check_api_unreachable(self, mock_get):
        """Enhanced health check should handle unreachable API"""
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")

        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["todoist_api"]["status"] == "unhealthy"
        assert data["todoist_api"]["latency_ms"] is None


class TestListTasks:
    """Tests for GET /tasks endpoint"""

    @patch("main.requests.get")
    def test_list_tasks_success(self, mock_get):
        """List tasks should return tasks from API"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": "123", "content": "Test task", "priority": 1}
        ]
        mock_get.return_value = mock_response

        response = client.get("/tasks")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["content"] == "Test task"

    @patch("main.requests.get")
    def test_list_tasks_with_filter(self, mock_get):
        """List tasks should pass filter to API"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        client.get("/tasks?filter=today")

        # Verify filter was passed in params
        call_args = mock_get.call_args
        assert call_args[1]["params"]["filter"] == "today"

    @patch("main.requests.get")
    @patch("main.time.sleep")  # Mock sleep to speed up test
    def test_list_tasks_api_error(self, mock_sleep, mock_get):
        """List tasks should handle API errors with retry"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_get.return_value = mock_response

        response = client.get("/tasks?use_cache=false")

        # Should retry 3 times (max_retries=3) and still fail
        assert response.status_code == 500
        assert mock_get.call_count == 4  # 1 initial + 3 retries

    @patch("main.requests.get")
    def test_list_tasks_with_priority_filter(self, mock_get):
        """List tasks should filter by priority"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": "1", "content": "Urgent task", "priority": 4},
            {"id": "2", "content": "High task", "priority": 3},
            {"id": "3", "content": "Normal task", "priority": 1}
        ]
        mock_get.return_value = mock_response

        response = client.get("/tasks?priority=4")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["priority"] == 4
        assert data[0]["content"] == "Urgent task"

    @patch("main.requests.get")
    def test_list_tasks_with_label_filter(self, mock_get):
        """List tasks should filter by label"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": "1", "content": "Work task", "labels": ["work", "urgent"]},
            {"id": "2", "content": "Home task", "labels": ["home"]},
            {"id": "3", "content": "Work task 2", "labels": ["work"]}
        ]
        mock_get.return_value = mock_response

        response = client.get("/tasks?label=work")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all("work" in task["labels"] for task in data)

    @patch("main.requests.get")
    def test_list_tasks_with_limit(self, mock_get):
        """List tasks should respect limit parameter"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": str(i), "content": f"Task {i}"} for i in range(1, 101)
        ]
        mock_get.return_value = mock_response

        response = client.get("/tasks?limit=10")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 10

    @patch("main.requests.get")
    def test_list_tasks_with_combined_filters(self, mock_get):
        """List tasks should handle combined filters"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": "1", "content": "Urgent work", "priority": 4, "labels": ["work"]},
            {"id": "2", "content": "High work", "priority": 3, "labels": ["work"]},
            {"id": "3", "content": "Urgent home", "priority": 4, "labels": ["home"]}
        ]
        mock_get.return_value = mock_response

        response = client.get("/tasks?priority=4&label=work&limit=5")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["priority"] == 4
        assert "work" in data[0]["labels"]


class TestCreateTask:
    """Tests for POST /tasks endpoint"""

    @patch("main.requests.post")
    def test_create_task_success(self, mock_post):
        """Create task should return created task"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "456",
            "content": "New task",
            "priority": 2
        }
        mock_post.return_value = mock_response

        task_data = {
            "content": "New task",
            "priority": 2
        }
        response = client.post("/tasks", json=task_data)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "456"
        assert data["content"] == "New task"

    @patch("main.requests.post")
    def test_create_task_with_all_fields(self, mock_post):
        """Create task should handle all optional fields"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "789", "content": "Full task"}
        mock_post.return_value = mock_response

        task_data = {
            "content": "Full task",
            "description": "Task description",
            "project_id": "proj-1",
            "due_string": "tomorrow",
            "priority": 3,
            "labels": ["work", "urgent"]
        }
        response = client.post("/tasks", json=task_data)

        assert response.status_code == 200


class TestGetTask:
    """Tests for GET /tasks/{task_id} endpoint"""

    @patch("main.requests.get")
    def test_get_task_success(self, mock_get):
        """Get task should return specific task"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "123",
            "content": "Specific task"
        }
        mock_get.return_value = mock_response

        response = client.get("/tasks/123")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "123"

    @patch("main.requests.get")
    def test_get_task_not_found(self, mock_get):
        """Get task should handle 404"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Task not found"
        mock_get.return_value = mock_response

        response = client.get("/tasks/nonexistent")

        assert response.status_code == 404


class TestCompleteTask:
    """Tests for POST /tasks/{task_id}/close endpoint"""

    @patch("main.requests.post")
    def test_complete_task_success(self, mock_post):
        """Complete task should return success"""
        mock_response = Mock()
        mock_response.status_code = 204
        mock_post.return_value = mock_response

        response = client.post("/tasks/123/close")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"


class TestDeleteTask:
    """Tests for DELETE /tasks/{task_id} endpoint"""

    @patch("main.requests.delete")
    def test_delete_task_success(self, mock_delete):
        """Delete task should return success"""
        mock_response = Mock()
        mock_response.status_code = 204
        mock_delete.return_value = mock_response

        response = client.delete("/tasks/123")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"


class TestListProjects:
    """Tests for GET /projects endpoint"""

    @patch("main.requests.get")
    def test_list_projects_success(self, mock_get):
        """List projects should return projects"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": "proj-1", "name": "Work"},
            {"id": "proj-2", "name": "Personal"}
        ]
        mock_get.return_value = mock_response

        response = client.get("/projects")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "Work"


class TestRetryLogic:
    """Tests for retry decorator"""

    def test_retry_on_network_error(self):
        """Retry should work on network errors"""
        attempt_count = {"count": 0}

        @retry_on_failure(max_retries=2, base_delay=0.01)
        def failing_function():
            attempt_count["count"] += 1
            if attempt_count["count"] < 3:
                raise requests.exceptions.ConnectionError("Network error")
            return "success"

        result = failing_function()
        assert result == "success"
        assert attempt_count["count"] == 3

    def test_retry_exhaustion(self):
        """Retry should raise after max attempts"""
        @retry_on_failure(max_retries=2, base_delay=0.01)
        def always_failing():
            raise requests.exceptions.Timeout("Timeout")

        with pytest.raises(requests.exceptions.Timeout):
            always_failing()

    def test_no_retry_on_client_error(self):
        """Should not retry on 4xx errors"""
        from fastapi import HTTPException
        attempt_count = {"count": 0}

        @retry_on_failure(max_retries=3, base_delay=0.01)
        def client_error():
            attempt_count["count"] += 1
            raise HTTPException(status_code=404, detail="Not found")

        with pytest.raises(HTTPException) as exc:
            client_error()

        assert exc.value.status_code == 404
        assert attempt_count["count"] == 1  # No retries

    def test_retry_on_server_error(self):
        """Should retry on 5xx errors"""
        from fastapi import HTTPException
        attempt_count = {"count": 0}

        @retry_on_failure(max_retries=2, base_delay=0.01)
        def server_error():
            attempt_count["count"] += 1
            if attempt_count["count"] < 3:
                raise HTTPException(status_code=500, detail="Server error")
            return "recovered"

        result = server_error()
        assert result == "recovered"
        assert attempt_count["count"] == 3


class TestErrorHandling:
    """Tests for error handling"""

    @patch("main.requests.get")
    @patch("main.time.sleep")  # Mock sleep to speed up test
    def test_network_timeout(self, mock_sleep, mock_get):
        """Should handle network timeout gracefully with retry"""
        mock_get.side_effect = requests.exceptions.Timeout("Timeout")

        response = client.get("/tasks?use_cache=false")

        assert response.status_code == 503
        assert "unreachable" in response.json()["detail"].lower()
        # Should retry 3 times before giving up
        assert mock_get.call_count == 4  # 1 initial + 3 retries

    @patch("main.requests.post")
    def test_connection_error(self, mock_post):
        """Should handle connection errors"""
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")

        task_data = {"content": "Test"}
        response = client.post("/tasks", json=task_data)

        assert response.status_code == 503


class TestCaching:
    """Tests for caching functionality"""

    def setup_method(self):
        """Clear cache before each test"""
        _memory_cache.clear()

    def test_cache_key_generation(self):
        """Cache keys should be consistent for same parameters"""
        key1 = get_cache_key("tasks", priority=4, label="work", limit=10)
        key2 = get_cache_key("tasks", priority=4, label="work", limit=10)
        key3 = get_cache_key("tasks", priority=3, label="work", limit=10)

        assert key1 == key2
        assert key1 != key3

    def test_cache_set_and_get(self):
        """Should be able to set and get cached values"""
        test_data = [{"id": "1", "content": "Test task"}]
        cache_key = "test_key"

        set_cached(cache_key, test_data, ttl=60)
        cached_data = get_cached(cache_key)

        assert cached_data == test_data

    def test_cache_expiration(self):
        """Cache should expire after TTL"""
        test_data = [{"id": "1", "content": "Test task"}]
        cache_key = "test_key"

        set_cached(cache_key, test_data, ttl=0.1)  # 100ms TTL
        time.sleep(0.2)  # Wait for expiration

        cached_data = get_cached(cache_key)
        assert cached_data is None

    def test_cache_miss(self):
        """Should return None for cache miss"""
        cached_data = get_cached("nonexistent_key")
        assert cached_data is None

    @patch("main.requests.get")
    def test_list_tasks_uses_cache(self, mock_get):
        """Second request should use cache"""
        _memory_cache.clear()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": "1", "content": "Cached task"}
        ]
        mock_get.return_value = mock_response

        # First request - should hit API
        response1 = client.get("/tasks?priority=4")
        assert response1.status_code == 200
        assert mock_get.call_count == 1

        # Second request - should use cache
        response2 = client.get("/tasks?priority=4")
        assert response2.status_code == 200
        assert response2.json() == response1.json()
        assert mock_get.call_count == 1  # Still 1, didn't call API again

    @patch("main.requests.get")
    def test_list_tasks_cache_disabled(self, mock_get):
        """Should bypass cache when use_cache=false"""
        _memory_cache.clear()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"id": "1", "content": "Task"}]
        mock_get.return_value = mock_response

        # First request with cache disabled
        client.get("/tasks?use_cache=false")
        assert mock_get.call_count == 1

        # Second request with cache disabled
        client.get("/tasks?use_cache=false")
        assert mock_get.call_count == 2  # Called API again

    @patch("main.requests.get")
    def test_cache_per_query_parameters(self, mock_get):
        """Different query parameters should use different cache entries"""
        _memory_cache.clear()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"id": "1"}]
        mock_get.return_value = mock_response

        # Request with priority=4
        client.get("/tasks?priority=4")
        assert mock_get.call_count == 1

        # Request with priority=3 (different cache key)
        client.get("/tasks?priority=3")
        assert mock_get.call_count == 2

        # Request with priority=4 again (should use cache)
        client.get("/tasks?priority=4")
        assert mock_get.call_count == 2  # Didn't increase