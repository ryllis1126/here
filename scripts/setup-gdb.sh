#!/usr/bin/env bash
# Extract Ubuntu's matching Python ABI locally; no apt install or system writes.
set -euo pipefail
LAB_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$LAB_ROOT"
mkdir -p .cache/tools/libpython
names=(libpython3.10 libpython3.10-minimal libpython3.10-stdlib)
hashes=(cd9ffe066be6207dd4fcb25fe037222e90429b0923d1a5eb6e897afcbb151833 ccbd08562769e0a38b34005dc8bde200838e6c6530cc04ac34525129ed42d847 ee09afbc981a4aaa00053f019eab6b45dcc4dbeb4ca4fcc4277eff539e09f228)
for i in "${!names[@]}"; do
    package=${names[$i]}
    archive=".cache/tools/$package.deb"
    if [[ ! -f "$archive" ]]; then
        curl --fail --location --show-error --max-time 120 \
            "https://archive.ubuntu.com/ubuntu/pool/main/p/python3.10/${package}_3.10.12-1~22.04.18_amd64.deb" \
            --output "$archive.partial"
        printf '%s  %s\n' "${hashes[$i]}" "$archive.partial" | sha256sum --check -
        mv -- "$archive.partial" "$archive"
    fi
    printf '%s  %s\n' "${hashes[$i]}" "$archive" | sha256sum --check -
    dpkg-deb --extract "$archive" .cache/tools/libpython
done
bash scripts/lab.sh gdb --version
