# services/maigret_service.py
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

import maigret
from maigret.sites import MaigretDatabase

logger = logging.getLogger("maigret")
logger.setLevel(logging.WARNING)

# Locate Maigret's data.json inside the installed package
# This should work regardless of where your venv is
MAIGRET_DB_FILE = (
    Path(maigret.__file__).resolve().parent / "resources" / "data.json"
)

def _load_sites(
    top_sites: int,
    tags: Optional[List[str]] = None,
    site_list: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Load Maigret sites DB and filter by top/tags/site_list."""
    db = MaigretDatabase().load_from_path(str(MAIGRET_DB_FILE))

    tags = tags or []
    site_list = site_list or []

    sites = db.ranked_sites_dict(
        top=top_sites,
        tags=tags,
        names=site_list,
        disabled=False,
        id_type="username",
    )
    return sites


async def maigret_search_username(
    username: str,
    top_sites: int = 200,
    timeout: int = 30,
    tags: Optional[List[str]] = None,
    site_list: Optional[List[str]] = None,
    use_cookies: bool = False,
) -> Dict[str, Any]:
    """
    Run Maigret.search() for a single username and return JSON-friendly results.
    This is an async function you can await in FastAPI.
    """
    sites = _load_sites(top_sites=top_sites, tags=tags, site_list=site_list)

    cookies_file = "cookies.txt" if use_cookies else None

    # This is the important part: call maigret.search()
    raw_results: Dict[str, Any] = await maigret.search(
        username=username,
        site_dict=sites,
        timeout=timeout,
        logger=logger,
        id_type="username",
        cookies=cookies_file,
        is_parsing_enabled=True,
        recursive_search_enabled=True,
        check_domains=False,
        proxy=None,
        tor_proxy=None,
        i2p_proxy=None,
    )

    # Convert raw_results into JSON-serializable structure
    # raw_results is a dict[site_name -> site_data]
    sites_found = []
    sites_not_found = []

    for site_name, site_data in raw_results.items():
        status_obj = site_data.get("status")
        status_str = None
        tags_list: List[str] = []

        if status_obj is not None:
            # status_obj is a MaigretCheck instance; we just stringify it
            # and try to extract tags if present
            status_str = getattr(status_obj, "status", None)
            tags_list = list(getattr(status_obj, "tags", []) or [])

        entry = {
            "site": site_name,
            "url_main": site_data.get("url_main"),
            "url_user": site_data.get("url_user"),
            "category": site_data.get("category"),
            "status": status_str,
            "tags": tags_list,
        }

        if status_str and str(status_str).lower() in {"claimed", "found"}:
            sites_found.append(entry)
        else:
            sites_not_found.append(entry)

    return {
        "username": username,
        "sites_found": sites_found,
        "sites_not_found": sites_not_found,
        "total_sites_checked": len(raw_results),
    }
