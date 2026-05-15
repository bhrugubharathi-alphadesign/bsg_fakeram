# Dual CACTI/P-CACTI Backend Plan

## Goal

Use both modeling tools where each one has credible coverage:

- P-CACTI for sub-22 nm nodes with checked-in characterization data.
- Legacy HP CACTI for 22 nm and larger nodes, preserving the repo's existing
  22-90 nm coverage and the old larger-node compatibility patch.

The generator should expose one stable `Memory` data contract to the LEF,
Liberty, Verilog, memlib, and techmap generators regardless of which backend
produced the area, timing, and power numbers.

## Backend Policy

Default `--model_backend auto` selection:

- `tech_nm < 22`: use P-CACTI.
- `tech_nm >= 22`: use legacy CACTI.

Manual override:

- `--model_backend pcacti` forces P-CACTI and requires a matching P-CACTI XML
  characterization profile.
- `--model_backend cacti` forces legacy CACTI.

P-CACTI currently ships checked-in device profiles for 7, 14, and 22 nm. Auto
mode intentionally routes 22 nm to legacy CACTI so the 22-90 nm legacy coverage
remains contiguous. Forced P-CACTI at 22 nm is still useful for comparison.

## Stage 1: Tool Layout And Build

**Commit 1: Track P-CACTI intentionally**

- Keep P-CACTI vendored at `tools/pcacti`.
- Ignore P-CACTI build products while tracking its source and XML data.
- Keep local P-CACTI tool archives out of git.

**Commit 2: Restore legacy CACTI as a second backend**

- Set `PCACTI_BUILD_DIR=tools/pcacti`.
- Set `CACTI_BUILD_DIR=tools/cacti`.
- Make `make tools` build P-CACTI and clone/build patched HP CACTI.
- Restore `patches/cacti.patch` and `patches/nmlimitremoval_patch.sh`.
- Ignore the generated `tools/cacti` checkout.

**Validation**

- `make tools`
- Confirm both binaries exist:
  - `tools/pcacti/cacti`
  - `tools/cacti/cacti`

## Stage 2: Backend-Specific Config Writers

**Commit 1: Keep legacy CACTI config generation**

- Keep `scripts/utils/cacti_config.py`.
- Add a small writer function so `Memory` does not format the CACTI template
  inline.
- Keep the patched CACTI CSV output contract.

**Commit 2: Add P-CACTI XML generation**

- Add `scripts/utils/pcacti_config.py`.
- Generate P-CACTI XML from process data, SRAM geometry, banks, cache type, and
  port shape.
- Select P-CACTI device XMLs from the checked-in characterization profiles.
- Generate per-result-dir SRAM cell XML files so generated configs rerun from
  their result directories.

**Validation**

- Generate one legacy `cacti.cfg` for a 45 nm SRAM.
- Generate one P-CACTI `pcacti.xml` for a 7 nm SRAM.
- Confirm both generated configs use the expected port counts.

## Stage 3: Shared Result Contract

**Commit 1: Parse legacy CACTI output into common fields**

- Add `scripts/utils/cacti_results.py`.
- Read the patched `cacti.cfg.out` CSV.
- Return the same keys used by downstream `Memory` fields.

**Commit 2: Patch and parse P-CACTI machine-readable output**

- Patch P-CACTI to write `pcacti.csv`.
- Add `scripts/utils/pcacti_results.py`.
- Return the same keys as the legacy CACTI parser.

**Validation**

- Check all common fields are present and positive:
  - tech node
  - capacity
  - output width
  - access/cycle time
  - read/write dynamic energy
  - leakage
  - area
  - FO4
  - width/height

## Stage 4: Runtime Backend Selection

**Commit 1: Add explicit backend selection**

- Add `--model_backend {auto,pcacti,cacti}` to `scripts/run.py`.
- Keep `--pcacti_dir` and `--cacti_dir` as real backend-specific directory
  overrides.
- In auto mode, route sub-22 nm to P-CACTI and 22 nm or larger to legacy CACTI.

**Commit 2: Split `Memory` execution paths**

- Add `Memory.__run_pcacti`.
- Add `Memory.__run_cacti`.
- Use `subprocess.run` for both backends.
- Capture stdout/stderr into per-SRAM result files.
- Raise clear errors when the selected backend binary or characterization data
  is missing.

**Validation**

- 7 nm auto run creates `pcacti.xml` and `pcacti.csv`.
- 22 nm auto run creates `cacti.cfg` and `cacti.cfg.out`.
- Forcing each backend either works or fails with a direct reason.

## Stage 5: Compatibility And Coverage Tests

**Commit 1: Update example configs**

- Keep a 7 nm P-CACTI example.
- Update legacy-node examples with required `port_shape` fields.
- Preserve the existing generated-view contract.

**Commit 2: Add smoke coverage**

- Smoke test 7 nm through P-CACTI.
- Smoke test 22, 45, and 90 nm through legacy CACTI.
- Include at least 1RW and 1RW1R shapes.
- Check generated LEF/Liberty/Verilog/memlib/techmap files exist.

**Validation**

- `make run CONFIG=example_cfgs/pcacti7.cfg`
- `make run CONFIG=example_cfgs/freepdk45.cfg`
- Temporary or checked-in 22/90 nm configs route through legacy CACTI.

## Stage 6: Documentation And Cleanup

**Commit 1: Document backend coverage**

- Update `README.md` setup instructions to say `make tools` builds both
  P-CACTI and legacy CACTI.
- Document auto backend selection.
- Document the known P-CACTI profile set and the legacy CACTI coverage role.

**Commit 2: Clean up stale assumptions**

- Remove comments that imply P-CACTI fully replaces CACTI.
- Keep legacy CACTI commands as active make targets, not dead comments.
- Keep generated results and tool build products ignored.

**Validation**

- `python3 -m py_compile scripts/run.py scripts/utils/*.py`
- `git diff --check`
- Fresh `make tools`
- End-to-end smoke runs for the P-CACTI and legacy CACTI paths.
