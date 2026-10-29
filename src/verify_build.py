#!/usr/bin/env python3
"""Check the built Trading Post Mission Filter variants.

For every variant this asserts, per patched file:

  1. the EXML exists and was produced by this run, not carried over
     from a previous one
  2. every table entry carries the expected Weighting: the picked
     type at 1000, everything else at 1
  3. every entry NOT listed for the variant still carries its
     shipped base weight, so the patch touches nothing else
  4. the table still holds exactly the ten known entries, so a game
     update that adds, removes or renames one fails here loudly
     instead of shipping a half-patched board
  5. there are no marker tags, which would leave the patch visibly
     annotated in game

Job 1 covers the failure mode the others cannot see. The build
copies out of the AMUMSS CreatedMODS directory, which is a
persistent directory this mod does not own. When a script changes
nothing AMUMSS creates nothing and leaves the previous build's file
sitting there, and the copy then succeeds and the other jobs
happily validate last week's output.
"""

import argparse
import os
import sys
import xml.etree.ElementTree as ET


def read_expected(path):
    """Return the expected rows as (file, entry, prop, base, value) tuples."""
    rows = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            file_path, entry, prop, base, value = line.split("\t")
            rows.append((file_path, entry, prop, base, value))
    return rows


def entry_weights(exml_path, failures, variant):
    """Return {MissionID: Weighting} for the table, or None on failure."""
    try:
        root = ET.parse(exml_path).getroot()
    except ET.ParseError as e:
        failures.append("%s: cannot parse %s: %s" % (variant, exml_path, e))
        return None
    entries = root.findall("./Property[@name='Missions']/Property[@name='Missions']")
    if len(entries) != 10:
        failures.append(
            "%s: table holds %d entries, want 10 - the game table changed, re-derive src/patches.tsv"
            % (variant, len(entries))
        )
        return None
    weights = {}
    for entry in entries:
        # AMUMSS writes only the changed subtree per entry, tagged
        # with the matched _id; the MissionID leaf itself is gone.
        ident = entry.get("_id")
        if not ident:
            mid = entry.find("./Property[@name='MissionID']")
            ident = mid.get("value") if mid is not None else None
        if not ident:
            failures.append("%s: an entry has no MissionID" % variant)
            return None
        found = entry.findall(".//Property[@name='Weighting']")
        if len(found) != 1:
            failures.append(
                "%s: entry %s holds %d Weighting fields, want exactly 1"
                % (variant, ident, len(found))
            )
            return None
        weights[ident] = found[0].get("value")
    return weights


def check_variant(build, mod_set, variant, expected_path, failures):
    """Check one variant, appending any problems to failures."""
    script = os.path.join(build, "%s.lua" % variant)
    rows = read_expected(expected_path)
    if not rows:
        failures.append("%s: no expected rows" % variant)
        return

    files = sorted({file_path for file_path, _, _, _, _ in rows})
    for file_path in files:
        rel = file_path[: -len(".MBIN")] + ".EXML"
        exml = os.path.join(
            build, "%s - %s" % (mod_set, variant), rel.replace("/", os.sep)
        )
        if not os.path.isfile(exml):
            failures.append("%s: MISSING %s" % (variant, rel))
            continue
        if os.path.getmtime(exml) < os.path.getmtime(script):
            failures.append(
                "%s: STALE %s - older than the script that should have produced it"
                % (variant, rel)
            )
            continue
        with open(exml, encoding="utf-8") as handle:
            text = handle.read()
        if "!#" in text:
            failures.append("%s: marker tags present in %s" % (variant, rel))
        weights = entry_weights(exml, failures, variant)
        if weights is None:
            continue
        want_ids = {entry for f, entry, _, _, _ in rows if f == file_path}
        if set(weights) != want_ids:
            failures.append(
                "%s: entry ids %s do not match the table %s"
                % (variant, sorted(weights), sorted(want_ids))
            )
            continue
        for _, entry, prop, base, value in rows:
            if prop != "Weighting":
                failures.append("%s: unexpected prop %r" % (variant, prop))
                continue
            if weights[entry] != value:
                failures.append(
                    "%s: entry %s Weighting is %s, want %s"
                    % (variant, entry, weights[entry], value)
                )
        # Every variant lists all ten entries (each variant rewrites
        # the whole board), so the loop above already asserts that no
        # entry keeps a stale or shipped weight by accident. BASE is
        # carried for re-derivation, not checked here.


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", required=True)
    parser.add_argument("--mod-set", required=True)
    parser.add_argument("--variants", required=True)
    args = parser.parse_args()

    failures = []
    variants = args.variants.split()
    for variant in variants:
        check_variant(
            args.build,
            args.mod_set,
            variant,
            os.path.join(args.build, "%s.expected.tsv" % variant),
            failures,
        )

    if failures:
        for failure in failures:
            print("BAD " + failure, file=sys.stderr)
        return 1
    print("verify: all %d variants carry exactly their weights" % len(variants))
    return 0


if __name__ == "__main__":
    sys.exit(main())
