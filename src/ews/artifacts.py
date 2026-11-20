"""Publish complete result directories and verify their provenance."""
import hashlib
import json
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

from .data_check import FILES

def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def input_hashes(raw):
    return {key: sha256_file(raw / name) for key, name in FILES.items()}

@contextmanager
def publication(destination):
    destination = Path(destination).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise ValueError(f"Thư mục kết quả đã tồn tại: {destination}. Hãy chọn --out mới.")
    with TemporaryDirectory(prefix=".ews-", dir=destination.parent) as temp:
        staging = Path(temp) / "run"
        staging.mkdir()
        yield staging
        if destination.exists():
            raise ValueError(f"Thư mục kết quả đã tồn tại: {destination}")
        staging.rename(destination)

def seal(out, kind):
    files = {path.name: sha256_file(path) for path in sorted(out.iterdir()) if path.is_file()}
    payload = {"schema": 1, "kind": kind, "files": files}
    (out / "manifest.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

def verify_artifacts(directory, kind=None):
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    if manifest["schema"] != 1 or (kind and manifest["kind"] != kind):
        raise ValueError(f"Loại bộ kết quả không hợp lệ: {directory}")
    files = manifest["files"]
    actual = {path.name for path in directory.iterdir() if path.is_file()} - {"manifest.json", ".gitkeep"}
    if actual != files.keys():
        raise ValueError(f"Danh sách file không khớp manifest: {sorted(actual ^ files.keys())}")
    for name, expected in files.items():
        if sha256_file(directory / name) != expected:
            raise ValueError(f"Checksum không khớp: {name}")
    return manifest

def month_key(value):
    import re
    if not re.fullmatch(r"[0-9]{4}-(0[1-9]|1[0-2])", value):
        raise ValueError("Tháng phải có dạng YYYY-MM")
    return value
