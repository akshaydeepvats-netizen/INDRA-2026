"""RainViewer public radar-map fallback.

RainViewer provides rendered radar tiles and timestamps only.
It is not an official warning feed or calibrated rainfall data.
"""
import logging
from . import net

log = logging.getLogger("indra.rainviewer")

API_URL = "https://api.rainviewer.com/public/weather-maps.json"
FEED = "rainviewer"


def frames(limit=12):
    """Return RainViewer radar frames and fetch metadata."""
    data, meta = net.get(
        API_URL,
        ttl=300,
        feed=FEED,
        timeout=20
    )

    if not isinstance(data, dict):
        return None, meta

    host = str(data.get("host") or "").rstrip("/")
    past = (data.get("radar") or {}).get("past") or []

    if not host.startswith("https://") or not isinstance(past, list):
        net.feed_mark(
            FEED, False,
            error="Invalid RainViewer metadata"
        )
        return None, {
            "status": "UNAVAILABLE",
            "error": "Invalid RainViewer metadata"
        }

    normalized = []

    for item in past:
        try:
            timestamp = int(item["time"])
            path = str(item["path"])

            if not path.startswith("/v2/radar/") or ".." in path:
                continue

            tile_url = (
                f"{host}{path}/256/"
                "{z}/{x}/{y}/2/1_1.png"
            )

            normalized.append({
                "time": timestamp,
                "tiles": tile_url
            })

        except (KeyError, TypeError, ValueError):
            continue

    normalized.sort(key=lambda x: x["time"])
    normalized = normalized[-max(1, min(int(limit), 12)):]

    if not normalized:
        return None, {
            "status": "UNAVAILABLE",
            "error": "No RainViewer radar frames available"
        }

    return {
        "status": (
            "LIVE"
            if meta.get("status") in ("LIVE", "CACHED")
            else meta.get("status", "STALE")
        ),
        "provider": "RainViewer public weather radar API",
        "frames": normalized,
        "max_zoom": 7,
        "units": "Provider-rendered radar imagery; not calibrated mm/h",
        "attribution": (
            'Weather data by <a href="https://www.rainviewer.com/" '
            'target="_blank" rel="noopener">RainViewer</a>'
        ),
        "notice": (
            "RainViewer fallback radar imagery. Past frames only. "
            "Not an official warning, not NASA GPM IMERG, "
            "not calibrated rain rate, and not IMD DWR."
        )
    }, meta
