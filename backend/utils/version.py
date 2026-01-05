"""Version information utility"""
import os
import subprocess
from datetime import datetime
from pathlib import Path


def get_git_commit_hash() -> str:
    """Get current git commit hash (short version)"""
    try:
        # Try to get from environment variable first (set during Docker build)
        commit = os.getenv('GIT_COMMIT_SHA')
        if commit:
            return commit[:7]  # Short hash

        # Fallback to git command for local development
        result = subprocess.run(
            ['git', 'rev-parse', '--short', 'HEAD'],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return 'unknown'


def get_git_branch() -> str:
    """Get current git branch"""
    try:
        # Try to get from environment variable first (set during Docker build)
        branch = os.getenv('GIT_BRANCH')
        if branch:
            return branch

        # Fallback to git command for local development
        result = subprocess.run(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return 'unknown'


def get_build_timestamp() -> str:
    """Get build timestamp"""
    # Try to get from environment variable (set during Docker build)
    timestamp = os.getenv('BUILD_TIMESTAMP')
    if timestamp:
        return timestamp

    # For local development, return current time
    return datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')


def get_version_info() -> dict:
    """Get complete version information"""
    return {
        'commit': get_git_commit_hash(),
        'branch': get_git_branch(),
        'build_time': get_build_timestamp(),
        'environment': os.getenv('ENVIRONMENT', 'development')
    }
