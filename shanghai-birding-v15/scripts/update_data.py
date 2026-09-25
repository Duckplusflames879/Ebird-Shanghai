#!/usr/bin/env python3
"""Update local external data for the offline Shanghai birding app.

Live sources:
- Weather: Open-Meteo forecast API (no API key required)
- Bird observations: China Bird Report Center (中国观鸟记录中心) public search API.

The Bird Report Center search endpoint is encrypted on the wire. This updater
implements its public request signing/RSA payload encryption and AES response
unwrapping, then normalizes the returned reports into Chinese-only hotspot and
species names.

Observation rules:
- Inclusive seven-calendar-day window ending on the reference day.
- Only records with a real observation start date *and time* are kept.
- One displayed row is produced per (point, species). If the same species was
  recorded repeatedly at the same point, the row uses the latest observation
  time, while preserving occurrence count and summed counts.
- City-level locations are grouped into “其它观测记录” and receive no fake
  coordinates.
- Failed live updates never overwrite an existing successful snapshot.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7

SHANGHAI_LAT = 31.2304
SHANGHAI_LON = 121.4737
SHANGHAI_BBOX = {
    "swlat": 30.65, "swlng": 120.85,
    "nelat": 31.95, "nelng": 122.20,
}

BIRDREPORT_SEARCH_URL = "https://api.birdreport.cn/front/record/activity/search"
BIRDREPORT_TAXON_URL = "https://api.birdreport.cn/front/activity/taxon"
BIRDREPORT_SOURCE_URL = "https://www.birdreport.cn/home/search/page.html"
BIRDREPORT_PUBLIC_KEY_B64 = (
    "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCvxXa98E1uWXnBzXkS2yHUfnBM6n3PCwLdfIox03T91joBvjtoDqiQ5x3tTOfpHs3LtiqMMEafls6b0YWtgB1dse1W5m+FpeusVkCOkQxB4SZDH6tuerIknnmB/Hsq5wgEkIvO5Pff9biig6AyoAkdWpSek/1/B7zYIepYY0lxKQIDAQAB"
)
# The current public endpoint has used these response-encryption key sets in
# public reverse-engineering documentation. We try the current set first,
# then the earlier set for compatibility with older deployed API instances.
BIRDREPORT_AES_CONFIGS = (
    ("C8EB5514AF5ADDB94B2207B08C66601C", "55DD79C6F04E1A67"),
    ("3583ec0257e2f4c8195eec7410ff1619", "d93c0d5ec6352f20"),
)

KNOWN_HOTSPOTS = [
    {"id": "dongtan", "name": "崇明东滩", "district": "崇明区", "lat": 31.52, "lon": 121.99},
    {"id": "nanhui", "name": "南汇东滩", "district": "浦东新区", "lat": 30.90, "lon": 121.95},
    {"id": "binjiang", "name": "滨江森林公园", "district": "浦东新区", "lat": 31.48, "lon": 121.58},
    {"id": "gongqing", "name": "共青森林公园", "district": "杨浦区", "lat": 31.35, "lon": 121.55},
    {"id": "wusong", "name": "吴淞炮台湾湿地森林公园", "district": "宝山区", "lat": 31.38, "lon": 121.49},
    {"id": "xisha", "name": "西沙明珠湖景区", "district": "崇明区", "lat": 31.62, "lon": 121.27},
    {"id": "dongping", "name": "东平国家森林公园", "district": "崇明区", "lat": 31.66, "lon": 121.40},
    {"id": "shanghai_bay", "name": "上海海湾国家森林公园", "district": "奉贤区", "lat": 30.86, "lon": 121.46},
    {"id": "century_park", "name": "世纪公园", "district": "浦东新区", "lat": 31.22, "lon": 121.55},
    {"id": "botanical_garden", "name": "上海植物园", "district": "徐汇区", "lat": 31.14, "lon": 121.45},
]
KNOWN_BY_ID = {spot["id"]: spot for spot in KNOWN_HOTSPOTS}
POINT_ALIASES = {
    "滨江森林公园": "binjiang",
    "滨江森林公园,上海": "binjiang",
    "滨江森林公园,上海市": "binjiang",
    "binjiang forest park": "binjiang",
    "binjiang forest park,shanghai": "binjiang",
    "shanghai binjiang forest park": "binjiang",
    "崇明东滩": "dongtan",
    "东滩": "dongtan",
    "chongming dongtan": "dongtan",
    "dongtan": "dongtan",
    "南汇东滩": "nanhui",
    "nanhui dongtan": "nanhui",
    "共青森林公园": "gongqing",
    "gongqing forest park": "gongqing",
    "吴淞炮台湾湿地森林公园": "wusong",
    "wusong paotaiwan wetland forest park": "wusong",
    "wusong fort bay forest park": "wusong",
    "西沙明珠湖景区": "xisha",
    "xisha pearl lake scenic area": "xisha",
    "xisha pearl lake": "xisha",
    "东平国家森林公园": "dongping",
    "dongping national forest park": "dongping",
    "上海海湾国家森林公园": "shanghai_bay",
    "shanghai bay national forest park": "shanghai_bay",
    "shanghai gulf national forest park": "shanghai_bay",
    "世纪公园": "century_park",
    "century park": "century_park",
    "century park,shanghai": "century_park",
    "上海植物园": "botanical_garden",
    "shanghai botanical garden": "botanical_garden",
    "shanghai botanical garden,shanghai": "botanical_garden",
}

WEATHER_TYPES = {
    0: ("晴", "clear", "☀"), 1: ("大部晴朗", "clear", "🌤"), 2: ("局部多云", "cloudy", "⛅"), 3: ("多云", "cloudy", "☁"),
    45: ("雾", "cloudy", "🌫"), 48: ("雾凇", "cloudy", "🌫"), 51: ("小毛毛雨", "rain", "🌦"), 53: ("毛毛雨", "rain", "🌦"), 55: ("较强毛毛雨", "rain", "🌧"),
    61: ("小雨", "rain", "🌦"), 63: ("中雨", "rain", "🌧"), 65: ("大雨", "rain", "🌧"), 71: ("小雪", "rain", "🌨"), 73: ("中雪", "rain", "🌨"), 75: ("大雪", "rain", "🌨"),
    80: ("阵雨", "rain", "🌦"), 81: ("较强阵雨", "rain", "🌧"), 82: ("强阵雨", "rain", "⛈"), 95: ("雷暴", "rain", "⛈"), 96: ("雷暴伴冰雹", "rain", "⛈"), 99: ("强雷暴伴冰雹", "rain", "⛈"),
}
BIRD_LEXICON_PATH = Path(__file__).resolve().parents[1] / "data" / "birds.js"


def fetch_json(url: str, timeout: int = 30) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": "ShanghaiBirdingMVP/2.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status} from {url}")
        return json.load(response)


def weather_url() -> str:
    params = {
        "latitude": SHANGHAI_LAT, "longitude": SHANGHAI_LON,
        "daily": ",".join(["weather_code", "temperature_2m_max", "temperature_2m_min", "wind_direction_10m_dominant", "wind_speed_10m_max"]),
        "forecast_days": 7, "timezone": "Asia/Shanghai",
    }
    return "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(params)


def wind_level(speed_kmh: float) -> int:
    if speed_kmh < 1: return 0
    if speed_kmh < 5: return 1
    if speed_kmh < 11: return 2
    if speed_kmh < 19: return 3
    if speed_kmh < 28: return 4
    if speed_kmh < 38: return 5
    if speed_kmh < 49: return 6
    if speed_kmh < 61: return 7
    return 8


def wind_direction(degrees: float) -> str:
    dirs = ["北", "东北", "东", "东南", "南", "西南", "西", "西北"]
    return dirs[int((degrees + 22.5) // 45) % 8]


def fetch_weather() -> dict[str, Any]:
    data = fetch_json(weather_url())
    daily = data.get("daily") or {}
    dates = daily.get("time") or []
    codes = daily.get("weather_code") or []
    maxs = daily.get("temperature_2m_max") or []
    mins = daily.get("temperature_2m_min") or []
    winds = daily.get("wind_direction_10m_dominant") or []
    speeds = daily.get("wind_speed_10m_max") or []
    if len(dates) != 7 or any(len(x) < 7 for x in (codes, maxs, mins, winds, speeds)):
        raise RuntimeError("Open-Meteo returned incomplete 7-day forecast")
    forecast = []
    for i in range(7):
        label, kind, icon = WEATHER_TYPES.get(int(codes[i]), ("未知", "cloudy", "—"))
        forecast.append({
            "date": dates[i], "weather": label, "weatherType": kind, "icon": icon,
            "tempMin": round(float(mins[i])), "tempMax": round(float(maxs[i])),
            "windDirection": wind_direction(float(winds[i])), "windLevel": wind_level(float(speeds[i])),
        })
    return {"forecast": forecast}


def load_local_birds() -> dict[str, dict[str, str]]:
    text = BIRD_LEXICON_PATH.read_text(encoding="utf-8")
    matches = re.findall(r'\["([^"]+)","([^"]+)","([^"]+)","([^"]+)"\]', text)
    return {name: {"id": bid, "name": name, "family": family, "genus": genus} for bid, name, family, genus in matches}


def chinese_only(value: str) -> str:
    text = re.sub(r"[（(][^）)]*[）)]", "", str(value or ""))
    text = re.sub(r"\s*(?:Shanghai|China|上海市|上海)\s*$", "", text, flags=re.I)
    han = "".join(re.findall(r"[\u3400-\u4dbf\u4e00-\u9fff]+", text))
    return han.strip()


def normalize_point_name(value: str) -> str:
    raw = str(value or "").strip().replace("，", ",")
    raw = re.sub(r"[（(][^）)]*[）)]", "", raw)
    raw = re.sub(r"\s*(?:,?\s*(?:Shanghai(?:,\s*China)?|上海市|上海))\s*$", "", raw, flags=re.I)
    raw = raw.strip(" ,-/—–")
    compact = re.sub(r"[\s,]+", "", raw).lower()
    if compact in {"shanghai", "shanghaicity", "上海", "上海市"} or not raw:
        return "其它观测记录"
    aliases_compact = {re.sub(r"[\s,]+", "", key).lower(): value for key, value in POINT_ALIASES.items()}
    alias = aliases_compact.get(compact)
    if alias:
        return KNOWN_BY_ID[alias]["name"]
    han = chinese_only(raw)
    if han:
        return han
    return "其它观测记录"


def district_from_name(name: str) -> str:
    districts = ["崇明区", "浦东新区", "杨浦区", "宝山区", "奉贤区", "徐汇区", "黄浦区", "静安区", "虹口区", "长宁区", "普陀区", "闵行区", "嘉定区", "金山区", "松江区", "青浦区"]
    return next((x for x in districts if x in str(name or "")), "上海市")


def coords_from_location(value: Any) -> tuple[float, float] | None:
    text = str(value or "")
    parts = [x.strip() for x in text.split(",")]
    if len(parts) < 2:
        return None
    try:
        lng, lat = float(parts[0]), float(parts[1])
    except ValueError:
        return None
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        return None
    return lat, lng


def request_public_key() -> Any:
    der = base64.b64decode(BIRDREPORT_PUBLIC_KEY_B64)
    return serialization.load_der_public_key(der)


_PUBLIC_KEY = request_public_key()


def sorted_query_json(query_string: str) -> str:
    values: dict[str, str] = {}
    for chunk in query_string.split("&"):
        if "=" in chunk:
            key, value = chunk.split("=", 1)
        else:
            key, value = chunk, ""
        values[key] = value
    ordered = {key: values[key] for key in sorted(values)}
    return json.dumps(ordered, ensure_ascii=True, separators=(",", ":"))


def rsa_encrypt_long(text: str) -> str:
    raw = text.encode("utf-8")
    max_len = _PUBLIC_KEY.key_size // 8 - 11
    chunks: list[bytes] = []
    current = bytearray()
    for char in text:
        encoded = char.encode("utf-8")
        if current and len(current) + len(encoded) > max_len:
            chunks.append(bytes(current))
            current = bytearray()
        current.extend(encoded)
    if current:
        chunks.append(bytes(current))
    if not chunks and raw == b"":
        chunks = [b""]
    encrypted = b"".join(_PUBLIC_KEY.encrypt(chunk, padding.PKCS1v15()) for chunk in chunks)
    return base64.b64encode(encrypted).decode("ascii")


def sign_request(query_string: str) -> tuple[dict[str, str], str]:
    plain = sorted_query_json(query_string)
    timestamp = str(int(datetime.now(timezone.utc).timestamp() * 1000))
    request_id = uuid.uuid4().hex
    sign = hashlib.md5((plain + request_id + timestamp).encode("utf-8")).hexdigest()
    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://www.birdreport.cn",
        "Referer": "https://www.birdreport.cn/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/145.0.0.0 Safari/537.36",
        "requestId": request_id,
        "sign": sign,
        "timestamp": timestamp,
    }
    return headers, rsa_encrypt_long(plain)


def aes_decrypt_text(cipher_b64: str) -> str:
    ciphertext = base64.b64decode(cipher_b64)
    for key_text, iv_text in BIRDREPORT_AES_CONFIGS:
        try:
            decryptor = Cipher(algorithms.AES(key_text.encode()), modes.CBC(iv_text.encode())).decryptor()
            padded = decryptor.update(ciphertext) + decryptor.finalize()
            unpadder = PKCS7(128).unpadder()
            plain = unpadder.update(padded) + unpadder.finalize()
            text = plain.decode("utf-8")
            json.loads(text)
            return text
        except Exception:
            continue
    raise RuntimeError("unable to decrypt China Bird Report Center response")


def birdreport_post(endpoint: str, params: dict[str, str], timeout: int = 30) -> Any:
    query = urllib.parse.urlencode(params)
    headers, encrypted = sign_request(query)
    if os.getenv("BIRDREPORT_AUTH_TOKEN", "").strip():
        headers["X-Auth-Token"] = os.getenv("BIRDREPORT_AUTH_TOKEN", "").strip()
    request = urllib.request.Request(endpoint, data=encrypted.encode("ascii"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                raise RuntimeError(f"China Bird Report Center HTTP {response.status}")
            envelope = json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise RuntimeError(
                f"中国观鸟记录中心拒绝访问（HTTP {exc.code}）。"
                "如果当前部署要求访问令牌，请设置环境变量 BIRDREPORT_AUTH_TOKEN 后重试。"
            ) from exc
        raise RuntimeError(f"中国观鸟记录中心 HTTP {exc.code}") from exc
    if not isinstance(envelope, dict) or "data" not in envelope:
        raise RuntimeError("China Bird Report Center returned an invalid response envelope")
    return json.loads(aes_decrypt_text(str(envelope["data"])))


def search_reports(start: date, end: date, page: int, limit: int = 100) -> Any:
    params = {
        "page": str(page), "limit": str(limit), "taxonid": "",
        "startTime": start.isoformat(), "endTime": end.isoformat(),
        "province": "上海市", "city": "", "district": "", "pointname": "",
        "username": "", "serial_id": "", "ctime": "", "taxonname": "",
        "state": "2", "mode": "0", "outside_type": "0",
    }
    return birdreport_post(BIRDREPORT_SEARCH_URL, params)


def fetch_report_taxa(activity_id: Any) -> list[dict[str, Any]]:
    result = birdreport_post(BIRDREPORT_TAXON_URL, {"page": "1", "limit": "1500", "activityid": str(activity_id)})
    if isinstance(result, list):
        return result
    if isinstance(result, dict):
        for key in ("data", "list", "records"):
            value = result.get(key)
            if isinstance(value, list):
                return value
    return []


def valid_observed_at(value: Any) -> str | None:
    text = str(value or "").strip()
    if not re.search(r"\b\d{1,2}:\d{2}(?::\d{2})?\b", text):
        return None
    text = text.replace("T", " ")
    try:
        datetime.strptime(text[:19], "%Y-%m-%d %H:%M:%S")
        return text[:19]
    except ValueError:
        try:
            return datetime.strptime(text[:16], "%Y-%m-%d %H:%M").strftime("%Y-%m-%d %H:%M")
        except ValueError:
            return None


def normalize_taxon_name(value: Any, local_birds: dict[str, dict[str, str]]) -> tuple[str, str] | None:
    source_name = chinese_only(str(value or ""))
    if not source_name:
        return None
    local = local_birds.get(source_name)
    if local:
        return local["id"], local["name"]
    return f"birdreport_{hashlib.sha1(source_name.encode()).hexdigest()[:12]}", source_name


def aggregate_reports(reports: list[dict[str, Any]], taxa_by_report: dict[str, list[dict[str, Any]]], local_birds: dict[str, dict[str, str]], window: dict[str, str]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    groups: dict[tuple[str, str], dict[str, Any]] = {}
    city_records: dict[str, dict[str, Any]] = {}
    dropped_unknown_time = 0
    raw_taxon_records = 0
    dropped_non_chinese = 0

    for report in reports:
        point_raw = report.get("point_name") or report.get("pointName") or report.get("pointname") or ""
        point_name = normalize_point_name(point_raw)
        coords = coords_from_location(report.get("location"))
        observed_at = valid_observed_at(report.get("start_time") or report.get("startTime") or report.get("start_time_str"))
        if observed_at is None:
            dropped_unknown_time += 1
            continue
        report_id = str(report.get("id") or report.get("activityid") or report.get("serial_id") or report.get("report_id") or "")
        taxa = taxa_by_report.get(report_id, [])
        for taxon in taxa:
            raw_taxon_records += 1
            species = normalize_taxon_name(taxon.get("taxon_name") or taxon.get("taxonName") or taxon.get("name"), local_birds)
            if species is None:
                dropped_non_chinese += 1
                continue
            species_id, species_name = species
            try:
                count = max(0, int(float(taxon.get("taxon_count") or taxon.get("taxonCount") or 0)))
            except (ValueError, TypeError):
                count = 0
            source_record = {
                "reportId": report_id,
                "speciesId": species_id,
                "speciesName": species_name,
                "observedAt": observed_at,
                "count": count,
                "originalPointName": point_raw,
            }
            if point_name == "其它观测记录":
                bucket = city_records.get(species_id)
                if bucket is None:
                    bucket = {"speciesId": species_id, "speciesName": species_name, "observedAt": observed_at, "count": count, "occurrenceCount": 1, "reports": [source_record]}
                    city_records[species_id] = bucket
                else:
                    bucket["occurrenceCount"] += 1
                    bucket["count"] += count
                    if observed_at > bucket["observedAt"]:
                        bucket["observedAt"] = observed_at
                    bucket["reports"].append(source_record)
                continue
            known = next((spot for spot in KNOWN_HOTSPOTS if spot["name"] == point_name), None)
            if known:
                point_id = known["id"]
                point_key = f"known:{point_id}"
            else:
                latlon = coords or (None, None)
                point_key = f"point:{point_name}" if point_name != "其它观测记录" else f"point:{point_name}:{latlon[0]}:{latlon[1]}"
            group_key = (point_key, species_id)
            bucket = groups.get(group_key)
            if bucket is None:
                groups[group_key] = {
                    "pointKey": point_key,
                    "pointName": point_name,
                    "coords": coords,
                    "speciesId": species_id,
                    "speciesName": species_name,
                    "observedAt": observed_at,
                    "count": count,
                    "occurrenceCount": 1,
                    "reports": [source_record],
                }
            else:
                bucket["occurrenceCount"] += 1
                bucket["count"] += count
                bucket["reports"].append(source_record)
                if observed_at > bucket["observedAt"]:
                    bucket["observedAt"] = observed_at

    by_point: dict[str, dict[str, Any]] = {}
    for bucket in groups.values():
        point_key = bucket["pointKey"]
        if point_key not in by_point:
            by_point[point_key] = {
                "pointKey": point_key, "name": bucket["pointName"], "coords": bucket["coords"], "species": []
            }
        by_point[point_key]["species"].append(bucket)

    output: list[dict[str, Any]] = []
    auto_index = 0
    for point_key, point in by_point.items():
        known = next((spot for spot in KNOWN_HOTSPOTS if f"known:{spot['id']}" == point_key), None)
        if known:
            point_id = known["id"]; name = known["name"]; district = known["district"]; lat = known["lat"]; lon = known["lon"]; discovery = "known_site"
        else:
            auto_index += 1
            name = point["name"] if point["name"] != "其它观测记录" else f"上海市观测点{auto_index}"
            district = district_from_name(name)
            coords = point["coords"] or (None, None)
            lat = round(coords[0], 5) if coords[0] is not None else None
            lon = round(coords[1], 5) if coords[1] is not None else None
            point_id = f"birdreport_site_{hashlib.sha1(f'{name}|{lat}|{lon}'.encode()).hexdigest()[:12]}"
            discovery = "source_point"
        species_rows = sorted(point["species"], key=lambda x: (x["observedAt"], x["speciesName"]), reverse=True)
        records = []
        for row in species_rows:
            records.append({
                "observationId": max(row["reports"], key=lambda r: r["observedAt"])["reportId"],
                "speciesId": row["speciesId"], "speciesName": row["speciesName"],
                "observedAt": row["observedAt"], "latestCount": row["reports"][max(range(len(row["reports"])), key=lambda i: row["reports"][i]["observedAt"])]["count"],
                "totalCount": row["count"], "occurrenceCount": row["occurrenceCount"],
                "sourceUrl": f"{BIRDREPORT_SOURCE_URL}",
            })
        output.append({
            "id": point_id, "name": name, "district": district, "lat": lat, "lon": lon,
            "observations": [{"speciesId": r["speciesId"], "speciesName": r["speciesName"], "frequency": r["occurrenceCount"]} for r in records],
            "records": records, "observationCount": len(records), "sourceObservationCount": sum(r["occurrenceCount"] for r in records),
            "observationWindow": window, "source": "中国观鸟记录中心", "sourceUrl": BIRDREPORT_SOURCE_URL, "discovery": discovery,
        })

    if city_records:
        records = []
        for row in sorted(city_records.values(), key=lambda x: (x["observedAt"], x["speciesName"]), reverse=True):
            latest_report = max(row["reports"], key=lambda r: r["observedAt"])
            records.append({
                "observationId": latest_report["reportId"], "speciesId": row["speciesId"], "speciesName": row["speciesName"],
                "observedAt": row["observedAt"], "latestCount": latest_report["count"], "totalCount": row["count"],
                "occurrenceCount": row["occurrenceCount"], "sourceUrl": BIRDREPORT_SOURCE_URL,
            })
        output.append({
            "id": "other_shanghai", "name": "其它观测记录", "district": "上海市", "lat": None, "lon": None,
            "observations": [{"speciesId": r["speciesId"], "speciesName": r["speciesName"], "frequency": r["occurrenceCount"]} for r in records],
            "records": records, "observationCount": len(records), "sourceObservationCount": sum(r["occurrenceCount"] for r in records),
            "observationWindow": window, "source": "中国观鸟记录中心", "sourceUrl": BIRDREPORT_SOURCE_URL, "discovery": "city_level",
        })

    output.sort(key=lambda x: (x["id"] == "other_shanghai", -int(x["sourceObservationCount"]), x["name"]))
    meta = {
        "source": "中国观鸟记录中心", "sourceUrl": BIRDREPORT_SOURCE_URL,
        "observationWindow": window, "rawReportCount": len(reports), "rawTaxonRecordCount": raw_taxon_records,
        "displayedRecordCount": sum(int(h["observationCount"]) for h in output),
        "sourceObservationCount": sum(int(h["sourceObservationCount"]) for h in output),
        "droppedUnknownTimeReportCount": dropped_unknown_time, "droppedNonChineseTaxonCount": dropped_non_chinese,
        "retrievedAt": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "scope": "上海市行政区域，公开观鸟记录中心记录",
    }
    return output, meta


def fetch_birdreport_hotspots(reference_day: date | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    today = reference_day or date.today()
    start = today - timedelta(days=6)
    reports: list[dict[str, Any]] = []
    page = 1
    while True:
        page_data = search_reports(start, today, page, limit=100)
        if isinstance(page_data, dict):
            batch = page_data.get("data") or page_data.get("list") or page_data.get("records") or []
        else:
            batch = page_data
        if not isinstance(batch, list) or not batch:
            break
        reports.extend([r for r in batch if isinstance(r, dict)])
        if len(batch) < 100:
            break
        page += 1
        if page > 200:
            raise RuntimeError("China Bird Report Center returned an unexpectedly large result set")

    taxa_by_report: dict[str, list[dict[str, Any]]] = {}
    failures: list[str] = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {}
        for report in reports:
            report_id = str(report.get("id") or report.get("activityid") or report.get("serial_id") or report.get("report_id") or "")
            if report_id:
                futures[pool.submit(fetch_report_taxa, report_id)] = report_id
        for future in as_completed(futures):
            report_id = futures[future]
            try:
                taxa_by_report[report_id] = future.result()
            except Exception as exc:
                failures.append(f"{report_id}: {exc}")
    if failures:
        raise RuntimeError(f"failed to retrieve bird details for {len(failures)} reports; first: {failures[0]}")

    local_birds = load_local_birds()
    window = {"start": start.isoformat(), "end": today.isoformat()}
    hotspots, meta = aggregate_reports(reports, taxa_by_report, local_birds, window)
    if not hotspots or meta["sourceObservationCount"] == 0:
        raise RuntimeError("中国观鸟记录中心最近 7 日没有可用的、带具体时间的上海公开鸟类观测记录")
    return hotspots, meta


def validate_payload(data: dict[str, Any]) -> None:
    if data.get("version") != 1 or data.get("app") != "shanghai-birding":
        raise ValueError("invalid app/version")
    forecast = ((data.get("weather") or {}).get("forecast"))
    if not isinstance(forecast, list) or len(forecast) != 7:
        raise ValueError("weather.forecast must contain exactly 7 days")
    hotspots = data.get("hotspots")
    if not isinstance(hotspots, list):
        raise ValueError("hotspots must be a list")
    hotspot_data = data.get("hotspotData")
    if not isinstance(hotspot_data, dict) or hotspot_data.get("source") != "中国观鸟记录中心":
        raise ValueError("hotspotData must declare China Bird Report Center as the source")
    window = hotspot_data.get("observationWindow") or {}
    if not window.get("start") or not window.get("end"):
        raise ValueError("hotspotData must include observationWindow")
    ws, we = date.fromisoformat(window["start"]), date.fromisoformat(window["end"])
    if (we - ws).days != 6:
        raise ValueError("hotspot observation window must span exactly 7 calendar days")
    for hotspot in hotspots:
        required = ("id", "name", "district", "lat", "lon", "observations", "records", "observationCount", "observationWindow", "source", "sourceUrl")
        if not all(k in hotspot for k in required):
            raise ValueError("invalid hotspot")
        if hotspot["source"] != "中国观鸟记录中心" or hotspot["observationWindow"] != window:
            raise ValueError("hotspot source/window mismatch")
        if not any("\u3400" <= ch <= "\u9fff" for ch in hotspot["name"]):
            raise ValueError("hotspot names must be Chinese")
        if hotspot.get("discovery") == "city_level":
            if hotspot["lat"] is not None or hotspot["lon"] is not None:
                raise ValueError("city-level hotspot must not claim precise coordinates")
        else:
            if not (-90 <= float(hotspot["lat"]) <= 90 and -180 <= float(hotspot["lon"]) <= 180):
                raise ValueError("invalid hotspot coordinates")
        if int(hotspot["observationCount"]) != len(hotspot["records"]):
            raise ValueError("observationCount must match displayed records")
        for record in hotspot["records"]:
            for key in ("observationId", "speciesId", "speciesName", "observedAt", "latestCount", "totalCount", "occurrenceCount"):
                if key not in record:
                    raise ValueError(f"missing record field: {key}")
            if not any("\u3400" <= ch <= "\u9fff" for ch in record["speciesName"]):
                raise ValueError("species names must be Chinese")
            if not valid_observed_at(record["observedAt"]):
                raise ValueError("every displayed observation record must have a real time")
            if int(record["occurrenceCount"]) < 1:
                raise ValueError("occurrenceCount must be >= 1")
        if len({(r["speciesId"], r["speciesName"]) for r in hotspot["records"]}) != len(hotspot["records"]):
            raise ValueError("same species must be merged within a hotspot")
    if data.get("sourceStatus") == "ok" and not hotspots:
        raise ValueError("successful live update must contain at least one hotspot")


def to_js(data: dict[str, Any]) -> str:
    return "window.EXTERNAL_DATA = " + json.dumps(data, ensure_ascii=False, indent=2) + ";\n"


def load_fixture(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    validate_payload(data)
    return data


def empty_snapshot() -> dict[str, Any]:
    today = date.today()
    return {
        "version": 1, "app": "shanghai-birding", "updatedAt": "", "sourceStatus": "not_fetched",
        "weather": {"forecast": []}, "hotspots": [], "hotspotData": {
            "source": "中国观鸟记录中心", "sourceUrl": BIRDREPORT_SOURCE_URL,
            "observationWindow": {"start": (today - timedelta(days=6)).isoformat(), "end": today.isoformat()},
            "retrievedAt": "", "scope": "上海市行政区域，公开观鸟记录中心记录",
        },
    }


def build_live(reference: date | None = None) -> dict[str, Any]:
    data = {
        "version": 1, "app": "shanghai-birding",
        "updatedAt": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "weather": fetch_weather(), "hotspots": [], "hotspotData": {}, "sourceStatus": "ok",
    }
    hotspots, hotspot_meta = fetch_birdreport_hotspots(reference)
    data["hotspots"], data["hotspotData"] = hotspots, hotspot_meta
    validate_payload(data)
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(Path(__file__).resolve().parents[1] / "data" / "latest_data.js"))
    parser.add_argument("--fixture")
    parser.add_argument("--reference-date")
    args = parser.parse_args()
    output = Path(args.output)
    try:
        if args.fixture and args.reference_date:
            raise ValueError("--fixture and --reference-date cannot be used together")
        if args.fixture:
            data = load_fixture(Path(args.fixture))
        elif args.reference_date:
            data = build_live(date.fromisoformat(args.reference_date))
        else:
            data = build_live()
        output.parent.mkdir(parents=True, exist_ok=True)
        temp = output.with_suffix(output.suffix + ".tmp")
        temp.write_text(to_js(data), encoding="utf-8")
        temp.replace(output)
        print(f"updated: {output}")
        print(f"weather_days: {len(data['weather']['forecast'])}")
        print(f"hotspots: {len(data['hotspots'])}")
        print(f"displayed_species_records: {data['hotspotData'].get('displayedRecordCount', 0)}")
        print(f"source_observations: {data['hotspotData'].get('sourceObservationCount', 0)}")
        return 0
    except Exception as exc:
        print(f"update failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
