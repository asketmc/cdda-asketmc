# CDDA 0.G Additive release changelog

This file is generated from reviewed changelog fragments and immutable release manifests. Do not edit it by hand.

- The release sections below are deltas, newest first.
- [PATCHNOTES_ADDITIVE_0G.md](PATCHNOTES_ADDITIVE_0G.md) remains the cumulative, curated overview of the fork.
- [Release process](doc/RELEASING.md) explains how a release is prepared and verified.

## CDDA 0.G Additive 2026.08.29.1

Released: 2026-08-29

Changes since [v0.G-additive-2026.08.26.2](https://github.com/asketmc/cdda-asketmc/releases/tag/v0.G-additive-2026.08.26.2).

For the cumulative fork overview, see [PATCHNOTES_ADDITIVE_0G.md](https://github.com/asketmc/cdda-asketmc/blob/main/PATCHNOTES_ADDITIVE_0G.md).

### Player changes

#### Features

- Add practical sorting and capacity-aware bulk transfers to inventory menus. ([PR #26](https://github.com/asketmc/cdda-asketmc/pull/26))
  - Advanced Inventory gains amount and value-density sorts, while classic pickup and drop can sort by stack weight or volume.
  - Move All considers volume, pocket limits, and character carry weight while preserving bulk-unload groups.
  - Save compatibility: Compatible with existing 0.G additive saves.
- Preserve progress when corpse processing is interrupted and resumed. ([PR #27](https://github.com/asketmc/cdda-asketmc/pull/27))
  - All eight corpse-processing methods track independent fractional progress on the corpse across movement and save/load.
  - The butchery menu reports partial completion, while completed work clears its marker and produces output once.
  - Save compatibility: Compatible with existing 0.G additive saves.

#### Interface

- Keep the Windows tiles interface sharp and fully visible across mixed-DPI monitors. ([PR #24](https://github.com/asketmc/cdda-asketmc/pull/24))
  - Windowed and maximized layouts preserve at least an 80x24 terminal while fitting the active monitor work area.
  - Moving the game between monitors refreshes fonts, render targets, window placement, and fullscreen restore dimensions without compounding scale changes.
  - Save compatibility: Compatible with existing 0.G additive saves.

#### Bugfixes

- Climb down supported ledges safely when the same route is climbable upward. ([PR #22](https://github.com/asketmc/cdda-asketmc/pull/22))
  - Downspouts, fences, ladders, braced walls, and nearby vehicles support controlled descent; multi-level routes require support on every level.
  - Unsupported ledges retain the existing risky and tool-assisted behavior; supported routes preserve grappling hooks, ropes, and web rappelling resources.
  - Save compatibility: Compatible with existing 0.G additive saves.
- Killing a guaranteed-hostile NPC no longer causes innocent-kill guilt before they enter an active combat attitude. ([PR #25](https://github.com/asketmc/cdda-asketmc/pull/25))
  - Kill-on-sight faction relationships now count as guaranteed hostility even while the NPC still has NPCATT\_NULL.
  - Attacking and killing a genuinely neutral NPC still applies the existing innocent-kill morale penalty.
  - Save compatibility: Compatible with existing 0.G additive saves.

### Build and maintainer changes

#### Infrastructure

- Report pull requests above 400 or 800 changed lines without blocking CI. ([PR #22](https://github.com/asketmc/cdda-asketmc/pull/22))
- Manual Windows build requests now publish a short-lived downloadable package and verification files. ([PR #25](https://github.com/asketmc/cdda-asketmc/pull/25))

### Intentionally omitted

- [PR #28](https://github.com/asketmc/cdda-asketmc/pull/28): Release metadata only; player changes are recorded in their source pull requests.

### Validation recorded for this release

- The tag workflow must reproduce identical executable and ZIP hashes from two clean release builds.
- The exact staged archive must pass checksum, metadata, extraction, and --check-mods dda validation before publication.

## CDDA 0.G Additive 2026.08.26.2

Released: 2026-08-26

Changes since [v0.G-additive-2026.08.26.1](https://github.com/asketmc/cdda-asketmc/releases/tag/v0.G-additive-2026.08.26.1).

For the cumulative fork overview, see [PATCHNOTES_ADDITIVE_0G.md](https://github.com/asketmc/cdda-asketmc/blob/main/PATCHNOTES_ADDITIVE_0G.md).

### Player changes

#### Features

- Let followers obtain safe food, clean water, emergency warmth, shelter, and last-resort forage from permitted nearby supplies. ([PR #13](https://github.com/asketmc/cdda-asketmc/pull/13))
  - Save compatibility: Compatible with existing 0.G additive saves.
  - Known limit: Followers use only owned, accessible supplies and do not autonomously consume dirty water or forage outside emergency hunger.
- Let followers heal themselves when safe and optionally heal allies without abandoning assigned work. ([PR #14](https://github.com/asketmc/cdda-asketmc/pull/14))
  - Follower healing rules migrate safely, combat danger blocks non-urgent treatment, and interrupted active or stashed work resumes exactly once.
  - Save compatibility: Compatible with existing 0.G additive saves.
- Let followers treat registered vitamin deficiencies and prefer tolerable food while retaining a critical-starvation fallback. ([PR #14](https://github.com/asketmc/cdda-asketmc/pull/14))
  - Save compatibility: Compatible with existing 0.G additive saves.
- Let assigned camp workers interrupt work for critical needs, resume it exactly once, return to their assigned camp, and spend downtime inside it. ([PR #15](https://github.com/asketmc/cdda-asketmc/pull/15))
  - Save compatibility: Compatible with existing 0.G additive saves.
  - Known limit: This keeps the 0.G scheduler and sorting model; it does not import the modern global behavior tree or activity-actor sorter.

#### Interface

- Publish a strict per-release feature list alongside the cumulative fork overview. ([PR #20](https://github.com/asketmc/cdda-asketmc/pull/20))
  - The Windows archive includes release notes, complete release history, save-compatibility guidance, and known limits.
  - Save compatibility: Not applicable to save data.

#### Bugfixes

- Respect ownership, pickup rules, personal zones, no-pickup zones, locked vehicle cargo, and unreachable-candidate fallback during autonomous survival. ([PR #13](https://github.com/asketmc/cdda-asketmc/pull/13))
  - Save compatibility: Compatible with existing 0.G additive saves.
- Prevent invalid weapon scores and obvious empty-hand preference without changing combat coefficients or loudness rules. ([PR #14](https://github.com/asketmc/cdda-asketmc/pull/14))
  - Save compatibility: Compatible with existing 0.G additive saves.
- Fall through to feasible lower-priority camp jobs when sorting has no reachable source or usable destination. ([PR #15](https://github.com/asketmc/cdda-asketmc/pull/15))
  - Save compatibility: Compatible with existing 0.G additive saves.
- Make local and radio camp liquid-storage checks query-pure and reserve separate fixtures for incompatible liquid results. ([PR #15](https://github.com/asketmc/cdda-asketmc/pull/15))
  - Save compatibility: Compatible with existing 0.G additive saves.

### Build and maintainer changes

#### Build

- Bind release notes, embedded metadata, build provenance, and the Windows archive into one immutable checksum set. ([PR #20](https://github.com/asketmc/cdda-asketmc/pull/20))
  - Tagged reruns require the existing release title, body, asset names, checksums, and every uploaded byte to match.

#### Infrastructure

- Update actions/checkout from 5.1.0 to 7.0.1. ([PR #8](https://github.com/asketmc/cdda-asketmc/pull/8))
- Update actions/cache/save from 4.3.0 to 6.1.0. ([PR #9](https://github.com/asketmc/cdda-asketmc/pull/9))
- Update actions/cache/restore from 4.3.0 to 6.1.0. ([PR #10](https://github.com/asketmc/cdda-asketmc/pull/10))
- Update actions/upload-artifact from 4.6.2 to 7.0.1. ([PR #11](https://github.com/asketmc/cdda-asketmc/pull/11))
- Harden CI with explicit least privilege, pinned security audits, grouped dependency updates, and build provenance attestations. ([PR #17](https://github.com/asketmc/cdda-asketmc/pull/17))
  - Workflow jobs declare their permissions, actionlint and zizmor inspect workflow changes, and release archives receive Sigstore-backed GitHub provenance.
  - Dependabot tracks grouped Actions and Python-tooling updates to reduce overlapping CI runs.
- Remove the OpenSSF Scorecard workflow that could not run under the repository's GitHub-owned Actions allowlist. ([PR #19](https://github.com/asketmc/cdda-asketmc/pull/19))
  - The pinned actionlint and zizmor audits, explicit workflow permissions, and release provenance attestation remain enabled.
- Generate release history from reviewed, immutable pull-request fragments and explicit published-release boundaries. ([PR #20](https://github.com/asketmc/cdda-asketmc/pull/20))
  - CI verifies exact first-parent PR coverage, rejects historical rewrites, and derives future squash identities from immutable reviewed fragments instead of editable commit subjects.

### Intentionally omitted

- [PR #21](https://github.com/asketmc/cdda-asketmc/pull/21): Release metadata only; player changes are recorded in their source pull requests.

### Validation recorded for this release

- The tag workflow must reproduce identical executable and ZIP hashes from two clean release builds.
- The exact staged archive must pass checksum, metadata, extraction, and --check-mods dda validation before publication.

## CDDA 0.G Additive 2026.08.26.1

Released: 2026-08-26

Changes since [v0.G-additive-2026.08.25](https://github.com/asketmc/cdda-asketmc/releases/tag/v0.G-additive-2026.08.25).

For the cumulative fork overview, see [PATCHNOTES_ADDITIVE_0G.md](https://github.com/asketmc/cdda-asketmc/blob/main/PATCHNOTES_ADDITIVE_0G.md).

### Player changes

#### Features

- Make EMP-damaged electronics repairable and support the optional temporary reboot behavior. ([PR #4](https://github.com/asketmc/cdda-asketmc/pull/4))
  - EMP damage now uses explicit electronic faults and data-driven repair or reboot behavior instead of permanently ruining affected devices.
  - Save compatibility: Compatible with existing 0.G additive saves.
- Let followers sleep normally and keep fatigue, temperature, and wetness state across active play and loading. ([PR #6](https://github.com/asketmc/cdda-asketmc/pull/6))
  - Save compatibility: Compatible with existing 0.G additive saves.
  - Known limit: Offline temperature catch-up is capped and uses current conditions rather than reconstructing historical weather.
- Use normal digestion for camp water and allow camp residents to receive mopping work. ([PR #6](https://github.com/asketmc/cdda-asketmc/pull/6))
  - Save compatibility: Compatible with existing 0.G additive saves.

#### Bugfixes

- Recover from Windows audio initialization failures without aborting game startup. ([PR #3](https://github.com/asketmc/cdda-asketmc/pull/3))
  - Retry the selected SDL audio backend once, then try DirectSound when no explicit SDL\_AUDIODRIVER override is set.
  - Load the soundpack only after the mixer opens and continue without sound if every bounded attempt fails.
  - Log the selected backend, playback devices, mixer backend, default device, and obtained format.
  - Save compatibility: Compatible with existing 0.G additive saves.
  - Known limit: The recovery remains on the bundled SDL 2 and SDL\_mixer stack; Windows hardware-fault injection was not part of validation.
- Keep NPC sorting out of personal zones and add new work priorities without overwriting saved choices. ([PR #6](https://github.com/asketmc/cdda-asketmc/pull/6))
  - Save compatibility: Compatible with existing 0.G additive saves.
- Report pickup targets removed during an activity without opening a debug-error popup. ([PR #7](https://github.com/asketmc/cdda-asketmc/pull/7))
  - The activity tells the player how many queued items disappeared, records useful context in debug.log, and continues with surviving targets.
  - An item location that was never valid still raises a diagnostic because it indicates a programming error.
  - Save compatibility: Compatible with existing 0.G additive saves.
- Let NPC mopping jobs find, fetch, and safely wield stored mops. ([PR #12](https://github.com/asketmc/cdda-asketmc/pull/12))
  - Save compatibility: Compatible with existing 0.G additive saves.
- Preserve pickup descriptions across save/load and quietly invalidate already-lost NPC butchery targets. ([PR #12](https://github.com/asketmc/cdda-asketmc/pull/12))
  - Unexpected item-location failures remain loud diagnostics instead of being broadly suppressed.
  - Save compatibility: Compatible with existing 0.G additive saves.

### Build and maintainer changes

#### Build

- Build Windows x64 Tiles and Sound packages in CI and publish checksum-bound tagged releases. ([PR #5](https://github.com/asketmc/cdda-asketmc/pull/5))
  - Pull requests compile with the checksum-pinned MXE GCC toolchain without retaining binaries.
  - Tagged main commits build twice and publish only when executable and ZIP hashes reproduce.

#### Infrastructure

- Wait for the packaged Windows GUI process and validate its real --check-mods exit code. ([PR #16](https://github.com/asketmc/cdda-asketmc/pull/16))
  - The release gate now fails on the process object's exit code instead of relying on an unset PowerShell LASTEXITCODE value.

### Known limits

- Windows audio recovery was source-compiled and contract-tested, but automatic fallback was not exercised with an injected hardware failure.
- Follower offline temperature catch-up is capped and uses current conditions instead of replaying historical weather.
- The release keeps the bounded 0.G donor closure; SDL 3, autonomous follower redesigns, and unrelated later content are not included.

### Validation recorded for this release

- Two clean release builds produced identical executable and ZIP hashes.
- The exact staged ZIP was checksum-verified and extracted on Windows.
- Embedded full-commit provenance was verified.
- The packaged executable passed --check-mods dda.

## CDDA 0.G Additive 2026.08.25

Released: 2026-08-25

This is the first release in the strict changelog chain. It records the fork state at adoption and the pull requests merged into that build.

For the cumulative fork overview, see [PATCHNOTES_ADDITIVE_0G.md](https://github.com/asketmc/cdda-asketmc/blob/main/PATCHNOTES_ADDITIVE_0G.md).

### Player changes

#### Features

- Add the selected EOC scripting APIs required by the fork's additive content and automation features.
  - Save compatibility: Compatible with existing 0.G additive saves.
  - Known limit: This is the documented dependency closure, not a wholesale import of the later EOC architecture.
- Add practical quality-of-life behavior for fast deconstruction, heavy-vehicle movement, BMI health, batch handling, and practical skill use.
  - Save compatibility: Compatible with existing 0.G additive saves.
- Add vehicle locks, tiedown handling, workshop functions, generator and backup behavior, automatic drinking, routing improvements, and related vehicle content.
  - Save compatibility: Compatible with existing 0.G additive saves.
  - Known limit: Existing vehicles are not broadly retrofitted with newly added parts.
- Expand follower crafting, rules, nutrition, storage, radio control, camp transfer, brick production, and CBM surgery.
  - Save compatibility: Compatible with existing 0.G additive saves.

#### Interface

- Expand the Ultica and Surveyors visual sets with current terrain IDs, higher-resolution sprites, multi-Z support, occlusion, animations, themes, fonts, and sound cues.
  - Existing worlds remain loadable; a new world is recommended when complete exposure to added map content matters.
  - Save compatibility: A new world is recommended to receive the complete change.
- Backport inventory, crafting, e-reader, search, item-information, and ASCII-art interface improvements.
  - Save compatibility: Compatible with existing 0.G additive saves.

#### Mods

- Add riot-equipment repair, CBM salvage, and the bounded Useful Helicopters compatibility subset.
  - Save compatibility: Compatible with existing 0.G additive saves.

#### Bugfixes

- Fix selected NPC dialogue-close crashes and NPC rotation failures.
  - Save compatibility: Compatible with existing 0.G additive saves.
- Keep contained items owned by unloaded NPCs resolvable after saving and loading. ([PR #1](https://github.com/asketmc/cdda-asketmc/pull/1))
  - Character-rooted contained item locations wait until unloaded NPC owners are registered, while map and vehicle locations retain eager validation.
  - Save compatibility: Compatible with existing 0.G additive saves.

#### Performance

- Reduce repeated work in recipe lookup, inventory key handling, and repair selection. ([PR #2](https://github.com/asketmc/cdda-asketmc/pull/2))
  - Recipe lookup filters candidates before collecting complete source sets.
  - Reserved input bindings and repeated repair calculations are cached without changing modifier or component semantics.
  - Save compatibility: Compatible with existing 0.G additive saves.

### Build and maintainer changes

#### Infrastructure

- Enforce the 0.G additive preservation boundary with donor provenance, exclusion records, focused contracts, and a fail-closed audit.

### Known limits

- The fork deliberately excludes unrelated later-branch removals, migrations, balance changes, and large architectural rewrites.
- The cumulative scope and donor-specific limitations remain authoritative in PATCHNOTES\_ADDITIVE\_0G.md and the backport reports.

### Validation recorded for this release

- The exact tagged tree produced a Windows x64 Tiles and Sound build.
- Dark Days Ahead mod JSON, additive audit, and portable feature contracts passed.
- The focused item-location regression object compiled.
- A copied-save load smoke completed with no new item\_location errors.
