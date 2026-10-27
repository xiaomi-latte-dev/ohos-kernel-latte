"""Process and filesystem helpers."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def run(cmd, cwd=None, env=None, check=True):
    print("+", " ".join(str(c) for c in cmd), flush=True)
    result = subprocess.run(cmd, cwd=cwd, env=env, text=True)
    if check and result.returncode != 0:
        raise SystemExit("command failed: " + " ".join(str(c) for c in cmd))
    return result


def copy_tree(src: Path, dst: Path):
    if not src.is_dir():
        raise SystemExit("source not found: " + str(src))
    if dst.exists():
        shutil.rmtree(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["cp", "-a", str(src), str(dst)], check=True)


def make(kroot: Path, out: Path, env, *args: str, extra=None):
    cmd = ["make", "-C", str(kroot), "O=" + str(out), "ARCH=x86_64", "LLVM=1", *args]
    run_env = env.copy()
    if extra:
        run_env.update(extra)
    run(cmd, env=run_env)
