#!/usr/bin/env python3
"""Create only NEW regular laboratory Ext4 images; never mount the host."""
import argparse
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parent.parent


def existing_image(name):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*\.img", name):
        raise ValueError("expected a simple lab image filename")
    image = ROOT / ".cache/images" / name
    if image.is_symlink() or not image.is_file():
        raise ValueError("expected an existing regular lab image, not a device or symlink")
    return str(image)


def reserve_image(directory, name, size_mib):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*\.img", name):
        raise ValueError("image must be a simple filename ending in .img")
    if not 16 <= size_mib <= 2048:
        raise ValueError("lab image size must be between 16 and 2048 MiB")
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    image = directory / name
    # EXCL refuses regular files AND dangling symlinks. Never truncate a user file.
    fd = os.open(image, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644)
    try:
        os.ftruncate(fd, size_mib * 1024 * 1024)
    finally:
        os.close(fd)
    return image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name")
    parser.add_argument("staging", type=Path)
    parser.add_argument("--size-mib", type=int, default=40)
    args = parser.parse_args()
    staging = args.staging.resolve(strict=True)
    if not staging.is_dir():
        parser.error("staging must be a directory")
    image = reserve_image(ROOT / ".cache/images", args.name, args.size_mib)
    command = ["mkfs.ext4", "-q", "-F", "-L", "HERE-LAB", "-E", "root_owner=0:0",
               "-d", str(staging), str(image)]
    print(f"COMMAND: {command!r}", flush=True)
    subprocess.run(command, check=True, timeout=120)
    subprocess.run(["e2fsck", "-fn", str(image)], check=True, timeout=120)
    print(f"IMAGE={image}\nEXIT_CODE=0")


if __name__ == "__main__":
    main()
