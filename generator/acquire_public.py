"""Acquire and cache public S1-S3 reference inputs for Bangladesh.

Sources:
- geoBoundaries gbOpen, BGD ADM2, simplified GeoJSON
- WorldPop Global2 API v2, 2022 age/sex estimates by ADM2 polygon
- Open-Meteo Historical Weather API, ERA5-Land daily district-centroid series
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

BOUNDARY_API = "https://www.geoboundaries.org/api/current/gbOpen/BGD/ADM2/"
WORLDPOP_API = "https://api.worldpop.org/v2"
WEATHER_API = "https://archive-api.open-meteo.com/v1/archive"
DISTRICTS = [
    "Bagerhat", "Bandarban", "Barguna", "Barishal", "Bhola", "Bogura",
    "Brahmanbaria", "Chandpur", "Chapainawabganj", "Chattogram", "Chuadanga",
    "Cox's Bazar", "Cumilla", "Dhaka", "Dinajpur", "Faridpur", "Feni",
    "Gaibandha", "Gazipur", "Gopalganj", "Habiganj", "Joypurhat", "Jamalpur",
    "Jashore", "Jhalokati", "Jhenaidah", "Khagrachhari", "Khulna",
    "Kishoreganj", "Kurigram", "Kushtia", "Lakshmipur", "Lalmonirhat",
    "Madaripur", "Magura", "Manikganj", "Meherpur", "Moulvibazar",
    "Munshiganj", "Mymensingh", "Naogaon", "Narail", "Narayanganj",
    "Narsingdi", "Natore", "Netrokona", "Nilphamari", "Noakhali", "Pabna",
    "Panchagarh", "Patuakhali", "Pirojpur", "Rajbari", "Rajshahi",
    "Rangamati", "Rangpur", "Satkhira", "Shariatpur", "Sherpur", "Sirajganj",
    "Sunamganj", "Sylhet", "Tangail", "Thakurgaon"
]
ALIASES = {
    "barisal": "Barishal", "bogra": "Bogura", "brahamanbaria": "Brahmanbaria", "chittagong": "Chattogram",
    "comilla": "Cumilla", "jessore": "Jashore", "jhalakathi": "Jhalokati",
    "jaipurhat": "Joypurhat", "nawabganj": "Chapainawabganj", "maulvibazar": "Moulvibazar", "netrakona": "Netrokona",
}

def norm(value):
    return re.sub(r"[^a-z0-9]", "", str(value).lower())

def canonical_district(name):
    key = norm(name)
    alias = {norm(k): v for k, v in ALIASES.items()}
    canonical = {norm(d): d for d in DISTRICTS}
    return alias.get(key, canonical.get(key))

def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def request_json(session, url, **kwargs):
    response = session.get(url, timeout=120, **kwargs)
    response.raise_for_status()
    return response.json()

def start_worldpop_task(session, district, geometry, cache_path):
    if cache_path.exists():
        cached = json.loads(cache_path.read_text(encoding="utf-8"))
        if cached.get("status") == "success" and "result" in cached:
            return {"result": cached["result"], "cache_path": cache_path}
    response = session.post(
        f"{WORLDPOP_API}/agesex",
        json={"geojson": geometry, "year": 2022, "age_range": [0, 90],
              "sex": "both", "resolution": "1km"},
        timeout=120,
    )
    response.raise_for_status()
    submitted = response.json()
    task_id = submitted.get("task_id") or submitted.get("taskid")
    if not task_id:
        raise RuntimeError(f"WorldPop did not return a task ID for {district}: {submitted}")
    return {"task_id": task_id, "cache_path": cache_path}

def poll_worldpop_task(district, task_id, cache_path):
    deadline = time.monotonic() + 900
    with requests.Session() as session:
        session.headers.update({"User-Agent": "EpiScope-CSE4345/1.0 (student coursework)"})
        while time.monotonic() < deadline:
            result = request_json(session, f"{WORLDPOP_API}/tasks/{task_id}")
            status = str(result.get("status", "")).lower()
            if status == "success":
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path.write_text(json.dumps(result), encoding="utf-8")
                return result["result"]
            if status in {"failure", "failed", "error"}:
                raise RuntimeError(f"WorldPop task failed for {district}: {result}")
            time.sleep(3)
    raise TimeoutError(f"WorldPop task timed out for {district}; rerun to retry.")
def age_start(label):
    found = re.search(r"\d+", str(label))
    if found:
        return int(found.group())
    return None

def population_row(district, result):
    pyramid = result.get("agesex_pyramid", [])
    age_bins = {"age_0_4": 0.0, "age_5_17": 0.0, "age_18_49": 0.0,
                "age_50_64": 0.0, "age_65_plus": 0.0}
    male = 0.0
    female = 0.0
    groups = [(0, 5, "age_0_4"), (5, 18, "age_5_17"),
              (18, 50, "age_18_49"), (50, 65, "age_50_64"),
              (65, 101, "age_65_plus")]
    for item in pyramid:
        m = float(item.get("male", 0) or 0)
        f = float(item.get("female", 0) or 0)
        male += m
        female += f
        start = age_start(item.get("age", item.get("class", "")))
        if start is None:
            continue
        # WorldPop's age bins are usually five-year intervals. Allocate a boundary
        # interval proportionally when it overlaps two of our broader age bands.
        label = str(item.get("age", ""))
        ends = re.findall(r"\d+", label)
        end = int(ends[1]) if len(ends) > 1 else start + 5
        if "+" in label or start >= 90:
            end = 101
        end = max(start + 1, end)
        width = end - start
        for low, high, key in groups:
            overlap = max(0, min(end, high) - max(start, low))
            if overlap:
                age_bins[key] += (m + f) * overlap / width
    total = float(result.get("total_population", male + female) or (male + female))
    return {"district": district, "population": round(total),
            "male_population": round(male), "female_population": round(female),
            **{key: round(value) for key, value in age_bins.items()}}

def walk_positions(value):
    if isinstance(value, (list, tuple)):
        if len(value) >= 2 and isinstance(value[0], (int, float)) and isinstance(value[1], (int, float)):
            yield value[0], value[1]
        else:
            for child in value:
                yield from walk_positions(child)

def centroid(geometry):
    points = list(walk_positions(geometry["coordinates"]))
    if not points:
        raise ValueError("Boundary geometry contains no coordinate pairs")
    return (sum(p[1] for p in points) / len(points),
            sum(p[0] for p in points) / len(points))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data/reference")
    parser.add_argument("--start", default="2021-01-01")
    parser.add_argument("--end", default="2025-12-31")
    parser.add_argument("--request-delay", type=float, default=1.0,
                        help="Seconds between API jobs/requests")
    args = parser.parse_args()
    out = Path(args.out)
    cache = out / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": "EpiScope-CSE4345/1.0 (student coursework)"})

    boundary_meta = request_json(session, BOUNDARY_API)
    boundary_url = boundary_meta.get("simplifiedGeometryGeoJSON") or boundary_meta["gjDownloadURL"]
    boundary_cache = cache / "boundaries.geojson"
    if boundary_cache.exists():
        boundary_data = json.loads(boundary_cache.read_text(encoding="utf-8"))
    else:
        response = session.get(boundary_url, timeout=180)
        response.raise_for_status()
        boundary_data = response.json()
        boundary_cache.write_text(json.dumps(boundary_data), encoding="utf-8")

    features = boundary_data.get("features", [])
    if len(features) != 64:
        raise RuntimeError(f"Expected 64 ADM2 features, received {len(features)}")
    normalized_features = []
    for feature in features:
        props = feature.get("properties", {})
        source_name = props.get("shapeName") or props.get("shapeName_en") or props.get("name")
        district = canonical_district(source_name)
        if not district:
            raise RuntimeError(f"Cannot map geoBoundaries district name: {source_name!r}")
        props["district"] = district
        normalized_features.append(feature)
    boundary_data["features"] = normalized_features
    boundary_path = out / "boundaries.geojson"
    boundary_path.write_text(json.dumps(boundary_data), encoding="utf-8")
    feature_by_district = {f["properties"]["district"]: f for f in normalized_features}
    if set(feature_by_district) != set(DISTRICTS):
        missing = sorted(set(DISTRICTS) - set(feature_by_district))
        raise RuntimeError(f"District boundary mismatch; missing: {missing}")

    population_fields = ["district", "population", "male_population", "female_population",
                         "age_0_4", "age_5_17", "age_18_49", "age_50_64", "age_65_plus"]
    pop_path = out / "population.csv"
    cached_pop = {}
    if pop_path.exists():
        with pop_path.open(encoding="utf-8", newline="") as stream:
            cached_pop = {row["district"]: row for row in csv.DictReader(stream)}
    populations_by_district = {}
    pending = {}
    for district in DISTRICTS:
        if district in cached_pop:
            populations_by_district[district] = cached_pop[district]
            continue
        task_cache = cache / "worldpop" / f"{norm(district)}_2022_agesex.json"
        task_cache.parent.mkdir(parents=True, exist_ok=True)
        pending[district] = start_worldpop_task(
            session, district, feature_by_district[district]["geometry"], task_cache)
        if args.request_delay:
            time.sleep(args.request_delay)

    futures = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        for district, job in pending.items():
            if "result" in job:
                populations_by_district[district] = population_row(district, job["result"])
            else:
                future = pool.submit(poll_worldpop_task, district, job["task_id"], job["cache_path"])
                futures[future] = district
        completed = 0
        for future in as_completed(futures):
            district = futures[future]
            populations_by_district[district] = population_row(district, future.result())
            completed += 1
            if completed % 8 == 0 or completed == len(futures):
                print(f"WorldPop population completed: {completed}/{len(futures)} pending districts")
    populations = [populations_by_district[district] for district in DISTRICTS]
    with pop_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=population_fields)
        writer.writeheader()
        writer.writerows(populations)

    weather_path = out / "weather.csv"
    metadata_path = out / "source_metadata.json"
    previous_metadata = {}
    if metadata_path.exists():
        previous_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    previous_weather = next((item for item in previous_metadata.get("sources", [])
                             if item.get("id") == "S3"), {})
    reuse_weather_csv = (previous_weather.get("start_date") == args.start and
                         previous_weather.get("end_date") == args.end)
    cached_weather = {}
    if reuse_weather_csv and weather_path.exists():
        with weather_path.open(encoding="utf-8", newline="") as stream:
            for row in csv.DictReader(stream):
                cached_weather.setdefault(row["district"], []).append(row)
    weather_rows = []
    for index, district in enumerate(DISTRICTS):
        if district in cached_weather and cached_weather[district]:
            weather_rows.extend(cached_weather[district])
            continue
        lat, lon = centroid(feature_by_district[district]["geometry"])
        weather_cache = cache / "weather" / f"{norm(district)}_{args.start}_{args.end}.json"
        weather_cache.parent.mkdir(parents=True, exist_ok=True)
        if weather_cache.exists():
            payload = json.loads(weather_cache.read_text(encoding="utf-8"))
        else:
            for attempt in range(8):
                response = session.get(WEATHER_API, params={
                    "latitude": f"{lat:.5f}", "longitude": f"{lon:.5f}",
                    "start_date": args.start, "end_date": args.end,
                    "daily": "precipitation_sum,temperature_2m_mean,relative_humidity_2m_mean",
                    "timezone": "Asia/Dhaka", "models": "era5_land"
                }, timeout=180)
                if response.status_code == 429 or response.status_code >= 500:
                    retry_after = response.headers.get("Retry-After")
                    wait_seconds = float(retry_after) if retry_after and retry_after.isdigit() else min(60 * (2 ** attempt), 900)
                    if attempt == 7:
                        response.raise_for_status()
                    print(f"Open-Meteo rate/server limit for {district}; retrying in {wait_seconds:.0f}s (attempt {attempt + 1}/8).")
                    time.sleep(wait_seconds)
                    continue
                response.raise_for_status()
                payload = response.json()
                break
            weather_cache.write_text(json.dumps(payload), encoding="utf-8")
        daily = payload.get("daily", {})
        required = ["time", "precipitation_sum", "temperature_2m_mean",
                    "relative_humidity_2m_mean"]
        if any(key not in daily for key in required):
            raise RuntimeError(f"Open-Meteo response missing daily fields for {district}: {payload}")
        for i, day in enumerate(daily["time"]):
            weather_rows.append({
                "district": district, "date": day,
                "precipitation_mm": daily["precipitation_sum"][i],
                "temperature_c": daily["temperature_2m_mean"][i],
                "relative_humidity_pct": daily["relative_humidity_2m_mean"][i],
                "latitude": round(float(payload["latitude"]), 5),
                "longitude": round(float(payload["longitude"]), 5),
            })
        if args.request_delay:
            time.sleep(args.request_delay)
        if (index + 1) % 8 == 0:
            print(f"Open-Meteo weather completed: {index + 1}/64 districts")
    with weather_path.open("w", encoding="utf-8", newline="") as stream:
        fields = ["district", "date", "precipitation_mm", "temperature_c",
                  "relative_humidity_pct", "latitude", "longitude"]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(weather_rows)

    metadata = {
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "sources": [
            {"dataset": "Administrative boundaries, Bangladesh ADM2",
             "id": "S1", "provider": "geoBoundaries gbOpen",
             "api_url": BOUNDARY_API, "download_url": boundary_url,
             "boundary_year": boundary_meta.get("boundaryYearRepresented"),
             "boundary_source": boundary_meta.get("boundarySource"),
             "license": boundary_meta.get("boundaryLicense"),
             "attribution": "geoBoundaries, William & Mary; CC BY 3.0 IGO"},
            {"dataset": "Population age/sex estimates, Bangladesh, 2022",
             "id": "S2", "provider": "WorldPop Global2 API v2",
             "api_url": f"{WORLDPOP_API}/agesex", "year": 2022,
             "resolution": "1km", "license": "CC BY 4.0",
             "note": "Modelled estimates; not official BBS census counts."},
            {"dataset": "Daily historical weather at district centroids",
             "id": "S3", "provider": "Open-Meteo Historical Weather API",
             "api_url": WEATHER_API, "model": "ERA5-Land",
             "start_date": args.start, "end_date": args.end,
             "variables": ["precipitation_sum", "temperature_2m_mean",
                           "relative_humidity_2m_mean"],
             "license": "CC BY 4.0", "attribution": "Weather data by Open-Meteo.com"}
        ],
        "files": {p.name: {"sha256": sha256(p), "bytes": p.stat().st_size}
                  for p in [boundary_path, pop_path, weather_path]},
        "district_count": 64, "weather_row_count": len(weather_rows)
    }
    (out / "source_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Public S1-S3 reference files ready at {out}: 64 districts, {len(weather_rows):,} daily weather rows.")
if __name__ == "__main__":
    main()







