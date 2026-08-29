# Progression Backport Report

This report records the deliberately selected restorations that reopen classic
0.G exploration and character-progression routes.  The fork keeps later systems
when they add useful structure, but does not let those systems erase every
independent route to the same fantasy.

## Batch 1: energy and classic exploration

### Donor and regression provenance

| Concern | Upstream change used as regression boundary | Fork adaptation |
| --- | --- | --- |
| Solar irradiance | [DDA #59179](https://github.com/CleverRaven/Cataclysm-DDA/pull/59179), head `02fd00dbad1c9d4b27c3062c811df7923e66a7e4` | Keep the irradiance calculation; change only the base panel rating. |
| Static generators replacing ASRGs | [DDA #62459](https://github.com/CleverRaven/Cataclysm-DDA/pull/62459), head `50860c3d760af519c5da509bfd20445b13de3e47` | Restore one compact ASRG at the irradiator while keeping conventional generators at mundane sites. |
| Rarer unique map specials | [DDA #46701](https://github.com/CleverRaven/Cataclysm-DDA/pull/46701), head `63b16f846cfed619bdc365dfec8b79e2b09b4f4a` | Retain the map-special framework and uniqueness flags, but raise selected occurrence weights. |

The donor heads are evidence for the behavior being adapted, not merge bases.
No donor branch was merged wholesale.

### Implemented behavior

The standard vehicle solar panel is rated at 90 W, 1.8 times the 0.G value.
Every derived panel continues to use its existing proportional modifier, and
the C++ irradiance calculation remains unchanged.  This raises practical clear-
day, winter, and cloudy production together rather than installing a parallel
weather model.

The irradiator facility again contains a compact ASRG in containment.  The fork
already had rare ASRGs in several high-technology sites, so the restoration is
intentionally narrower than reverting every replacement from #62459.  Outposts
and shipwrecks keep conventional backup generators.

Classic exploration uses these occurrence contracts:

| Special | Occurrences | Preserved constraints |
| --- | ---: | --- |
| Ordinary LMOE shelter | 1–3 | `CLASSIC`, `MAN_MADE`; normal map-special placement |
| Classic lab | 65/100 | `LAB`, `UNIQUE` |
| Central lab | 60/100 | `LAB`, `UNIQUE`; fixed multi-tile layout |
| Ice lab | 25/100 | `LAB`, `UNIQUE` |

The ordinary LMOE can use suitable land and begins twenty overmap tiles from a
city.  The quest-locked and occupied LMOE variants are unchanged.  Existing
generated overmaps remain untouched; new terrain generation receives the new
selection weights.  Each of the three ordinary underground layouts guarantees
one `lmoe_guns` survival-firearm cache in its existing hidden storage area.

The autodoc classic-lab finale now places one guaranteed `bionics_common` group.
The other four finale families already guarantee a substantial reward source:
nanofabricator template, portal technology, mutagen tank, or the turret-finale
reward room.  Their loot was not inflated further.

### Explicit exclusions

- No change to sun irradiance, weather, seasons, sunrise, or panel obstruction.
- No ASRG restoration to prisons, rural outposts, or shipwrecks.
- No removal of `UNIQUE`, `LAB`, `CLASSIC`, or map-special placement rules.
- No map migration or rewrite of already generated terrain.
- No microlab loot redesign and no unrelated map-special frequency changes.

### Regression contracts

`tools.test_progression_backports` checks the exact panel tier, the thematic
ASRG placement and conventional-generator exclusions, special occurrence and
flag contracts, one guaranteed cache in each ordinary LMOE layout, and a
deterministic reward source for each classic one-level lab finale.
`tests/vehicle_power_test.cpp` keeps the seasonal irradiance tests and updates
their expected output for the 90 W panel.

## Batch 1: dangerous military salvage sites

### Donor and regression provenance

| Concern | Upstream change used as regression boundary | Fork adaptation |
| --- | --- | --- |
| Aboveground turret removal | [DDA #55790](https://github.com/CleverRaven/Cataclysm-DDA/pull/55790), head `769398842484007f1de117bb1630ba7734252432` | Restore weapon turrets only at military roadblocks and outposts, with damage and sharply limited ammunition. |
| Military extra rarity | [DDA #55908](https://github.com/CleverRaven/Cataclysm-DDA/pull/55908), head `78774681a7fdd09e65a5583a61ce663669e0834b` | Raise only the default field and road weights; do not revert police loot or unrelated extra weights. |

### Implemented behavior

The default region's field `mx_military` weight changes from 4 to 12 and its
road weight changes from 50 to 125.  The surrounding tables remain unchanged,
so both encounters stay rare relative to ordinary field details, roadblocks,
casings, roadworks, and civilian scenes.

The military branch of a roadblock now chooses an M249 turret 70% of the time,
an M240 turret 25% of the time, and an M2 turret 5% of the time.  Every weapon
turret starts at 30–70% of maximum hit points.  Its ammunition is restricted to
80–240 rounds of 5.56 mm, 50–150 rounds of 7.62 NATO, or 20–60 rounds of .50
BMG respectively.  The police branch remains unchanged and continues to use
riot-control platforms.

Each of the two military outpost layouts keeps two deterministic searchlights.
Two other perimeter positions independently have a 40% chance to contain a
damaged M249 turret with 80–240 rounds.  This makes the site dangerous without
turning every outpost into a four-turret ammunition cache.

The reusable mapgen `spawn_data.hp_percent` field accepts an integer or range
within 1–100 and defaults to 100.  It lets mapgen describe already damaged
machines without creating duplicate monster types or permanently reducing the
turrets' maximum hit points.

### Explicit exclusions

- No return to full-health, full-ammunition aboveground turrets.
- No change to police roadblocks or police rifle loot.
- No change to military extras in cities, subways, labs, or modded regions.
- No new turret monster type and no change to turret attacks, armor, or drops.

### Regression contracts

`tools.test_progression_backports` locks the regional weights, outpost encounter
shape, ammunition ranges, damage range, and roadblock weapon tiers.  The Catch2
test `mapgen monster spawn_data sets ammunition and damage` constructs a turret
through update mapgen, spawns it, and verifies both 50% hit points and exactly
80 rounds of 5.56 mm ammunition.

## Batch 2: independent CBM scavenging routes

### Donor and regression provenance

| Concern | Upstream change used as regression boundary | Fork adaptation |
| --- | --- | --- |
| Ordinary zombie CBM removal | [DDA #49892](https://github.com/CleverRaven/Cataclysm-DDA/pull/49892), head `b6da28650d025ca47a99ab7db9e066b378c8e49e` | Preserve the fork's skill-scaled dissection route for scientists, technicians, soldiers, bio-operators, and Exodii zomborgs. |
| Mine and high-value vault removals | [DDA #55329](https://github.com/CleverRaven/Cataclysm-DDA/pull/55329), commit `190ebd75663a51bff9846493c32e8cbe3294e222`; [DDA #55999](https://github.com/CleverRaven/Cataclysm-DDA/pull/55999), commits `4c789b3ea7` and `37bedfb48a` | Restore low-weight utility salvage in mines, but leave generic vaults, random loot, and survivor lairs unchanged. |
| Location-wide CBM cleanup | [DDA #56552](https://github.com/CleverRaven/Cataclysm-DDA/pull/56552), commits `cf376f`, `8aab`, `8ec` | Restore selected caches at medical, scientific, electronic, military, and robotic sites at lower rates than the removed placements. |

The donor changes define what disappeared; they are not merge bases.  The fork
does not revert the Exodii or map-special systems and does not import unrelated
late-game loot tables.

### Implemented behavior

The existing corpse-dissection route remains the primary renewable scavenging
path.  Scientists, technicians, military zombies, bio-operators, elite
bio-operators, and Exodii zomborgs can yield CBMs only through dissection.  Each
recovered implant remains filthy, non-sterile, unpackaged, and affected by the
salvaged-bionic fault.  The number recovered scales with dissection skill and is
capped at five.  This preserves the dangerous field-surgery loop without
restoring clean CBMs as ordinary death drops.

Low-rate environmental routes now complement that loop:

| Route | Restored contract |
| --- | --- |
| Hospital medical supplies | Common CBM group at weight 5. |
| Mine equipment | Integrated tools, light, fire, magnet, resonator, hydraulics, and weight CBMs at weights 2–3. |
| Science and technology loot | Thirteen thematic utility or medical CBMs at weights 2–4. |
| Robofac basic trade | Common CBM group at weight 25 alongside the existing trade stock. |
| Bionic basement | One guaranteed common CBM group in the surgery room. |
| Bunker basement | One 35% military-CBM cache. |
| Military base clinic | One 25% military-CBM cache in the existing secure storage mapping. |
| Mortuary, police evidence, prison autodoc | One common-CBM cache at 15%, 5%, and 10% respectively. |
| Electronics store | Two independent 15% common-CBM display caches, with no repeated rolls. |

These are independent discovery opportunities, not guaranteed full progression
trees.  Exodii stock and zomborg salvage remain available and are not displaced.

### Explicit exclusions

- No clean direct CBM death drops and no bypass of dissection skill.
- No CBM restoration to banks, generic vaults, random-main loot, survivor
  lairs, storage units, or the fire tower.
- No broad hospital, military, or laboratory loot rollback.
- No removal or weakening of Exodii zomborg harvest tables.
- No change to CBM cleaning, sterilization, packing, fault repair, or install
  requirements in this batch.

### Regression contracts

`tools.test_progression_backports` checks the full dirty-salvage contract for
ordinary and Exodii corpses, exact restored item-group weights, exact mapgen
cache rates and coordinates, and the absence of repeat rolls in the electronics
store.  The additive audit separately binds every modified core entity or
anonymous mapgen object to an explicit target fingerprint.

## Batch 2: classic CBM utility

### Donor and regression provenance

| Concern | Upstream change used as regression boundary | Fork adaptation |
| --- | --- | --- |
| Integrated Toolset reduction | [DDA #52889](https://github.com/CleverRaven/Cataclysm-DDA/pull/52889), merge `661b2fdd8861a767b3960c75cb780a3a08840ebe` | Keep the fork's integrated multitool structure and restore the classic work qualities to both pseudo-tools. |
| Railgun replacement | [DDA #61176](https://github.com/CleverRaven/Cataclysm-DDA/pull/61176), commits `50dc6b5ece497cb39604675c7a45cc2e2b719b69` and `bbcd9a98a95e` | Reactivate the Railgun as a distinct CBM while retaining Throwing Assist. |

### Implemented behavior

The Integrated Multitool's stowed pseudo-tool and its extended hand-held form
both provide the classic hammering, fine hammering, metal and wood sawing,
wrenching, wheel fastening, screwdriving, cutting, prying, nail pulling, and
drilling qualities.  The extended form retains its existing welding, soldering,
and repair actions.  The existing included-bionic structure is unchanged, so
old characters with `bio_tools` continue to receive the extended mode.

The Railgun CBM, its implant item, and its autodoc installation data move out of
the obsolete catalog into their normal active files.  It is a rare entry in the
general and military CBM pools, remains available from elite bio-operators, and
has low-weight routes through ranged zomborg salvage and tier-three Exodii
stock.  The passive Throwing Assist CBM remains active under its existing ID;
neither CBM replaces the other.

An active Railgun doubles range and improves damage only for ferric thrown
items.  A powered throw adds the existing lightning projectile effect and
consumes 10 kJ.  The restored implementation now checks that the full trigger
cost is available before granting range, damage, or lightning, preventing an
active but empty implant from providing free throws.

### Explicit exclusions

- No removal or renaming of Throwing Assist.
- No new modular tool CBM tree, slot migration, or save conversion.
- No change to ordinary throwing balance, non-ferric items, mech-assisted
  throws, bionic power storage, or bionic installation difficulty.
- No restoration of unrelated obsolete CBMs or obsolete item groups.

### Regression contracts

`tools.test_progression_backports` verifies active Railgun definitions,
installation data, all selected distribution routes, coexistence with Throwing
Assist, both multitool quality sets, and the power-safety hooks.  The Catch2
test `railgun requires and consumes its trigger power` checks doubled range and
increased damage at 10 kJ, the lightning effect and exact 10 kJ consumption,
and ordinary behavior with only 9 kJ available.
