# ohos-kernel-latte

OpenHarmony multi-kernel x86_64 QEMU builder in Python.

## Features

- multi-kernel matrix in annotated versions.json + versions.schema.json
- shared dependency cache under .cache/repos
- no OHOS source tree dependency for HDF/common_modules/BCL/FreeBSD/ohemu
- per-version workspace copies; cached repositories and kernels/ clones are never modified
- per-version patches and defconfig
- optional 6.1 LTS variant

## Commands

    python3 ohos_kernel.py list
    python3 ohos_kernel.py prepare 7.0
    python3 ohos_kernel.py build 7.0
    python3 ohos_kernel.py package 7.0
    python3 ohos_kernel.py all 7.0
    python3 ohos_kernel.py clean 7.0
    python3 ohos_kernel.py reset 7.0
    python3 ohos_kernel.py make 7.0 menuconfig

## Kernels

    7.0            6.6   enabled   OpenHarmony-7.0-Release
    6.1-lts        6.6   enabled   OpenHarmony-6.1-Release
    6.1-lts-5.10   5.10  disabled  OpenHarmony-6.1-Release
    7.0-5.10       5.10  disabled  OpenHarmony-7.0-Release

6.1 LTS currently reuses the 7.0 QEMU patch set and is marked experimental in
versions.json; replace patches/v6.1-k6.6 when a dedicated set is available.

## Cache

Repositories are cloned once into:

    .cache/repos/<repo-name>/<branch>

Then copied into:

    work/<name>/ohos/<repo-path>

Kernel builds use symlinks into work/<name>/ohos and never write to
.cache/repos.

## Toolchain

The builder uses the OpenHarmony clang prebuilt when available, otherwise
system clang/ld.lld. Override explicitly with:

    CLANG_BIN=/path/to/llvm/bin python3 ohos_kernel.py build 7.0

## Outputs

    kernels/<name>/          pristine clone of the upstream branch
    work/<name>/src/         working copy; device and local patches live here
    work/<name>/ohos/        per-variant dependency copy
    work/<name>/out/         kernel build output (O=)
    out/<name>/bzImage
    out/<name>/modules/
    out/<name>/firmware/
    out/ohos-kernel-<name>.tar.gz

<name> is v<release>-k<kernel-version>, e.g. v7.0-k6.6; kernels/, work/ and
out/ all use it.

## Toolchain cache

OpenHarmony LLVM 15.0.4 is a standalone tarball, not only an SDK file:

    https://repo.huaweicloud.com/openharmony/compiler/clang/15.0.4-02fbe8/linux/clang_linux-x86_64-02fbe8-20260908.tar.gz

Size: 789238720 bytes
SHA256: 8c1173e6386e2c7f72ca8350693fb2cf122b6fc6107fa66c77c6ba6283743edf

ohos_kernel.py downloads and verifies it into:

    .cache/toolchain/clang-15.0.4/llvm

The driver then uses .cache/toolchain/clang-15.0.4/llvm/bin/clang instead of
the SDK tree. Override with CLANG_BIN if needed:

    CLANG_BIN=/path/to/llvm/bin python3 ohos_kernel.py build 7.0

## Patches

Official QEMU device patches are fetched from the device_qemu repository cache:

    work/<name>/ohos/device/qemu/common/virt_full/kernel/patch

Set official_patches in versions.json to change that path. Local override patches are searched recursively under:

    patches/v<release>-k<kernel-version>/**/*.patch

Examples:

    patches/v7.0-k6.6/
    patches/v7.0-k5.10/
    patches/v6.1-k6.6/
    patches/v6.1-k5.10/

They are applied after the official set. Do not duplicate official patches in
the local tree.

The name v<release>-k<kernel-version> (system release plus kernel version) is
the project-wide naming for a kernel variant, not a patches-only key. The same
name is used by configs/ defconfigs, patches/ directories and kernels/ caches:

    name            defconfig                     patches/ + kernels/
    v7.0-k6.6       v7.0_defconfig                v7.0-k6.6
    v7.0-k5.10      v7.0-k5.10_defconfig          v7.0-k5.10
    v6.1-k6.6       v6.1-lts_defconfig            v6.1-k6.6
    v6.1-k5.10      v6.1-lts-k5.10_defconfig      v6.1-k5.10

The name is stored in the patches field of versions.json, so a version always
has a matching patches/kernels pair. Versions that share a name share one
kernel cache directory.

## Kernel clone, working copy and outputs

kernels/<name> is a pristine clone of the upstream branch, where <name> is
v<release>-k<kernel-version> (for example kernels/v7.0-k6.6 for the 7.0
version). prepare never writes to it: it copies the clone into
work/<name>/src and applies the device and local patches, the HDF symlinks,
the defconfig and the x86 CPU tweaks there. Build artifacts never go there
either; the kernel O= output is written to work/<name>/out.

clean removes only build output:

    work/<name>/out
    out/<name>

reset drops the whole per-variant workspace (work/<name> and out/<name>) and
leaves the pristine clone in kernels/<name> untouched, so the next prepare
starts from a fresh copy:

    python3 ohos_kernel.py reset 7.0
    python3 ohos_kernel.py prepare 7.0
    python3 ohos_kernel.py build 7.0
