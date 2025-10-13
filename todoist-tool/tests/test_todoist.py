"""
Unit tests for Todoist Tool Server

Tests cover:
- Health check endpoint
- Task CRUD operations
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

# Add parent directory to path to import main
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Mock environment variables before importing main
os.environ["TODOIST_API_KEY"] = "test-api-key"

from main import app, retry_on_failure


client = TestClient(app)


class TestHealthEndpoint:
    """Tests for health check endpoint"""

    def test_health_check_returns_healthy(self):
        """Health endpoint should return status: healthy"""
        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy", "service": "todoist-tool"}


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
    def test_list_tasks_api_error(self, mock_get):
        """List tasks should handle API errors"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_get.return_value = mock_response

        response = client.get("/tasks")

        assert response.status_code == 500


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
    def test_network_timeout(self, mock_get):
        """Should handle network timeout gracefully"""
        mock_get.side_effect = requests.exceptions.Timeout("Timeout")

        response = client.get("/tasks")

        assert response.status_code == 503
        assert "unreachable" in response.json()["detail"].lower()

    @patch("main.requests.post")
    def test_connection_error(self, mock_post):
        """Should handle connection errors"""
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")

        task_data = {"content": "Test"}
        response = client.post("/tasks", json=task_data)

        assert response.status_code == 503
