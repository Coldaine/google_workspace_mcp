# Testing Assessment & Strategy
**Date:** 2025-11-20
**Repository:** google_workspace_mcp
**Current Status:** 🔴 **CRITICAL - ZERO TEST COVERAGE**

---

## Executive Summary

### Current State: 🔴 **NO TESTS**

- **Test Files:** 0 found
- **Test Directories:** 0 found
- **Test Coverage:** 0%
- **Lines of Code:** ~8,429 lines (core + auth + consolidated tools)
- **CI/CD Testing:** ❌ None (only linting)

### Risk Assessment: 🔴 **HIGH RISK**

**Critical Concerns:**
- ❌ **No regression protection** during Phase 2 consolidation
- ❌ **OAuth flows untested** (complex multi-step authentication)
- ❌ **Consolidated tools unvalidated** (Gmail, Tasks, Apps Script)
- ❌ **Tool tier filtering untested** (just fixed critical bug - needs validation!)
- ❌ **Service decorator logic unchecked** (automatic credential injection)
- ❌ **Error handling unproven** (SSL fallbacks, token refresh)

**Impact:**
- Phase 1 consolidation worked by **luck, not validation**
- Phase 2+ consolidation could introduce regressions
- Production deployments lack automated quality gates
- Breaking changes may go undetected

---

## Testing Infrastructure Analysis

### ✅ Dependencies Configured (but not used)

**Test dependencies in `pyproject.toml`:**
```toml
[project.optional-dependencies]
test = [
    "pytest>=8.3.0",         # ✅ Configured
    "pytest-asyncio>=0.23.0", # ✅ Configured (for async tests)
    "requests>=2.32.3",       # ✅ Configured (HTTP mocking?)
]
```

**Missing Dependencies:**
- ❌ `pytest-mock` - For easier mocking
- ❌ `pytest-cov` - For coverage reporting
- ❌ `responses` - For HTTP request mocking
- ❌ `freezegun` - For time-based testing
- ❌ `google-api-python-client-stubs` - Type stubs for Google APIs

### ❌ No Test Configuration

**Missing `pytest` configuration in `pyproject.toml`:**
```toml
# Should exist but doesn't:
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
asyncio_mode = "auto"
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "auth: Authentication tests",
]
```

### ❌ No CI/CD Test Workflow

**Current workflow:** `.github/workflows/ruff.yml` (linting only)

**Missing:** `.github/workflows/test.yml`
```yaml
# Should exist but doesn't:
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: pip install -e ".[test]"
      - run: pytest --cov --cov-report=xml
      - uses: codecov/codecov-action@v4  # Optional: coverage reporting
```

---

## Critical Areas Requiring Tests

### 1. 🔴 **OAuth Authentication** (HIGH PRIORITY)

**Files:** `auth/google_auth.py` (400+ lines), `auth/service_decorator.py` (300+ lines)

**Why Critical:**
- Complex multi-step OAuth 2.0/2.1 flows
- Session management with bearer tokens
- Credential storage and retrieval
- Token refresh logic
- Error handling for expired/invalid tokens

**Must Test:**
- ✅ OAuth 2.0 flow initialization
- ✅ OAuth 2.1 flow with PKCE
- ✅ Credential storage and retrieval
- ✅ Token refresh on expiry
- ✅ Multi-user credential isolation
- ✅ Single-user fallback mode
- ✅ Session-to-credential mapping
- ✅ Error handling (invalid tokens, refresh failures)

**Mocking Required:**
```python
# Mock Google OAuth flow
from unittest.mock import Mock, patch
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

@patch('google_auth_oauthlib.flow.Flow.from_client_secrets_file')
def test_start_auth_flow(mock_flow):
    mock_flow.return_value.authorization_url.return_value = (
        'https://accounts.google.com/o/oauth2/auth?...',
        'state123'
    )
    # Test auth flow initialization
```

**Test Coverage Needed:**
- Unit tests: 90%+ (pure logic)
- Integration tests: Key flows (auth, refresh, multi-user)

---

### 2. 🔴 **Service Decorator & Caching** (HIGH PRIORITY)

**Files:** `auth/service_decorator.py`

**Why Critical:**
- Automatic credential injection via `@require_google_service()`
- 30-minute service caching (TTL logic)
- Scope validation
- OAuth version detection (2.0 vs 2.1)
- User email override in OAuth 2.1 mode

**Must Test:**
- ✅ Service decorator applies correctly
- ✅ Credentials injected into function
- ✅ Service caching works (hit/miss)
- ✅ TTL expiration triggers refresh
- ✅ Scope validation catches mismatches
- ✅ OAuth version detection logic
- ✅ User email override behavior

**Mocking Required:**
```python
from auth.service_decorator import require_google_service
from googleapiclient.discovery import build

@patch('googleapiclient.discovery.build')
@patch('auth.google_auth.get_authenticated_google_service')
def test_service_decorator(mock_get_service, mock_build):
    mock_service = Mock()
    mock_get_service.return_value = mock_service

    @require_google_service("gmail", "gmail_read")
    async def test_tool(service, user_google_email: str):
        return service

    result = await test_tool(user_google_email="test@example.com")
    assert result == mock_service
```

**Test Coverage Needed:**
- Unit tests: 95%+ (decorator logic)
- Integration tests: Cache behavior

---

### 3. 🔴 **Consolidated Tools** (HIGH PRIORITY)

**Files:**
- `gmail/gmail_tools.py` (1,279 lines)
- `gtasks/tasks_tools.py` (676 lines)
- `gappsscript/appsscript_tools.py` (559 lines)

**Why Critical:**
- New consolidation pattern used in Phase 1
- Complex operation routing (Literal parameters)
- Parameter validation logic
- Batch operations (Gmail SSL fallbacks)
- Multi-page pagination (Tasks)
- Hierarchical structures (StructuredTask)

**Must Test:**

#### Gmail Tools (`get_gmail_content`)
```python
@pytest.mark.asyncio
@patch('gmail.gmail_tools.asyncio.to_thread')
async def test_get_gmail_content_message_operation(mock_to_thread):
    """Test get_gmail_content with operation='message'"""
    mock_service = Mock()
    mock_message = {
        'id': 'msg123',
        'payload': {
            'headers': [
                {'name': 'Subject', 'value': 'Test Subject'},
                {'name': 'From', 'value': 'sender@example.com'}
            ],
            'body': {'data': 'dGVzdCBib2R5'}  # base64: 'test body'
        }
    }
    mock_to_thread.return_value = mock_message

    result = await get_gmail_content(
        service=mock_service,
        user_google_email="test@example.com",
        operation="message",
        message_id="msg123"
    )

    assert "Test Subject" in result
    assert "sender@example.com" in result
```

#### Tasks Tools (`manage_task`)
```python
@pytest.mark.asyncio
@patch('gtasks.tasks_tools.asyncio.to_thread')
async def test_manage_task_create_operation(mock_to_thread):
    """Test manage_task with operation='create'"""
    mock_service = Mock()
    mock_task = {'id': 'task123', 'title': 'New Task', 'status': 'needsAction'}
    mock_to_thread.return_value = mock_task

    result = await manage_task(
        service=mock_service,
        user_google_email="test@example.com",
        operation="create",
        task_list_id="list123",
        title="New Task"
    )

    assert "task123" in result
    assert "New Task" in result
```

#### Apps Script Tools (`manage_script_project`)
```python
@pytest.mark.asyncio
@patch('gappsscript.appsscript_tools.asyncio.to_thread')
async def test_manage_script_project_get_operation(mock_to_thread):
    """Test manage_script_project with operation='get'"""
    mock_service = Mock()
    mock_project = {
        'scriptId': 'script123',
        'title': 'Test Script',
        'createTime': '2024-01-01T00:00:00Z'
    }
    mock_to_thread.return_value = mock_project

    result = await manage_script_project(
        service=mock_service,
        user_google_email="test@example.com",
        operation="get",
        script_id="script123"
    )

    assert "script123" in result
    assert "Test Script" in result
```

**Test Coverage Needed:**
- Unit tests: 85%+ per tool
- All operations tested: `list`, `get`, `create`, `update`, `delete`, `move` (where applicable)
- Parameter validation tests
- Error handling tests

---

### 4. 🟡 **Tool Tier Filtering** (MEDIUM PRIORITY - JUST FIXED!)

**Files:** `core/tool_tiers.yaml`, `main.py`

**Why Critical:**
- **Just fixed critical bug** - needs validation to prevent regression!
- Tier filtering enables granular deployments
- Docker/Helm use `TOOL_TIER` env var
- Incorrect filtering = missing/wrong tools loaded

**Must Test:**
```python
import yaml
from main import server

def test_tool_tiers_yaml_valid():
    """Verify tool_tiers.yaml is valid YAML"""
    with open('core/tool_tiers.yaml') as f:
        tiers = yaml.safe_load(f)
    assert tiers is not None
    assert 'gmail' in tiers
    assert 'tasks' in tiers
    assert 'appsscript' in tiers

def test_gmail_tools_match_tier_config():
    """Verify Gmail tools in YAML match implementation"""
    with open('core/tool_tiers.yaml') as f:
        tiers = yaml.safe_load(f)

    # Extract all Gmail tools from YAML
    yaml_tools = set()
    for tier in ['core', 'extended', 'complete']:
        if tiers['gmail'][tier]:
            yaml_tools.update([t for t in tiers['gmail'][tier] if t != 'start_google_auth'])

    # Expected Gmail tools from implementation
    expected_tools = {
        'search_gmail_messages',
        'get_gmail_content',
        'send_gmail_message',
        'draft_gmail_message',
        'manage_gmail_label',
        'modify_gmail_labels'
    }

    assert yaml_tools == expected_tools, f"Mismatch: {yaml_tools ^ expected_tools}"

def test_tier_filtering_core_only():
    """Test that TOOL_TIER=core only loads core tier tools"""
    import os
    os.environ['TOOL_TIER'] = 'core'

    # Re-import to apply tier filtering
    import importlib
    import main
    importlib.reload(main)

    tools = main.server.list_tools()
    tool_names = {t['name'] for t in tools}

    # Gmail core tools should be present
    assert 'search_gmail_messages' in tool_names
    assert 'get_gmail_content' in tool_names
    assert 'send_gmail_message' in tool_names

    # Gmail extended/complete tools should NOT be present
    assert 'draft_gmail_message' not in tool_names
    assert 'modify_gmail_labels' not in tool_names
```

**Test Coverage Needed:**
- Schema validation: 100%
- Tool matching: 100% (all services)
- Tier filtering logic: 90%+

---

### 5. 🟡 **Error Handling** (MEDIUM PRIORITY)

**Files:** `core/utils.py`, all `*_tools.py` files

**Why Critical:**
- `@handle_http_errors()` decorator used everywhere
- SSL fallback logic in Gmail batch operations
- Token refresh error handling
- HTTP 4xx/5xx error responses

**Must Test:**
```python
@pytest.mark.asyncio
async def test_gmail_batch_ssl_fallback():
    """Test Gmail batch operation falls back on SSL errors"""
    from gmail.gmail_tools import get_gmail_content
    import ssl

    mock_service = Mock()
    # First call raises SSL error, second succeeds
    mock_service.users().messages().get().execute.side_effect = [
        ssl.SSLError("SSL error"),
        {'id': 'msg1', 'payload': {...}}
    ]

    result = await get_gmail_content(
        service=mock_service,
        operation="messages_batch",
        message_ids=["msg1"],
        ...
    )

    # Should succeed despite SSL error
    assert "msg1" in result

@pytest.mark.asyncio
async def test_token_refresh_on_expiry():
    """Test token automatically refreshes on expiry"""
    from auth.google_auth import get_authenticated_google_service
    from google.auth.exceptions import RefreshError

    mock_creds = Mock()
    mock_creds.expired = True
    mock_creds.refresh = Mock()

    service = await get_authenticated_google_service(
        "gmail",
        user_google_email="test@example.com"
    )

    # Token should have been refreshed
    mock_creds.refresh.assert_called_once()
```

**Test Coverage Needed:**
- Error decorator: 90%+
- SSL fallbacks: 100%
- Token refresh: 95%+

---

### 6. 🟢 **Server Initialization** (LOW PRIORITY)

**Files:** `core/server.py`, `main.py`

**Why Test:**
- Validates server starts correctly
- Middleware stack configured
- Tools registered
- OAuth providers initialized

**Must Test:**
```python
def test_server_initializes():
    """Test server instance created correctly"""
    from core.server import server
    assert server is not None
    assert server.name == "google_workspace"

def test_tools_registered():
    """Test all expected tools are registered"""
    from main import server
    tools = server.list_tools()

    # Should have 63 tools after Phase 1 consolidation
    assert len(tools) >= 60  # Allow some flexibility

    # Check critical tools exist
    tool_names = {t['name'] for t in tools}
    assert 'search_gmail_messages' in tool_names
    assert 'manage_task' in tool_names
    assert 'manage_script_project' in tool_names
    assert 'start_google_auth' in tool_names
```

**Test Coverage Needed:**
- Smoke tests: 100%
- Tool registration: 90%+

---

## Mocking Strategy

### 🎯 **What to Mock**

#### 1. Google API Clients
```python
from unittest.mock import Mock, patch, MagicMock
from googleapiclient.discovery import build

@patch('googleapiclient.discovery.build')
def test_with_mocked_service(mock_build):
    """Mock Google API service"""
    mock_service = MagicMock()
    mock_build.return_value = mock_service

    # Configure mock responses
    mock_service.users().messages().list().execute.return_value = {
        'messages': [{'id': 'msg1', 'threadId': 'thread1'}]
    }

    # Test code that uses the service
    ...
```

#### 2. OAuth Flows
```python
@patch('google_auth_oauthlib.flow.Flow.from_client_secrets_file')
@patch('google.oauth2.credentials.Credentials')
def test_oauth_flow(mock_credentials, mock_flow):
    """Mock OAuth authentication flow"""
    mock_flow_instance = Mock()
    mock_flow.return_value = mock_flow_instance

    mock_flow_instance.authorization_url.return_value = (
        'https://accounts.google.com/...',
        'state123'
    )

    mock_creds = Mock()
    mock_creds.token = 'access_token_123'
    mock_credentials.return_value = mock_creds

    # Test auth flow
    ...
```

#### 3. File System (Credentials)
```python
@patch('builtins.open', create=True)
@patch('os.path.exists')
def test_credential_storage(mock_exists, mock_open):
    """Mock credential file operations"""
    mock_exists.return_value = True
    mock_file = MagicMock()
    mock_open.return_value.__enter__.return_value = mock_file
    mock_file.read.return_value = '{"token": "...", "refresh_token": "..."}'

    # Test credential loading
    ...
```

#### 4. Async Operations
```python
import asyncio
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
@patch('asyncio.to_thread', new_callable=AsyncMock)
async def test_async_operation(mock_to_thread):
    """Mock async Google API calls"""
    mock_to_thread.return_value = {'result': 'success'}

    result = await some_async_function()
    assert result['result'] == 'success'
```

#### 5. FastMCP Context
```python
@patch('fastmcp.server.dependencies.get_context')
def test_with_mocked_context(mock_get_context):
    """Mock FastMCP request context"""
    mock_ctx = Mock()
    mock_ctx.get_state.return_value = 'user@example.com'
    mock_ctx.session_id = 'session123'
    mock_get_context.return_value = mock_ctx

    # Test code that uses context
    ...
```

### ❌ **What NOT to Mock**

- **Business Logic:** Don't mock the code you're testing
- **Data Structures:** `StructuredTask`, parameter validation
- **Helper Functions:** Internal utilities (test them directly)
- **Type Checking:** Literal type validation

---

## Recommended Test Structure

```
google_workspace_mcp/
├── tests/
│   ├── __init__.py
│   ├── conftest.py                 # Shared fixtures
│   │
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── auth/
│   │   │   ├── test_google_auth.py         # OAuth flows
│   │   │   ├── test_service_decorator.py   # Service injection
│   │   │   ├── test_credential_store.py    # Credential management
│   │   │   └── test_oauth21_session.py     # Session store
│   │   │
│   │   ├── tools/
│   │   │   ├── test_gmail_tools.py         # Gmail consolidated tools
│   │   │   ├── test_tasks_tools.py         # Tasks consolidated tools
│   │   │   ├── test_appsscript_tools.py    # Apps Script tools
│   │   │   ├── test_docs_tools.py          # (Future) Docs tools
│   │   │   └── ...
│   │   │
│   │   ├── core/
│   │   │   ├── test_server.py              # Server initialization
│   │   │   ├── test_tool_tiers.py          # Tier filtering
│   │   │   ├── test_error_handling.py      # Error decorators
│   │   │   └── test_utils.py               # Utility functions
│   │   │
│   │   └── ...
│   │
│   ├── integration/
│   │   ├── __init__.py
│   │   ├── test_auth_flow.py           # End-to-end OAuth
│   │   ├── test_tool_registration.py   # Tool loading
│   │   ├── test_tier_filtering.py      # Tier-based deployment
│   │   └── test_service_caching.py     # Service TTL behavior
│   │
│   └── fixtures/
│       ├── sample_credentials.json
│       ├── sample_client_secret.json
│       └── mock_api_responses.py
```

---

## Priority Test Implementation Plan

### Phase 0: Infrastructure (IMMEDIATE)

**Effort:** 2-4 hours
**Files to Create:**
- `tests/conftest.py` - Shared fixtures
- `.github/workflows/test.yml` - CI/CD test workflow
- Update `pyproject.toml` - Add pytest config

**Deliverables:**
- ✅ Test directory structure
- ✅ Pytest configuration
- ✅ CI/CD pipeline
- ✅ Shared fixtures (mock services, credentials)

### Phase 1: Critical Path (HIGH PRIORITY)

**Effort:** 1-2 weeks
**Target Coverage:** 70%+ of critical code

**Tests to Implement:**
1. **Tool Tier Validation** (URGENT - just fixed!)
   - `test_tool_tiers_yaml_valid()`
   - `test_gmail_tools_match_tier_config()`
   - `test_tasks_tools_match_tier_config()`
   - `test_appsscript_tools_match_tier_config()`
   - `test_tier_filtering_core()`
   - `test_tier_filtering_extended()`
   - `test_tier_filtering_complete()`

2. **OAuth Authentication**
   - `test_start_auth_flow()`
   - `test_handle_auth_callback()`
   - `test_token_refresh()`
   - `test_credential_storage()`
   - `test_multi_user_isolation()`

3. **Service Decorator**
   - `test_service_injection()`
   - `test_service_caching()`
   - `test_cache_ttl_expiry()`
   - `test_scope_validation()`

4. **Consolidated Tools** (one operation per tool minimum)
   - Gmail: `test_get_gmail_content_message()`
   - Gmail: `test_manage_gmail_label_list()`
   - Tasks: `test_manage_task_create()`
   - Tasks: `test_manage_task_list_list()`
   - Apps Script: `test_manage_script_project_get()`

**Deliverables:**
- ✅ 70%+ coverage on auth layer
- ✅ 60%+ coverage on consolidated tools
- ✅ 100% coverage on tool tier validation
- ✅ CI/CD passing on all PRs

### Phase 2: Comprehensive Coverage (MEDIUM PRIORITY)

**Effort:** 2-3 weeks
**Target Coverage:** 85%+ overall

**Tests to Add:**
1. **All Tool Operations**
   - Gmail: All 5 operations × 6 tools = 30+ tests
   - Tasks: All 6 operations × 3 tools = 18+ tests
   - Apps Script: All operations × 5 tools = 15+ tests

2. **Error Handling**
   - SSL fallback scenarios
   - HTTP 4xx/5xx responses
   - Token expiry/refresh failures
   - Invalid parameters

3. **Integration Tests**
   - End-to-end auth flow
   - Service caching behavior
   - Tool registration with tiers

**Deliverables:**
- ✅ 85%+ overall coverage
- ✅ All critical paths tested
- ✅ Integration tests passing

### Phase 3: Edge Cases & Optimization (LOW PRIORITY)

**Effort:** 1-2 weeks
**Target Coverage:** 90%+ overall

**Tests to Add:**
1. **Edge Cases**
   - Empty responses
   - Malformed data
   - Concurrent requests
   - Rate limiting

2. **Performance Tests**
   - Service cache efficiency
   - Batch operation limits
   - Pagination handling

**Deliverables:**
- ✅ 90%+ overall coverage
- ✅ Performance benchmarks
- ✅ Load testing results

---

## Missing Test Dependencies

### Required Additions to `pyproject.toml`

```toml
[project.optional-dependencies]
test = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",              # NEW: Coverage reporting
    "pytest-mock>=3.12.0",             # NEW: Easier mocking
    "requests>=2.32.3",
    "responses>=0.24.0",               # NEW: HTTP request mocking
    "freezegun>=1.4.0",                # NEW: Time manipulation
    "google-api-python-client-stubs>=1.20.0",  # NEW: Type stubs
]
```

### Install Commands

```bash
# Install test dependencies
pip install -e ".[test]"

# Or with uv (faster)
uv sync --extra test

# Run tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html --cov-report=term

# Run specific test file
pytest tests/unit/auth/test_google_auth.py

# Run specific test
pytest tests/unit/auth/test_google_auth.py::test_start_auth_flow

# Run with markers
pytest -m "unit"              # Only unit tests
pytest -m "integration"       # Only integration tests
pytest -m "auth"              # Only auth tests
```

---

## Sample Test Files

### `tests/conftest.py` (Shared Fixtures)

```python
"""Shared pytest fixtures for all tests."""
import pytest
from unittest.mock import Mock, MagicMock
from google.oauth2.credentials import Credentials


@pytest.fixture
def mock_credentials():
    """Mock Google OAuth credentials."""
    creds = Mock(spec=Credentials)
    creds.token = "mock_access_token"
    creds.refresh_token = "mock_refresh_token"
    creds.expired = False
    creds.valid = True
    return creds


@pytest.fixture
def mock_gmail_service():
    """Mock Gmail API service."""
    service = MagicMock()
    return service


@pytest.fixture
def mock_tasks_service():
    """Mock Tasks API service."""
    service = MagicMock()
    return service


@pytest.fixture
def mock_script_service():
    """Mock Apps Script API service."""
    service = MagicMock()
    return service


@pytest.fixture
def sample_gmail_message():
    """Sample Gmail message API response."""
    return {
        'id': 'msg123',
        'threadId': 'thread123',
        'payload': {
            'headers': [
                {'name': 'Subject', 'value': 'Test Email'},
                {'name': 'From', 'value': 'sender@example.com'},
                {'name': 'To', 'value': 'recipient@example.com'},
            ],
            'body': {
                'size': 11,
                'data': 'SGVsbG8gV29ybGQ='  # base64: "Hello World"
            }
        },
        'labelIds': ['INBOX', 'UNREAD']
    }


@pytest.fixture
def sample_task():
    """Sample Tasks API task response."""
    return {
        'id': 'task123',
        'title': 'Test Task',
        'status': 'needsAction',
        'notes': 'Task notes',
        'due': '2024-12-31T23:59:59.000Z',
        'updated': '2024-01-01T00:00:00.000Z'
    }


@pytest.fixture
def sample_script_project():
    """Sample Apps Script project response."""
    return {
        'scriptId': 'script123',
        'title': 'Test Script',
        'createTime': '2024-01-01T00:00:00Z',
        'updateTime': '2024-01-02T00:00:00Z',
    }
```

### `tests/unit/core/test_tool_tiers.py` (URGENT!)

```python
"""Tests for tool tier filtering - CRITICAL after recent fix."""
import pytest
import yaml
from pathlib import Path


def test_tool_tiers_yaml_exists():
    """Verify tool_tiers.yaml file exists."""
    yaml_path = Path('core/tool_tiers.yaml')
    assert yaml_path.exists(), "tool_tiers.yaml not found"


def test_tool_tiers_yaml_valid_syntax():
    """Verify tool_tiers.yaml is valid YAML."""
    with open('core/tool_tiers.yaml') as f:
        tiers = yaml.safe_load(f)

    assert tiers is not None
    assert isinstance(tiers, dict)


def test_tool_tiers_has_all_services():
    """Verify all services are present in tool_tiers.yaml."""
    with open('core/tool_tiers.yaml') as f:
        tiers = yaml.safe_load(f)

    expected_services = [
        'gmail', 'tasks', 'appsscript', 'drive', 'calendar',
        'docs', 'sheets', 'forms', 'slides', 'chat', 'search'
    ]

    for service in expected_services:
        assert service in tiers, f"Service '{service}' missing from tool_tiers.yaml"


def test_gmail_tools_match_implementation():
    """Verify Gmail tools in YAML match actual implementation."""
    with open('core/tool_tiers.yaml') as f:
        tiers = yaml.safe_load(f)

    # Extract Gmail tools from YAML (excluding start_google_auth)
    yaml_tools = set()
    for tier in ['core', 'extended', 'complete']:
        if tiers['gmail'][tier]:
            yaml_tools.update([t for t in tiers['gmail'][tier] if t != 'start_google_auth'])

    # Expected Gmail tools (consolidated)
    expected_tools = {
        'search_gmail_messages',
        'get_gmail_content',          # Consolidated
        'send_gmail_message',
        'draft_gmail_message',
        'manage_gmail_label',
        'modify_gmail_labels'          # Consolidated
    }

    assert yaml_tools == expected_tools, \
        f"Gmail tools mismatch.\nIn YAML but not expected: {yaml_tools - expected_tools}\n" \
        f"Expected but not in YAML: {expected_tools - yaml_tools}"


def test_tasks_tools_match_implementation():
    """Verify Tasks tools in YAML match actual implementation."""
    with open('core/tool_tiers.yaml') as f:
        tiers = yaml.safe_load(f)

    yaml_tools = set()
    for tier in ['core', 'extended', 'complete']:
        if tiers['tasks'][tier]:
            yaml_tools.update(tiers['tasks'][tier])

    expected_tools = {
        'manage_task',              # Consolidated
        'manage_task_list',         # Consolidated
        'clear_completed_tasks'
    }

    assert yaml_tools == expected_tools, \
        f"Tasks tools mismatch.\nIn YAML: {yaml_tools}\nExpected: {expected_tools}"


def test_appsscript_tools_match_implementation():
    """Verify Apps Script tools in YAML match actual implementation."""
    with open('core/tool_tiers.yaml') as f:
        tiers = yaml.safe_load(f)

    yaml_tools = set()
    for tier in ['core', 'extended', 'complete']:
        if tiers['appsscript'][tier]:
            yaml_tools.update(tiers['appsscript'][tier])

    expected_tools = {
        'manage_script_project',
        'execute_script',
        'manage_script_version',
        'manage_script_deployment',
        'monitor_script_execution'
    }

    assert yaml_tools == expected_tools, \
        f"Apps Script tools mismatch.\nIn YAML: {yaml_tools}\nExpected: {expected_tools}"


def test_no_duplicate_tools_across_tiers():
    """Verify no tool appears in multiple tiers within a service."""
    with open('core/tool_tiers.yaml') as f:
        tiers = yaml.safe_load(f)

    for service, tier_dict in tiers.items():
        all_tools = []
        for tier, tools in tier_dict.items():
            if tools:
                all_tools.extend(tools)

        # Check for duplicates
        duplicates = [t for t in all_tools if all_tools.count(t) > 1]
        assert not duplicates, \
            f"Service '{service}' has duplicate tools across tiers: {set(duplicates)}"


@pytest.mark.parametrize("service,tier", [
    ("gmail", "core"),
    ("gmail", "extended"),
    ("tasks", "core"),
    ("appsscript", "core"),
])
def test_tier_has_valid_structure(service, tier):
    """Verify each tier has valid structure (list or empty list)."""
    with open('core/tool_tiers.yaml') as f:
        tiers = yaml.safe_load(f)

    assert tier in tiers[service], f"Tier '{tier}' missing from '{service}'"
    tier_tools = tiers[service][tier]
    assert isinstance(tier_tools, (list, type(None))), \
        f"Tier '{tier}' in '{service}' should be a list, got {type(tier_tools)}"
```

### `tests/unit/tools/test_gmail_tools.py` (Sample)

```python
"""Tests for Gmail consolidated tools."""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from gmail.gmail_tools import (
    get_gmail_content,
    manage_gmail_label,
    modify_gmail_labels
)


@pytest.mark.asyncio
@patch('gmail.gmail_tools.asyncio.to_thread')
async def test_get_gmail_content_message_operation(mock_to_thread, sample_gmail_message):
    """Test get_gmail_content with operation='message'."""
    mock_service = Mock()

    # Mock metadata fetch
    mock_metadata = {
        'payload': {
            'headers': [
                {'name': 'Subject', 'value': 'Test Email'},
                {'name': 'From', 'value': 'sender@example.com'}
            ]
        }
    }

    # Mock full message fetch
    mock_to_thread.side_effect = [mock_metadata, sample_gmail_message]

    result = await get_gmail_content(
        service=mock_service,
        user_google_email="test@example.com",
        operation="message",
        message_id="msg123"
    )

    assert "Test Email" in result
    assert "sender@example.com" in result
    assert "Hello World" in result or "SGVsbG8gV29ybGQ=" in result


@pytest.mark.asyncio
async def test_get_gmail_content_missing_message_id():
    """Test get_gmail_content raises error when message_id missing."""
    mock_service = Mock()

    with pytest.raises(ValueError, match="message_id.*required"):
        await get_gmail_content(
            service=mock_service,
            user_google_email="test@example.com",
            operation="message",
            message_id=None  # Should raise error
        )


@pytest.mark.asyncio
@patch('gmail.gmail_tools.asyncio.to_thread')
async def test_manage_gmail_label_list_operation(mock_to_thread):
    """Test manage_gmail_label with operation='list'."""
    mock_service = Mock()
    mock_labels = {
        'labels': [
            {'id': 'label1', 'name': 'Personal', 'type': 'user'},
            {'id': 'label2', 'name': 'Work', 'type': 'user'}
        ]
    }
    mock_to_thread.return_value = mock_labels

    result = await manage_gmail_label(
        service=mock_service,
        user_google_email="test@example.com",
        operation="list"
    )

    assert "Personal" in result
    assert "Work" in result
```

---

## Immediate Action Items

### 1. Create Test Infrastructure (Day 1)

```bash
# Create test directory structure
mkdir -p tests/{unit/{auth,tools,core},integration,fixtures}
touch tests/__init__.py
touch tests/unit/__init__.py
touch tests/unit/auth/__init__.py
touch tests/unit/tools/__init__.py
touch tests/unit/core/__init__.py
touch tests/integration/__init__.py

# Create conftest.py
# (Copy sample from above)

# Update pyproject.toml
# (Add pytest config and missing dependencies)
```

### 2. Add CI/CD Test Workflow (Day 1)

Create `.github/workflows/test.yml`:
```yaml
name: Tests

on:
  pull_request:
    branches: [ main ]
  push:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install uv
      uses: astral-sh/setup-uv@v4

    - name: Install dependencies
      run: |
        uv sync --extra test

    - name: Run tests with coverage
      run: |
        uv run pytest --cov=. --cov-report=xml --cov-report=term

    - name: Upload coverage to Codecov (optional)
      uses: codecov/codecov-action@v4
      with:
        file: ./coverage.xml
        flags: unittests
        name: codecov-${{ matrix.python-version }}
```

### 3. Write URGENT Tests (Week 1)

**Priority Order:**
1. ✅ `tests/unit/core/test_tool_tiers.py` - Validate recent fix!
2. ✅ `tests/unit/auth/test_google_auth.py` - OAuth basics
3. ✅ `tests/unit/auth/test_service_decorator.py` - Service injection
4. ✅ `tests/unit/tools/test_gmail_tools.py` - Gmail consolidation
5. ✅ `tests/unit/tools/test_tasks_tools.py` - Tasks consolidation

---

## Success Criteria

### Minimum Viable Testing (Week 1)
- [ ] Test infrastructure created
- [ ] CI/CD workflow added
- [ ] Tool tier validation tests (100% coverage)
- [ ] Basic OAuth tests (50% coverage)
- [ ] One test per consolidated tool operation (30% coverage)
- [ ] CI/CD passing on all PRs

### Phase 1 Complete (Week 2-3)
- [ ] 70%+ coverage on auth layer
- [ ] 60%+ coverage on consolidated tools
- [ ] 100% coverage on tool tier filtering
- [ ] All critical paths tested
- [ ] Zero test failures

### Phase 2 Complete (Week 4-6)
- [ ] 85%+ overall coverage
- [ ] All tool operations tested
- [ ] Error handling comprehensive
- [ ] Integration tests passing
- [ ] Performance benchmarks established

### Phase 3 Complete (Week 7-8)
- [ ] 90%+ overall coverage
- [ ] Edge cases covered
- [ ] Load testing complete
- [ ] Documentation updated

---

## Conclusion

**Current Status:** 🔴 **ZERO TEST COVERAGE - HIGH RISK**

**Immediate Priority:**
1. Create test infrastructure (Day 1)
2. Add CI/CD workflow (Day 1)
3. Write tool tier validation tests (Week 1) - **URGENT after recent fix!**
4. Write basic OAuth and tool tests (Week 1)

**Recommendation:**
- ⚠️ **PAUSE Phase 2 consolidation** until minimum viable testing is in place
- ✅ **Implement Phase 0 + Phase 1 tests** before continuing with Docs consolidation
- ✅ **Add test coverage reporting** to track progress
- ✅ **Make tests a PR requirement** to prevent future regressions

**Risk Mitigation:**
- Tool tier fix validated by tests (prevents regression)
- OAuth flows tested (prevents auth breakage)
- Consolidated tools validated (prevents functionality loss)
- CI/CD catches issues before merge

---

**Assessment Date:** 2025-11-20
**Next Review:** After Phase 1 testing complete
**Owner:** Engineering Team
