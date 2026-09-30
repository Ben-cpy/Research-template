"""Small, domain-independent run record and checkpoint helpers."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
    os.replace(temporary, path)


def load_rows(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    rows: dict[str, dict[str, Any]] = {}
    for line in path.read_text().splitlines():
        if line:
            row = json.loads(line)
            key = str(row["id"])
            if key in rows:
                raise ValueError(f"duplicate checkpoint id: {key}")
            rows[key] = row
    return rows


def append_row(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def start_run(config_path: Path, input_paths: list[Path]) -> tuple[dict[str, Any], Path]:
    """Freeze a run before work; refuse to resume if its identity changed."""
    if not (ROOT / ".git").exists() or Path(_git("rev-parse", "--show-toplevel")) != ROOT:
        raise RuntimeError("initialize and commit this template as its own Git repository first")

    config_path = config_path.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    output_dir = (ROOT / config["output_dir"]).resolve()
    if not output_dir.is_relative_to(ROOT):
        raise ValueError("output_dir must be inside the project")

    inputs = {str(path.resolve().relative_to(ROOT)): _sha256(path.read_bytes()) for path in input_paths}
    untracked: dict[str, dict[str, Any]] = {}
    for name in _git("ls-files", "--others", "--exclude-standard").splitlines():
        path = ROOT / name
        if path.is_file():
            raw = path.read_bytes()
            untracked[name] = {"sha256": _sha256(raw)}
            if len(raw) <= 256 * 1024:
                try:
                    untracked[name]["content"] = raw.decode("utf-8")
                except UnicodeDecodeError:
                    pass

    source = {
        "commit": _git("rev-parse", "HEAD"),
        "diff": _git("diff", "HEAD", "--binary"),
        "untracked": untracked,
    }
    environment = {
        "python": sys.version,
        "platform": platform.platform(),
        "uv_lock_sha256": _sha256((ROOT / "uv.lock").read_bytes()),
    }
    identity = _sha256(_json_bytes({"config": config, "source": source, "inputs": inputs, "environment": environment}))
    record = {
        "identity": identity,
        "config": config,
        "config_path": str(config_path.relative_to(ROOT)),
        "inputs_sha256": inputs,
        "code_snapshot": {
            str(path.resolve().relative_to(ROOT)): path.read_text(encoding="utf-8")
            for path in input_paths if path.suffix == ".py"
        },
        "source": source,
        "command": sys.argv,
        "environment": environment,
    }
    provenance_path = output_dir / "provenance.json"
    if provenance_path.exists():
        previous = json.loads(provenance_path.read_text(encoding="utf-8"))
        if previous["identity"] != identity:
            raise RuntimeError(f"run identity changed; choose a new output_dir: {output_dir}")
    else:
        output_dir.mkdir(parents=True, exist_ok=True)
        write_json(provenance_path, record)
        write_json(output_dir / "config.json", config)
    return config, output_dir
