# H5 interface and information backport report

## Scope

This slice adds selected post-0.G interface conveniences to the additive 0.G
fork. It does not import later crafting probabilities, container balance,
items, recipes, spawn tables, or wholesale 0.H data.

## Shipped behavior and provenance

| Behavior | Upstream provenance | Target treatment |
| --- | --- | --- |
| Exact minor-crafting-failure estimate | `390a452daae568608a9424adfe31a60940e75b88`, tests adapted from `b4c7879041d962f9bbc9fbbb480d1179da7b03e4` | Selective calculation and UI transplant |
| Open several containers in AIM | `8690ca05317709978ed6c6d5a424c6eacc34bbc0`, PR #65560 `3981ca7f8123babf8d0dc5e03680f5a90f9ddcee`, navigation `9eb4e707982adaaeb1945f03fe30136eadce4377`, capacity fix `5370fb4f6a24a2145b58f88c245dc8a5f24b408e`, load fix `a334d3d7ef6c1ea85fe25d3e67ee85c3fdc30078` | Full required container chain plus bounded correctness fixes |
| Direct Insert command | PR #68176 `254ed0e3c46a891bd33b845369a6ae443e505218` | Clean backport |
| Visible insertion denial reasons | PR #68191 `bde90cf985cfc8f2e640a31f6b5eda190967ee4a` | UI/reason reporting only |
| Estimated washing duration | PR #68542 `46ed75d4b4a2a828a3c0bc454336e2e301be08e1` | Backport plus 0.G stat-cell adaptation |
| Filter by covered body part | PR #68623 `18db0c6cfd92533630ada5ed158a904ec5247d7f` | Clean backport plus focused test |
| Inventory-filter history | PR #68645 `e4c0fba2d026747e13fe39fc45755481702b9695` | Backport preserving the 0.G query API |
| Scan several books into an e-reader | PR #68880 `cf5829a79bf0bd58b8296dd68620e0238e1ec439`, speed fix `c3fc2551f6032f8de2bf0e660665df33abac37fc`, 0.I duplicate-index fix `cfe6b00c5e692a744db096a55dbdecf4090a2307` | Full bounded activity path with legacy-load support |
| Display source mod/origin | PR #68585 `b60c6b3e565a86df9f691283c113eae25c10fb9e` | Scenario, profession, city, and rural-map UI |
| Snippets in item descriptions | PR #69149 `9dbc11fbfdbb93f479a1d4a437610567fee54df7` | Engine support and test fixture only; no bulk H items |
| Compatible ASCII art | Official 0.G `d6ec466140839dd70c1a43671eb4a08b007695c2` compared with `upstream-cdda/0.H-branch` | Only compatible net-new art and bindings recorded in `doc/backports/H5-ASCII-MANIFEST.tsv` |

## Player-facing details

- The crafting recipe panel shows the exact chance that the existing 0.G dice
  roll will produce a minor failure. The roll itself and every outcome
  threshold are unchanged.
- AIM can keep two container views open, move items between them, highlight the
  other pane's container, and leave a container with **X**. The pane-local
  container foundation also fixes nested-container insertion and stale
  container references.
- **Ctrl+B** opens Insert directly without replacing 0.G's existing **v** morale
  shortcut. Items that cannot be inserted remain visible but
  disabled, with the concrete capacity, pocket, watertight, spill, or nesting
  reason shown by the selector.
- Washing selection shows required water, cleanser, and an estimated duration.
- Item searches accept `v:<body part>`, for example `v:hands` or `v:eyes`.
- Pressing Up while editing an AIM or inventory filter recalls shared item
  filter history.
- E-readers accept a multi-selection of physical books. Duplicate copies are
  scanned only once, high-speed characters do not skip the last selected book,
  and old saves containing the former single `book` activity field still load.
- Character creation and overmap information can identify the source mod of a
  scenario, profession, or map terrain, including rural terrain outside a city.
- Item and item-variant descriptions may expand snippet tags once when the item
  is created, then retain the selected text through copies and saves.

## Compatibility corrections from independent review

- E-reader book boundaries now use the speed-adjusted activity move budget.
  Fast characters carry surplus progress into the next book, slow characters
  do not finish early, and legacy single-book activities retain their saved
  `moves_left` instead of completing on the first resumed turn. Battery use is
  tied to persisted scanned-page boundaries rather than the wall clock, so the
  charge estimate matches fast, slow, offset, and save/resume scans.
- The persisted 0.G numeric value for AIM worn items remains 13. The new parent
  pseudo-area is appended after it, missing pane-local container fields receive
  a safe sentinel, and invalid or stale container views reopen their base area
  (or All) instead of a blank container pane.
- AIM transfer limits use the active container's direct remaining capacity,
  not the map tile underneath it. The Insert selector and activity now share
  one direct-containment predicate, including partial charges and non-rigid
  parent-container limits.
- Insert is bound to **Ctrl+B** because plain **b** is southwest movement and
  0.G already uses **v** for morale. This keeps all three actions directly
  accessible and avoids first-registered-action shadowing.

## Explicit preservation boundary

- `9ca0afe20000b5bf39f7996e21ab8626e7c3f3f4` was not imported because it
  changes catastrophic crafting-failure balance.
- `e1b490845549d275c375edfde6b97a8dbb2eb878` was not imported because it mixes
  presentation with charged-quality behavior.
- The later normal-distribution crafting formula was not imported. The target
  estimate analytically enumerates the unchanged 0.G discrete dice formula.
- No bulk 0.H snippets, item definitions, descriptions, or unrelated ASCII art
  were copied.

## Validation boundary

- Every changed C++ translation unit and each added/changed focused test unit
  was compiled under WSL GCC with PCH disabled. The repository's old
  FlatBuffers PCH is incompatible with the installed GCC and was not modified.
- `build-scripts/validate_json.py` validates the complete committed JSON tree.
- `tools/additive_audit.py --self-test` and
  `tools/additive_audit.py --target HEAD` are the fail-closed preservation gate.
- Focused tests cover the exact 0.G crafting probability, snippet expansion and
  persistence, `v:` body-part filtering, speed-adjusted e-reader boundaries,
  page-based battery use and resume, legacy in-progress e-reader loading, AIM
  container fallback/capacity, Insert selector/activity parity, and 0.G AIM
  save-state defaults. Every
  affected source and focused test translation unit compiled successfully.
  Final linked tests and the exact stacked Windows Tiles+Sound build are owned
  by the parent integration run.
- Direct key/UI checks for Insert, AIM nested-container navigation, washing
  estimates, filter history, and multi-book selection remain manual runtime
  checks; no headless curses UI claim is made.
