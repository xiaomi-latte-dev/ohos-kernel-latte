"""Per-version paths."""
from pathlib import Path

from .config import BASE


def kernel_root(key: str) -> Path:
    """Kernel cache dir, keyed like patches/: v<release>-k<kernel-version>."""
    return BASE / "kernels" / key


def work_root(key: str) -> Path:
    """Per-variant workspace: <name>/ohos deps and <name>/out build output."""
    return BASE / "work" / key


def out_root(key: str) -> Path:
    """Final artifacts, named like kernels/: v<release>-k<kernel-version>."""
    return BASE / "out" / key


def build_root(key: str) -> Path:
    return work_root(key) / "out"
