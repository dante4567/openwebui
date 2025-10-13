"""
Todoist Tool Server for OpenWebUI
Provides task management capabilities via Todoist API
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import os
import sys
import logging
from typing import Optional, List
from datetime import datetime
import time
from functools import wraps

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


@app.get("/tasks")
@retry_on_failure(max_retries=3, base_delay=1.0)
def list_tasks(project_id: Optional[str] = None, filter: Optional[str] = None):
    """
    List all tasks

    Args:
        project_id: Filter by project ID
        filter: Todoist filter string (e.g., "today", "overdue", "@work")
    """
    start_time = time.time()
    params = {}
    if project_id:
        params["project_id"] = project_id
    if filter:
        params["filter"] = filter

    logger.info("Fetching tasks", extra={"project_id": project_id, "filter": filter})

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
        logger.info("Tasks fetched successfully", extra={
            "task_count": len(tasks),
            "latency_ms": round(latency * 1000, 2)
        })
        return tasks

    except requests.exceptions.RequestException as e:
        logger.error("Network error fetching tasks", extra={"error": str(e)})
        raise HTTPException(status_code=503, detail=f"Todoist API unreachable: {str(e)}")


@app.post("/tasks")
@retry_on_failure(max_retries=3, base_delay=1.0)
def create_task(task: Task):
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
def get_task(task_id: str):
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
def complete_task(task_id: str):
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
def reopen_task(task_id: str):
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
def update_task(task_id: str, updates: TaskUpdate):
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
def delete_task(task_id: str):
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
def list_projects():
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
