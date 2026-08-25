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
portable contracts and a real Windows x64 Tiles+Sound compile/link plus
ephemeral deterministic-package gate using checksum-verified MXE GCC 11.2.
Pull-request compiler outputs are not retained.

A `v0.G-additive-*` tag must reproduce identical executable and ZIP hashes from
two clean builds. The exact staged archive is then extracted on Windows, checked
for full-SHA provenance, and run with `--check-mods dda`. It is published as an
immutable prerelease until an operator downloads that asset and completes the
copied-save load smoke on Windows. The full Catch build has a pre-existing
EOC-test compile failure; the copied-save smoke remains the final release
recommendation check.
