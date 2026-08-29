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
6. Record the change in exactly the documents named under "Documentation routing".
7. Never commit saves, local config, caches, build trees, or credentials.

## Documentation routing

Each record answers one question. Stating the same fact in two of them is how
these files rot.

| Record | Question it answers | Written when |
| --- | --- | --- |
| `changelog/changes/pr-<n>.json` | What landed in this pull request? | Every pull request |
| `CHANGELOG.md`, `doc/releases/` | What changed between two releases? | Generated; never by hand |
| `PATCHNOTES_ADDITIVE_0G.md` | How does this fork differ from vanilla 0.G? | A real difference appears |
| `BACKPORTS.md`, `*_BACKPORT_REPORT.md` | Where did the code come from, what was excluded? | Any transplant |
| `CURRENT_STATE.md` | What builds and what is validated right now? | That status changes |

### Patch-note rules

`PATCHNOTES_ADDITIVE_0G.md` is a catalogue, not a second changelog. It ships
inside the Windows package, so a stranger reads it before trusting the fork.

1. Write the player-observable effect, never the implementation. A sentence that
   names a function, file, or data structure belongs in a backport report.
2. Tag every difference `New`, `Improved`, or `Fixed` **against vanilla 0.G**. A
   defect this fork introduced and fixed before shipping was never broken for any
   reader, so it earns no entry: correct that pull request's fragment instead of
   adding a second one.
3. One entry per difference. When a later change extends an entry, amend it in
   place rather than appending a near-duplicate.
4. No dates, release tags, or fork pull-request numbers; chronology lives in the
   generated `CHANGELOG.md`. Cite the upstream donor instead, as `DDA #73610`,
   because provenance is the part a reader cannot look up.
5. No commit ids, TODO markers, validation evidence, or review history.
6. When an area exceeds its entry budget the entries are too granular. Merge
   them; do not raise the budget.

## Required local gates

```sh
python tools/additive_audit.py --self-test
python tools/additive_audit.py --target HEAD
python tools/patchnotes_lint.py
python -m unittest tools.test_patchnotes_lint tools.test_h5_interface_qol \
  tools.test_h6_antigrind tools.test_h6_backup_generator
```

Run affected C++ Catch tests and `cataclysm-tiles.exe --check-mods dda` when
source or game data changes. A playable release additionally needs an exact-tree
Windows Tiles+Sound build and copied-save load smoke.

Known baseline limitation: the full C++ build is too heavy for every small edit;
the lightweight hosted workflow is not release proof.
