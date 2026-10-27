"""Toolchain download cache."""
from __future__ import annotations

import hashlib
import os
import shutil
import tarfile
import urllib.request
from pathlib import Path
from typing import Dict, Optional

from .config import BASE, KernelSpec, load_toolchains


def ensure_toolchain(name: str) -> Optional[str]:
    if not name:
        return None
    base = BASE / ".cache" / "toolchain" / name
    clang = base / "llvm" / "bin" / "clang"
    if clang.is_file():
        return str(clang.parent)
    spec = load_toolchains().get(name)
    if spec is None:
        print("unknown toolchain " + name)
        return None
    base.mkdir(parents=True, exist_ok=True)
    archive = base / "download.tar.gz"
    if not archive.is_file() or archive.stat().st_size == 0:
        print("download toolchain " + name)
        urllib.request.urlretrieve(spec.url, archive)
    digest = hashlib.sha256()
    with open(archive, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    actual = digest.hexdigest()
    if actual != spec.sha256:
        archive.unlink(missing_ok=True)
        raise SystemExit("toolchain sha256 mismatch: " + actual)
    extract = base / "extract"
    if extract.exists():
        shutil.rmtree(extract)
    extract.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "r:gz") as tf:
        tf.extractall(extract)
    root = extract / spec.archive_root
    if not root.is_dir():
        dirs = [p for p in extract.iterdir() if p.is_dir()]
        if not dirs:
            raise SystemExit("toolchain archive has no directory")
        root = dirs[0]
    target = base / "llvm"
    if target.exists():
        shutil.rmtree(target)
    shutil.move(str(root), str(target))
    shutil.rmtree(extract, ignore_errors=True)
    archive.unlink(missing_ok=True)
    return str((target / "bin").resolve())


def kernel_env(spec: KernelSpec) -> Dict[str, str]:
    env = os.environ.copy()
    clang_bin = os.environ.get("CLANG_BIN")
    if not clang_bin:
        try:
            clang_bin = ensure_toolchain(spec.toolchain)
        except Exception as exc:
            raise SystemExit("toolchain unavailable: " + str(exc) +
                             "; set CLANG_BIN or check the network")
    if not clang_bin:
        raise SystemExit("toolchain " + spec.toolchain + " unavailable; set CLANG_BIN")
    env["PATH"] = clang_bin + ":" + env.get("PATH", "")
    env["PRODUCT_PATH"] = "vendor/ohemu/virt"
    return env
