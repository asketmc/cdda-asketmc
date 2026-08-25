# Current State

- Authoritative branch: `main`
- Vanilla foundation: `d6ec466140839dd70c1a43671eb4a08b007695c2` (0.G)
- Public history starts from the current integrated source snapshot.
- The selected H3-H6 delivery set is complete; exclusions are recorded below.

Recent integrated fixes include vehicle and general tileset directional
normalization. Modern UltiCa and SurveyorsMap four-direction arrays are adapted
to the 0.G N/E/S/W contract; legacy compatibility sheets remain unchanged.
Selected recipe lookup, inventory-letter assignment, and repair-selector paths
use bounded caches and early filtering without changing their displayed results.
Character-rooted contained item locations now resolve lazily after unloaded NPCs
are registered, preserving interrupted activity targets across save/load.

## Fast validation

```sh
python -m unittest tools.test_h5_interface_qol tools.test_h6_antigrind \
  tools.test_h6_backup_generator \
  tools.gfx_tools.test_backport_tileset_release \
  tools.gfx_tools.test_build_ultica_hires \
  tools.gfx_tools.test_beauty_backport_assets \
  tools.gfx_tools.test_visual_ui_donor_contracts
python tools/additive_audit.py --self-test
python tools/additive_audit.py --target HEAD
```

## Release boundary

`BUILD_INFO.txt` records the production command. Pull requests run the fast
portable contracts and a real Windows x64 Tiles+Sound compile/link gate using
MXE GCC 11.2. Pull-request binaries are not retained. A
`v0.G-additive-*` tag packages that exact commit and publishes its ZIP and
SHA256 checksum to GitHub Releases.

Tag `v0.G-additive-2026.08.25` identifies the current Windows Tiles+Sound
release. The full Catch build has a pre-existing EOC-test compile failure, and
cross-compilation cannot prove save behavior on Windows; a copied-save load
smoke remains the final release recommendation check.
