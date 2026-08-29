# Progression Backport Report

These batches reopen selected classic 0.G progression routes without removing later systems or wholesale-merging donor branches. Donor heads mark regression boundaries.

## Batch 1: energy and dangerous exploration

### Provenance and adaptations

| Concern | Upstream boundary | Fork adaptation |
| --- | --- | --- |
| Solar irradiance | [DDA #59179](https://github.com/CleverRaven/Cataclysm-DDA/pull/59179), head `02fd00db00b7f5cdc77e8e1f217af59b81285adc` | Keep irradiance; rate the base panel at 90 W. |
| Static generators replacing ASRGs | [DDA #62459](https://github.com/CleverRaven/Cataclysm-DDA/pull/62459), head `50860c3d059930ff302982228c3e15da67a7bd54` | Restore one compact ASRG at the irradiator only. |
| Rarer unique map specials | [DDA #46701](https://github.com/CleverRaven/Cataclysm-DDA/pull/46701), head `63b16f84884817c0d64a62d5e53591af80e1e747` | Retain map-special and uniqueness rules; raise selected occurrence weights. |
| Aboveground turret removal | [DDA #55790](https://github.com/CleverRaven/Cataclysm-DDA/pull/55790), head `7693988475c10a20b6de5df64656640d61f0512b` | Restore damaged, partly loaded turrets at military roadblocks and outposts. |
| Military extra rarity | [DDA #55908](https://github.com/CleverRaven/Cataclysm-DDA/pull/55908), head `78774681cdb396eb7a0cd8f826c083a5175b2ba8` | Raise default field and road weights only. |
| Reward and spawn persistence plumbing | Local fork adaptation; no donor import | Add the LMOE cache, finale CBM roll, and backward-compatible `spawn_data` save fields needed by the selected behavior. |

### Implemented behavior

The standard solar panel produces 90 W while derived panels keep proportional modifiers and irradiance calculations. The irradiator adds one compact ASRG without replacing either conventional generator; outposts and shipwrecks retain conventional generators.
Ordinary `CLASSIC`/`MAN_MADE` LMOEs occur 1-3 times on suitable land at city distance 20+. `LAB`/`UNIQUE` classic, central, and ice labs use 65/100, 60/100, and 25/100 occurrence contracts; fixed layouts stay unchanged.
Each ordinary base-game LMOE parent guarantees one hidden `lmoe_guns` cache through a palette marker. No Hope suppresses only the gun and preserves its existing reduced food rolls. Shared storage stays unchanged, excluding occupied and Whately LMOEs. The autodoc finale guarantees `bionics_common`; other finales retain guaranteed rewards.
Default-region military-extra weights are 12 in fields and 125 on roads. Military roadblocks retain their riot turrets and add adjacent M249/M240/M2 turrets at exact 70/25/5 weights, with 30-70% hit points and 80-240/50-150/20-60 ammunition. Outposts retain four searchlights and add two distinct 40% damaged-M249 positions; police roadblocks and loot are unchanged.
`spawn_data.hp_percent` accepts 1-100 or an ascending range. `ammo_qty` adjusts the loaded monster's ammunition pool without replacing IDs, preserving Generic Guns compatibility. Explicit `ammo` is mutually exclusive. All fields persist for saved pending spawns; legacy eight-field arrays load with defaults.
### Exclusions and contracts

No existing-overmap migration, microlab redesign, unrelated frequency change, broad ASRG restoration, full-strength turret, turret type/stat/drop change, police branch change, modded-region military weight, or non-military extra change is included. `tools.test_progression_backports` locks energy, scoping, rewards, military encounter shape, and Generic Guns ammunition. Focused Catch2 contracts execute probability boundaries, parsing, monster state, legacy and pending-spawn loading, and solar output.

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

Scientists retain their pre-existing clean death-drop lottery, while scientists, technicians, military zombies, bio-operators, and Exodii zomborgs all retain skill-scaled dirty dissection salvage. Dissected implants remain filthy, non-sterile, unpackaged, and faulted. Low-weight routes return to hospitals, mines, science loot, Robofac trade, and sparse basement, bunker, military clinic, mortuary, police, prison, and electronics caches. Exodii stock remains available.

The Integrated Multitool's stowed and extended forms regain hammering, sawing, wrenching, screwdriving, cutting, prying, nail-pulling, and drilling qualities. Save-facing IDs and the existing included-bionic structure are unchanged.

Railgun and its implant are active again beside Throwing Assist, with rare military, bio-operator, zomborg, and Exodii tier-three routes. Its autodoc software uses the installation-program pool. An active Railgun doubles uncapped range and improves damage only for ferric items when the full 10 kJ trigger cost is available; a powered throw adds lightning and consumes exactly 10 kJ. Powered mech throw assist takes precedence and suppresses all Railgun effects consistently.

### Exclusions and contracts

No clean direct Railgun death-drop route, generic-vault rollback, Exodii weakening, cleaning/install bypass, modular-tool migration, unrelated obsolete CBM, or non-ferric throwing change is included. `tools.test_progression_backports` locks dirty corpse salvage, exact low-weight routes, mapgen cache scope, active definitions, coexistence, qualities, and power hooks. Focused Catch2 Railgun contracts execute generic and graded-steel 10 kJ/9 kJ paths plus powered-mech suppression.

The Windows workflow compiles and executes every focused Catch2 filter, prints JUnit diagnostics on failure, and rejects zero-test discovery. Validation boundary: exact-head additive audits, required Python tests, source compilation, and Windows Catch results are recorded on the PR; `--check-mods dda`, Generic Guns runtime, copied-save loading, and playable-release smoke remain required before merge unless exact-tree evidence is recorded.

## Batch 3: expert manual installation and tuned Exodii progression

### Provenance and adaptations

| Concern | Upstream boundary | Fork adaptation |
| --- | --- | --- |
| Global manual-install route removed | [DDA #40360](https://github.com/CleverRaven/Cataclysm-DDA/pull/40360), head `1eefd32f08b40d4eece719b187213dc16651d778`; original optional mod `04d7f8bd7260a50a5608b199cd123363e2752edb` | Restore the option through an off-by-default bundled mod, but add explicit skill, equipment, anesthetic, sterility, pain, and failure boundaries. |
| Dangerous surgical failures | [DDA #40874](https://github.com/CleverRaven/Cataclysm-DDA/pull/40874), head `e273237253820f4105f007cd3613f9d16e2b9408` | Retain the existing damage and faulty-install failure path; improvised success is capped at 95%. |
| Rubik merchant and trust tiers | [DDA #51267](https://github.com/CleverRaven/Cataclysm-DDA/pull/51267), head `d00041bfcd3b219353d6393c6c0734e1027dbaf6`; [DDA #52380](https://github.com/CleverRaven/Cataclysm-DDA/pull/52380), head `19d11dc1ffa3baf59b1a764468fbe165e31e3782` | Keep Rubik's deterministic stock and installer role, including trust-gated sales. |
| Later pacing and fee gates | [DDA #55046](https://github.com/CleverRaven/Cataclysm-DDA/pull/55046), head `859f94c8321bf531163f9c090b9b60819c3c01a6`; [DDA #57135](https://github.com/CleverRaven/Cataclysm-DDA/pull/57135), head `b1d98c70d6e5197debf1e9902dba5357697bbe75`; [DDA #58708](https://github.com/CleverRaven/Cataclysm-DDA/pull/58708), head `3bc741251e7c6d7cf80d9d8cbbf8cd22d72a5866` | Use a three-day cadence, lower tier thresholds, permit locked stock to accumulate, and halve only the Exodii service multiplier. |

### Implemented behavior

Core declares `MANUAL_BIONIC_INSTALLATION` false. Enabling the bundled **Manual Bionic Installation** mod changes it to true for that world. A positive-difficulty CBM with no dedicated `installation_requirement` then becomes eligible for self-installation only at electronics 8, health care 6, and mechanics 4. Zero-difficulty implants without a procedure remain ineligible instead of entering undefined failure arithmetic. Dedicated per-CBM procedures continue to use their own requirements.

The generic procedure requires fine cutting and screwdriving tools, a charged soldering or repair tool, solder, disinfectant, and sterile dressings. Existing checks still reject filthy, non-sterile, and deployed/faulted implants; existing weight- and difficulty-scaled anesthetic is still consumed. Starting improvised surgery adds `10 + 3 × difficulty` pain. Its displayed and executed success chance share a 95% ceiling, so even an expert retains failure risk and the existing dangerous-failure consequences.

Rubik now restocks every three days. The tier trust thresholds are 1, 8, 16, and 30; salvage tech joins tier three at 16. Removing `strict` permits higher-tier inventory to accumulate during restocks, but `can_sell` continues to refuse it until the corresponding faction trust is reached. The long interaction timer is also three days, so continued dealings can earn trust on the same cadence.

Exodii installation service uses a one-times implant-price multiplier instead of the general two-times multiplier. Non-Exodii installers retain the old multiplier, and the existing ownership/trading component of the price is unchanged. Together with Batch 2 scavenging, this keeps Rubik deterministic without making Rubik the only source of implants.

### Exclusions and contracts

No manual uninstallation, safe or guaranteed surgery, dirty-CBM bypass, free anesthetic, lower-skill shortcut, blanket `installation_requirement` rewrite, Exodii inventory expansion, trust bypass, instant restock, or non-Exodii price reduction is included. Existing CBM IDs, slots, upgrades, mutations, operation activity data, and saves remain unchanged.

`tools.test_progression_backports` locks the disabled core option, opt-in mod, exact procedure resources, runtime guards, tier thresholds, restock cadence, and focused Windows gate. Catch2 executes the option and all three skill floors, verifies the 95% ceiling, zero-difficulty rejection, and non-interruptible surgery start, and distinguishes Exodii from ordinary installation-service pricing. The additive audit binds the modified Exodii entities and rejects accidental core replacements.
