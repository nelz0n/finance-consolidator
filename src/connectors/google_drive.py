"""Google Drive connector for file operations."""

import os
import io
import time
from pathlib import Path
from typing import List, Dict, Optional
from fnmatch import fnmatch

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

from src.connectors.auth import get_credentials
from src.utils.logger import get_logger

logger = get_logger()


class GoogleDriveConnector:
    """Connector for Google Drive API operations."""

    def __init__(self, credentials_path: str, token_path: str):
        """
        Initialize Google Drive connector.

        Args:
            credentials_path: Path to Google API credentials JSON file
            token_path: Path to store/load authentication token
        """
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None
        self.creds = None

        logger.info("Initializing Google Drive connector")

    def authenticate(self) -> bool:
        """
        Authenticate with Google Drive API using OAuth 2.0 flow.

        Returns:
            True if authentication successful, False otherwise
        """
        try:
            # Get credentials using shared auth module
            self.creds = get_credentials(self.credentials_path, self.token_path)

            # Build the Drive service
            self.service = build('drive', 'v3', credentials=self.creds)
            logger.info("Successfully authenticated with Google Drive API")
            return True

        except FileNotFoundError as e:
            logger.error(str(e))
            return False
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            return False

    def list_files(
        self,
        folder_id: str,
        file_pattern: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        List files in a Google Drive folder.

        Args:
            folder_id: Google Drive folder ID
            file_pattern: Optional filename pattern (e.g., "*.csv", "csob_*.csv")

        Returns:
            List of dictionaries with keys: id, name, modified_time
        """
        if not self.service:
            logger.error("Not authenticated. Call authenticate() first.")
            return []

        try:
            logger.info(f"Listing files in folder {folder_id}")

            # Build query to get files in folder
            query = f"'{folder_id}' in parents and trashed = false"

            # Get files from Drive
            results = self.service.files().list(
                q=query,
                fields="files(id, name, modifiedTime, mimeType)",
                orderBy="modifiedTime desc"
            ).execute()

            files = results.get('files', [])

            if not files:
                logger.warning(f"No files found in folder {folder_id}")
                return []

            # Filter by pattern if provided
            if file_pattern:
                logger.debug(f"Filtering files by pattern: {file_pattern}")
                files = [
                    f for f in files
                    if fnmatch(f['name'], file_pattern)
                ]

            # Format results
            result = []
            for file in files:
                result.append({
                    'id': file['id'],
                    'name': file['name'],
                    'modified_time': file['modifiedTime'],
                    'mime_type': file.get('mimeType', '')
                })

            logger.info(f"Found {len(result)} files")
            return result

        except HttpError as e:
            logger.error(f"HTTP error listing files: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Error listing files: {str(e)}")
            return []

    def download_file(self, file_id: str, destination: str, max_retries: int = 3) -> bool:
        """
        Download a file from Google Drive to local path with retry logic.

        Args:
            file_id: Google Drive file ID
            destination: Local destination path
            max_retries: Maximum number of retry attempts (default: 3)

        Returns:
            True if download successful, False otherwise
        """
        if not self.service:
            logger.error("Not authenticated. Call authenticate() first.")
            return False

        # Create destination directory if it doesn't exist
        os.makedirs(os.path.dirname(destination), exist_ok=True)

        # Retry loop with exponential backoff
        for attempt in range(max_retries):
            fh = None
            try:
                if attempt > 0:
                    logger.info(f"Retry attempt {attempt + 1}/{max_retries} for file {file_id}")
                else:
                    logger.info(f"Downloading file {file_id} to {destination}")

                # Get file metadata to check name and size
                file_metadata = self.service.files().get(fileId=file_id, fields="name, size").execute()
                file_name = file_metadata.get('name', 'unknown')
                file_size = int(file_metadata.get('size', 0))

                logger.debug(f"File: {file_name}, Size: {file_size} bytes")

                # Request file content with timeout
                request = self.service.files().get_media(fileId=file_id)

                # Configure chunk size based on file size
                # Smaller chunks for better reliability on large files
                chunk_size = 1024 * 1024  # 1MB chunks

                # Download file
                fh = io.FileIO(destination, 'wb')
                downloader = MediaIoBaseDownload(fh, request, chunksize=chunk_size)

                done = False
                last_progress = 0
                while not done:
                    status, done = downloader.next_chunk()
                    if status:
                        progress = int(status.progress() * 100)
                        if progress != last_progress:
                            logger.debug(f"Download progress: {progress}%")
                            last_progress = progress

                fh.close()
                fh = None

                logger.info(f"Successfully downloaded {file_name} to {destination}")
                return True

            except HttpError as e:
                if fh:
                    fh.close()

                logger.error(f"HTTP error downloading file (attempt {attempt + 1}/{max_retries}): {str(e)}")

                # Don't retry on 404 or auth errors
                if e.resp.status in [404, 401, 403]:
                    logger.error(f"Non-retryable error: {e.resp.status}")
                    return False

                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    logger.info(f"Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                else:
                    return False

            except Exception as e:
                if fh:
                    fh.close()

                logger.error(f"Error downloading file (attempt {attempt + 1}/{max_retries}): {str(e)}")

                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    logger.info(f"Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                else:
                    return False

        return False

    def get_file_content(self, file_id: str) -> Optional[bytes]:
        """
        Get file content directly without saving to disk.

        Args:
            file_id: Google Drive file ID

        Returns:
            File content as bytes, or None if error
        """
        if not self.service:
            logger.error("Not authenticated. Call authenticate() first.")
            return None

        try:
            logger.debug(f"Getting content for file {file_id}")

            # Request file content
            request = self.service.files().get_media(fileId=file_id)

            # Download to memory
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)

            done = False
            while not done:
                status, done = downloader.next_chunk()

            content = fh.getvalue()
            logger.debug(f"Retrieved {len(content)} bytes")
            return content

        except HttpError as e:
            logger.error(f"HTTP error getting file content: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error getting file content: {str(e)}")
            return None

    def get_file_metadata(self, file_id: str) -> Optional[Dict]:
        """
        Get file metadata from Google Drive.

        Args:
            file_id: Google Drive file ID

        Returns:
            Dictionary with file metadata, or None if error
        """
        if not self.service:
            logger.error("Not authenticated. Call authenticate() first.")
            return None

        try:
            logger.debug(f"Getting metadata for file {file_id}")

            file_metadata = self.service.files().get(
                fileId=file_id,
                fields="id, name, mimeType, modifiedTime, size, createdTime"
            ).execute()

            return file_metadata

        except HttpError as e:
            logger.error(f"HTTP error getting file metadata: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error getting file metadata: {str(e)}")
            return None
