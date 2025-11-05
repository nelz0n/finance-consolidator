"""
File Scanner - Auto-discovers files from Google Drive and matches them to institutions

Scans Google Drive folder for files and matches them against institution filename patterns.
Returns structured list of files with their matched institutions for processing.
"""

import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
from fnmatch import fnmatch
import yaml

from ..connectors.google_drive import GoogleDriveConnector

logger = logging.getLogger(__name__)


class FileScanner:
    """
    Scans Google Drive for files and matches them to institution configurations.

    Attributes:
        drive: GoogleDriveConnector instance
        institutions_config: Loaded institution configurations
        config_dir: Path to institution config directory
    """

    def __init__(self, drive: GoogleDriveConnector, config_dir: str = "config/institutions"):
        """
        Initialize the file scanner.

        Args:
            drive: GoogleDriveConnector instance
            config_dir: Path to directory containing institution YAML configs
        """
        self.drive = drive
        self.config_dir = Path(config_dir)
        self.institutions_config = {}

        # Load all institution configurations
        self._load_institution_configs()

    def _load_institution_configs(self) -> None:
        """Load all institution YAML configuration files."""
        if not self.config_dir.exists():
            logger.warning(f"Institution config directory not found: {self.config_dir}")
            return

        yaml_files = list(self.config_dir.glob("*.yaml")) + list(self.config_dir.glob("*.yml"))

        for yaml_file in yaml_files:
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)

                institution_name = config.get('institution', {}).get('name')
                if institution_name:
                    self.institutions_config[institution_name] = config
                    logger.info(f"Loaded configuration for institution: {institution_name}")
                else:
                    logger.warning(f"No institution name found in {yaml_file.name}")

            except Exception as e:
                logger.error(f"Error loading institution config {yaml_file.name}: {e}")

        logger.info(f"Loaded {len(self.institutions_config)} institution configurations")

    def _match_file_to_institution(self, filename: str) -> Optional[str]:
        """
        Match a filename against institution patterns.

        Args:
            filename: Name of the file to match

        Returns:
            Institution name if matched, None otherwise
        """
        for institution_name, config in self.institutions_config.items():
            patterns = config.get('file_detection', {}).get('filename_patterns', [])

            for pattern in patterns:
                if fnmatch(filename.lower(), pattern.lower()):
                    logger.debug(f"File '{filename}' matched pattern '{pattern}' for {institution_name}")
                    return institution_name

        logger.debug(f"File '{filename}' did not match any institution patterns")
        return None

    def scan_files(self, folder_id: str, enabled_institutions: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Scan Google Drive folder and return files matched to institutions.

        Args:
            folder_id: Google Drive folder ID to scan
            enabled_institutions: Optional list of institution names to filter by.
                                If None or empty, all institutions are processed.

        Returns:
            List of dictionaries with file info and matched institution:
            [
                {
                    'file_id': 'abc123',
                    'filename': 'csob_export.csv',
                    'institution': 'ČSOB',
                    'config': {...},  # Full institution config
                    'mime_type': 'text/csv',
                    'size': 12345,
                    'modified_time': '2024-10-15T10:30:00Z'
                },
                ...
            ]
        """
        logger.info(f"Scanning Google Drive folder: {folder_id}")

        try:
            # Get all files from the folder
            all_files = self.drive.list_files(folder_id)
            logger.info(f"Found {len(all_files)} total files in Drive folder")

            matched_files = []
            unmatched_files = []

            for file_info in all_files:
                filename = file_info.get('name', '')

                # Match file to institution
                institution_name = self._match_file_to_institution(filename)

                if institution_name:
                    # Check if institution is enabled
                    if enabled_institutions and institution_name not in enabled_institutions:
                        logger.debug(f"Skipping {filename}: institution {institution_name} not enabled")
                        continue

                    # Add institution info to file data
                    file_data = {
                        'file_id': file_info.get('id'),
                        'filename': filename,
                        'institution': institution_name,
                        'config': self.institutions_config[institution_name],
                        'mime_type': file_info.get('mimeType'),
                        'size': file_info.get('size'),
                        'modified_time': file_info.get('modifiedTime')
                    }
                    matched_files.append(file_data)
                    logger.info(f"✓ Matched: {filename} → {institution_name}")
                else:
                    unmatched_files.append(filename)

            # Log summary
            logger.info(f"\nScan Summary:")
            logger.info(f"  Total files: {len(all_files)}")
            logger.info(f"  Matched: {len(matched_files)}")
            logger.info(f"  Unmatched: {len(unmatched_files)}")

            if unmatched_files:
                logger.warning(f"Unmatched files: {', '.join(unmatched_files)}")

            # Group by institution
            by_institution = {}
            for file in matched_files:
                inst = file['institution']
                by_institution[inst] = by_institution.get(inst, 0) + 1

            logger.info("Files by institution:")
            for inst, count in by_institution.items():
                logger.info(f"  {inst}: {count} files")

            return matched_files

        except Exception as e:
            logger.error(f"Error scanning files: {e}")
            raise

    def get_institution_config(self, institution_name: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific institution.

        Args:
            institution_name: Name of the institution

        Returns:
            Institution configuration dict or None if not found
        """
        return self.institutions_config.get(institution_name)

    def list_institutions(self) -> List[str]:
        """
        Get list of all loaded institution names.

        Returns:
            List of institution names
        """
        return list(self.institutions_config.keys())


def scan_drive_files(drive: GoogleDriveConnector,
                     folder_id: str,
                     config_dir: str = "config/institutions",
                     enabled_institutions: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Convenience function to scan files in one call.

    Args:
        drive: GoogleDriveConnector instance
        folder_id: Google Drive folder ID
        config_dir: Path to institution configs
        enabled_institutions: Optional list of enabled institutions

    Returns:
        List of matched files with institution info
    """
    scanner = FileScanner(drive, config_dir)
    return scanner.scan_files(folder_id, enabled_institutions)
