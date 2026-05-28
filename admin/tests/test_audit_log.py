"""audit_log: JSONL 追記の最小テスト"""
import json
from pathlib import Path

from admin.lib import audit_log


def test_log_appends_jsonl(tmp_path, monkeypatch):
    log_path = tmp_path / "admin.log"
    monkeypatch.setattr(audit_log, "LOG_PATH", log_path)
    audit_log.log(op="set_coords", slug="x", details={"lat": 35.667, "lng": 139.722})
    audit_log.log(op="add_photo", slug="y", details={"file": "a.jpg"})
    lines = log_path.read_text().splitlines()
    assert len(lines) == 2
    e1 = json.loads(lines[0])
    assert e1["op"] == "set_coords"
    assert e1["slug"] == "x"
    assert "ts" in e1
