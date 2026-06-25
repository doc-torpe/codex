#!/usr/bin/env python3
"""Render the declarations recoverable from native Python 3.14 bytecode."""

from __future__ import annotations

import argparse
import marshal
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("bytecode", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pychd", type=Path, default=Path("/tmp/pychd"))
    args = parser.parse_args()

    sys.path.insert(0, str(args.pychd))
    from pychd.rules import decompile_with_rules

    code = marshal.loads(args.bytecode.read_bytes())
    result = decompile_with_rules(code)
    args.output.write_text(result.module.render() + "\n", encoding="utf-8")
    print(f"Wrote {args.output}; rule confidence: {result.confidence:.1%}")


if __name__ == "__main__":
    main()
