"""Dependency cache and per-version workspace."""
from __future__ import annotations

from pathlib import Path
from typing import Dict

from .config import CACHE, KernelSpec, RepoSpec, kernel_id
from .paths import work_root
from .util import copy_tree, run


def cache_repo(name: str, repo: RepoSpec, branch: str) -> Path:
    dst = CACHE / name / branch
    if dst.is_dir():
        return dst
    dst.parent.mkdir(parents=True, exist_ok=True)
    print("cache clone " + name + " @ " + branch)
    run(["git", "clone", "--depth=1", "--single-branch",
         "-b", branch, repo.url, str(dst)])
    return dst


def prepare_deps(version: str, spec: KernelSpec, repos: Dict[str, RepoSpec]):
    root = work_root(kernel_id(version, spec)) / "ohos"
    root.mkdir(parents=True, exist_ok=True)
    for name, branch in spec.deps.items():
        repo = repos[name]
        cached = cache_repo(name, repo, branch)
        src = cached / repo.subpath if repo.subpath else cached
        dst = root / repo.path
        print("materialize " + name + " -> " + str(dst))
        copy_tree(src, dst)
    return root
