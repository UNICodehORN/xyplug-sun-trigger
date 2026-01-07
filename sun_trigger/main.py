#!/usr/bin/env python3

def main():
    import sys
    import json
    import requests
    from datetime import datetime, timedelta
    from pathlib import Path
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

    DEFAULT_TIMEZONE = "UTC"
    DEFAULT_CACHE_DIR = Path("/tmp")
    API_URL = "https://api.sunrise-sunset.org/json"

    data = json.load(sys.stdin)
    response = {"xy": 1, "items": []}

    def load_sun_times(lat, lng, date_str, cache_dir: Path):
        cache_file = cache_dir / "sun_cache.json"

        if cache_file.exists():
            try:
                cache = json.loads(cache_file.read_text(encoding="utf-8"))
                if (
                    cache.get("lat") == lat
                    and cache.get("lng") == lng
                    and cache.get("date") == date_str
                ):
                    return cache["results"]
            except Exception:
                pass

        r = requests.get(
            API_URL,
            params={
                "lat": lat,
                "lng": lng,
                "date": date_str,
                "formatted": 0
            },
            timeout=5
        )
        r.raise_for_status()
        results = r.json()["results"]

        cache_file.write_text(
            json.dumps(
                {"lat": lat, "lng": lng, "date": date_str, "results": results}
            ),
            encoding="utf-8"
        )

        return results

    for item in data.get("items", []):
        dargs = item.get("dargs", {})
        params = item.get("params", {})

        tz_name = item.get("timezone", DEFAULT_TIMEZONE)
        try:
            tz = ZoneInfo(tz_name)
        except ZoneInfoNotFoundError:
            tz = ZoneInfo(DEFAULT_TIMEZONE)

        lat = params.get("latitude") or params.get("lat")
        lng = params.get("longitude") or params.get("lng")
        execute_after = params.get("executeAfter")  # "Sunrise" | "Sunset"
        offset_minutes = int(params.get("offsetInMinutes", 0))
        cache_dir = Path(params.get("cachingDir", DEFAULT_CACHE_DIR))

        if lat is None or lng is None or execute_after not in ("Sunrise", "Sunset"):
            response["items"].append({"launch": False})
            continue

        year = int(dargs["year"])
        month = int(dargs["month"])
        day = int(dargs["day"])
        hour = int(dargs["hour"])
        minute = int(dargs["minute"])

        job_time = datetime(year, month, day, hour, minute, tzinfo=tz)
        date_str = f"{year:04d}-{month:02d}-{day:02d}"

        try:
            sun = load_sun_times(lat, lng, date_str, cache_dir)
        except Exception as e:
            print(f"Sun API error: {e}", file=sys.stderr)
            response["items"].append({"launch": False})
            continue

        if execute_after == "Sunrise":
            base_utc = datetime.fromisoformat(sun["sunrise"].replace("Z", "+00:00"))
        else:
            base_utc = datetime.fromisoformat(sun["sunset"].replace("Z", "+00:00"))

        base_local = base_utc.astimezone(tz) + timedelta(minutes=offset_minutes)

        response["items"].append(
            {"launch": job_time >= base_local}
        )

    print(json.dumps(response))


if __name__ == "__main__":
    main()

