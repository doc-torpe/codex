#!/usr/bin/env python3
"""Extract files from a PyInstaller one-file executable."""

from __future__ import annotations

import argparse
import struct
import zlib
from pathlib import Path

MAGIC = b"MEI\014\013\012\013\016"
COOKIE_SIZE = 88  # PyInstaller CArchive cookie


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("executable", type=Path)
    parser.add_argument("--output", type=Path, default=Path("extracted"))
    args = parser.parse_args()

    data = args.executable.read_bytes()
    cookie_pos = data.rfind(MAGIC)
    if cookie_pos < 0 or cookie_pos + COOKIE_SIZE != len(data):
        raise SystemExit("PyInstaller cookie not found at the end of this executable")

    _, package_length, toc_offset, toc_length, pyvers, pylib = struct.unpack(
        "!8sIIII64s", data[cookie_pos : cookie_pos + COOKIE_SIZE]
    )
    package_start = len(data) - package_length
    toc_start = package_start + toc_offset
    toc_end = toc_start + toc_length
    output = args.output
    output.mkdir(parents=True, exist_ok=True)

    print(f"Python version code: {pyvers}; Python DLL: {pylib.split(b'\0')[0].decode()}")
    pos = toc_start
    count = 0
    while pos < toc_end:
        entry_size, offset, length, uncompressed_length, compressed, typecode = struct.unpack(
            "!IIIIBc", data[pos : pos + 18]
        )
        name_end = data.index(b"\0", pos + 18, pos + entry_size)
        name = data[pos + 18 : name_end].decode("utf-8")
        payload = data[package_start + offset : package_start + offset + length]
        if compressed:
            payload = zlib.decompress(payload)
        if len(payload) != uncompressed_length:
            raise ValueError(f"Length mismatch for {name}")
        destination = output / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(payload)
        print(f"{typecode.decode()} {name}")
        count += 1
        pos += entry_size
    print(f"Extracted {count} archive entries to {output}")


if __name__ == "__main__":
    main()
