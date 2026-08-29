# Progression Backport Report

These batches reopen selected classic 0.G progression routes without removing later systems or wholesale-merging donor branches.

## Batch 1: energy and dangerous exploration

### Provenance and adaptations

| Concern | Upstream boundary | Fork adaptation |
| --- | --- | --- |
| Solar irradiance | [DDA #59179](https://github.com/CleverRaven/Cataclysm-DDA/pull/59179), head `02fd00db00b7f5cdc77e8e1f217af59b81285adc` | Keep irradiance; rate the base panel at 90 W. |
| Static generators replacing ASRGs | [DDA #62459](https://github.com/CleverRaven/Cataclysm-DDA/pull/62459), head `50860c3d059930ff302982228c3e15da67a7bd54` | Restore one compact ASRG at the irradiator only. |
| Rarer unique map specials | [DDA #46701](https://github.com/CleverRaven/Cataclysm-DDA/pull/46701), head `63b16f84884817c0d64a62d5e53591af80e1e747` | Retain map-special and uniqueness rules; raise selected occurrence weights. |
| Aboveground turret removal | [DDA #55790](https://github.com/CleverRaven/Cataclysm-DDA/pull/55790), head `7693988475c10a20b6de5df64656640d61f0512b` | Restore damaged, partly loaded turrets at military roadblocks and outposts. |
| Military extra rarity | [DDA #55908](https://github.com/CleverRaven/Cataclysm-DDA/pull/55908), head `78774681cdb396eb7a0cd8f826c083a5175b2ba8` | Raise default field and road weights only. |

### Implemented behavior

The standard solar panel produces 90 W while derived panels keep proportional modifiers and irradiance calculations. The irradiator contains one compact ASRG; outposts and shipwrecks retain conventional generators.

Ordinary LMOEs occur 1-3 times and each parent layout guarantees one hidden `lmoe_guns` cache. Shared storage stays unchanged, excluding occupied and Aftershock Whately LMOEs. Classic, central, and ice labs use 65/100, 60/100, and 25/100 occurrence contracts. The autodoc finale guarantees `bionics_common`; other finales retain guaranteed rewards.

Default-region military-extra weights are 12 in fields and 125 on roads. Roadblocks select M249/M240/M2 turrets at exact 70/25/5 weights, with 30-70% hit points and 80-240/50-150/20-60 ammunition. Outposts have two 40% damaged-M249 positions; police roadblocks and loot are unchanged.

`spawn_data.hp_percent` accepts 1-100 or an ascending range. `ammo_qty` applies to the loaded monster type's ammunition pool, preserving Generic Guns compatibility. Explicit `ammo` is mutually exclusive. All fields persist for saved pending spawns, while legacy eight-field arrays load with defaults.

### Exclusions and contracts

No existing-overmap migration, microlab redesign, broad ASRG restoration, full-strength turret, monster-type change, police branch change, or modded-region weight change is included. `tools.test_progression_backports` locks energy, scope, rewards, encounter shape, and mod ammunition. Focused Catch2 contracts execute probability boundaries, parsing, monster state, legacy loading, and pending-spawn round trips; the Windows workflow fails on zero discovery.

## Batch 2: independent CBM scavenging and utility

### Provenance and adaptations

| Concern | Upstream boundary | Fork adaptation |
| --- | --- | --- |
| Ordinary zombie CBM removal | [DDA #49892](https://github.com/CleverRaven/Cataclysm-DDA/pull/49892), head `daa8650237e3a03f546fba2514cb2c5ac367d4d1` | Preserve the fork's skill-scaled, dirty dissection route. |
| Mine and vault removals | [DDA #55329](https://github.com/CleverRaven/Cataclysm-DDA/pull/55329), head `190ebd1fba412e3fc51ccdc91cdded3a4793fe36`; [DDA #55999](https://github.com/CleverRaven/Cataclysm-DDA/pull/55999), head `e4587e7f62edfa14cbed3ccf02baa25a5341337f` | Restore low-weight thematic salvage, not generic vault loot. |
| Location-wide CBM cleanup | [DDA #56552](https://github.com/CleverRaven/Cataclysm-DDA/pull/56552), head `60fabfe768f3c5472e08cbb3f8a61bb19b2370f5` | Restore selected medical, scientific, electronic, military, and robotic caches. |
| Integrated Toolset reduction | [DDA #52889](https://github.com/CleverRaven/Cataclysm-DDA/pull/52889), merge `661b2fdd8861a767b3960c75cb780a3a08840ebe` | Restore classic work qualities to both integrated pseudo-tools. |
| Railgun replacement | [DDA #61176](https://github.com/CleverRaven/Cataclysm-DDA/pull/61176), head `5aaf90e11a469f4a530e0f9e08da25ed018886ad` | Reactivate Railgun while retaining Throwing Assist. |

### Implemented behavior

Scientists, technicians, military zombies, bio-operators, and Exodii zomborgs retain dissection-only, skill-scaled CBM salvage. Recovered implants remain filthy, non-sterile, unpackaged, and faulted. Low-weight routes return to hospitals, mines, science loot, Robofac trade, and sparse basement, bunker, military clinic, mortuary, police, prison, and electronics caches. Exodii stock remains available.

The Integrated Multitool's stowed and extended forms regain hammering, sawing, wrenching, screwdriving, cutting, prying, nail-pulling, and drilling qualities. Save-facing IDs and the existing included-bionic structure are unchanged.

Railgun, its implant, and its autodoc software are active again beside Throwing Assist. It has rare general, military, bio-operator, zomborg, Exodii tier-three, and installation-program routes. An active Railgun doubles uncapped range and improves damage only for ferric items when the full 10 kJ trigger cost is available; a powered throw adds lightning and consumes exactly 10 kJ. Powered mech throw assist takes precedence and suppresses all Railgun effects consistently.

### Exclusions and contracts

No clean direct death drops, generic-vault rollback, Exodii weakening, cleaning/install bypass, modular-tool migration, unrelated obsolete CBM, or non-ferric throwing change is included. `tools.test_progression_backports` locks dirty corpse salvage, exact low-weight routes, mapgen cache scope, active definitions, coexistence, qualities, and power hooks. The focused Catch2 Railgun contract executes generic and graded-steel 10 kJ/9 kJ paths plus powered-mech suppression.
