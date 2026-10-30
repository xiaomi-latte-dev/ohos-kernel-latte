"""Kernel build, package and clean."""
from __future__ import annotations

import os
import shutil
import tarfile

from .config import KernelSpec, kernel_id
from .paths import build_root, kernel_root, out_root, src_root, work_root
from .prepare import fix_x86_cpu, install_defconfig
from .toolchain import kernel_env
from .util import make


def build_one(version: str, spec: KernelSpec):
    key = kernel_id(version, spec)
    ksrc = src_root(key)
    if not ksrc.is_dir():
        raise SystemExit("kernel not prepared: " + version +
                         " (run prepare first, expected " + str(ksrc) + ")")
    env = kernel_env(spec)
    out = build_root(key)
    if not (out / ".config").is_file():
        install_defconfig(spec, ksrc)
        make(ksrc, out, env, spec.defconfig)
    fix_x86_cpu(ksrc, out, env)
    make(ksrc, out, env, "olddefconfig")
    extra = {"KCFLAGS": "-Wno-unused-command-line-argument -Wno-error=unused-command-line-argument"}
    make(ksrc, out, env, "-j" + str(os.cpu_count() or 1), extra=extra)

    dst = out_root(key)
    (dst / "modules").mkdir(parents=True, exist_ok=True)
    (dst / "firmware").mkdir(parents=True, exist_ok=True)
    shutil.copy2(out / "arch/x86/boot/bzImage", dst / "bzImage")
    for ko in out.rglob("*.ko"):
        shutil.copy2(ko, dst / "modules" / ko.name)
    fw = work_root(key) / "ohos/device/qemu/common/virt_full/kernel/firmware"
    if fw.is_dir():
        for item in fw.iterdir():
            target = dst / "firmware" / item.name
            if item.is_dir():
                shutil.copytree(item, target, dirs_exist_ok=True)
            else:
                shutil.copy2(item, target)
    hdf = work_root(key) / "ohos/vendor/ohemu/virt/hdf_config/khdf"
    for name in ["built-in.a", ".built-in.a.cmd", "hdf_hcs.hcb",
                 "hdf_hcs_hex.o", "modules.order", ".modules.order.cmd"]:
        p = hdf / name
        if p.exists() or p.is_symlink():
            p.unlink()
    print("built " + version + ": " + str(dst / "bzImage"))


def package_one(version: str, spec: KernelSpec):
    key = kernel_id(version, spec)
    dst = out_root(key)
    if not (dst / "bzImage").is_file():
        raise SystemExit("nothing to package: " + version)
    tar = out_root(key).parent / ("ohos-kernel-" + key + ".tar.gz")
    with tarfile.open(tar, "w:gz") as tf:
        for name in ["bzImage", "modules", "firmware"]:
            p = dst / name
            if p.exists():
                tf.add(p, arcname=name)
    print("packaged " + str(tar))


def clean_one(version: str, spec: KernelSpec):
    shutil.rmtree(build_root(kernel_id(version, spec)), ignore_errors=True)
    shutil.rmtree(out_root(kernel_id(version, spec)), ignore_errors=True)
    print("cleaned build output for " + version)


def reset_one(version: str, spec: KernelSpec):
    key = kernel_id(version, spec)
    wroot = work_root(key)
    if not wroot.is_dir():
        raise SystemExit("nothing to reset: " + str(wroot))
    print("reset " + version + ": drop " + str(wroot) +
          " (pristine clone kept in " + str(kernel_root(key)) + ")")
    shutil.rmtree(wroot, ignore_errors=True)
    shutil.rmtree(out_root(key), ignore_errors=True)
