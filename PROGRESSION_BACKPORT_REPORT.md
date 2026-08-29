# Progression Backport Report
This batch reopens selected classic 0.G exploration and power routes without removing later systems or wholesale-merging donor branches. Donor heads mark regression boundaries.

## Provenance and adaptations

| Concern | Upstream boundary | Fork adaptation |
| --- | --- | --- |
| Solar irradiance | [DDA #59179](https://github.com/CleverRaven/Cataclysm-DDA/pull/59179), head `02fd00db00b7f5cdc77e8e1f217af59b81285adc` | Keep irradiance; rate the base panel at 90 W. |
| Static generators replacing ASRGs | [DDA #62459](https://github.com/CleverRaven/Cataclysm-DDA/pull/62459), head `50860c3d059930ff302982228c3e15da67a7bd54` | Restore one compact ASRG at the irradiator only. |
| Rarer unique map specials | [DDA #46701](https://github.com/CleverRaven/Cataclysm-DDA/pull/46701), head `63b16f84884817c0d64a62d5e53591af80e1e747` | Retain map-special and uniqueness rules; raise selected occurrence weights. |
| Aboveground turret removal | [DDA #55790](https://github.com/CleverRaven/Cataclysm-DDA/pull/55790), head `7693988475c10a20b6de5df64656640d61f0512b` | Restore damaged, partly loaded turrets at military roadblocks and outposts. |
| Military extra rarity | [DDA #55908](https://github.com/CleverRaven/Cataclysm-DDA/pull/55908), head `78774681cdb396eb7a0cd8f826c083a5175b2ba8` | Raise default field and road weights only. |

## Implemented behavior

The standard solar panel produces 90 W while derived panels keep proportional modifiers and irradiance calculations. The irradiator contains one compact ASRG beside one conventional generator; outposts and shipwrecks retain conventional generators.

Ordinary `CLASSIC`/`MAN_MADE` LMOEs occur 1-3 times on suitable land at city distance 20+. `LAB`/`UNIQUE` classic, central, and ice labs use 65/100, 60/100, and 25/100 occurrence contracts; fixed layouts stay unchanged.

Each ordinary LMOE parent guarantees one hidden `lmoe_guns` cache. Shared storage stays unchanged, excluding occupied and Whately LMOEs. The autodoc finale guarantees `bionics_common`; other finales retain guaranteed rewards.

Default-region military-extra weights are 12 in fields and 125 on roads. Roadblocks select M249/M240/M2 turrets at exact 70/25/5 weights, with 30-70% hit points and 80-240/50-150/20-60 ammunition. Outposts have two 40% damaged-M249 positions; police roadblocks and loot are unchanged.

`spawn_data.hp_percent` accepts 1-100 or an ascending range. `ammo_qty` adjusts the loaded monster's ammunition pool without replacing IDs, preserving Generic Guns compatibility. Explicit `ammo` is mutually exclusive. All fields persist for saved pending spawns; legacy eight-field arrays load with defaults.

## Exclusions

No existing-overmap migration, microlab redesign, unrelated frequency change, broad ASRG restoration, full-strength turret, turret type/stat/drop change, police branch change, modded-region military weight, or non-military extra change is included.

## Regression contracts

`tools.test_progression_backports` locks energy, scoping, rewards, military encounter shape, and Generic Guns ammunition. Focused Catch2 contracts execute probability boundaries, parsing, monster state, legacy and pending-spawn loading, and solar output. The Windows workflow executes every focused filter and fails on zero discovery.
