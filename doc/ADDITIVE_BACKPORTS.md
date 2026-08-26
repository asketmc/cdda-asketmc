# 0.G additive backport manifest

This branch starts at stable 0.G commit `d6ec466140839dd70c1a43671eb4a08b007695c2`.
Its scope is deliberately additive: the listed mechanics and new content may be
added, but 0.G balance values, spawn rates, recipes, items, monsters, and existing
vehicle parts must not be removed or rebalanced as collateral changes.

## KISS delivery report

This is the delivery order for the playable fork.  It is a curated backport, not
an attempt to turn 0.G into a later release wholesale.

### 1. Car and V-Jill

The primary slice is the mobile-base/vehicle path:

- Lockable and pickable vehicle doors, including NPC and door-motor handling
  for locks.
- Directed floodlights, craftable mountable heating and cooling, a
  one-cylinder diesel engine, added refrigeration parts, and a portable hand
  truck.
- Vehicle prototype export; furniture tie-down, loading, unloading, and
  vertical dragging; and direct-route autodrive selection.
- Vehicle enchantments/effects, multi-pocket turret/tool support, typed part
  locations, and save-compatibility regressions for the imported state.
- Practical vehicle UI: installation-failure explanations, visual part-shape
  selection, charger draw, battery status, cable connections, and fast vehicle
  zone toggles.

These features extend the construction and operation of a 0.G road home.  They
do not replace existing 0.G parts or silently retrofit generated vehicle
prototypes.

### 2. Camp and NPC followers

The follower/base slice adds:

- Friendly-NPC crafting orders, crafter switching, the normal camp crafting
  menu, bulk job priorities, a dedicated follower-rules screen, and visible
  reservation of items already in use.
- NPC e-book reading, magazine reloading, crafted-liquid handling, location and
  personality information, and improved camp radio-tower behavior.
- Nutrient-aware camp food stores and worker meals, medicine/mutagen storage,
  liquid recipes and zoned containers, brick camp expansions, and static-NPC
  faction camps.
- Protagonist/follower export and import plus allied-NPC CBM surgery.

The imported behavior is adapted to 0.G data and interfaces; later balance
tables are not imported with it.

### 3. Optional UI and extra content

- Useful Helicopters is a separate, non-default vehicle-content option.
- CBM recovery from selected zombie corpses restores an additive science and
  combat salvage loop in core play.
- Riot armor, its separate guards, and both riot-helmet visor states can be
  repaired with plastic-capable workshop tools using thermoplastic resin
  chunks.
- The official 2026-08-23 UltiCa and SurveyorsMap release is installed without
  dropping 0.G-only sprite IDs. Visibility/depth fixes, asynchronous run and
  smash animation, weather/field variants, armor appearance overrides, eight
  color themes, JetBrains Mono, richer sound-event selection, and corrected NPC
  footsteps are described in `doc/VISUAL_UI_BACKPORT_REPORT.md`.
- The data-driven Structured Sidebar was already present in the target and is
  retained rather than duplicated.
- H5 interface QoL adds exact 0.G crafting-failure estimates, multi-container
  AIM navigation, a direct Insert command with denial reasons, washing-time
  estimates, body-part filters and filter history, multi-book e-reader scans,
  source-origin labels, snippet-capable descriptions, and compatible net-new
  ASCII art. See `H5_INTERFACE_QOL_BACKPORT_REPORT.md` and
  `doc/backports/H5-ASCII-MANIFEST.tsv`.

### 4. Stable EOC toolkit checkpoint

The H3 release slice adds opt-in scripting APIs for event subscriptions,
activity callbacks, scoped variables, stored conditions, simple branching,
mutation callbacks, inventory/map selectors, conditioned monster attacks, and
preventable NPC-death events. It imports no demonstration missions, monsters,
locations, or balance tables. See `H3_EOC_BACKPORT_REPORT.md` and the gameplay
summary in `PATCHNOTES_ADDITIVE_0G.md`.

The `foreach` donor is complete. Later tile/variable-object/trait-variant
extensions remain outside this stable checkpoint.

### Intentional trims and drops

To keep this backport buildable and useful today:

- There is no blanket transplant of every vehicle-part ID added after 0.G.  An
  ID diff is only a candidate list; this branch imports selected self-contained
  parts and their acquisition paths.
- The later concrete-mixer vehicle-part set, hand-control/pedal-extender set,
  and `VEH_TOOLS` kitchen/workshop set are not imported.  Each depends on later
  control, consumer, or vehicle-tool subsystems and would require changing
  existing 0.G behavior rather than adding a bounded feature.
- Heating and cooling remain craftable, installable parts.  Existing vehicle
  prototypes are not automatically mutated to contain HVAC.
- Unrelated later appliances, stowed-item variants, total-conversion content,
  and dependency-heavy content chains are outside this delivery.  Their mere
  presence in a later release is not enough reason to import them.
- Sky Islands was dropped after the third Windows validation attempt.  Its
  donor data has dozens of descriptions rejected by the strict 0.G text-style
  loader; repairing that broad optional mode exceeded today's KISS scope.  The
  donor import remains recoverable from local Git history.
- The synthetic single-cell vehicle-lock pathfinding regression was also
  dropped after its third fixture failure.  Locking, unlocking, picking,
  interaction, and save-state coverage remain; the separately reviewed
  part-index predicate correction is retained, but this exact synthetic route
  case is not claimed as runtime-validated.
- No content removal, spawn/balance-table replacement, or broad rebalance is an
  acceptable shortcut for any backport in this manifest.

### Validation boundary

The additive audit below is the data-preservation gate.  The attempted full-tree
Linux GCC 12 build was stopped after untouched 0.G code at
`src/debug.cpp:1507` triggered an `ignored-attributes` warning promoted to an
error.  That host-toolchain incompatibility is not treated as a backport
failure, and the full Linux build is intentionally dropped rather than patched
around by changing unrelated baseline code.  Windows GCC 11 Tiles+Sound is the
definitive build and packaging path; its actual result must be reported with
the produced package rather than inferred from the Linux attempt.

## NPC and faction camps

### 0.H sources

- Camp radio tower: `105643d9c221878cbc25026f69a1a093b968ac77`
- Show an NPC's location: `c5464ce2cfe454f19dad12fc6858d1b9afbf6b78`
- NPCs read e-books: `f424b9cabf635d26bbf88462c27e6f40dc905495`
- Export/import protagonist and followers: `d9554a710079071f9bc9263c0e400747cc635671`
- Friendly NPC crafting: `9f7e85168485ec57388fb20957a86851819fc86b`
- Switch crafter in crafting UI: `9566d7478413f0f051416b36ccb47c5f4c5c8313`
- NPC doctors operate on allied NPCs: `514271b7adda6a48a1670b8add1630b62a42556b`
- NPCs reload magazines: `808783065144ee7154d2f7f8d0800d6292ff764d`
- Camp liquid storage and recipes: `8ee75e58dbe2e1487d60b11f947f42ef06c44dfc`,
  `f0562880fde59469ce3d790848c6fbb4fe3efcc3`
- NPC personality appraisal: `51b0773871725330c95de4b0c756a732790b299e`

### 0.I sources

- Camp vitamins/food and workers eating: `1b817a03a1d6b83a15786182d864720dc4f3b3c7`,
  `98de57e8e501871660bcc2ca723fa8444e3a5762`
- Drugs/mutagens accepted by camp stores: `87c8ed1cac8624a00b37733bce356ae8b2636f0d`
- Camp crafting GUI: `c7c024a3eee5c8f87d054e443d29be9eb18ffefd`
- Set all companion job priorities: `2ef326b4f6b6b6903c8e60379edfa15f06406d7a`
- Dedicated follower rules UI: upstream 0.I follower-rules series ending in
  `3f6bf65242b836a489cbf42156196106879b5f28`
- NPC liquid handling: `735056826951395fc40dc1fbe32b1f7d93f0a6c4`
- Brick camp expansions: `767b21aeee1bcb9caf0535f2027acaa0608bf3c1`
- Reserved camp items marked in use and static-faction stores are ported as
  isolated behavior/data changes, not by importing the 0.I balance tables.

## Vehicles

### 0.H sources

- Directed floodlight: `b9b4f82faa2de2f35a6f2a848782e5565aeed514`
- Lockable/pickable doors: `7fa704b74f8e79796486a4d728dc67a8beae1673`
- Vehicle heaters/AC: additive subset of `d17fca57b0748cf104b320642c681ca923f0c722`
- One-cylinder diesel: additive subset of `735b626a7b4385e3d4b13bb8a2ece179c1e15326`
- Export vehicle prototype: `1acaa4969df653e8edb179c43449b5930f6d798a`
- Explain failed part installation: `15703184b51631073a3fb5706eedc957fbdc5169`

### 0.I and 0.J sources

- Furniture tie-down/haul and transfer: `0c4a5cb6ada19d9beab47912fd47be88922f1e84`,
  `8da3588df354017e81d6e5e088e4fb979cebe812`
- Vehicle enchantments/effects: `5e8e5fa144a6d1570751c2d00da945228213739a`
- Visual part-shape UI: `b4cf46dbc7f8c7eaf94feb8065f09817f8a4014d`
- Charger draw display: `c7b8e84f7c2b1f8c7035b8713ce74d77222cf808`
- Better loading and vertical dragging: `95cdd3dc224b649d7697cc6a2f50744e4262dcca`,
  `802eb50ef413373444e5f58538dac75135ed8291`
- Direct-route autodrive: `7d96862d832b2e9f94f4ac5b1ab9a0c1a9721bce`
- JSON vehicle-part locations: `2c06deb2167ae73c657543eae0173e4057652ee4`
- Portable hand truck: additive data subset of
  `52145660c858f55fc58d60f583aa9ccccda0bcb1`
- Vehicle-zone toggle, cable display, battery widget:
  `4b7a2f2c1c15a72f8b4db57c6a99f4802fcb0ec5`,
  `622854282c8eb62d8c39fca8da22ffb8b74f5054`,
  `a595a116f1503f6c2e8c55cfb5af2b9a3680859f`

The 0.I vehicle-part candidate set is generated by an ID-level JSON diff.
Existing 0.G entities remain authoritative; only IDs absent from 0.G are
candidates for import, and only self-contained candidates selected for this
manifest are actually imported.

## Follower QoL donor disposition

| Area | Donor | Result |
| --- | --- | --- |
| NPC temperature, wetness, sleep, camp water | CleverRaven #86016 (`69e67579e0adf6bc345904242c40e88e1237d74d`) | Adapted to the 0.G NPC update and camp APIs |
| Camp mopping job | CleverRaven #86257 (`4813d0e10e9baa048aea3f9e32afb77145fdda0c`) | Adapted to the legacy `mop`/`mop_folded` requirement and fetch path; no later MOP-quality migration |
| Personal sorting-zone isolation | CleverRaven #86254 (`eba56896b357c633f17973c5442d3b69f7832895`) | Adapted to the legacy move-loot activity |
| Crafting UI, bulk priorities, worker food/vitamins, larder medicine | #67458, #77715, #77573, #71546, #71670, #76025 | Already present |
| Warmth response | CleverRaven #86004 (`41418fe32bf85c67348963ce75ef7b2a72862b37`) | Adapted directly to body temperature and the legacy needs cascade |
| Local food, water, clothing, shelter and foraging | CleverRaven #86035 (`3c6ec8d3aeb14d7f366db6f3823a69c60b53fb2e`), #86052 (`4018cea0a1d4f32c0dad492f7df38b7cbbb807e4`) | Adapted without the modern behavior tree; adds ownership, protected-zone and locked-cargo guards |
| Legacy priorities and camp lifecycle | #86172, #86173 | Adapted to the 0.G cascade and `assigned_camp`; modern behavior tree and mission framework excluded |
| Activity-actor sorting rewrites | #83980, #84311 | Not applicable to the legacy direct sorting implementation |
| Safe self/ally first aid | TLG #1603 (`5fd614b81aeb7de418b4ed239e5b7e8f93828cba`) | Adapted with a save-compatible follower rule and activity restoration |
| Vitamin and food selection | TLG #2982 (`87448bac93398575e854128d00840b73d3f7c7ac`) | Adapted for data-defined deficiencies, safe non-addictive treatment, rot-aware ranking, and starvation fallback |
| Weapon comparison correctness | TLG #2746 (`336d552d6df48f73ddfd1f63f7572cd3ad15238b`) | Empty-hand selection fix and defensive offered-weapon ammo accounting only; balance changes excluded |
| Camp recipe sources and liquid checks | #78612, #81148 | Existing behavior retained; book/e-book access and non-mutating liquid preflight adapted without the later camp framework |
| Legacy sorter | #83980, #84311 | Valid-work precheck and false no-work result fixed; activity actors, physical walking and bagful sorting excluded |

Local scavenging uses the existing **Allow pickup** follower rule as its opt-in.
Unowned ground items are eligible, while personal and no-NPC-pickup zones remain
hard exclusions. Vehicle cargo additionally requires matching ownership; a
cargo lock blocks only its own mount while the vehicle is locked.

Active NPC temperature effects are refreshed every turn; the heavier needs
update remains throttled. Save-load catch-up advances temperature, wetness, and
frostbite by up to two days of elapsed turns under the current conditions. The
bound prevents overflow in legacy integer counters and is already enough for
temperature convergence and full drying. This deliberately does not invent a
historical weather trace that 0.G never persisted.

## Additive data audit

`tools/additive_audit.py` is the fail-closed data gate for this branch. It always
uses exact stable 0.G commit `d6ec466140839dd70c1a43671eb4a08b007695c2`
as its baseline; changing the manifest to another baseline is rejected.

Run its focused regression tests and then audit the committed target tree:

```sh
python tools/additive_audit.py --self-test
python tools/additive_audit.py --target HEAD
```

Use `--target WORKTREE` before committing to include current tracked and
untracked files. The audit returns nonzero when a baseline core or built-in-mod
ID, anonymous object, path, or non-JSON resource disappears; an existing
definition or resource changes without an exact fingerprinted allow-list entry;
an allow-list entry becomes stale; a required donor entity or file is absent;
an accepted optional-mod tree drifts; or an optional import is enabled directly
or transitively by `data/mods/default.json`.

This private fork deliberately has no GitHub Actions workflow or hosted CI
consumer. Release candidates run the self-test and committed-tree audit with
local tools, and record the exact result in `BUILD_INFO.txt` and the pull
request.

Core means `data/json`, `data/core`, and `data/raw`. The audit indexes direct
top-level JSON objects by `type` plus `id`, `abstract`, or legacy `ident`;
recipe results and snippet categories have type-specific identities, and
list-valued IDs are expanded. Adding a second definition fragment to an
existing ID is reported as an existing-ID change and also needs an allow-list
fingerprint.

Identity namespaces follow the relevant 0.G loaders rather than blindly using
the literal JSON `type`. In particular, all item types registered through
`Item_factory` share the `itype_id` namespace. A type change therefore remains
an existing-item modification, and simultaneous definitions such as `GENERIC`
and `AMMO` with the same ID are rejected as a cross-type collision.

Every `MOD_INFO`-rooted package below `data/mods` is compared independently from
core and from every other built-in mod. A baseline package cannot disappear.
Within each package, baseline identities, anonymous objects, paths, and
non-JSON resources are fail-closed just like core data. Entirely new packages
and new unique IDs remain additive; an ID newly defined more than once is
rejected. The `dev:default` metadata file is audited as its own package, so a
change to the default mod set cannot hide inside the optional-mod namespace.
`MOD_INFO` identity mirrors `mod_manager.cpp`: legacy `ident` takes precedence
over `id`. Metadata containing both fields with different values is rejected,
preventing the audited dependency graph from differing from the game's graph.

The machine-readable manifest is `tools/additive_audit_manifest.json`. It
records these Cataclysm-2040 imports and their classification:

- Lockable vehicle doors (`0ccfe3659c71d6a982290b2cd201737c6942b9bb`):
  core entities and required core paths.
- CBMs from zombie corpses (`b6da28650d025ca47a99ab7db9e066b378c8e49e`):
  core entities and required core paths.  The donor's duplicate `bionics_sci`
  fragment is deliberately omitted; this fork reuses the identical 0.G pool.
- Useful Helicopters (`dec27b76f7ab44a37c84971c63bf9062b1fd2503`):
  optional mod, content fingerprinted and not default-enabled.

The core allow-lists and the three `allowed_builtin_mod_*` arrays fingerprint
the complete target definition or resource for every approved change. Each
built-in-mod entry also names its `mod_id`, so permission for an ID in one mod
cannot authorize the same ID in another. Later edits to an approved definition
do not inherit blanket permission. When a feature intentionally needs another
existing-definition change, review the semantic diff first and then update only
that fingerprint and reason. The current built-in-mod entries cover the static
camp annotations in Aftershock and Magiclysm.

This audit is intentionally narrow. It does not prove C++ behavior or replace
the game's JSON loader/checker. Top-level objects without a recognized identity
are protected by path-scoped canonical fingerprints rather than semantic IDs.
The donor optional-mod payload fingerprints normalize line endings and do not
prove that the recorded donor commit is available locally or that every donor
file was imported without adaptation.
