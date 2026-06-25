#!/usr/bin/env python3
"""Extract a PyInstaller PYZ archive and disassemble application bytecode."""

from __future__ import annotations

import argparse
import dis
import importlib.util
import marshal
import struct
import types
import zlib
from pathlib import Path


def extract_pyz(path: Path, output: Path) -> None:
    data = path.read_bytes()
    if data[:4] != b"PYZ\0":
        raise SystemExit("Not a PYZ archive")
    toc_offset = struct.unpack("!I", data[8:12])[0]
    toc = marshal.loads(data[toc_offset:])
    output.mkdir(parents=True, exist_ok=True)
    for name, entry in toc:
        typecode, offset, length = entry
        payload = zlib.decompress(data[offset : offset + length])
        module_path = output / (name.replace(".", "/") + ("/__init__.pyc" if typecode == 1 else ".pyc"))
        module_path.parent.mkdir(parents=True, exist_ok=True)
        # Python's current pyc header is 16 bytes; payload is a marshalled code object.
        module_path.write_bytes(importlib.util.MAGIC_NUMBER + b"\0" * 12 + payload)
    print(f"Extracted {len(toc)} PYZ modules to {output}")


def write_disassembly(code: types.CodeType, stream, indent: int = 0) -> None:
    prefix = " " * indent
    stream.write(f"{prefix}# code object: {code.co_qualname} ({code.co_filename}:{code.co_firstlineno})\n")
    stream.write(f"{prefix}# args={code.co_argcount}, posonly={code.co_posonlyargcount}, kwonly={code.co_kwonlyargcount}, locals={code.co_varnames}\n")
    for instruction in dis.Bytecode(code, show_caches=False):
        stream.write(f"{prefix}{instruction.offset:>4} {instruction.opname:<30} {instruction.argrepr}\n")
    for constant in code.co_consts:
        if isinstance(constant, types.CodeType):
            stream.write("\n")
            write_disassembly(constant, stream, indent + 2)


def disassemble_script(path: Path, output: Path) -> None:
    code = marshal.loads(path.read_bytes())
    if not isinstance(code, types.CodeType):
        raise SystemExit(f"{path} does not contain a code object")
    with output.open("w", encoding="utf-8") as stream:
        write_disassembly(code, stream)
    print(f"Wrote disassembly to {output}")


def main() -> None:
    parser = argparse.ArgumentParser()
    subcommands = parser.add_subparsers(dest="command", required=True)
    pyz = subcommands.add_parser("pyz")
    pyz.add_argument("archive", type=Path)
    pyz.add_argument("--output", type=Path, default=Path("pyz_modules"))
    script = subcommands.add_parser("script")
    script.add_argument("bytecode", type=Path)
    script.add_argument("--output", type=Path, default=Path("portable_motor_gui.dis"))
    args = parser.parse_args()
    if args.command == "pyz":
        extract_pyz(args.archive, args.output)
    else:
        disassemble_script(args.bytecode, args.output)


if __name__ == "__main__":
    main()
