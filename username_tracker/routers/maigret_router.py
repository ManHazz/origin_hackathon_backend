# routers/maigret_router.py

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from username_tracker.services.maigret_service import maigret_search_username

router = APIRouter(prefix="/maigret", tags=["maigret"])


@router.get("/search")
async def search_username(
    username: str = Query(..., description="Username to search (OSINT)"),
    top_sites: int = Query(200, ge=1, le=500),
    timeout: int = Query(30, ge=5, le=120),
    tags: Optional[List[str]] = Query(None, description="Filter sites by tags"),
    site_list: Optional[List[str]] = Query(
        None, description="Explicit list of site names to check"
    ),
    use_cookies: bool = Query(False),
):
    """
    Perform username OSINT lookup using Maigret and return JSON data only.
    """
    try:
        data = await maigret_search_username(
            username=username,
            top_sites=top_sites,
            timeout=timeout,
            tags=tags,
            site_list=site_list,
            use_cookies=use_cookies,
        )
        return data
    except Exception as e:
        # You can log e here
        raise HTTPException(status_code=500, detail=str(e))
