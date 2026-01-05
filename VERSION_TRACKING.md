# Version Tracking Guide

## Overview
The application now includes comprehensive version tracking to help you identify which code version is running at all times.

## Where to See Version Info

### 1. Web UI (Sidebar Footer)
Open the app in your browser - version info appears at the bottom of the sidebar:
```
Version:  459f413
Branch:   main
Built:    2026-01-05
```

### 2. API Endpoint
```bash
curl http://localhost:8000/api/v1/version
```

Returns:
```json
{
  "commit": "459f413",
  "branch": "main",
  "build_time": "2026-01-05 17:02:07 UTC",
  "environment": "development"
}
```

## Docker Image Tags

When GitHub Actions builds your Docker image, it creates multiple tags:

1. **`latest`** - Always points to the most recent main branch build
2. **`main`** - Latest commit on main branch
3. **`main-459f413`** - Specific commit SHA (short form)

### Example: Pulling a Specific Version
```bash
# Pull latest
docker pull ghcr.io/nelz0n/finance-consolidator:latest

# Pull specific commit
docker pull ghcr.io/nelz0n/finance-consolidator:main-459f413
```

## How to Verify Your Running Version

### Local Development
1. Open http://localhost:5173
2. Check sidebar footer - shows your current git commit
3. If you make changes, the commit hash updates when you commit

### Docker/NAS Deployment
1. Open your deployed app (e.g., http://nas:8000)
2. Check sidebar footer - shows the commit from when image was built
3. Compare with GitHub to see if you're on latest:
   - Go to https://github.com/nelz0n/finance-consolidator/commits/main
   - First commit hash should match what's in your sidebar

### Quick Check Script
```bash
# Check what's running locally
curl -s http://localhost:8000/api/v1/version | jq -r '.commit'

# Check what's running on your NAS (replace with your NAS URL)
curl -s http://your-nas-url:8000/api/v1/version | jq -r '.commit'

# Compare with latest GitHub commit
git log -1 --format="%h"
```

## Workflow

### 1. Make Changes Locally
```bash
# Your changes are in files...
# Version shows current commit (e.g., 459f413)
```

### 2. Commit and Push
```bash
git add .
git commit -m "Your changes"
git push origin main
# New commit created (e.g., abc1234)
```

### 3. GitHub Actions Build
- Automatically triggered on push to main
- Builds Docker image with version info embedded
- Tags image: `main-abc1234`
- Pushes to GitHub Container Registry

### 4. Deploy to NAS
```bash
# Pull latest image
docker pull ghcr.io/nelz0n/finance-consolidator:latest

# Restart container
docker-compose down
docker-compose up -d
```

### 5. Verify Deployment
1. Open app in browser
2. Check sidebar footer shows `abc1234`
3. Confirm it matches latest GitHub commit

## Troubleshooting

### Version Showing "unknown"
- **Local**: Git not installed or not in PATH
- **Docker**: Build args not passed correctly (check GitHub Actions logs)

### Version Not Updating After Pull
- Make sure you're pulling the correct tag
- Restart the container after pulling
- Check Docker image ID: `docker images | grep finance-consolidator`

### Different Version in UI vs API
- This shouldn't happen - both read from same source
- Clear browser cache and hard refresh (Ctrl+F5)
- Restart backend server

## Technical Details

### Environment Variables (Docker)
The following are set at build time:
- `GIT_COMMIT_SHA`: Full commit hash from GitHub
- `GIT_BRANCH`: Branch name (usually "main")
- `BUILD_TIMESTAMP`: When the image was built
- `ENVIRONMENT`: Set to "production" in Docker

### Source Code
- `backend/utils/version.py`: Version detection logic
- `backend/app.py`: GET /api/v1/version endpoint
- `frontend/src/components/layout/Layout.svelte`: UI display
- `.github/workflows/docker-publish.yml`: CI/CD configuration
- `Dockerfile`: Build args and environment setup
