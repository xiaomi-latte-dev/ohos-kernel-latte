"""Configuration models and paths."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, TypedDict

BASE = Path(__file__).resolve().parent.parent
CONFIG_FILE = BASE / "versions.json"
CACHE = BASE / ".cache" / "repos"


class RawRepo(TypedDict, total=False):
    url: str
    path: str
    subpath: str
    description: str


class RawToolchain(TypedDict, total=False):
    url: str
    sha256: str
    archive_root: str
    description: str


class RawKernel(TypedDict, total=False):
    description: str
    kernel_version: str
    repo: str
    branch: str
    patches: Optional[str]
    defconfig: str
    enabled: bool
    deps: Dict[str, str]
    notes: str
    toolchain: str
    official_patches: Optional[str]


@dataclass(frozen=True)
class ToolchainSpec:
    url: str
    sha256: str
    archive_root: str
    description: str = ""


@dataclass(frozen=True)
class RepoSpec:
    url: str
    path: str
    subpath: Optional[str] = None
    description: str = ""


@dataclass(frozen=True)
class KernelSpec:
    description: str
    kernel_version: str
    repo: str
    branch: str
    patches: Optional[str]
    defconfig: str
    enabled: bool
    deps: Dict[str, str] = field(default_factory=dict)
    notes: str = ""
    toolchain: str = "clang-15.0.4"
    official_patches: Optional[str] = None


def load_config():
    raw = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    repos = {name: RepoSpec(**spec) for name, spec in raw["repos"].items()}
    kernels = {name: KernelSpec(**spec) for name, spec in raw["kernels"].items()}
    return raw.get("default", "7.0"), repos, kernels


def load_toolchains() -> Dict[str, ToolchainSpec]:
    raw = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    return {name: ToolchainSpec(**spec)
            for name, spec in raw.get("toolchains", {}).items()}
