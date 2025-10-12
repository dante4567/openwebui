"""
Todoist Tool Server for OpenWebUI
Provides task management capabilities via Todoist API
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import os
from typing import Optional, List

app = FastAPI(
    title="Todoist Tool",
    description="Task management via Todoist API",
    version="1.0.0"
)

TODOIST_API_KEY = os.getenv("TODOIST_API_KEY")
TODOIST_API_URL = "https://api.todoist.com/rest/v2"

if not TODOIST_API_KEY:
    raise ValueError("TODOIST_API_KEY environment variable is required")

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
    return {"status": "healthy", "service": "todoist-tool"}


@app.get("/tasks")
def list_tasks(project_id: Optional[str] = None, filter: Optional[str] = None):
    """
    List all tasks

    Args:
        project_id: Filter by project ID
        filter: Todoist filter string (e.g., "today", "overdue", "@work")
    """
    params = {}
    if project_id:
        params["project_id"] = project_id
    if filter:
        params["filter"] = filter

    response = requests.get(f"{TODOIST_API_URL}/tasks", headers=headers, params=params)

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    return response.json()


@app.post("/tasks")
def create_task(task: Task):
    """
    Create a new task

    Args:
        task: Task details (content is required)

    Returns:
        Created task object
    """
    response = requests.post(
        f"{TODOIST_API_URL}/tasks",
        headers=headers,
        json=task.dict(exclude_none=True)
    )

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    return response.json()


@app.get("/tasks/{task_id}")
def get_task(task_id: str):
    """Get a specific task by ID"""
    response = requests.get(f"{TODOIST_API_URL}/tasks/{task_id}", headers=headers)

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    return response.json()


@app.post("/tasks/{task_id}/close")
def complete_task(task_id: str):
    """Mark a task as completed"""
    response = requests.post(f"{TODOIST_API_URL}/tasks/{task_id}/close", headers=headers)

    if response.status_code != 204:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    return {"status": "success", "message": f"Task {task_id} completed"}


@app.post("/tasks/{task_id}/reopen")
def reopen_task(task_id: str):
    """Reopen a completed task"""
    response = requests.post(f"{TODOIST_API_URL}/tasks/{task_id}/reopen", headers=headers)

    if response.status_code != 204:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    return {"status": "success", "message": f"Task {task_id} reopened"}


@app.post("/tasks/{task_id}")
def update_task(task_id: str, updates: TaskUpdate):
    """Update an existing task"""
    response = requests.post(
        f"{TODOIST_API_URL}/tasks/{task_id}",
        headers=headers,
        json=updates.dict(exclude_none=True)
    )

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    return response.json()


@app.delete("/tasks/{task_id}")
def delete_task(task_id: str):
    """Delete a task"""
    response = requests.delete(f"{TODOIST_API_URL}/tasks/{task_id}", headers=headers)

    if response.status_code != 204:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    return {"status": "success", "message": f"Task {task_id} deleted"}


@app.get("/projects")
def list_projects():
    """List all projects"""
    response = requests.get(f"{TODOIST_API_URL}/projects", headers=headers)

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    return response.json()
