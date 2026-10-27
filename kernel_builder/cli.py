"""Command line interface."""
from __future__ import annotations

import argparse

from .build import build_one, clean_one, package_one, reset_one
from .config import load_config
from .paths import build_root, kernel_root
from .prepare import prepare_one
from .toolchain import kernel_env
from .util import make


def select(names):
    default, repos, kernels = load_config()
    selected = names or [default]
    for name in selected:
        if name not in kernels:
            raise SystemExit("unknown kernel: " + name)
    return repos, kernels, selected


def main():
    parser = argparse.ArgumentParser(description="OpenHarmony multi-kernel builder")
    sub = parser.add_subparsers(dest="cmd", required=True)
    for cmd in ["prepare", "build", "package", "clean", "reset"]:
        p = sub.add_parser(cmd)
        p.add_argument("versions", nargs="*")
    sub.add_parser("list")
    p_all = sub.add_parser("all")
    p_all.add_argument("versions", nargs="*")
    p_make = sub.add_parser("make")
    p_make.add_argument("version")
    p_make.add_argument("args", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    if args.cmd == "list":
        default, repos, kernels = load_config()
        for name, spec in kernels.items():
            state = "enabled" if spec.enabled else "disabled"
            print(name.ljust(16), spec.kernel_version.ljust(8), state.ljust(10),
                  spec.branch, "|", spec.description)
        return

    repos, kernels, names = select(getattr(args, "versions", []))
    if args.cmd == "make":
        spec = kernels[args.version]
        env = kernel_env(spec)
        make(kernel_root(args.version), build_root(args.version), env, *args.args)
        return
    for name in names:
        spec = kernels[name]
        if args.cmd == "prepare":
            prepare_one(name, spec, repos)
        elif args.cmd == "build":
            build_one(name, spec)
        elif args.cmd == "package":
            package_one(name)
        elif args.cmd == "clean":
            clean_one(name)
        elif args.cmd == "reset":
            reset_one(name)
        elif args.cmd == "all":
            prepare_one(name, spec, repos)
            build_one(name, spec)
            package_one(name)
