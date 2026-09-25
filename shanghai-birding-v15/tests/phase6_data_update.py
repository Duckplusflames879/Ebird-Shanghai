import json
import subprocess
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
fixture=ROOT/"tests/external_fixture.json"
with tempfile.TemporaryDirectory() as d:
    out=Path(d)/"latest_data.js"
    out.write_text("SENTINEL\n",encoding="utf8")
    ok=subprocess.run(["python3",str(ROOT/"scripts/update_data.py"),"--fixture",str(fixture),"--output",str(out)],capture_output=True,text=True)
    assert ok.returncode==0, ok.stderr
    assert "window.EXTERNAL_DATA" in out.read_text(encoding="utf8")
    bad=Path(d)/"bad.json"
    bad.write_text(json.dumps({"version":1}),encoding="utf8")
    failed=subprocess.run(["python3",str(ROOT/"scripts/update_data.py"),"--fixture",str(bad),"--output",str(out)],capture_output=True,text=True)
    assert failed.returncode!=0
    assert "window.EXTERNAL_DATA" in out.read_text(encoding="utf8"), "failed update must not overwrite last good output"
print("PHASE 6 LEGACY DATA UPDATE FAILURE-PROTECTION PASS")
