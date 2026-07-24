#!/usr/bin/env python3
"""Pre-commit hook: block committing anything under benchmarks/raw/ (§252 — large
generated datasets, build outputs, and raw transient profiles are ignored; curated
benchmark evidence belongs in benchmarks/reports/, not benchmarks/raw/).
"""

import sys
from pathlib import PurePosixPath

RAW_PREFIX = PurePosixPath("benchmarks/raw")
ALLOWED_NAMES = {".gitkeep"}


def main(argv: list[str]) -> int:
    offending = []
    for arg in argv:
        path = PurePosixPath(arg.replace("\\", "/"))
        if path.name in ALLOWED_NAMES:
            continue
        if path == RAW_PREFIX or RAW_PREFIX in path.parents:
            offending.append(arg)

    if offending:
        print("Refusing to commit raw benchmark output (§252, benchmarks/raw/ is git-ignored evidence, not source):")
        for path in offending:
            print(f"  {path}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
