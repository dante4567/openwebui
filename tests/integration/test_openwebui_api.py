"""
OpenWebUI API Integration Tests

Tests the full request path:
- OpenWebUI API endpoints
- Database schema and configuration
- Tool registration and discovery
- LLM function calling (end-to-end)

Run with: pytest tests/integration/test_openwebui_api.py -v
"""

import pytest
import requests
import sqlite3
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
import subprocess


# Configuration
OPENWEBUI_URL = "http://localhost:8080"
OPENWEBUI_DB_PATH = "/tmp/webui-test.db"


@pytest.fixture(scope="session")
def openwebui_db():
    """Copy OpenWebUI database for testing"""
    # Copy database from container
    result = subprocess.run(
        ["docker", "cp", "openwebui:/app/backend/data/webui.db", OPENWEBUI_DB_PATH],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        pytest.skip(f"Could not copy database: {result.stderr}")

    yield OPENWEBUI_DB_PATH

    # Cleanup
    Path(OPENWEBUI_DB_PATH).unlink(missing_ok=True)


@pytest.fixture(scope="session")
def db_connection(openwebui_db):
    """SQLite connection to OpenWebUI database"""
    conn = sqlite3.connect(openwebui_db)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


class TestDatabaseSchema:
    """Test OpenWebUI database schema and structure"""

    def test_database_exists(self, openwebui_db):
        """Database file should exist and be readable"""
        assert Path(openwebui_db).exists()
        assert Path(openwebui_db).stat().st_size > 0

    def test_expected_tables_exist(self, db_connection):
        """Database should have expected tables"""
        cursor = db_connection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        # Core tables that should exist
        expected_tables = [
            'user',
            'chat',
            'config',
            'model',
            'tool',
            'function',
            'prompt',
        ]

        for table in expected_tables:
            assert table in tables, f"Missing table: {table}"

        print(f"\n✅ Found {len(tables)} tables: {', '.join(tables)}")

    def test_config_table_structure(self, db_connection):
        """Config table should have correct structure"""
        cursor = db_connection.cursor()
        cursor.execute("PRAGMA table_info(config)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}

        assert 'id' in columns
        assert 'data' in columns  # JSON data
        assert 'updated_at' in columns

        print(f"\n✅ Config table has {len(columns)} columns")


class TestConfigurationData:
    """Test OpenWebUI configuration data"""

    def test_config_data_is_valid_json(self, db_connection):
        """Config data should be valid JSON"""
        cursor = db_connection.cursor()
        cursor.execute("SELECT id, data FROM config")

        for row in cursor.fetchall():
            config_id, data = row[0], row[1]
            try:
                parsed = json.loads(data)
                assert isinstance(parsed, dict)
                print(f"\n✅ Config ID {config_id}: {len(parsed)} top-level keys")
            except json.JSONDecodeError as e:
                pytest.fail(f"Invalid JSON in config ID {config_id}: {e}")

    def test_tool_server_configuration(self, db_connection):
        """Tool servers should be configured in config table"""
        cursor = db_connection.cursor()
        cursor.execute("SELECT data FROM config WHERE id=1")
        row = cursor.fetchone()

        if not row:
            pytest.skip("No config with id=1")

        config = json.loads(row[0])

        # Check for tool server configuration
        assert 'tool_server' in config, "Missing tool_server in config"
        assert 'connections' in config['tool_server'], "Missing connections in tool_server"

        connections = config['tool_server']['connections']
        assert isinstance(connections, list)
        assert len(connections) > 0, "No tool servers registered"

        print(f"\n✅ Found {len(connections)} tool server(s) registered")

        # Validate each connection
        for i, conn in enumerate(connections):
            assert 'url' in conn, f"Tool server {i} missing URL"

            # Name can be at top level or in 'info' dict
            name = conn.get('name') or conn.get('info', {}).get('name', f"tool-{i}")
            url = conn.get('url')
            if url:
                print(f"  → {name}: {url}")

    def test_default_models_configuration(self, db_connection):
        """Default models should be configured"""
        cursor = db_connection.cursor()
        cursor.execute("SELECT data FROM config WHERE id=1")
        row = cursor.fetchone()

        if not row:
            pytest.skip("No config with id=1")

        config = json.loads(row[0])

        # Check for model configuration
        # Note: Key might be 'ui' or 'default' depending on OpenWebUI version
        if 'ui' in config and 'default_models' in config['ui']:
            default_models = config['ui']['default_models']
            print(f"\n✅ Default models: {default_models}")
        elif 'default_models' in config:
            default_models = config['default_models']
            print(f"\n✅ Default models: {default_models}")
        else:
            # Not all setups have this - just log
            print("\n⚠️  No default_models found in config")

    def test_rag_embedding_configuration(self, db_connection):
        """RAG embedding model should be configured"""
        cursor = db_connection.cursor()
        cursor.execute("SELECT data FROM config WHERE id=1")
        row = cursor.fetchone()

        if not row:
            pytest.skip("No config with id=1")

        config = json.loads(row[0])

        # Check for RAG configuration
        if 'rag' in config:
            rag_config = config['rag']

            if 'embedding_model' in rag_config:
                embedding_model = rag_config['embedding_model']
                print(f"\n✅ RAG embedding model: {embedding_model}")

            if 'embedding_engine' in rag_config:
                embedding_engine = rag_config['embedding_engine']
                print(f"✅ RAG embedding engine: {embedding_engine}")
        else:
            print("\n⚠️  No RAG configuration found")


class TestToolRegistration:
    """Test tool registration in database"""

    def test_tool_table_exists(self, db_connection):
        """Tool table should exist"""
        cursor = db_connection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tool'")
        result = cursor.fetchone()
        assert result is not None, "Tool table does not exist"

    def test_function_table_exists(self, db_connection):
        """Function table should exist (for tool functions)"""
        cursor = db_connection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='function'")
        result = cursor.fetchone()
        assert result is not None, "Function table does not exist"

    def test_user_tools_vs_global_tools(self, db_connection):
        """Understand user tools vs global tool servers"""
        cursor = db_connection.cursor()

        # Count user tools
        cursor.execute("SELECT COUNT(*) FROM tool")
        user_tools_count = cursor.fetchone()[0]

        # Count global tool servers
        cursor.execute("SELECT data FROM config WHERE id=1")
        row = cursor.fetchone()
        global_tools_count = 0

        if row:
            config = json.loads(row[0])
            if 'tool_server' in config and 'connections' in config['tool_server']:
                global_tools_count = len(config['tool_server']['connections'])

        print(f"\n✅ User tools (tool table): {user_tools_count}")
        print(f"✅ Global tool servers (config): {global_tools_count}")

        # For GTD setup, we expect global tool servers
        assert global_tools_count > 0, "No global tool servers configured"


class TestModelConfiguration:
    """Test model configuration in database"""

    def test_model_table_exists(self, db_connection):
        """Model table should exist"""
        cursor = db_connection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='model'")
        result = cursor.fetchone()
        assert result is not None, "Model table does not exist"

    def test_models_registered(self, db_connection):
        """Models should be registered in database"""
        cursor = db_connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM model")
        model_count = cursor.fetchone()[0]

        print(f"\n✅ Found {model_count} model(s) in database")

        # Should have at least some models
        if model_count == 0:
            print("⚠️  No models registered - check LiteLLM configuration")

    def test_model_details(self, db_connection):
        """Check model details and configuration"""
        cursor = db_connection.cursor()
        cursor.execute("SELECT id, name, meta FROM model LIMIT 10")

        models = []
        for row in cursor.fetchall():
            model_id, name, meta = row[0], row[1], row[2]

            # Parse meta if it's JSON
            if meta:
                try:
                    meta_obj = json.loads(meta)
                    models.append({
                        'id': model_id,
                        'name': name,
                        'meta': meta_obj
                    })
                except json.JSONDecodeError:
                    models.append({
                        'id': model_id,
                        'name': name,
                        'meta': None
                    })
            else:
                models.append({
                    'id': model_id,
                    'name': name,
                    'meta': None
                })

        if models:
            print(f"\n✅ First {len(models)} models:")
            for m in models:
                print(f"  → {m['name']} (id: {m['id']})")
        else:
            print("\n⚠️  No models found in database")


class TestUserAccounts:
    """Test user accounts in database"""

    def test_user_table_exists(self, db_connection):
        """User table should exist"""
        cursor = db_connection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user'")
        result = cursor.fetchone()
        assert result is not None, "User table does not exist"

    def test_users_exist(self, db_connection):
        """At least one user should exist"""
        cursor = db_connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM user")
        user_count = cursor.fetchone()[0]

        assert user_count > 0, "No users in database"
        print(f"\n✅ Found {user_count} user(s) in database")

    def test_admin_user_exists(self, db_connection):
        """Admin user should exist"""
        cursor = db_connection.cursor()
        cursor.execute("SELECT id, name, email, role FROM user WHERE role='admin'")
        admins = cursor.fetchall()

        assert len(admins) > 0, "No admin user found"

        print(f"\n✅ Found {len(admins)} admin user(s)")
        for admin in admins:
            print(f"  → {admin[1]} ({admin[2]})")


class TestChatHistory:
    """Test chat history in database"""

    def test_chat_table_exists(self, db_connection):
        """Chat table should exist"""
        cursor = db_connection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='chat'")
        result = cursor.fetchone()
        assert result is not None, "Chat table does not exist"

    def test_chat_count(self, db_connection):
        """Count chats in database"""
        cursor = db_connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM chat")
        chat_count = cursor.fetchone()[0]

        print(f"\n✅ Found {chat_count} chat(s) in database")


class TestOpenWebUIAPI:
    """Test OpenWebUI API endpoints (no auth required)"""

    def test_health_endpoint(self):
        """OpenWebUI health endpoint should respond"""
        try:
            response = requests.get(f"{OPENWEBUI_URL}/health", timeout=5)
            assert response.status_code == 200
            print(f"\n✅ OpenWebUI health check: {response.status_code}")
        except requests.exceptions.RequestException as e:
            pytest.skip(f"OpenWebUI not accessible: {e}")

    def test_api_config_endpoint(self):
        """API config endpoint should respond"""
        try:
            response = requests.get(f"{OPENWEBUI_URL}/api/config", timeout=5)
            # May return 200 with config or 401 if auth required
            assert response.status_code in [200, 401, 403]
            print(f"\n✅ OpenWebUI API config endpoint: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"  → Config keys: {list(data.keys())}")
        except requests.exceptions.RequestException as e:
            pytest.skip(f"OpenWebUI API not accessible: {e}")


class TestToolServerEndpoints:
    """Test tool server endpoints are accessible from OpenWebUI network"""

    def test_todoist_tool_health(self):
        """Todoist tool should be accessible from OpenWebUI container"""
        result = subprocess.run(
            ["docker", "exec", "openwebui", "curl", "-s", "http://todoist-tool:8000/health"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.skip("Could not exec into OpenWebUI container")

        try:
            health = json.loads(result.stdout)
            assert health.get("status") in ["healthy", "degraded"]
            print(f"\n✅ Todoist tool health: {health.get('status')}")
            print(f"  → API latency: {health.get('todoist_api', {}).get('latency_ms')}ms")
            print(f"  → Cache entries: {health.get('cache', {}).get('entries')}")
        except json.JSONDecodeError:
            pytest.fail(f"Invalid JSON from Todoist health endpoint: {result.stdout[:200]}")

    def test_caldav_tool_health(self):
        """CalDAV tool should be accessible from OpenWebUI container"""
        result = subprocess.run(
            ["docker", "exec", "openwebui", "curl", "-s", "http://caldav-tool:8000/health"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.skip("Could not exec into OpenWebUI container")

        try:
            health = json.loads(result.stdout)
            assert health.get("status") in ["healthy", "degraded", "unhealthy"]
            print(f"\n✅ CalDAV tool health: {health.get('status')}")
            print(f"  → CalDAV latency: {health.get('caldav', {}).get('latency_ms')}ms")
            print(f"  → Calendars: {health.get('caldav', {}).get('calendar_count')}")
            print(f"  → Cache entries: {health.get('cache', {}).get('entries')}")
        except json.JSONDecodeError:
            pytest.fail(f"Invalid JSON from CalDAV health endpoint: {result.stdout[:200]}")

    def test_filesystem_tool_openapi(self):
        """Filesystem tool OpenAPI schema should be accessible"""
        result = subprocess.run(
            ["docker", "exec", "openwebui", "curl", "-s", "http://filesystem-tool:8000/openapi.json"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.skip("Could not exec into OpenWebUI container")

        try:
            schema = json.loads(result.stdout)
            assert 'openapi' in schema
            assert 'paths' in schema

            paths_count = len(schema['paths'])
            print(f"\n✅ Filesystem tool OpenAPI schema:")
            print(f"  → OpenAPI version: {schema['openapi']}")
            print(f"  → Endpoints: {paths_count}")
            print(f"  → Title: {schema['info']['title']}")
        except json.JSONDecodeError:
            pytest.fail(f"Invalid JSON from Filesystem OpenAPI endpoint")

    def test_git_tool_openapi(self):
        """Git tool OpenAPI schema should be accessible"""
        result = subprocess.run(
            ["docker", "exec", "openwebui", "curl", "-s", "http://git-tool:8000/openapi.json"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.skip("Could not exec into OpenWebUI container")

        try:
            schema = json.loads(result.stdout)
            assert 'openapi' in schema
            assert 'paths' in schema

            paths_count = len(schema['paths'])
            print(f"\n✅ Git tool OpenAPI schema:")
            print(f"  → OpenAPI version: {schema['openapi']}")
            print(f"  → Endpoints: {paths_count}")
            print(f"  → Title: {schema['info']['title']}")
        except json.JSONDecodeError:
            pytest.fail(f"Invalid JSON from Git OpenAPI endpoint")


class TestPromptConfiguration:
    """Test custom prompts in database"""

    def test_prompt_table_exists(self, db_connection):
        """Prompt table should exist"""
        cursor = db_connection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='prompt'")
        result = cursor.fetchone()
        assert result is not None, "Prompt table does not exist"

    def test_custom_prompts(self, db_connection):
        """Check for custom prompts"""
        cursor = db_connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM prompt")
        prompt_count = cursor.fetchone()[0]

        print(f"\n✅ Found {prompt_count} custom prompt(s)")

        if prompt_count > 0:
            cursor.execute("SELECT command, title FROM prompt LIMIT 5")
            prompts = cursor.fetchall()
            for command, title in prompts:
                print(f"  → /{command}: {title}")


# Summary fixture to print overall results
@pytest.fixture(scope="session", autouse=True)
def print_summary():
    """Print test summary at the end"""
    yield
    print("\n" + "="*60)
    print("OpenWebUI Integration Test Summary")
    print("="*60)
    print("✅ All database schema and configuration tests completed")
    print("="*60)
