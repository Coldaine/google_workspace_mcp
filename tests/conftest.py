import os
import sys
import pytest
from dotenv import load_dotenv

# Add project root to path so we can import from src/core/etc
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables from .env file if it exists
load_dotenv()

@pytest.fixture(scope="session")
def test_email():
    """
    Returns the email address to use for live tests.
    Defaults to the one used in live_test.py if not set in env.
    """
    return os.getenv("TEST_GOOGLE_EMAIL", "pmaclyman@gmail.com")

@pytest.fixture(scope="session")
def check_creds():
    """
    Fixture to check if credentials are present before running integration tests.
    """
    if not os.getenv("GOOGLE_OAUTH_CLIENT_ID") or not os.getenv("GOOGLE_OAUTH_CLIENT_SECRET"):
        pytest.skip("GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET not set. Skipping integration tests.")
