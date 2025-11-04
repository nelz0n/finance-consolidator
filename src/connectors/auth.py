"""Shared authentication for Google APIs."""

import os
import pickle
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from src.utils.logger import get_logger

logger = get_logger()

# Combined scopes for both Drive and Sheets
SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/spreadsheets'
]


def get_credentials(credentials_path: str, token_path: str) -> Credentials:
    """
    Get Google API credentials with both Drive and Sheets scopes.

    Args:
        credentials_path: Path to credentials JSON file
        token_path: Path to store/load token

    Returns:
        Google OAuth2 credentials

    Raises:
        FileNotFoundError: If credentials file doesn't exist
        Exception: If authentication fails
    """
    creds = None

    # Check if token already exists
    if os.path.exists(token_path):
        logger.debug(f"Loading existing token from {token_path}")
        try:
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
        except Exception as e:
            logger.warning(f"Failed to load token: {e}")
            creds = None

    # If credentials are invalid or don't exist, refresh or create new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing expired credentials")
            try:
                creds.refresh(Request())
            except Exception as e:
                logger.warning(f"Failed to refresh token: {e}")
                creds = None

        if not creds:
            # Check if credentials file exists
            if not os.path.exists(credentials_path):
                logger.error(f"Credentials file not found: {credentials_path}")
                raise FileNotFoundError(
                    f"Credentials file not found: {credentials_path}\n"
                    "Please download credentials from Google Cloud Console"
                )

            logger.info("Starting OAuth 2.0 flow for Drive and Sheets access")
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_path, SCOPES
            )
            creds = flow.run_local_server(port=0)
            logger.info("OAuth flow completed successfully")

        # Save the credentials for future use
        logger.debug(f"Saving token to {token_path}")
        os.makedirs(os.path.dirname(token_path), exist_ok=True)
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)

    return creds
