# Trading Post Mission Filter

The yellow mission terminal at outer space trading posts offers a
mix of mission types, and the package delivery run is rare.
Install one option below and the terminal keeps offering that
work.

## Options

- Package delivery only
- Asteroid mining only
- Salvage only
- Slime cleanup only

Pick one in the installer. To switch types, reinstall and pick
another; missions already on the board stay as they are, new ones
follow the new choice.

## Install

Use a mod manager (Amethyst or Vortex) with the
`Trading Post Mission Filter.zip` from the release and pick one
option in the installer. Without a manager, unzip it, open the
folder for the option you want and copy everything inside it into
`GAMEDATA/MODS/Trading Post Mission Filter`. To switch, reinstall
and pick another.

## Compatibility

Built for Forsaken. Single-player mission boards only; nothing
outside the trading post board changes.

## Re-deriving on a game update

The board lives in
`METADATA/SIMULATION/MISSIONS/TABLES/SPACEOUTPOSTMISSIONTABLE.MBIN`
(10 entries as of Forsaken). After a game update:

1. Fetch the latest MBINCompiler (`AMUMSS_HOME`, see Makefile).
2. Extract and decompile the table from the installed PAKs and
   read every entry's `MissionBoardOptions` Weighting. The table
   must still hold the same ten `MissionID` values; any added,
   removed or renamed entry fails `make verify` loudly on
   purpose.
3. Update the BASE column in `src/patches.tsv` and the VALUE
   column if the wanted odds changed.
4. Bump `VERSION`, `make release`, deploy and check the board in
   game: the picked type should fill nearly every slot.
