# H6 Backup Generator Backport Report

## Scope

This is the isolated H6 backup-generator slice for the additive 0.G fork. It
adds a portable, placeable diesel grid generator without replacing any 0.G
generator furniture, mapgen, spawn data, item, recipe, or deconstruction yield.

## Upstream provenance

| Role | Upstream change | Use in this backport |
| --- | --- | --- |
| Foundation | PR #66551, commit `e5d56d7d53b5e9c534903d18ad2add29c088bc93` | Construction, construction group, portable item, grid-appliance part, and furniture examine conversion |
| Recipe follow-up | PR #66551, commit `6acf2c1fd09b56369590452eb5d245bf3eb932d5` | Selected uncraft concept only; its replacement of the 0.G furniture deconstruction table was deliberately rejected |
| Recipe completion | PR #66551, commit `54a3bc00160568af5a47b22c7933b492aa43a598` | Craft and uncraft requirements using the engine, frame, fuel tank, and vehicle-wrench tooling |
| Output upgrade | PR #69124, merge commit `d9c856e4284da39c20e4d87996c9a6d15fcc7e7f` | 7.5 kW generator component and 7.3 kW net appliance output |

The donor changes were selectively transplanted into the current 0.G data
layout. No donor commit was cherry-picked wholesale.

## Shipped behavior

- `active_backup_generator` is a 200 kg, 200 L portable appliance item with a
  rigid, watertight 10 L integral fuel pocket.
- `ap_active_backup_generator` is a diesel grid appliance using the donor's
  combined engine/reactor/fluid-tank model and producing 7,300 W net power.
- The existing `f_active_backup_generator` examine action converts the map
  fixture in place into a removable grid appliance. The appliance Remove
  action recovers the portable item. Its original flags, bash drops, and
  five-entry deconstruction table are retained.
- `app_active_backup_generator` and `place_active_backup_generator` expose
  placement in the appliance construction menu.
- The Mechanics 3 autolearned recipe takes 90 minutes and consumes one 7.5 kW
  generator, inline-four diesel engine, vehicle frame, and large jerrycan. It
  uses the existing `vehicle_wrench_2` requirement bundle.
- The 45-minute uncraft recipe requires wrenching 2 and returns those same four
  major components.

## 0.G compatibility adaptations

- The later donor expresses vehicle-part `power` and `epower` with unit
  strings. The 0.G loader stores these two fields as integers, so this port uses
  `power: 7` and `epower: 7300`, matching the target schema and donor values.
- The 0.G vehicle-part validator also requires default intact and broken ASCII
  symbols even when variants are present, so the appliance defines `0` and `#`.
- The donor's `EASY_DECONSTRUCT` flag and replacement furniture deconstruction
  output were not imported. Converting by examine is an additional path;
  normal 0.G deconstruction still yields scrap, sheet metal, JP-8 in a large
  jerrycan, an inline-four diesel engine, and bearings.
- Generator spawn tables, airdrops, obsolete definitions, and later
  one-cylinder-engine changes are outside this slice.
- The additive audit allowlist names only the modified existing furniture and
  pins its exact post-backport fingerprint. Every other shipped definition has
  a new identity.

## Focused regression check

`python tools/test_h6_backup_generator.py` verifies:

1. portable-item capacity, appliance output/fuel flags, and mandatory 0.G
   intact/broken symbols;
2. construction/group wiring and furniture examine conversion;
3. preservation of the original furniture deconstruction table;
4. symmetric craft/uncraft components and wrench requirements.

The normal repository JSON validator and fail-closed additive audit remain the
authoritative broad data gates. A manual gameplay check should still connect
the placed appliance to a battery/grid, add diesel, enable it, and observe net
charging under load.
