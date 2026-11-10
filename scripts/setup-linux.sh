#!/usr/bin/env bash
# Course firmware and native dtc, verified and kept inside the project.
set -euo pipefail
LAB_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$LAB_ROOT"
mkdir -p .cache/images .cache/tools/dtc
fetch() {
    local file=$1 digest=$2 url=$3
    if [[ -f "$file" ]] && printf '%s  %s\n' "$digest" "$file" | sha256sum --check --status; then
        printf 'VERIFIED: %s\n' "$file"
        return
    fi
    curl --fail --location --show-error --max-time 180 "$url" --output "$file.partial"
    printf '%s  %s\n' "$digest" "$file.partial" | sha256sum --check -
    mv -- "$file.partial" "$file"
}
fetch .cache/images/linux-busybox-rv64gc.bin edd320d80d5c05175c899b9328ee11809226459271ea76eaef59efd4328c178b \
    https://github.com/here-emulator/here/releases/download/prebuilt-kernels/linux-busybox-rv64gc.bin
fetch .cache/tools/device-tree-compiler.deb b2c1e8c86f18b6bda26408f92bfb9ec1a1e40bfdc41f1034600ccd68e82d2ed7 \
    https://archive.ubuntu.com/ubuntu/pool/main/d/device-tree-compiler/device-tree-compiler_1.7.0-2build1_amd64.deb
fetch .cache/tools/libfdt1.deb 274d20dfab9d6b216b5de85446a93f6ce5b2cd82c847b8dfdc508577f76eb96a \
    https://archive.ubuntu.com/ubuntu/pool/main/d/device-tree-compiler/libfdt1_1.7.0-2build1_amd64.deb
dpkg-deb --extract .cache/tools/device-tree-compiler.deb .cache/tools/dtc
dpkg-deb --extract .cache/tools/libfdt1.deb .cache/tools/dtc
bash scripts/lab.sh dtc --version
