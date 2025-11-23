import pytest
import sys

def test_gdocs_imports():
    """
    Verify that gdocs tools can be imported successfully.
    Equivalent to the old smoke_test.py.
    """
    try:
        from gdocs.docs_tools import modify_doc_content, insert_doc_elements, manage_doc_operations
        assert True
    except ImportError as e:
        pytest.fail(f"Failed to import Docs tools: {e}")

def test_auth_imports():
    """
    Verify that auth modules can be imported.
    """
    try:
        from auth.google_auth import GoogleAuthenticationError
        assert True
    except ImportError as e:
        pytest.fail(f"Failed to import Auth modules: {e}")
