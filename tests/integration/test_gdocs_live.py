import pytest
import re
import os
from gdocs.docs_tools import create_doc, get_doc_content

# Helper to unwrap the FastMCP tool if necessary
def unwrap_tool(tool):
    if hasattr(tool, 'fn'):
        return tool.fn
    elif hasattr(tool, '__wrapped__'):
        return tool.__wrapped__
    return tool

@pytest.mark.asyncio
@pytest.mark.integration
async def test_create_and_read_doc(test_email, check_creds):
    """
    Integration test that creates a Google Doc and then reads it back.
    Requires valid Google Credentials in the environment.
    """
    print(f"\nTesting with email: {test_email}")
    
    # 1. Create Doc
    create_func = unwrap_tool(create_doc)
    title = "MCP Pytest Integration Doc"
    initial_content = "Hello from Pytest!\nThis document was created automatically."
    
    try:
        create_result = await create_func(
            user_google_email=test_email,
            title=title,
            content=initial_content
        )
    except Exception as e:
        if "GoogleAuthenticationError" in str(type(e).__name__):
            pytest.fail(f"Authentication failed. Please run the auth flow manually first. Error: {e}")
        raise e

    assert "Created Google Doc" in create_result
    
    # Extract ID
    match = re.search(r"\(ID: ([^\)]+)\)", create_result)
    assert match is not None, "Could not parse Doc ID from result"
    doc_id = match.group(1)
    print(f"Created Doc ID: {doc_id}")

    # 2. Read Doc
    read_func = unwrap_tool(get_doc_content)
    read_result = await read_func(
        user_google_email=test_email,
        document_id=doc_id
    )
    
    # Verify content
    assert title in read_result
    assert "Hello from Pytest!" in read_result
