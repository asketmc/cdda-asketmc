# Progression Backport Report
This batch reopens selected classic 0.G exploration and power routes without removing later systems or importing
unrelated donor changes. Donor heads mark regression boundaries; no donor branch was merged wholesale.

## Provenance and adaptations

| Concern | Upstream boundary | Fork adaptation |
| --- | --- | --- |
| Solar irradiance | [DDA #59179](https://github.com/CleverRaven/Cataclysm-DDA/pull/59179), head `02fd00db00b7f5cdc77e8e1f217af59b81285adc` | Keep irradiance; rate the base panel at 90 W. |
| Static generators replacing ASRGs | [DDA #62459](https://github.com/CleverRaven/Cataclysm-DDA/pull/62459), head `50860c3d059930ff302982228c3e15da67a7bd54` | Restore one compact ASRG at the irradiator only. |
| Rarer unique map specials | [DDA #46701](https://github.com/CleverRaven/Cataclysm-DDA/pull/46701), head `63b16f84884817c0d64a62d5e53591af80e1e747` | Retain map-special and uniqueness rules; raise selected occurrence weights. |
| Aboveground turret removal | [DDA #55790](https://github.com/CleverRaven/Cataclysm-DDA/pull/55790), head `7693988475c10a20b6de5df64656640d61f0512b` | Restore damaged, partly loaded turrets at military roadblocks and outposts. |
| Military extra rarity | [DDA #55908](https://github.com/CleverRaven/Cataclysm-DDA/pull/55908), head `78774681cdb396eb7a0cd8f826c083a5175b2ba8` | Raise default field and road weights only. |

## Implemented behavior

The standard solar panel produces 90 W while derived panels keep their proportional modifiers and irradiance calculations.
The irradiator contains a compact ASRG; outposts and shipwrecks retain conventional generators.

Classic exploration uses these new-generation occurrence contracts:

| Special | Occurrences | Preserved constraints |
| --- | ---: | --- |
| Ordinary LMOE shelter | 1-3 | `CLASSIC`, `MAN_MADE`; suitable land; city distance 20+ |
| Classic lab | 65/100 | `LAB`, `UNIQUE` |
| Central lab | 60/100 | `LAB`, `UNIQUE`; fixed multi-tile layout |
| Ice lab | 25/100 | `LAB`, `UNIQUE` |

Each ordinary LMOE parent layout guarantees one hidden `lmoe_guns` cache. Shared storage stays unchanged, so occupied and
Whately LMOEs do not inherit it. The autodoc finale guarantees `bionics_common`; other finales retain guaranteed rewards.

Default-region military-extra weights are 12 in fields and 125 on roads. Roadblocks select M249/M240/M2 turrets at exact
70/25/5 weights, with 30-70% hit points and 80-240/50-150/20-60 ammunition. Outposts have two 40% damaged-M249 positions;
police roadblocks and loot are unchanged.

`spawn_data.hp_percent` accepts 1-100 or an ascending range. `ammo_qty` applies to the loaded monster type's ammunition
pool instead of replacing IDs, preserving Generic Guns compatibility. Explicit `ammo` is mutually exclusive. All
fields persist for saved pending spawns, while legacy eight-field arrays load with defaults.

## Exclusions

- No existing overmap migration, microlab redesign, or unrelated frequency change.
- No ASRG restoration to prisons, rural outposts, or shipwrecks.
- No full-health or full-ammunition aboveground turrets.
- No turret attack, armor, drop, maximum-hit-point, or monster-type changes.
- No change to modded-region military weights or non-military map extras.

## Regression contracts

`tools.test_progression_backports` locks energy, scoping, rewards, military encounter shape, and Generic Guns ammunition.
Focused Catch2 contracts execute 70/25/5 boundaries, parsing, monster state, legacy loading, and pending-spawn round trips.
The Windows workflow runs both Catch2 filters and fails on zero discovery.
