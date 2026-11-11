#!/usr/bin/env python3
"""Boot Alpine as the real Ext4 root, install APKs, compile and run C in HERE."""
import importlib
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
session = importlib.import_module("linux-session")
image = importlib.import_module("lab-image").existing_image(os.environ.get("HERE_ALPINE_IMAGE", "alpine-lab.img"))
prefix = os.environ.get("HERE_LAB_CHAPTER", "ch6")
command = ["target/release/here", ".cache/images/linux-busybox-rv64gc.bin",
           "--dtb", "dts/alpine-lab.dtb", "--device", f"virtio-block:{image}",
           "--device", "virtio-rng:/dev/urandom", "--max-cycles", "40000000000"]
commands = (
    "export PATH=/usr/sbin:/usr/bin:/sbin:/bin\n"
    "cat /etc/alpine-release\n"
    "cat /proc/mounts\n"
    "readlink /proc/1/exe\n"
    "apk --no-network add /opt/apks/*.apk; echo APK_STATUS=$?\n"
    "apk info -e gcc make musl-dev; echo PACKAGES_STATUS=$?\n"
    "gcc --version\n"
    "make --version\n"
    "printf '%s\\n' '#include <stdio.h>' 'int main(void) { int sum=0; for(int i=1;i<=6;i++)sum+=i; printf(\"ALPINE GCC PASS: %d\\n\",sum*2); return sum!=21; }' > /root/native.c\n"
    "gcc -O2 -march=rv64gc -mabi=lp64d /root/native.c -o /root/native; echo GCC_STATUS=$?\n"
    "/root/native; echo NATIVE_STATUS=$?\n"
    "sync\n"
    "poweroff -f\n"
)
early = (
    "mount -t proc proc /proc\n"
    "mount -t sysfs sysfs /sys\n"
    "mdev -s\n"
    "mkdir -p /newroot\n"
    "mount -t ext4 /dev/vda /newroot\n"
    "umount /proc\n"
    "umount /sys\n"
    "exec /sbin/switch_root /newroot /sbin/init\n"
)
text = session.run(command, f"{prefix}-alpine.txt", early, host_timeout=600,
                   after_ready=("HERE_ALPINE_ROOT_READY", commands))
for expected in ("3.24.4", "APK_STATUS=0", "PACKAGES_STATUS=0", "GCC_STATUS=0",
                 "NATIVE_STATUS=0", "ALPINE GCC PASS: 42"):
    assert session.result_line(text, expected), f"missing {expected}:\n{text[-8000:]}"
assert "/dev/vda / ext4 rw" in text and "HERE_ALPINE_ROOT_READY" in text, text[-8000:]
assert "Run /bin/sh as init process" in text, "kernel did not run the early PID1 shell"
assert "Run /init as init process" not in text, "booted the bundled initramfs instead"
assert "I/O error" not in text, "disk reads must not fail during package installation"
print("Alpine: real Ext4 root, APK installation, native GCC compilation and result 42 verified")
