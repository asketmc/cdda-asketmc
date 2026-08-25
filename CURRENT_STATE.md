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
Windows sound initialization now uses bounded retries, records backend/device
diagnostics, falls back from a failed default backend to DirectSound, and skips
soundpack loading when no mixer is available.

## Fast validation

```sh
python -m unittest tools.test_h5_interface_qol tools.test_h6_antigrind \
  tools.test_h6_backup_generator \
  tools.test_windows_audio_recovery \
  tools.gfx_tools.test_backport_tileset_release \
  tools.gfx_tools.test_build_ultica_hires \
  tools.gfx_tools.test_beauty_backport_assets \
  tools.gfx_tools.test_visual_ui_donor_contracts
python tools/additive_audit.py --self-test
python tools/additive_audit.py --target HEAD
```

## Release boundary

`BUILD_INFO.txt` records the production command. Hosted checks cover portable
Python/data contracts only. Tag `v0.G-additive-2026.08.25` identifies the
Windows Tiles+Sound release; its asset checksum is published beside the ZIP.
The full Catch build has a pre-existing EOC-test compile failure, so the P0
release gates are the exact-tree Windows build, focused changed-object compile,
`--check-mods dda`, and copied-save load smoke.
