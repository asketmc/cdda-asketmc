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

`BUILD_INFO.txt` records the production command. Hosted checks cover portable
Python/data contracts only. A release still requires the exact-tree Windows
Tiles+Sound build, affected C++ tests, `--check-mods dda`, and a copied-save
load smoke. No current baseline failure is accepted for these focused gates.
