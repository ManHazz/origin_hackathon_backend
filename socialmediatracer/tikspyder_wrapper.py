# tikspyder_wrapper.py
import asyncio
import os
import time
import glob
import math

import pandas as pd  # or use csv module if you don't want pandas

from socialmediatracer.utils import (
    get_config_attrs,
    verify_date_argument,
    create_output_data_path,
    get_project_root,
)
from socialmediatracer.data_collectors import TikTokDataCollector

def _ensure_event_loop():
    """
    Ensure the current thread has an asyncio event loop.
    Maigret/TikSpyder internally calls asyncio.get_event_loop(),
    which on Python 3.11+ raises if no loop is set in this thread.
    """
    try:
        # If there is a running loop, we’re fine
        asyncio.get_running_loop()
    except RuntimeError:
        # No loop in this thread → create and set one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

def _json_safe(obj):
    """
    Recursively replace NaN/inf with None so json.dumps won't crash.
    """
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(x) for x in obj]
    return obj

def fetch_tiktok_by_query(
    query: str,
    *,
    use_apify: bool = False,
    number_of_results: int = 25,
    after: str | None = None,   # 'YYYY-MM-DD' or None
    before: str | None = None,  # 'YYYY-MM-DD' or None
    output_dir: str | None = None,
) -> list[dict]:
    """
    Run TikSpyder for a keyword search and return all rows from the
    generated CSVs as a list of dicts.
    """
    _ensure_event_loop()
    # Locate project root and config directory
    project_root = get_project_root()
    config_dir = os.path.join(project_root, "config")

    # Load API keys & other config
    config_attrs = get_config_attrs(config_dir)

    # Build args similarly to main.py
    args = {
        # SerpAPI options
        "q": query,
        "user": None,
        "tag": None,
        "google_domain": "google.com",
        "gl": None,
        "hl": None,
        "cr": None,
        "safe": "active",
        "lr": None,
        "depth": 3,

        # Google advanced search
        "before": before,
        "after": after,

        # Apify options
        "apify": use_apify,
        "oldest_post_date": None,
        "newest_post_date": None,
        "number_of_results": number_of_results,

        # Optional arguments
        "use_tor": False,
        "download": False,          # we just want metadata
        "max_workers": None,
        "app": False,
    }

    # Choose output directory (same default pattern as CLI)
    if output_dir is None:
        output_dir = os.path.join(
            project_root,
            "tikspyder-data",
            str(int(time.time())),
        )
    args["output"] = output_dir

    # Merge config.ini values (API keys etc.)
    args.update(config_attrs)

    # Validate any dates we passed in
    for key in ("before", "after"):
        if args[key]:
            verify_date_argument(args, key)

    # Ensure output path exists
    create_output_data_path(output_dir)

    # Run the collector (same calls as in main.py)
    collector = TikTokDataCollector(args=args)
    collector.collect_search_data()
    collector.generate_data_files()

    # Collect all CSV rows into a single list of dicts
    csv_files = glob.glob(os.path.join(output_dir, "*.csv"))
    all_rows: list[dict] = []

    for path in csv_files:
        df = pd.read_csv(path)
        all_rows.extend(df.to_dict("records"))

    return _json_safe(all_rows)
