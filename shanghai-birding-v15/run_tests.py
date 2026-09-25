#!/usr/bin/env python3
from __future__ import annotations

import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COMMANDS = [
    [sys.executable, str(ROOT/'tests'/'static_quality.py')],
    ['node', str(ROOT/'tests'/'phase1_logic.mjs')],
    ['node', str(ROOT/'tests'/'phase0.mjs')],
    [sys.executable, str(ROOT/'tests'/'phase0_browser.py')],
    [sys.executable, str(ROOT/'tests'/'phase1_browser.py')],
    [sys.executable, str(ROOT/'tests'/'phase2_records.py')],
    [sys.executable, str(ROOT/'tests'/'phase3_lexicon.py')],
    [sys.executable, str(ROOT/'tests'/'phase4_home.py')],
    [sys.executable, str(ROOT/'tests'/'phase5_weather_hotspots.py')],
    [sys.executable, str(ROOT/'tests'/'phase6_data_update.py')],
    [sys.executable, str(ROOT/'tests'/'phase7_settings.py')],
    [sys.executable, str(ROOT/'tests'/'phase8_integration.py')],
    [sys.executable, str(ROOT/'tests'/'phase9_multi_species_records.py')],
    [sys.executable, str(ROOT/'tests'/'phase10_memos.py')],
    [sys.executable, str(ROOT/'tests'/'phase11_hotspot_map.py')],
    [sys.executable, str(ROOT/'tests'/'phase12_lexicon_ime.py')],
    [sys.executable, str(ROOT/'tests'/'phase15_hotspot_live_data.py')],
    [sys.executable, str(ROOT/'tests'/'phase16_hotspot_live_browser.py')],
    [sys.executable, str(ROOT/'tests'/'phase13_lexicon_details.py')],
    [sys.executable, str(ROOT/'tests'/'phase14_bird_details_completeness.py')],
    [sys.executable, str(ROOT/'tests'/'phase17_hotspot_names_and_records.py')],
    [sys.executable, str(ROOT/'tests'/'phase18_birdreport_source.py')],
    [sys.executable, str(ROOT/'tests'/'phase19_birdreport_browser_contract.py')],
    [sys.executable, str(ROOT/'tests'/'phase20_hotspot_ui_contract.py')],
    [sys.executable, str(ROOT/'tests'/'phase21_auto_update_contract.py')],
    [sys.executable, str(ROOT/'tests'/'phase22_auto_update_server.py')],
    ['node', str(ROOT/'tests'/'phase23_auto_update_client.mjs')],
    [sys.executable, str(ROOT/'tests'/'phase24_birdreport_import_contract.py')],
    [sys.executable, str(ROOT/'tests'/'phase25_birdreport_import_browser.py')],
    [sys.executable, str(ROOT/'tests'/'phase26_birdreport_fetch_export.py')],
    [sys.executable, str(ROOT/'tests'/'phase27_birdreport_bat.py')],
    [sys.executable, str(ROOT/'tests'/'phase28_ebird_direct_contract.py')],
    [sys.executable, str(ROOT/'tests'/'phase29_ebird_import_browser.py')],
    [sys.executable, str(ROOT/'tests'/'phase30_ebird_fetch_browser.py')],
    [sys.executable, str(ROOT/'tests'/'phase31_index_direct_ebird.py')],
    [sys.executable, str(ROOT/'tests'/'phase32_birdreport_web_import.py')],
    [sys.executable, str(ROOT/'tests'/'phase33_hotspot_generic_import.py')],
    [sys.executable, str(ROOT/'tests'/'phase36_birdreport_web_export_core.py')],
    [sys.executable, str(ROOT/'tests'/'phase36_birdreport_web_export_browser.py')],
    [sys.executable, str(ROOT/'tests'/'phase37_hotspot_import_web_browser.py')],
    [sys.executable, str(ROOT/'tests'/'phase38_settings_web_import.py')],
    [sys.executable, str(ROOT/'tests'/'phase39_ebird_embedded_and_merge.py')],
    [sys.executable, str(ROOT/'tests'/'phase40_hotspot_duplicate_merge.py')],
    [sys.executable, str(ROOT/'tests'/'phase41_weather_live_api.py')],
]
TEST_TIMEOUT_SECONDS = 180


def terminate_process_group(process: subprocess.Popen[object]) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=3)
    except Exception:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except Exception:
            pass


def run_one(index: int, command: list[str]) -> int:
    print(f'[{index}/{len(COMMANDS)}] {" ".join(command)}', flush=True)
    log_path = Path(tempfile.gettempdir()) / f'shanghai_birding_test_{index}.log'
    with log_path.open('w', encoding='utf-8') as log:
        process = subprocess.Popen(
            command,
            cwd=ROOT,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            code = process.wait(timeout=TEST_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            terminate_process_group(process)
            print(f'TEST SUITE FAILED: timeout after {TEST_TIMEOUT_SECONDS}s at step {index}', file=sys.stderr, flush=True)
            print(log_path.read_text(encoding='utf-8', errors='replace')[-4000:], file=sys.stderr)
            return 124
    output = log_path.read_text(encoding='utf-8', errors='replace').strip()
    if code != 0:
        print(f'TEST SUITE FAILED at step {index}: return code {code}', file=sys.stderr, flush=True)
        print(output[-4000:], file=sys.stderr)
        return code
    if output:
        print(output.splitlines()[-1], flush=True)
    return 0


for i, command in enumerate(COMMANDS, 1):
    code = run_one(i, command)
    if code:
        sys.exit(code)

print(f'ALL TESTS PASS ({len(COMMANDS)} test commands)', flush=True)
