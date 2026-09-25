#!/usr/bin/env python3
"""Fetch China's Bird Report Center's latest 7-day Shanghai records.

This program deliberately writes the standalone JSON import format consumed by
ShanghaiBirding's Settings -> 观鸟点数据导入. It does not modify data/latest_data.js.
"""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone
from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
UPDATER = ROOT / "scripts" / "update_data.py"
spec = importlib.util.spec_from_file_location("update_data", UPDATER)
if spec is None or spec.loader is None:
    raise RuntimeError("无法加载 scripts/update_data.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def build_import(reference_day: date | None = None) -> dict:
    hotspots, meta = mod.fetch_birdreport_hotspots(reference_day)
    return {
        "format": "shanghai-birding-birdreport-7d",
        "version": 1,
        "app": "shanghai-birding",
        "source": "中国观鸟记录中心",
        "sourceUrl": mod.BIRDREPORT_SOURCE_URL,
        "generatedAt": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "retrievedAt": meta.get("retrievedAt", ""),
        "observationWindow": meta["observationWindow"],
        "hotspotData": meta,
        "hotspots": hotspots,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="抓取上海最近7日中国观鸟记录中心数据并生成导入 JSON")
    parser.add_argument("--output", help="输出 JSON 文件路径；默认生成 birdreport-7d-import-YYYY-MM-DD.json")
    parser.add_argument("--reference-date", help="以指定日期作为7日窗口结束日，格式 YYYY-MM-DD")
    args = parser.parse_args()
    try:
        reference = date.fromisoformat(args.reference_date) if args.reference_date else None
        data = build_import(reference)
        output = Path(args.output) if args.output else ROOT / f"birdreport-7d-import-{data['observationWindow']['end']}.json"
        if not output.is_absolute():
            output = ROOT / output
        output = output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        tmp = output.with_suffix(output.suffix + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(output)
        print(f"generated: {output}")
        print(f"observation_window: {data['observationWindow']['start']} -> {data['observationWindow']['end']}")
        print(f"hotspots: {len(data['hotspots'])}")
        print(f"species_rows: {data['hotspotData'].get('displayedRecordCount', 0)}")
        print(f"source_observations: {data['hotspotData'].get('sourceObservationCount', 0)}")
        return 0
    except Exception as exc:
        print(f"generation failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
