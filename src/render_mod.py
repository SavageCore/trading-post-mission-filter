#!/usr/bin/env python3
"""Render one variant of the Trading Post Mission Filter mod.

Reads the patch rows in src/patches.tsv, keeps the rows tagged for
the asked variant, writes the rendered Lua script and the expected
values that make verify checks the built EXML against.

The table drives both so a value can never be patched without also
being checked, and the two can never drift apart.
"""

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def read_table(path):
    """Return the patch rows as (file, entry, prop, base, value, scopes) tuples."""
    rows = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) != 6:
                raise SystemExit("bad patch row (need 6 tab separated fields): %r" % line)
            file_path, entry, prop, base, value, scopes = parts
            rows.append(
                (
                    file_path.strip(),
                    entry.strip(),
                    prop.strip(),
                    base.strip(),
                    value.strip(),
                    scopes.strip(),
                )
            )
    return rows


def in_scope(scopes, wanted):
    """A row is patched when its scope tag is the asked variant."""
    tags = {s.strip() for s in scopes.split(",") if s.strip()}
    return wanted in tags


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", required=True)
    parser.add_argument("--desc", required=True)
    parser.add_argument("--table", default=os.path.join(HERE, "patches.tsv"))
    parser.add_argument("--template", default=os.path.join(HERE, "mission.lua.in"))
    parser.add_argument("--out-script", required=True)
    parser.add_argument("--out-expected", required=True)
    args = parser.parse_args()

    rows = read_table(args.table)
    wanted = [
        (file_path, entry, prop, base, value)
        for file_path, entry, prop, base, value, scopes in rows
        if in_scope(scopes, args.variant)
    ]
    if not wanted:
        raise SystemExit("no patch rows for variant %r" % args.variant)

    patch_lines = []
    expected_lines = []
    for file_path, entry, prop, base, value in wanted:
        patch_lines.append(
            '    { file = "%s", entry = "%s", prop = "%s", value = "%s" },'
            % (file_path, entry, prop, value)
        )
        expected_lines.append(
            "%s\t%s\t%s\t%s\t%s" % (file_path, entry, prop, base, value)
        )

    with open(args.template, encoding="utf-8") as handle:
        template = handle.read()

    rendered = (
        template.replace("@VARIANT_LABEL@", args.variant)
        .replace("@DESC@", args.desc)
        .replace("@PATCHES@", "\n".join(patch_lines))
    )

    if "@" in rendered:
        leftover = [line for line in rendered.split("\n") if "@" in line]
        raise SystemExit("unsubstituted placeholder left in the script: %r" % leftover)

    with open(args.out_script, "w", encoding="utf-8") as handle:
        handle.write(rendered)
    with open(args.out_expected, "w", encoding="utf-8") as handle:
        handle.write("\n".join(expected_lines) + "\n")

    print(
        "rendered %s: %d entries, %d values"
        % (args.variant, len({e for _, e, _, _, _ in wanted}), len(expected_lines))
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
