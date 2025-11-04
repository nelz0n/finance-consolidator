# Google Drive Connector Documentation

## Overview

The `GoogleDriveConnector` class provides a Python interface to the Google Drive API for listing and downloading files from Google Drive folders.

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Get Google API Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Drive API
4. Create OAuth 2.0 Client ID credentials for Desktop application
5. Download the credentials JSON file
6. Save as `data/credentials/google_credentials.json`

### 3. First-Time Authentication

On first run, the connector will:
1. Open your browser for OAuth authentication
2. Ask you to grant permissions
3. Save a token to `data/credentials/token.pickle` for future use

## Usage

### Basic Example

```python
from src.connectors.google_drive import GoogleDriveConnector

# Initialize connector
drive = GoogleDriveConnector(
    credentials_path="data/credentials/google_credentials.json",
    token_path="data/credentials/token.pickle"
)

# Authenticate
if not drive.authenticate():
    print("Authentication failed!")
    exit(1)

# List all files in a folder
folder_id = "your-folder-id-here"
files = drive.list_files(folder_id)

for file in files:
    print(f"{file['name']} - {file['modified_time']}")
```

### List Files with Pattern Matching

```python
# List only CSV files
csv_files = drive.list_files(folder_id, file_pattern="*.csv")

# List ČSOB files
csob_files = drive.list_files(folder_id, file_pattern="csob_*.csv")

# List Partners Bank files
partners_files = drive.list_files(folder_id, file_pattern="vypis_*.xlsx")
```

### Download File

```python
# Download file to local path
file_id = "your-file-id-here"
destination = "data/downloads/myfile.csv"

if drive.download_file(file_id, destination):
    print(f"Downloaded to {destination}")
else:
    print("Download failed")
```

### Get File Content Directly

```python
# Get file content without saving to disk
content = drive.get_file_content(file_id)

if content:
    # Process content (e.g., for CSV)
    import io
    text = content.decode('utf-8')
    print(text[:100])  # First 100 characters
```

### Get File Metadata

```python
# Get detailed file information
metadata = drive.get_file_metadata(file_id)

if metadata:
    print(f"Name: {metadata['name']}")
    print(f"Size: {metadata['size']} bytes")
    print(f"Created: {metadata['createdTime']}")
    print(f"Modified: {metadata['modifiedTime']}")
```

## API Reference

### `GoogleDriveConnector(credentials_path, token_path)`

Initialize the Google Drive connector.

**Parameters:**
- `credentials_path` (str): Path to Google API credentials JSON file
- `token_path` (str): Path to store/load authentication token

### `authenticate() -> bool`

Authenticate with Google Drive API using OAuth 2.0 flow.

**Returns:**
- `bool`: True if authentication successful, False otherwise

**Notes:**
- Automatically handles token refresh if expired
- Opens browser on first authentication
- Saves token for future use

### `list_files(folder_id, file_pattern=None) -> List[Dict]`

List files in a Google Drive folder.

**Parameters:**
- `folder_id` (str): Google Drive folder ID
- `file_pattern` (str, optional): Filename pattern (e.g., "*.csv", "csob_*.csv")

**Returns:**
- `List[Dict]`: List of dictionaries with keys:
  - `id`: File ID
  - `name`: Filename
  - `modified_time`: Last modified timestamp
  - `mime_type`: MIME type

**Example:**
```python
files = drive.list_files("folder123", file_pattern="*.csv")
```

### `download_file(file_id, destination) -> bool`

Download a file from Google Drive to local path.

**Parameters:**
- `file_id` (str): Google Drive file ID
- `destination` (str): Local destination path

**Returns:**
- `bool`: True if download successful, False otherwise

**Notes:**
- Creates destination directory if it doesn't exist
- Shows download progress in logs

### `get_file_content(file_id) -> Optional[bytes]`

Get file content directly without saving to disk.

**Parameters:**
- `file_id` (str): Google Drive file ID

**Returns:**
- `bytes`: File content, or None if error

**Use Case:**
- Good for small files
- Process content in memory without disk I/O

### `get_file_metadata(file_id) -> Optional[Dict]`

Get file metadata from Google Drive.

**Parameters:**
- `file_id` (str): Google Drive file ID

**Returns:**
- `Dict`: File metadata with keys:
  - `id`: File ID
  - `name`: Filename
  - `mimeType`: MIME type
  - `modifiedTime`: Last modified timestamp
  - `size`: File size in bytes
  - `createdTime`: Creation timestamp

## Finding Folder/File IDs

### Folder ID
1. Open the folder in Google Drive web interface
2. Look at the URL: `https://drive.google.com/drive/folders/YOUR_FOLDER_ID`
3. Copy the ID after `/folders/`

### File ID
1. Right-click file in Google Drive
2. Select "Get link"
3. URL format: `https://drive.google.com/file/d/YOUR_FILE_ID/view`
4. Or use `list_files()` to get IDs programmatically

## Error Handling

The connector includes comprehensive error handling:

```python
from src.connectors.google_drive import GoogleDriveConnector
from src.utils import setup_logger

# Enable logging to see errors
logger = setup_logger(level='INFO', console=True)

drive = GoogleDriveConnector(credentials_path, token_path)

# All methods return False/None on error
if not drive.authenticate():
    logger.error("Check credentials file exists")

files = drive.list_files(folder_id)
if not files:
    logger.error("Check folder ID and permissions")
```

## Testing

Run the test script to verify your setup:

```bash
python scripts/test_drive_connection.py
```

This will:
1. Test authentication
2. List all files in your configured folder
3. Filter files by pattern (ČSOB, Partners, Wise)
4. Display results

## Troubleshooting

### "Credentials file not found"
- Ensure `google_credentials.json` exists in `data/credentials/`
- Check the path matches your configuration

### "Authentication failed"
- Delete `token.pickle` and re-authenticate
- Verify Google Drive API is enabled in Cloud Console
- Check OAuth consent screen is configured

### "No files found"
- Verify folder ID is correct
- Check folder permissions (must be accessible by authenticated user)
- Ensure files are not in trash

### "HTTP 404 error"
- File or folder ID is invalid
- File may have been deleted
- User doesn't have access to the file

## Permissions

The connector requests `drive.readonly` scope, which allows:
- ✓ List files
- ✓ Download files
- ✓ Read metadata
- ✗ Upload/modify/delete files

For upload/modification, change `SCOPES` in the code.

## Best Practices

1. **Token Management**: Keep `token.pickle` secure, don't commit to git
2. **Error Handling**: Always check return values
3. **Logging**: Enable logging for debugging
4. **Rate Limits**: Be aware of Google API quotas
5. **Pattern Matching**: Use specific patterns to reduce API calls

## Integration Example

Complete example from config to download:

```python
import yaml
from src.connectors.google_drive import GoogleDriveConnector
from src.utils import setup_logger

# Load config
with open('config/settings.yaml') as f:
    config = yaml.safe_load(f)

# Setup logger
logger = setup_logger(level=config['logging']['level'])

# Initialize connector
drive = GoogleDriveConnector(
    config['google_drive']['credentials_path'],
    config['google_drive']['token_path']
)

# Authenticate
if not drive.authenticate():
    logger.error("Authentication failed")
    exit(1)

# Get folder from config
folder_id = config['google_drive']['input_folder_id']

# List ČSOB files
csob_files = drive.list_files(folder_id, file_pattern="csob_*.csv")

# Download each file
for file in csob_files:
    destination = f"data/temp/{file['name']}"
    logger.info(f"Downloading {file['name']}...")

    if drive.download_file(file['id'], destination):
        logger.info(f"✓ Downloaded to {destination}")
    else:
        logger.error(f"✗ Failed to download {file['name']}")
```

## Next Steps

After setting up the Google Drive connector:
1. Implement `google_sheets.py` connector
2. Test with your actual Drive folder
3. Proceed to implement file parsers
4. Integrate into main processing pipeline
