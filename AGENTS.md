# Project Contract

The checked-out `main` branch is authoritative. The vanilla 0.G foundation
commit is provenance only; never reset, rebase, or replace current work with it.

## Immutable constraints

- Preserve all existing 0.G items, monsters, recipes, spawns, vehicle parts,
  chargen, world options, CBMs, mutations, weapons, and combat behavior.
- Preserve save compatibility and all merged additive backports.
- Prefer the smallest complete donor dependency closure.
- Do not wholesale-merge later CDDA branches.
- Do not import unrelated nerfs, removals, migrations, formatting, or redesigns.
- Do not add item faults, limb-loss infrastructure, mutation-tree migrations,
  broad active-item rewrites, or unrelated world/content packages.
- Use later branches only for direct correctness fixes to selected behavior.
- Keep donor PR/SHA, exclusions, validation, and known limits documented.

## Working rules

1. Inspect status, branch, HEAD, remotes, and recent history before editing.
2. Work from current `origin/main` on an isolated branch or worktree.
3. Preserve unrelated changes and avoid broad cleanup.
4. Add focused regression coverage for changed behavior.
5. Run cheap targeted checks while developing and the relevant final gate once.
6. Update `PATCHNOTES_ADDITIVE_0G.md`, `BACKPORTS.md`, or the relevant report.
7. Never commit saves, local config, caches, build trees, or credentials.

## Required local gates

```sh
python tools/additive_audit.py --self-test
python tools/additive_audit.py --target HEAD
python -m unittest tools.test_h5_interface_qol tools.test_h6_antigrind \
  tools.test_h6_backup_generator
```

Run affected C++ Catch tests and `cataclysm-tiles.exe --check-mods dda` when
source or game data changes. A playable release additionally needs an exact-tree
Windows Tiles+Sound build and copied-save load smoke.

Known baseline limitation: the full C++ build is too heavy for every small edit;
the lightweight hosted workflow is not release proof.
