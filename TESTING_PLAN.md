# Testing Plan for Google Workspace MCP

## Overview
This project uses `pytest` for testing. The test suite is divided into:
- **Unit Tests** (`tests/unit/`): Fast tests that verify imports and individual functions (mocked).
- **Integration Tests** (`tests/integration/`): Live tests that interact with real Google APIs.

## Prerequisites
1. **Environment Setup**:
   - Ensure dependencies are installed: `uv sync` or `pip install -e .[dev]`
   - Create a `.env` file in the root directory with your OAuth credentials:
     ```
     GOOGLE_OAUTH_CLIENT_ID=...
     GOOGLE_OAUTH_CLIENT_SECRET=...
     TEST_GOOGLE_EMAIL=your_email@gmail.com
     ```

## Running Tests

### Run All Tests
```bash
pytest
```

### Run Only Unit Tests
```bash
pytest tests/unit
```

### Run Only Integration Tests
**Note**: Integration tests require valid credentials and will create real files in your Google Drive.
```bash
pytest tests/integration
```

## Verification Steps (Manual)

### 1. Authentication
- **Action**: Connect an MCP client (e.g., Claude Desktop, VS Code) to the server.
- **Expected**: The server should initiate the OAuth flow. You should be redirected to Google to sign in.
- **Success**: You receive a token and the client shows "Connected".

### 2. Automated Test Suite
Run the full suite to verify all tools:
```bash
pytest -v
```

## Troubleshooting
- **Import Errors**: Run `pytest tests/unit` to verify code structure.
- **Auth Errors**: Check `.env` file and ensure `GOOGLE_OAUTH_CLIENT_ID` is set.
- **Skipped Tests**: Integration tests are skipped if credentials are missing.

