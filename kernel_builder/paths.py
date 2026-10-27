"""Per-version paths."""
from pathlib import Path

from .config import BASE


def kernel_root(version: str) -> Path:
    return BASE / "kernels" / version


def work_root(version: str) -> Path:
    return BASE / "work" / version


def out_root(version: str) -> Path:
    return BASE / "out" / version


def build_root(version: str) -> Path:
    return work_root(version) / "out"
