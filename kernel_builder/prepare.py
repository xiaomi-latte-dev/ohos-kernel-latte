"""Kernel preparation, patches, HDF and defconfig."""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict

from .config import BASE, KernelSpec, RepoSpec, kernel_id
from .deps import prepare_deps
from .paths import build_root, kernel_root, src_root, work_root
from .toolchain import kernel_env
from .util import make, run


def apply_one_patch(patch: Path, kroot: Path):
    print("apply " + str(patch.relative_to(BASE)))
    with open(patch, "rb") as f:
        result = subprocess.run(["patch", "-d", str(kroot), "-p1",
                                 "--no-backup-if-mismatch", "-N"], stdin=f)
    if result.returncode != 0:
        raise SystemExit("patch failed: " + str(patch))


def apply_patches(version: str, kroot: Path, deps_root: Path, spec: KernelSpec):
    if spec.official_patches:
        official = deps_root / spec.official_patches
        if official.is_dir():
            for patch in sorted(official.rglob("*.patch")):
                apply_one_patch(patch, kroot)
        else:
            print("official patch dir missing: " + str(official))
    rel = spec.patches or version
    local = BASE / "patches" / rel
    if local.is_dir():
        for patch in sorted(local.rglob("*.patch")):
            apply_one_patch(patch, kroot)


def setup_hdf(root: Path, kroot: Path):
    (kroot / "drivers" / "hdf").mkdir(parents=True, exist_ok=True)
    (kroot / "include").mkdir(parents=True, exist_ok=True)
    links = {
        kroot / "drivers/hdf/khdf": root / "drivers/hdf_core/adapter/khdf/linux",
        kroot / "drivers/hdf/framework": root / "drivers/hdf_core/framework",
        kroot / "drivers/hdf/inner_api": root / "drivers/hdf_core/interfaces/inner_api",
        kroot / "include/hdf": root / "drivers/hdf_core/framework/include",
    }
    for link, target in links.items():
        if link.is_symlink() or link.exists():
            link.unlink()
        link.symlink_to(target)
    copies = [
        (root / "kernel/linux/common_modules/memory_security", kroot / "fs/proc/memory_security"),
        (root / "kernel/linux/common_modules/code_sign", kroot / "fs/code_sign"),
        (root / "kernel/linux/common_modules/dec", kroot / "fs/dec"),
        (root / "third_party/bounds_checking_function", kroot / "bounds_checking_function"),
        (root / "third_party/FreeBSD/sys/dev/evdev", kroot / "drivers/hdf/evdev"),
    ]
    for src, dst in copies:
        if not src.is_dir():
            raise SystemExit("missing dependency: " + str(src))
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst, symlinks=True)
    hc_make = root / "drivers/hdf_core/framework/tools/hc-gen/Makefile"
    if hc_make.is_file():
        text = hc_make.read_text()
        text = text.replace("-std=gnu++14 -s", "-std=gnu++14 -s -include cstdint -Wno-error")
        hc_make.write_text(text)
    stdarg = kroot / "include/linux/stdarg.h"
    if stdarg.is_file():
        shutil.copy2(stdarg, kroot / "bounds_checking_function/include/stdarg.h")


def fix_x86_cpu(kroot: Path, out: Path, env):
    kconfig = kroot / "arch/x86/Kconfig.cpu"
    if not kconfig.is_file():
        return
    text = kconfig.read_text()
    text = re.sub(r"(config CPU_SUP_AMD\n\s+default )y", r"\1n", text)
    text = re.sub(r"(config CPU_SUP_HYGON\n\s+default )y", r"\1n", text)
    kconfig.write_text(text)
    for rel in ["arch/x86/kernel/cpu/Makefile", "arch/x86/events/amd/Makefile"]:
        p = kroot / rel
        if not p.is_file():
            continue
        lines = []
        for line in p.read_text().splitlines():
            if line.startswith("obj-$(CONFIG_CPU_SUP_AMD)"):
                line = "# " + line
            lines.append(line)
        p.write_text("\n".join(lines) + "\n")
    make(kroot, out, env, "olddefconfig")
    scripts_config = kroot / "scripts/config"
    if scripts_config.is_file():
        run([str(scripts_config), "--file", str(out / ".config"),
             "--disable", "CPU_SUP_HYGON", "--disable", "CPU_SUP_AMD"],
            env=env, check=False)
        make(kroot, out, env, "olddefconfig")


def install_defconfig(spec: KernelSpec, kroot: Path):
    src = BASE / "configs" / spec.defconfig
    if not src.is_file():
        raise SystemExit("defconfig not found: " + str(src))
    dst = kroot / "arch/x86/configs" / spec.defconfig
    shutil.copy2(src, dst)


def valid_kernel_worktree(kroot: Path) -> bool:
    git = kroot / ".git"
    if not git.exists() and not git.is_symlink():
        return False
    result = subprocess.run(["git", "-C", str(kroot), "rev-parse", "--is-inside-work-tree"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return result.returncode == 0


def pristine_clone(kroot: Path, spec: KernelSpec):
    """Keep kernels/<name> as an unmodified clone of the upstream branch."""
    if kroot.is_dir() and not valid_kernel_worktree(kroot):
        print("kernel clone is not a git worktree, re-cloning " + str(kroot))
        shutil.rmtree(kroot)
    if not kroot.is_dir():
        kroot.parent.mkdir(parents=True, exist_ok=True)
        run(["git", "clone", "--depth=1", "--single-branch",
             "-b", spec.branch, spec.repo, str(kroot)])


def work_copy(kroot: Path, wsrc: Path):
    """Copy the pristine kernel into work/<name>/src for patching.

    git clone --local silently falls back to a full copy for shallow clones,
    so copy the tree instead; reflink is used when the filesystem supports it.
    """
    if wsrc.is_dir() and not valid_kernel_worktree(wsrc):
        print("kernel working copy is not a git worktree, re-copying " + str(wsrc))
        shutil.rmtree(wsrc)
    if not wsrc.is_dir():
        wsrc.parent.mkdir(parents=True, exist_ok=True)
        print("copy working copy " + str(wsrc) + " from " + str(kroot))
        result = subprocess.run(["cp", "-a", "--reflink=auto",
                                 str(kroot), str(wsrc)])
        if result.returncode != 0:
            raise SystemExit("failed to copy kernel working copy")


def prepare_one(version: str, spec: KernelSpec, repos: Dict[str, RepoSpec]):
    if not spec.enabled:
        raise SystemExit("kernel " + version + " is disabled")
    key = kernel_id(version, spec)
    kroot = kernel_root(key)
    wroot = work_root(key)
    marker = wroot / ".ohos-prepared"
    if marker.exists():
        print("already prepared " + version + ", skip")
        return
    pristine_clone(kroot, spec)
    wsrc = src_root(key)
    work_copy(kroot, wsrc)
    deps_root = prepare_deps(version, spec, repos)
    apply_patches(version, wsrc, deps_root, spec)
    setup_hdf(deps_root, wsrc)
    install_defconfig(spec, wsrc)
    env = kernel_env(spec)
    out = build_root(key)
    make(wsrc, out, env, spec.defconfig)
    make(wsrc, out, env, "olddefconfig")
    fix_x86_cpu(wsrc, out, env)
    marker.write_text("ok\n")
    print("prepared " + version + " in " + str(wsrc))
