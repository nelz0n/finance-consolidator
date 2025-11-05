# Gemini Code Assistant Context

This document provides context for the Gemini Code Assistant to understand the "Finance Consolidator" project.

## Project Overview

This is a Python project designed to consolidate financial data from multiple sources into a single Google Sheet. It is intended to be run as a script that connects to Google Drive to find input files, parses them according to institution-specific configurations, normalizes the data into a common format, and then writes the data to a Google Sheet.

The project is currently partially implemented. The core structure, data models, and configuration are in place, but the main application logic for connecting, parsing, and writing data needs to be completed.

**Technologies:**

*   Python 3.8+
*   Google Drive API
*   Google Sheets API
*   Pandas
*   openpyxl
*   PyYAML

**Architecture:**

The application follows a modular architecture:

*   **Connectors:** Modules to interact with Google Drive and Google Sheets APIs.
*   **File Scanner:** A component to identify and download relevant transaction files from a specified Google Drive folder.
*   **Parsers:** Institution-specific parsers to handle different file formats (e.g., ČSOB CSV, Partners Bank XLSX).
*   **Normalizer:** A component to transform the raw parsed data into a standardized `Transaction` data model.
*   **Writer:** A component to write the normalized `Transaction` objects to a Google Sheet.
*   **Configuration:** The application is configured using YAML files located in the `config` directory. `settings.yaml` contains global settings, and the `config/institutions` directory holds configurations for each financial institution.

## Building and Running

### Installation

1.  Create and activate a Python virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```
2.  Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```

### Configuration

1.  **Google API Credentials:**
    *   Enable the Google Drive and Google Sheets APIs in your Google Cloud project.
    *   Create OAuth 2.0 credentials for a Desktop application.
    *   Download the credentials JSON file and save it as `data/credentials/google_credentials.json`.
2.  **Settings:**
    *   Edit `config/settings.yaml` to provide your Google Drive folder ID and Google Sheets spreadsheet ID.
    *   Update the owner mappings in the institution-specific configuration files in `config/institutions/`.

### Running the Application

The main entry point for the application is `src/main.py`. Once the implementation is complete, it can be run as follows:

*   **Process all files:**
    ```bash
    python -m src.main
    ```
*   **Perform a dry run (without writing to Google Sheets):**
    ```bash
    python -m src.main --dry-run
    ```
*   **Process files for a specific institution:**
    ```bash
    python -m src.main --institution csob
    ```
*   **Process files within a specific date range:**
    ```bash
    python -m src.main --from-date 2024-10-01 --to-date 2024-10-31
    ```

## Development Conventions

*   **Code Structure:** The source code is organized in the `src` directory, with subdirectories for `core` logic, `connectors`, `models`, and `utils`.
*   **Configuration:** All configuration is externalized into YAML files in the `config` directory.
*   **Data Models:** The project uses data models defined in `src/models` (e.g., `Transaction`, `Balance`) to represent the data.
*   **Implementation Guide:** The `IMPLEMENTATION_GUIDE.md` file outlines the remaining work to be done. Refer to this file for details on the functions and classes that need to be implemented.
*   **Testing:** The `scripts` directory contains helper scripts for testing configurations and other parts of the application.
