# Docker Deployment Guide

This project is containerized using Docker, allowing you to run the full stack (Frontend + Backend + Database) in a single container. This is ideal for deployment on personal servers or NAS devices (Synology, QNAP, Unraid, etc.).

## Prerequisites

- Docker
- Docker Compose

## Quick Start (Local)

1. **Build and Run:**
   ```bash
   docker-compose up -d --build
   ```

2. **Access the Application:**
   Open [http://localhost:8000](http://localhost:8000) in your browser.

3. **View Logs:**
   ```bash
   docker-compose logs -f
   ```

4. **Stop:**
   ```bash
   docker-compose down
   ```

## Configuration

The application uses the following directories which are mounted as volumes:

- `./config`: Contains configuration files (`settings.yaml`, `accounts.yaml`, `institutions/*.yaml`).
- `./data`: Stores the SQLite database (`finance.db`), uploaded files, logs, and cache.

### Environment Variables

Create a `.env` file in the same directory as `docker-compose.yml`:

```env
GEMINI_API_KEY=your_api_key_here
```

## Deploying to NAS (Synology/QNAP/Unraid)

To run this on your NAS, you generally need to move the necessary files and start the container.

### Option 1: Using Docker Compose (Recommended)

1. **Prepare Directory Structure:**
   Create a folder on your NAS (e.g., `/volume1/docker/finance-consolidator`) and create the following structure:
   ```
   finance-consolidator/
   ├── docker-compose.yml
   ├── config/              # Copy from your local project
   │   ├── settings.yaml
   │   ├── accounts.yaml
   │   └── institutions/
   └── data/                # Empty folder, will be populated by app
   ```

2. **Transfer Files:**
   - Copy `docker-compose.yml` from this repository.
   - Copy the contents of the `config/` directory.

3. **Build or Pull Image:**
   - **Build:** If your NAS supports building (has git/docker-cli), clone the repo and run `docker-compose up -d --build`.
   - **Pre-build:** Build the image on your computer and save it:
     ```bash
     # On your PC
     docker build -t finance-consolidator .
     docker save -o finance-consolidator.tar finance-consolidator
     ```
     Upload `finance-consolidator.tar` to your NAS and load it:
     ```bash
     # On NAS (SSH)
     docker load -i finance-consolidator.tar
     ```
     Then update `docker-compose.yml` to use `image: finance-consolidator:latest` instead of `build: .`.

4. **Start Container:**
   Run `docker-compose up -d` via SSH or use your NAS's Docker GUI (Portainer/Container Manager) to create a stack using the `docker-compose.yml`.

### Option 2: Single Container (No Compose)

If you prefer a single run command:

```bash
docker run -d \
  --name finance-consolidator \
  -p 8000:8000 \
  -v /path/to/data:/app/data \
  -v /path/to/config:/app/config \
  -e GEMINI_API_KEY=your_key \
  finance-consolidator:latest
```

## Troubleshooting

- **Permissions:** If you encounter permission errors on Linux/NAS, ensure the user running Docker has write access to `./data` and `./config`. You can specify a user in `docker-compose.yml` using `user: "1000:1000"`.
- **Port Conflicts:** If port 8000 is taken, change the mapping in `docker-compose.yml` (e.g., `"8080:8000"`).
- **Missing Config:** The application requires valid configuration files in `/app/config`. Ensure you have copied the `config/` directory correctly.
