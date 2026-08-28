# Visual, audio, and UI backport report

This report records the bounded visual/UI pass built on the current additive
0.G branch. It is not a wholesale merge of current experimental, and it does
not import unrelated combat, balance, content, or world-generation changes.

## Delivered

| Area | Upstream source | Target disposition |
|---|---|---|
| Tall-sprite occlusion | PR #63089, `ece67dbf829eb602e089f4a6185ea27d302ebdda` | Ported. Transparency/retraction and Off/On/Auto controls are available. |
| Run/smash animation | PRs #65622 and #66087, `01ecf0049eafeab0cfb9cb2fd45bc0240e805205`, `2af2001cc13501f91354511dc7ca8c8f84a6b314` | Ported, including asynchronous drawing follow-up. |
| Lower-Z vision/fog | PR #65738, `bd8b8abd02b4d4d0022dd048e706344e884e4789` | Ported to the 0.G flat tile-render list. |
| Isometric multi-Z vision | PR #66383, `6ce851fd71bf0fa456f62f3bf234fae98391bcd9`; selected correction from PR #82240, `738c111f431579f47e1b3c1356af14f43c89e762` | Adapted to the 0.G flat tile-render list. Per-tileset vertical spacing scales with pixelscale and zoom, fog uses the same transform, legacy sets without positive spacing remain single-Z, and the lower draw bound is clamped to `OVERMAP_DEPTH`. |
| Creature shadows | PR #66730, `1f5aaac9d40e965c0e3df16e68bc127f7797f9c2` | Adapted to the 0.G multi-Z draw loop. |
| Ledge sight coverage | PR #67434, `32e562d880a3396c45ca2530752b226e9de45402`; selected correction from PR #72293, `1b1a78e4647b0de0a4b12fd07957b48bacc87a52` | Selectively ported for player seen-cache processing only; the donor's Creature::sees stealth/balance changes are excluded. The correction retains the negative-coverage exit and applies the extra penalty only for target furniture. The target adaptation preserves 0.G `Z_TRANSPARENT` ramps, closes off-map cache access, and excludes pooled remote-camera caches from player-origin ledge post-processing. |
| Armor sprite override | PR #66931, `d5d3d0dfaa2185d05eda3be1894be67c382c6804` | Ported; available from character info with Shift+W. |
| Lower-Z visibility cache | PR #67997, `f12487cefcdd8c18f70ce68f73e09826bdced18d` | Adapted so lighting and invisibility are evaluated for each drawn lower tile. |
| Vertical look without 3D vision | PR #68660, `838f893323a9df497cad9e33766000f22deeb210`; cache-bound correction selected from PR #82240, `738c111f431579f47e1b3c1356af14f43c89e762` | Ported. Look Up/Down is available with `FOV_3D` disabled; remote Z-level dirtiness rebuilds the seen cache only when 3D FOV is active. |
| Eight UI themes | PR #68153, `826874d489184c7537d7ab47d4425b0ebf1d10dd` | Ported as data. |
| Weighted field sprites | PR #75636, `9eb6bdaa81d6c775230e09617cd5f91db0b31d0c` | Ported. |
| Animated rain variants | PR #80980, `64615706ab8a531be988bea36d4334b8a4a28e1c` | Ported. |
| Visible melee-hit feedback | PR #85166, `2fb12ed9fdf1faca3f7605bbfb2223ec0c961a26` | Selectively adapted. The current donor's later creature-lifetime and typed-coordinate APIs were not imported. |
| Specific weapon sounds | PR #86002, `b62a2db5f25737a2c0fece49d22b41ec47c1f092` | Adapted to 0.G gunmods, optionals, coordinates, and volume units. Generic fallback remains intact. |
| Correct NPC footsteps | PR #86249, `9e7cb7dac86634120b9e22bc1af5e610b3dc17e2` | Adapted to 0.G coordinates and optionals. |
| Current UltiCa/SurveyorsMap | CDDA-Tilesets release `2026-08-23`, `1f1988c5e144473f894fcb1e2914af51fd08b7af` | Installed with generated 0.G compatibility sheets and manifests. |
| UltiCa high-resolution terrain pilot | Private fork PR #8, `3d528d7da570a725087ddb7c6cb6e2f915254727` | Nine reviewed 64x64 common-terrain sprites plus fifteen exact 2x pavement connectivity sprites at logical 32x32 scale. |
| Crisp font defaults | JetBrains Mono 2.304 | Bundled under OFL; hinting control added; Terminus/Unifont retained as fallbacks. |
| Windows per-monitor DPI | Breeze PR #1173 | Adapted for PerMonitorV2 awareness, border-aware minimum-grid fitting, and runtime font/layout refresh when a window crosses displays. |
| Structured Sidebar/widgets | `mlange-42/cdda-structured-sidebar`, incorporated upstream before 0.G | Already present. Its complete widget-reference graph is regression-tested. |

The sound changes add routing hooks, not copyrighted sound assets. Otopack and
other existing packs keep their generic fallbacks and the 0.G suppressed-gun
event; a pack can opt into the new exact weapon/caliber/suppression/melee event
variants.

## P0 tileset compatibility result

The imported release follows current experimental identifiers, while this game
still contains stable 0.G identifiers. `tools/gfx_tools/backport_tileset_release.py`
computes the difference and appends legacy sheets rather than replacing old
coverage:

- UltiCa: 12,184 upstream-release IDs plus 388 retained 0.G-only IDs.
- SurveyorsMap: 3,037 upstream-release IDs plus 65 retained 0.G-only IDs.

These counts prove the union installed by this backport. They do not mean that
every modded or dynamically generated ID has unique art; ordinary fallback
sprites remain necessary.

The merger also rebases every retained tile's global sprite index after the
legacy images are appended. Referenced legacy sheets are retained even when
they contribute no tile ID themselves. This closes the follower-overlay bug in
which 0.G hair sprites still pointed into an opaque modern sheet and rendered a
gray tile-sized background.

The creature-shadow adaptation uses 0.G's existing `BLINK_SPEED` constant. The
original selective transplant called an option introduced after the 0.G base;
requesting that absent option produced a debug error followed by a null-option
crash during normal map input.

## Dropped or not applicable

### Map-memory refresh, PR #68131

**Disposition: not applicable after attempt 1.** The donor uses a later
multi-decoration cache (`memory_cache_dec_is_dirty`, decoration clearing, and a
`memorize_only` draw path) that does not exist in 0.G. The target has a
single-slot memory model and re-memorizes terrain before furniture, trap, and
vehicle decoration. Importing the donor would add a second memory architecture
rather than fix its stated bug in this target.

### 2026 colored-lighting chain

**Disposition: dropped as one inseparable chain after attempt 1.** The first
mandatory core PR #86066 produced ten source conflicts and two incompatible
test-data changes. Its automatically applicable tile code still referenced the
post-0.G row-bucketed `tile_render_info`, typed bubble-map coordinates, later
map draw caches, and later vehicle-part factory interfaces. PRs #86087, #86104,
#86107, #86139, #86248, and #86888 are follow-ups to that new core; the final
color data has no effect without it. A faithful port therefore requires a
renderer and lightmap migration and was stopped before unrelated architecture
could leak into the additive fork.

### Illustrated loading screens and hints

**Disposition: dropped before source transplantation.** The modern sequence is
built on the post-0.G ImGui loading UI (then custom/mod images, multiple vanilla
screens, and hints). The target loading path is curses/uilist-based and has no
image-surface contract. Implementing a new loading renderer is a separate
feature, not a data backport.

### Drop items from ledges, PR #65125

**Disposition: deferred.** This optional donor changes gameplay and damage
handling and is not a dependency of isometric multi-Z drawing, ledge sight
coverage, or vertical look. It remains an independently reviewable follow-up
rather than being folded into the mandatory visual-correctness bundle.

## Regression coverage and validation boundary

Every delivered gameplay/UI donor has its own named regression case in
`tools/gfx_tools/test_visual_ui_donor_contracts.py`.  The 16 cases cover PRs
#63089, #65622, #66087, #65738, #66383, #66730, #66931, #67434, #67997,
#68153, #68660, #75636, #80980, #85166, #86002, and #86249.  They verify the
complete target call path and required data, rather than merely checking that
a donor string exists.

The behavior that can be isolated from SDL is also exercised directly in
`tests/visual_ui_backport_test.cpp`: occlusion mode calculations, scaled
isometric spacing and fog at default/non-default zoom, legacy single-Z
fallback, deterministic weighted field variants, worn-armor overlay
replacement, specific firearm fallback ordering, and melee sound selection.
`tests/shadowcasting_test.cpp` covers ledge math, lower-floor bounds, and the
two-Z dirty-cache lifecycle with 3D FOV on and off. Existing
`tests/action_test.cpp` cases cover the old and new occlusion action IDs.

The remaining executable asset tests verify that:

- the tileset release merger preserves only genuinely missing legacy IDs,
  copies required sprite-dependency sheets, rebases direct and nested sprite
  references, removes unsupported release metadata, and emits a provenance
  manifest;
- installed tileset manifests, ID counts, and every referenced sheet image are
  checked;
- all eight theme palettes are checked for complete RGB definitions;
- the font, fallback order, and OFL file are checked;
- every Structured Sidebar widget reference is resolved against loaded UI data.

The combined Python suite contains **30 passing tests**, including direct,
nested, and cross-sheet sprite-rebasing cases, and all
16 shipped donor PRs have an explicit regression case.  The 0.G build has no
headless/offscreen SDL renderer fixture or configured C++ line-coverage job, so
an honest project-wide 80% C++ line figure cannot be produced in this bounded
backport.  Renderer and SDL sound behavior are instead covered by the pure C++
tests above and the donor call-path contracts.  A fresh Windows Tiles+Sound
compile and packaged runtime smoke check are pending the consolidated
post-merge release run.

The test runner previously aborted after otherwise successful assertions while
finalizing vehicle enchantments, because a vehicle-only cache constructed a
dialogue with two null actors.  The cache now uses a topic-only talker for its
constant/global-variable condition context.  This is a correctness fix for the
existing vehicle-enchantment path and allows the test process to fail closed.
