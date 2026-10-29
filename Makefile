# Trading Post Mission Filter
# Builds the FOMOD installer with the AMUMSS Linux port.
#
# What it does: the yellow mission terminal at outer space trading
# posts offers a mix of mission types, with the package delivery run
# rare. Each installer option rewrites the board weights so one type
# wins nearly every roll: package delivery, asteroid mining,
# salvage, or slime cleanup.
#
# Every value this mod patches lives in src/patches.tsv. That table
# drives both the rendered script and the verify step, so a value
# can never be patched without also being checked.
#
# Usage:
#   make release      clean + rebuild + verify + pack dist/ zip (default)
#   make verify       sanity-check the built outputs and the installer
#   make clean        remove build/ and dist/
#
# Override the AMUMSS install location if needed:
#   make AMUMSS_HOME=/path/to/AMUMSS release
#
# Game-update playbook (see README.md):
#   1. fetch latest MBINCompiler into AMUMSS_HOME
#   2. re-derive the bases in src/patches.tsv (see README.md)
#   3. bump VERSION below (the mod version, published on Nexus)
#   4. make release, import + deploy + test in game

AMUMSS_HOME ?= $(HOME)/AMUMSS
AMUMSS_LINUX ?= $(HOME)/Git/AMUMSS/linux

# The mod version, published as the version of the Nexus release. An
# unreleased build stays at 0.0.0; the first public release bumps this in the
# same commit that publishes it. The version is deliberately not part of the
# mod name: the artifact is named after the mod alone (see FOMOD_ZIP), because
# a mod manager names the installed mod after the archive file name and shows
# the version in a column of its own.
VERSION      := 0.1.0

MOD_SET      := Trading Post Mission Filter

SRC_TEMPLATE := src/mission.lua.in
SRC_TABLE    := src/patches.tsv

BUILD := build
DIST  := dist
STAMP := $(BUILD)/.built

# Installer variants, one per mission type. Each variant label names
# the rendered script, the CreatedMODS folder, the fomod source
# folder and the in-game MOD_FILENAME suffix, so it must match
# ModuleConfig.xml exactly.
VARIANT := postie-only asteroid-only salvage-only slime-only

# The scope each variant renders: the tag in src/patches.tsv whose
# rows carry this variant's weights.
SCOPES_postie-only   := postie-only:1
SCOPES_asteroid-only := asteroid-only:1
SCOPES_salvage-only  := salvage-only:1
SCOPES_slime-only    := slime-only:1

DESC_postie-only   := package delivery only
DESC_asteroid-only := asteroid mining only
DESC_salvage-only  := salvage only
DESC_slime-only    := slime cleanup only

RENDERED := $(addprefix $(BUILD)/,$(addsuffix .lua,$(VARIANT)))
EXPECTED := $(addprefix $(BUILD)/,$(addsuffix .expected.tsv,$(VARIANT)))

# clean runs before build runs before verify, so release must not be parallel.
.NOTPARALLEL:

.PHONY: all release build verify assets clean

all: release

# The artifact is named after the mod and nothing else, for the same reason
# the mod name carries no version: the file name is what a mod manager shows
# as the mod name.
FOMOD_ZIP := $(DIST)/$(MOD_SET).zip

release: clean build verify
	@rm -rf "$(BUILD)/fomodz" && mkdir -p "$(BUILD)/fomodz/fomod" $(addprefix "$(BUILD)/fomodz/",$(VARIANT))
	@set -e; for v in $(VARIANT); do cp -a "$(BUILD)/$(MOD_SET) - $$v/." "$(BUILD)/fomodz/$$v/"; done
	@cp src/ModuleConfig.xml "$(BUILD)/fomodz/fomod/"
	@mkdir -p "$(DIST)" && rm -f "$(FOMOD_ZIP)" && cd "$(BUILD)/fomodz" && zip -qr "$(shell pwd)/$(FOMOD_ZIP)" fomod $(VARIANT)
	@python3 src/verify_installer.py --config src/ModuleConfig.xml --archive "$(FOMOD_ZIP)" --mod-set "$(MOD_SET)" --variants "$(VARIANT)"
	@echo "packed: $(FOMOD_ZIP) (version $(VERSION))"

# Render one variant: the script and the expected values that verify checks
# the built EXML against. The guard turns a typo in VARIANT into a loud
# failure rather than a script with no patches.
$(BUILD)/%.lua $(BUILD)/%.expected.tsv: $(SRC_TEMPLATE) $(SRC_TABLE) src/render_mod.py
	@mkdir -p "$(BUILD)"
	@test -n "$(SCOPES_$*)" -a -n "$(DESC_$*)" || { echo "ERROR: unknown variant '$*' - add SCOPES_$* and DESC_$* to the Makefile" >&2; exit 1; }
	@python3 src/render_mod.py --variant "$*" --desc "$(DESC_$*)" --table "$(SRC_TABLE)" \
		--template "$(SRC_TEMPLATE)" \
		--out-script "$(BUILD)/$*.lua" --out-expected "$(BUILD)/$*.expected.tsv"

# One pipeline run builds every variant as an individual mod.
build: $(RENDERED)
	@test -d "$(AMUMSS_HOME)/MODBUILDER" || (echo "ERROR: no AMUMSS install at $(AMUMSS_HOME) (set AMUMSS_HOME=...)" >&2; exit 1; )
	@test -x "$(AMUMSS_HOME)/MODBUILDER/MBINCompiler-linux" || (echo "ERROR: run $(AMUMSS_LINUX)/scripts/fetch_mbincompiler.sh with AMUMSS_HOME=$(AMUMSS_HOME) first" >&2; exit 1; )
	@mkdir -p "$(BUILD)"
	@set -e; \
	if [ -d "$(AMUMSS_HOME)/ModScript" ]; then mv "$(AMUMSS_HOME)/ModScript" "$(AMUMSS_HOME)/ModScript.makebak"; trap 'rm -rf "$(AMUMSS_HOME)/ModScript"; mv "$(AMUMSS_HOME)/ModScript.makebak" "$(AMUMSS_HOME)/ModScript"' EXIT; fi; \
	mkdir -p "$(AMUMSS_HOME)/ModScript"; \
	cp $(RENDERED) "$(AMUMSS_HOME)/ModScript/"; \
	for v in $(VARIANT); do rm -rf "$(AMUMSS_HOME)/CreatedMODS/$(MOD_SET) - $$v"; done; \
	AMUMSS_HOME="$(AMUMSS_HOME)" "$(AMUMSS_LINUX)/buildmod.sh" --run-pipeline; \
	rm -rf "$(AMUMSS_HOME)/ModScript"; \
	if [ -d "$(AMUMSS_HOME)/ModScript.makebak" ]; then mv "$(AMUMSS_HOME)/ModScript.makebak" "$(AMUMSS_HOME)/ModScript"; fi; \
	trap - EXIT
	@set -e; for v in $(VARIANT); do \
		rm -rf "$(BUILD)/$(MOD_SET) - $$v"; \
		mkdir -p "$(BUILD)/$(MOD_SET) - $$v"; \
		cp -a "$(AMUMSS_HOME)/CreatedMODS/$(MOD_SET) - $$v"/* "$(BUILD)/$(MOD_SET) - $$v/"; \
	done
	@touch "$(STAMP)"
	@echo "built: $(foreach v,$(VARIANT),$(BUILD)/$(MOD_SET) - $(v) )"

# verify_build.py checks the built EXML against the rendered table.
# verify_installer.py checks that ModuleConfig.xml offers exactly the shipped
# variants, one folder per plugin, and that every offered folder was built.
# It also rejects conditional file installs: Amethyst applies every pattern in
# one regardless of the flags, which installed all nine variants at once.
verify: build
	@for n in "$$(sed -n 's:.*<moduleName>\(.*\)</moduleName>.*:\1:p' src/ModuleConfig.xml)" "$(MOD_SET)"; do \
		if printf '%s' "$$n" | grep -qE '[vV]?[0-9]+(\.[0-9]+)+'; then \
			echo "ERROR: the mod name must not carry a version: '$$n'" >&2; exit 1; \
		fi; \
	done
	@python3 src/verify_build.py --build "$(BUILD)" --mod-set "$(MOD_SET)" --variants "$(VARIANT)"
	@python3 src/verify_installer.py --config src/ModuleConfig.xml --build "$(BUILD)" --mod-set "$(MOD_SET)" --variants "$(VARIANT)" --diag ""

# Nexus page images from the source screenshot in assets/src. The generated
# images are build artifacts and are not tracked; the screenshot and the
# typeface are.
assets: assets/src/gallery-trading-post.jpg assets/generate.py
	python3 assets/generate.py

clean:
	rm -rf "$(BUILD)" "$(DIST)"
