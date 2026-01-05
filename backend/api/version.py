"""Version information API"""
from fastapi import APIRouter
from backend.utils.version import get_version_info

router = APIRouter()


@router.get("/")
async def get_version():
    """
    Get application version information.

    Returns:
        - commit: Git commit hash (short)
        - branch: Git branch name
        - build_time: Build timestamp
        - environment: Deployment environment (development/production)
    """
    return get_version_info()
