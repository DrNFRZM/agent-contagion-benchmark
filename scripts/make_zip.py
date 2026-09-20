"""Build agent-contagion-benchmark.zip from the repository, leaving out anything that must not be uploaded.

    python scripts/make_zip.py [output_dir]

Excluded: .env / key / token files, virtualenvs, caches, egg-info, model weights,
results/full and any file larger than 1 MB. The script fails if a secret-like string is found.
"""
from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = "agent-contagion-benchmark"
SKIP_DIRS = {".git", ".venv", "venv", "env", ".tox", ".nox", "__pycache__", ".pytest_cache",
             ".mypy_cache", ".ruff_cache", ".cache", "htmlcov", "huggingface", "models", "build", "dist",
             ".ipynb_checkpoints"}
SKIP_SUFFIX = {".pyc", ".zip", ".key", ".pem", ".safetensors", ".gguf", ".pt", ".pth", ".onnx", ".bin"}
MAX_BYTES = 1_000_000
SECRET = re.compile(
    r"\bsk-[A-Za-z0-9_-]{20,}|\bhf_[A-Za-z0-9]{20,}|\bghp_[A-Za-z0-9]{20,}|"
    r"\bgithub_pat_[A-Za-z0-9_]{20,}|\bAKIA[0-9A-Z]{16}|BEGIN [A-Z ]*PRIVATE KEY"
)


def skipped(p: Path) -> bool:
    rel = p.relative_to(ROOT)
    parts = set(rel.parts)
    if parts & SKIP_DIRS or any(x.endswith(".egg-info") for x in rel.parts):
        return True
    if rel.parts[:2] == ("results", "full"):
        return True
    n = p.name.lower()
    return (n in {".env", ".coverage"} or n.startswith(".env.") or "token" in n or "secret" in n
            or p.suffix.lower() in SKIP_SUFFIX or p.stat().st_size > MAX_BYTES)


def main() -> None:
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent
    out = out_dir / f"{NAME}.zip"
    files = sorted(p for p in ROOT.rglob("*") if p.is_file() and not skipped(p))
    for p in files:
        if p.suffix in {".py", ".md", ".yaml", ".yml", ".toml", ".csv", ".txt", ".cff", ""} and SECRET.search(
                p.read_text(encoding="utf-8", errors="ignore")):
            raise SystemExit(f"secret-like string in {p}; refusing to package")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for p in files:
            z.write(p, f"{NAME}/{p.relative_to(ROOT).as_posix()}")
    print(f"wrote {out} ({out.stat().st_size / 1024:.0f} KiB, {len(files)} files)")


if __name__ == "__main__":
    main()
