"""
Integration tests for LLM function calling with GTD tool servers

Tests that actual LLMs can successfully call Todoist and CalDAV tools
via function calling (tools/agentic capabilities).

Prerequisites:
- Tool servers running (todoist-tool, caldav-tool)
- OPENAI_API_KEY in environment (for real LLM tests)
- Optional: TOOL_API_KEY if authentication enabled

Run with: pytest tests/integration/test_llm_function_calling.py -v
"""

import os
import pytest
import requests
import json
from openai import OpenAI
from datetime import datetime


# Skip all tests if OPENAI_API_KEY not set
pytestmark = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set - skipping LLM function calling tests"
)


@pytest.fixture
def openai_client():
    """OpenAI client for function calling tests"""
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


@pytest.fixture
def tool_api_key():
    """API key for tool authentication (optional)"""
    return os.getenv("TOOL_API_KEY")


@pytest.fixture
def todoist_tool_schema():
    """
    Todoist tool schema in OpenAI function calling format
    Extracted from http://localhost:8007/openapi.json
    """
    return {
        "type": "function",
        "function": {
            "name": "todoist_create_task",
            "description": "Create a new task in Todoist",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Task content/title"
                    },
                    "description": {
                        "type": "string",
                        "description": "Task description (optional)"
                    },
                    "due_string": {
                        "type": "string",
                        "description": "Due date in natural language (e.g., 'tomorrow', 'next Monday')"
                    },
                    "priority": {
                        "type": "integer",
                        "description": "Priority: 1=normal, 2=high, 3=very high, 4=urgent",
                        "enum": [1, 2, 3, 4]
                    }
                },
                "required": ["content"]
            }
        }
    }


@pytest.fixture
def caldav_tool_schema():
    """CalDAV tool schema for creating calendar events"""
    return {
        "type": "function",
        "function": {
            "name": "caldav_create_event",
            "description": "Create a new calendar event",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "Event title/summary"
                    },
                    "start": {
                        "type": "string",
                        "description": "Start date/time in ISO format (YYYY-MM-DDTHH:MM:SS)"
                    },
                    "end": {
                        "type": "string",
                        "description": "End date/time in ISO format (YYYY-MM-DDTHH:MM:SS)"
                    },
                    "description": {
                        "type": "string",
                        "description": "Event description (optional)"
                    }
                },
                "required": ["summary", "start", "end"]
            }
        }
    }


def execute_todoist_function(function_args: dict, tool_api_key: str = None):
    """
    Execute Todoist function call by calling the actual tool server
    This simulates what the LLM agent would do with the function call result
    """
    headers = {"Content-Type": "application/json"}
    if tool_api_key:
        headers["Authorization"] = f"Bearer {tool_api_key}"

    response = requests.post(
        "http://localhost:8007/tasks",
        json=function_args,
        headers=headers,
        timeout=10
    )

    if response.status_code != 200:
        raise Exception(f"Tool server error: {response.status_code} - {response.text}")

    return response.json()


def execute_caldav_function(function_args: dict, tool_api_key: str = None):
    """Execute CalDAV function call by calling the actual tool server"""
    headers = {"Content-Type": "application/json"}
    if tool_api_key:
        headers["Authorization"] = f"Bearer {tool_api_key}"

    response = requests.post(
        "http://localhost:8008/events",
        json=function_args,
        headers=headers,
        timeout=10
    )

    if response.status_code != 200:
        raise Exception(f"Tool server error: {response.status_code} - {response.text}")

    return response.json()


class TestLLMFunctionCalling:
    """Test that LLMs can successfully use function calling with GTD tools"""

    def test_llm_creates_todoist_task(self, openai_client, todoist_tool_schema, tool_api_key):
        """
        Test that an LLM can use function calling to create a Todoist task

        Flow:
        1. User asks LLM to create a task
        2. LLM decides to call todoist_create_task function
        3. We execute the function call
        4. Verify task was created
        """
        # Step 1: Ask LLM to create a task
        user_message = "Create a task: 'Test LLM function calling' with priority 4 (urgent)"

        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant with access to Todoist task management. Use the tools when needed."
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            tools=[todoist_tool_schema],
            tool_choice="auto"
        )

        # Step 2: Verify LLM decided to call the function
        message = response.choices[0].message
        assert message.tool_calls is not None, "LLM did not use function calling"
        assert len(message.tool_calls) > 0, "No tool calls made"

        tool_call = message.tool_calls[0]
        assert tool_call.function.name == "todoist_create_task"

        # Step 3: Parse function arguments
        function_args = json.loads(tool_call.function.arguments)
        assert "content" in function_args
        assert "Test LLM function calling" in function_args["content"]
        assert function_args.get("priority") == 4

        # Step 4: Execute the function (call actual tool server)
        result = execute_todoist_function(function_args, tool_api_key)

        # Step 5: Verify task was created
        assert "id" in result
        assert "content" in result
        assert "Test LLM function calling" in result["content"]
        assert result.get("priority") == 4

        print(f"✅ LLM successfully created task: {result['id']}")

        # Cleanup: Delete the test task
        headers = {}
        if tool_api_key:
            headers["Authorization"] = f"Bearer {tool_api_key}"
        requests.delete(
            f"http://localhost:8007/tasks/{result['id']}",
            headers=headers
        )

    def test_llm_creates_calendar_event(self, openai_client, caldav_tool_schema, tool_api_key):
        """Test that an LLM can use function calling to create a calendar event"""

        # Step 1: Ask LLM to create an event
        user_message = "Schedule a meeting: 'LLM Function Test Meeting' tomorrow at 2pm for 1 hour"

        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant with access to calendar management. Use the tools when needed. Today is " + datetime.now().strftime("%Y-%m-%d")
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            tools=[caldav_tool_schema],
            tool_choice="auto"
        )

        # Step 2: Verify LLM decided to call the function
        message = response.choices[0].message
        assert message.tool_calls is not None, "LLM did not use function calling"
        assert len(message.tool_calls) > 0, "No tool calls made"

        tool_call = message.tool_calls[0]
        assert tool_call.function.name == "caldav_create_event"

        # Step 3: Parse function arguments
        function_args = json.loads(tool_call.function.arguments)
        assert "summary" in function_args
        assert "LLM Function Test Meeting" in function_args["summary"]
        assert "start" in function_args
        assert "end" in function_args

        # Step 4: Execute the function (call actual tool server)
        result = execute_caldav_function(function_args, tool_api_key)

        # Step 5: Verify event was created
        assert "uid" in result
        assert "status" in result
        assert result["status"] == "success"

        print(f"✅ LLM successfully created event: {result['uid']}")

        # Cleanup: Delete the test event
        headers = {}
        if tool_api_key:
            headers["Authorization"] = f"Bearer {tool_api_key}"
        requests.delete(
            f"http://localhost:8008/events/{result['uid']}",
            headers=headers
        )

    def test_llm_multi_step_workflow(self, openai_client, todoist_tool_schema, caldav_tool_schema, tool_api_key):
        """
        Test that an LLM can perform a multi-step GTD workflow
        Example: Create a task AND schedule a related calendar event
        """

        user_message = "I need to prepare a presentation. Create a task 'Prepare Q4 presentation' with priority 3, and schedule a 2-hour work session tomorrow at 10am."

        # First LLM call - might create task first
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a GTD assistant with access to task and calendar management. Today is " + datetime.now().strftime("%Y-%m-%d")
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            tools=[todoist_tool_schema, caldav_tool_schema],
            tool_choice="auto"
        )

        message = response.choices[0].message

        # LLM should make at least one tool call
        assert message.tool_calls is not None, "LLM did not use function calling"

        created_task = None
        created_event = None

        # Execute all tool calls
        for tool_call in message.tool_calls:
            function_args = json.loads(tool_call.function.arguments)

            if tool_call.function.name == "todoist_create_task":
                created_task = execute_todoist_function(function_args, tool_api_key)
                assert "Prepare Q4 presentation" in created_task["content"]
                assert created_task.get("priority") == 3
                print(f"✅ Created task: {created_task['id']}")

            elif tool_call.function.name == "caldav_create_event":
                created_event = execute_caldav_function(function_args, tool_api_key)
                print(f"✅ Created event: {created_event['uid']}")

        # Verify at least the task was created (calendar might need second turn)
        assert created_task is not None, "LLM did not create a task"

        # Cleanup
        headers = {}
        if tool_api_key:
            headers["Authorization"] = f"Bearer {tool_api_key}"

        if created_task:
            requests.delete(
                f"http://localhost:8007/tasks/{created_task['id']}",
                headers=headers
            )
        if created_event:
            requests.delete(
                f"http://localhost:8008/events/{created_event['uid']}",
                headers=headers
            )


if __name__ == "__main__":
    # Run with: python -m pytest tests/integration/test_llm_function_calling.py -v -s
    pytest.main([__file__, "-v", "-s"])
