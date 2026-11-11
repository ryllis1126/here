#!/usr/bin/env python3
"""Prepare reproducible Linux ABI programs and new laboratory disk images."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)


def run(command, **kwargs):
    print(f"COMMAND: {command!r}", flush=True)
    subprocess.run(command, check=True, timeout=120, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--busybox-image", default="busybox-lab.img")
    parser.add_argument("--alpine-image", default="alpine-lab.img")
    args = parser.parse_args()
    # Check all asset digests before executing tools or importing package content.
    packages = []
    for asset in json.loads(Path("scripts/linux-assets.json").read_text()):
        path = Path(asset["path"])
        if hashlib.sha256(path.read_bytes()).hexdigest() != asset["sha256"]:
            raise ValueError(f"asset digest mismatch: {path}")
        if path.parent == Path(".cache/linux/apks") and path.suffix == ".apk":
            packages.append(path)
    for name in (args.busybox_image, args.alpine_image):
        if os.path.lexists(ROOT / ".cache/images" / name):
            raise FileExistsError(f"image exists, choose a NEW filename: {name}")
    work = Path(tempfile.mkdtemp(prefix="prepare-", dir=ROOT / ".cache/linux"))
    print(f"WORK={work}", flush=True)
    base = work / "base"
    with tarfile.open(".cache/images/alpine-minirootfs-3.24.4-riscv64.tar.gz") as archive:
        # Official hash-verified rootfs has absolute BusyBox symlinks, retained
        # for the guest. No member pathname may escape this new staging tree.
        for member in archive.getmembers():
            if member.name.startswith("/") or ".." in Path(member.name).parts:
                raise ValueError(f"unsafe archive path {member.name}")
        archive.extractall(base, filter="fully_trusted")
    apk = work / "apk.static"
    with tarfile.open(".cache/tools/apk-tools-static-3.0.9-r0.apk", ignore_zeros=True) as archive:
        apk.write_bytes(archive.extractfile("sbin/apk.static").read())
    apk.chmod(0o755)
    sysroot = work / "sysroot"
    shutil.copytree(base, sysroot, symlinks=True)
    (sysroot / "var/cache/apk").mkdir(parents=True, exist_ok=True)
    run([str(apk), "--root", str(sysroot), "--arch", "riscv64", "--no-scripts", "--no-network",
         "add", ".cache/linux/apks/musl-1.2.6-r3.apk", ".cache/linux/apks/musl-dev-1.2.6-r3.apk",
         ".cache/linux/apks/libgcc-static-15.2.0-r5.apk"])
    disk = work / "busybox-disk"
    disk.mkdir()
    lib = sysroot / "usr/lib"
    run(["clang", "--target=riscv64-linux-musl", "-march=rv64gc", "-mabi=lp64d",
         f"--sysroot={sysroot}", "-fuse-ld=lld", "-O2", "-static", "-nostdlib", "-DHOST_TEST",
         str(lib / "crt1.o"), str(lib / "crti.o"), "test_resources/src/lab_calculator.c",
         "-Wl,--start-group", str(lib / "libc.a"),
         str(lib / "gcc/riscv64-alpine-linux-musl/15.2.0/libgcc.a"), "-Wl,--end-group",
         str(lib / "crtn.o"), "-o", str(disk / "calculator")])
    run(["python3", "scripts/lab-image.py", args.busybox_image, str(disk)])
    alpine = work / "alpine"
    shutil.copytree(base, alpine, symlinks=True)
    package_cache = alpine / "opt/apks"
    package_cache.mkdir(parents=True)
    for package in packages:
        shutil.copy2(package, package_cache)
    # Read-only course artifacts are copied into the image for native builds.
    (alpine / "root/lab_calculator.c").write_bytes(Path("test_resources/src/lab_calculator.c").read_bytes())
    (alpine / "etc/inittab").write_text(
        "# Isolated local laboratory console\n::sysinit:/sbin/lab-boot\n"
        "ttyS0::respawn:/bin/sh\n::ctrlaltdel:/sbin/reboot\n"
        "::shutdown:/bin/sync\n::shutdown:/bin/umount -a -r\n")
    boot = alpine / "sbin/lab-boot"
    boot.write_text("#!/bin/sh\nmount -t proc proc /proc\nmount -t sysfs sysfs /sys\n"
                    "mount -t devtmpfs devtmpfs /dev\nmkdir -p /dev/pts /run /tmp\n"
                    "mount -t devpts devpts /dev/pts\nmdev -s\n"
                    "echo HERE_ALPINE_ROOT_READY\n")
    boot.chmod(0o755)
    (alpine / "etc/profile").write_text('export PATH=/usr/sbin:/usr/bin:/sbin:/bin\nexport PS1="/ # "\n')
    run(["python3", "scripts/lab-image.py", args.alpine_image, str(alpine), "--size-mib", "512"])
    devnodes = work / "devnodes.debugfs"
    devnodes.write_text("cd /dev\nmknod console c 5 1\nmknod null c 1 3\n")
    run(["debugfs", "-w", "-f", str(devnodes), str(ROOT / ".cache/images" / args.alpine_image)])
    for stem in ("linux-lab", "alpine-lab"):
        run(["bash", "scripts/lab.sh", "dtc", "-I", "dts", "-O", "dtb", "-o",
             f"dts/{stem}.dtb", f"dts/{stem}.dts"])
    print("EXIT_CODE=0")


if __name__ == "__main__":
    main()
