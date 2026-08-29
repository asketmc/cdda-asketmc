# CDDA 0.G Additive Fork — Detailed Patch Notes

This repository begins with the integrated source snapshot documented below.
The matching Windows Tiles+Sound package is published under GitHub Releases.

## Persistent corpse processing

- Bleeding, quick and full butchery, field dressing, skinning, quartering,
  dismembering, and dissecting now retain fractional progress on the corpse.
- Interrupted work can be resumed after moving the corpse, changing to another
  valid tool, or saving and loading. Each method tracks progress independently,
  and the butchery menu shows partial completion.
- Finished work clears its marker and produces its normal result once. Starting
  a quick method does not block switching to a finer method later.

## Supported ledge descent

- A ledge can be climbed down safely when the same one-level route is climbable
  upward or has strong nearby support such as a downspout, fence, ladder,
  braced wall, or vehicle.
- A multi-level descent is safe only when every level has support. Unsupported
  ledges retain the existing risky climb or fall confirmation and damage.
- Unsupported ledges keep the existing grappling-hook, rope, and web-rappelling
  behavior. Supported routes take priority without consuming or deploying them.

## Windows audio recovery

- Audio initialization now records the active SDL backend and available
  playback devices in `debug.log`.
- A transient endpoint failure is retried once. On Windows, an unavailable or
  broken default backend automatically falls back to DirectSound and retries.
  An explicitly selected `SDL_AUDIODRIVER` remains authoritative.
- Soundpacks are parsed and preloaded only after the mixer opens successfully,
  preventing one device error from cascading into misleading soundpack errors.
- SDL3 was deliberately not transplanted: its modern CDDA/BN implementation is
  coupled to their full tiles, input, build, and packaging migrations. The
  bounded SDL2 recovery path fixes the 0.G failure without replacing that stack.

## Crash and rotation fixes

- Killing an NPC whose faction is already guaranteed hostile no longer applies
  the innocent-kill morale penalty merely because they had not yet switched to
  their active kill-or-flee attitude. Attacking a genuinely neutral NPC still
  marks the death as murder.
- EMP-damaged electronics now receive repairable faults instead of permanent
  breakage; game-style EMP rules can use temporary reboots with a small failure
  chance.
- Item-description recipe searches now filter learned, book, e-reader, and
  helper recipes while collecting them instead of building the full recipe set.
- Automatic inventory-letter assignment gathers reserved keys once and ignores
  modifier-only bindings when choosing plain inventory letters.
- The repair selector caches repeated chance and material-count calculations
  while preserving the displayed success, damage, and component values.
- TODO: add granular Catch coverage for recipe-source filtering, modified-key
  invlet reservation, and repair-cache equivalence; the Windows build is the P0 gate.
- Fixed save/load resolution for items inside containers carried by unloaded
  NPCs.  Interrupted follower and prisoner activities no longer emit cascades
  of missing-owner, lost-target, and invalid-parent `item_location` errors.
- Multi-turn pickup now reports items removed by other activity instead of
  raising a debug error.  Names and safe location descriptions survive saves,
  lost locations cannot retarget another item on load, and locations that never
  resolved still fail loudly.  Focused Catch coverage exercises multiple losses,
  a surviving target, an unrelated same-tile item, and a save/load round trip.
- NPC butchery jobs now quietly cancel when their corpse had already vanished
  before the save, while unexpected item-location resolution failures remain loud.
- Fixed an NPC dialogue crash when closing the final categorized talk topic.
- Normalized current UltiCa and SurveyorsMap directional sprites to the 0.G
  rotation contract. This fixes east/west mirroring for vehicles, diagonal
  pavement/grass edges, connected terrain, furniture, fields, and overmap art;
  existing vehicle map memory remains save-compatible.
- TODO: manually verify V-Jill and representative connected terrain in all four
  cardinal directions, and replay the NPC conversation that previously crashed.

- Vanilla foundation: official CDDA 0.G “Gaiman”, commit
  `d6ec466140839dd70c1a43671eb4a08b007695c2`.
- Published additive baseline: `fa6a397c4cbdab0a3bed17cdd113fdbafab59c9d`.
- Vehicle workshop/energy gameplay revision:
  `007b9b61a9f32a5fa22220a01e7fe563e04f2514`.
- Vehicle-light crafting hotfix:
  `f0ea37616cef193ffdb418ef9aa1722e7075d731`.
- Visual/UI/audio backport merge:
  `173167db5f6cfe1cd58a1f1dbfdf6d95896268b7`.
- Faucet Auto Drink integration:
  `3bb86c8e26d10` (donor `f44f1b1686cf093eef96f3b03b05a115fd991e4f`).
- Modern UltiCa layering compatibility:
  `a30276d113421f109ae94ccb0112642df3068fba`.
- Legacy UltiCa overlay/shadow correction:
  `29d30480830b52da0e33f431d1f74b191f6be673`.
- Reviewed UltiCa high-resolution terrain pilot:
  donor `3d528d7da570a725087ddb7c6cb6e2f915254727`.
- Stable H3 EOC integration revision:
  `eca58dd933f2bb4417c6ad9cf1b47485abd89138`.
- Follower-overlay and shadow-blink crash fix:
  `29d30480830b5`.
- This is **not** a wholesale upgrade to 0.H, 0.I, or current experimental.
  It is basic 0.G plus selected later mechanics and content.
- Existing 0.G items, monsters, recipes, spawn tables, vehicle parts, and
  balance remain the foundation. The backport was gated against unintended
  deletion or replacement of baseline content.

Spoiler-heavy lists are collapsed below. Normal sections explain mechanics
without revealing locations or rare loot pools.

## Followers and camp work

- Followers now actually fall asleep when tired instead of repeatedly lying
  down without recovering. Non-following NPCs no longer erase their fatigue.
- NPC body temperature and wetness update while active and reconcile after an
  unloaded NPC returns, so weather and shelter matter consistently. Unloaded
  exposure uses the conditions at load time because historical per-NPC weather
  is not stored by 0.G.
- Camp water is ingested into the NPC stomach instead of instantly resetting
  thirst, preserving the normal digestion model.
- Camp residents can be assigned mopping from the existing job-priority menu;
  they fetch either legacy mop item from loot storage before using the existing
  mopping-zone workflow.
- NPC automatic sorting ignores player-personal source and destination zones.
  Shared camp and vehicle zones continue to work normally.
- Focused Catch coverage exercises sleep, elapsed environmental updates,
  camp-water stomach capacity, mop fetching, and static/custom/vehicle sorting
  with personal-zone overlap.
- Followers in dangerous cold equip warm clothing from their inventory or
  permitted nearby ground and vehicle storage, then seek nearby indoor shelter.
- Hungry and thirsty followers can use permitted food and clean water from the
  ground or unlocked owned vehicle cargo. Ownership, pickup rules, personal
  zones, and no-NPC-pickup zones are respected. With the existing **Allow
  pickup** follower rule enabled, unowned ground supplies are intentionally
  eligible; disable it or use a protected zone to reserve dropped supplies.
- Seriously starving followers may forage nearby edible wild plants after
  camp, carried, ground, and cargo food are exhausted. Farms and protected
  zones are never foraged automatically.
- The normal crafting-menu follower orders, camp crafting UI, worker larder,
  vitamins, medicine/mutagen storage, follower-rules window, and bulk job
  priority controls were already present and remain unchanged.

These local survival actions are adapted to the 0.G needs cascade. The modern
global behavior tree and mission scheduler are not included.
- Followers start first aid only when safe.  A separate follower rule controls
  whether they spend their supplies on allies, and interrupted work resumes
  after treatment.
- Followers safely treat data-defined nutrient deficiencies with non-addictive
  food or medicine.  Treatment is throttled, never starts in combat, and stops
  after the deficiency clears.
- Very unpleasant or nausea-triggering food is avoided when alternatives
  exist, but remains available when the follower would otherwise starve.
- Unarmed followers no longer overvalue empty hands when choosing from carried
  weapons.  Offered non-guns also avoid bogus infinite-ammo diagnostics;
  ranged/melee coefficients and silent-weapon rules remain unchanged.
- Camp workers keep their current job through ordinary hunger, tiredness and
  minor wounds. Serious bleeding, infection, severe injury or starvation may
  interrupt the job, which is resumed after the need is handled.
- Camp assignment survives temporary follow and guard orders. A follower can
  be told to return to camp duties; displaced workers head for their camp and
  spend downtime inside its exact footprint. An unreachable route takes the
  worker off duty instead of retrying pathfinding every turn.
- Camp crafting recognizes recipes from physical books and powered e-readers
  in storage, offers only on-duty workers present at that camp, and rejects
  local or radio liquid crafts before work starts when the target camp has no
  compatible zoned liquid fixture. Existing fixtures containing the same liquid
  can be reused.
- The legacy sorter assigns move-loot only when unsorted items have a valid
  destination, preventing empty sorting work from blocking other camp jobs.
  The later walking sorter and activity actor framework are not imported.
- Loading old follower rules no longer lets a preceding rule value leak into
  missing override fields.

## Visuals, sound, fonts, and interface

### Current UltiCa and SurveyorsMap

- **UltimateCataclysm (UltiCa)** and **SurveyorsMap** are updated from the
  official tileset project's composed `2026-08-23` release, commit
  `1f1988c5e144473f894fcb1e2914af51fd08b7af`.
- Updating a modern tileset normally drops sprites for identifiers that were
  retired after 0.G. This fork adds compatibility sheets instead: UltiCa
  contains 12,184 current-release IDs plus 388 retained 0.G-only IDs;
  SurveyorsMap contains 3,037 current-release IDs plus 65 retained 0.G-only
  IDs. Existing 0.G visual coverage is therefore not discarded by the update.
- The exact release, counts, and compatibility images are recorded in a
  machine-readable `BACKPORT_MANIFEST.json` inside each tileset.
- Legacy sprite numbers are rebased to their appended compatibility sheets,
  including cross-sheet dependencies. This prevents old hair and equipment
  overlays from sampling opaque modern sprites and drawing a gray square behind
  followers.
- The 0.G tile loader now accepts the modern UltiCa layering schema used by
  that release: flag-array contexts, omitted default sprites, and appended
  sprite suffixes. This fixes the load-time `Expected a string` error without
  replacing or removing any 0.G tile data.
- This is exact release/legacy-ID preservation, not a dishonest claim that
  every possible mod or game entity has bespoke artwork. Missing sprites still
  use the normal tileset fallback.

### UltiCa high-resolution common-terrain pilot

- Nine reviewed 64x64 source sprites improve common summer grass, pavement,
  and the yellow pavement marker while the map keeps its 32x32 logical tile
  footprint through `pixelscale: 0.5`.
- Fifteen pavement connectivity sprites are exact 2x nearest-neighbor copies,
  preserving corners, T-junctions, edges, ends, and isolated pavement.
- The source images, prompts, hashes, pinned dependencies, builder, validator,
  and review images are included. The generated atlas is fail-closed and
  byte-idempotent.

### Depth, visibility, and animation

- Tall walls and other high sprites can become translucent or retract near the
  character instead of hiding important tiles. The new **Handle occlusion by
  high sprites** option supports Off, On, and Auto modes; transparency and
  retraction can be enabled independently. A keybinding can cycle the mode.
- Experimental 3D field of view now draws visible lower Z-levels with distance
  fog. Creatures standing above can cast a shadow onto the lower level, making
  vertical threats easier to read.
- Isometric tilesets now participate in the same bounded multi-Z drawing. Each
  isometric tileset can declare its own vertical pixel spacing
  (`zlevel_height`; 10 for SmashButton_iso and 96 for Ultica_iso), so lower
  floors, fog, vehicles, fields, and creature indicators remain aligned rather
  than collapsing onto one plane. The separation and fog are scaled together
  when zoom changes. Legacy isometric tilesets without a positive
  `zlevel_height` log a warning and retain safe single-Z drawing. The draw floor
  is clamped to the supported overmap depth when a large 3D range is selected.
- Ledges now provide coverage in the player's cross-Z visibility cache. Player
  stance and furniture at the target affect that visual occlusion, while the
  existing 0.G creature detection and stealth formulas remain unchanged. Open
  or geometrically irrelevant ledges do not invent cover. Existing 0.G
  `Z_TRANSPARENT` ramps remain open between floors, and out-of-map remembered
  tiles are treated as closed rather than indexing outside the visibility
  cache. Pooled remote-camera visibility skips this post-pass because applying
  one camera's ledge geometry would erase sight contributed by another camera.
- **Look Up** and **Look Down** work even when experimental 3D field of view is
  disabled. Moving the look cursor between floors rebuilds the relevant floor
  and visibility caches without enabling through-floor vision during normal
  play.
- The lower-level visibility cache is recalculated per Z-level, preventing a
  visible upper tile from incorrectly exposing an unseen lower tile.
- Running and smashing have visible tile animations. Their drawing is handled
  asynchronously so the animation does not add the old blocking pause to each
  action.
- Visible monster-on-monster melee attacks flash the actual target, using the
  same hit feedback already used when the player strikes a monster.
- Fields and weather can select weighted sprite variants. Rain tiles can vary
  and animate when the selected tileset supplies those sprites.
- Creature-shadow blinking uses the existing 0.G timing constant. This fixes a
  crash caused by the backport requesting the later, unavailable `BLINK_SPEED`
  option during normal map input.

### Character appearance and UI themes

- In the character-information screen, **Shift+W** can make one worn armor
  item use the sprite of another armor item or restore its default appearance.
  This only changes presentation; protection, encumbrance, pockets, and item
  identity are unchanged.
- Eight optional color themes are included: Abyss, Blood Moon, Empyrium,
  Oxygen, Shogun, Spark, Sun, and Vector.
- The data-driven **Structured Sidebar** and its configurable widgets were
  already present in this 0.G foundation and remain available. No duplicate or
  incompatible sidebar implementation was installed.

### Fonts and sound hooks

- Windows builds declare PerMonitorV2 awareness and scale runtime fonts for the
  monitor currently containing the game window. Moving between mixed-DPI
  monitors rebuilds the fonts and layout without changing saved font options.
- Windowed mode keeps a complete 80x24 terminal inside the usable work area by
  fitting DPI-scaled font metrics before applying the minimum window size.
- JetBrains Mono 2.304 is bundled under the SIL Open Font License and is now
  the first-choice sidebar, map, and overmap font. Terminus and Unifont remain
  fallbacks for glyph coverage.
- Blended text is enabled for new configurations. **Font hinting** can be set
  to Normal, Light, Monochrome, or None; restart after changing it. Existing
  independent sidebar, map, and overmap font-size controls remain available.
- Soundpacks can define firearm sounds by exact weapon, ammunition caliber,
  and suppressed state, and melee sounds by exact weapon. Packs without those
  entries continue through the normal generic fallback rather than becoming
  silent; the older 0.G suppressed-weapon event used by packs such as Otopack
  is also retained.
- NPC footsteps now use the NPC's actual position, terrain, direction, and
  footwear state instead of accidentally sampling the player's tile.

### Inventory, crafting, and information QoL

- Advanced Inventory Manager adds **amount**, **barter value per volume**, and
  **barter value per weight** sorting.
- Capacity-limited **Move All** checks volume, pocket limits, and character
  carry weight, warns about the active limit, and tries smaller items first. The
  donor's unrelated bucket and container behavior changes are not included.
- Classic pickup (`g`) and drop (`D`) selectors can sort stacks within their
  existing categories by total weight or total volume with **Ctrl+S**.
- Right Arrow and Numpad 6 with NumLock off confirm numeric quantity input when
  the cursor is at the end; ordinary text editing keeps its normal behavior.
- Recipe details now show the exact **minor failure chance** for this fork's
  unchanged 0.G crafting roll. This is information only: success, minor
  failure, catastrophic failure, skill, proficiency, and component behavior
  are not rebalanced.
- Advanced Inventory Manager can open and transfer between several containers.
  The other pane's container is highlighted, nested containers are handled,
  and **X** leaves a container for its parent location. Missing/stale saved
  containers fall back to a usable pane, and transfer limits come from the
  selected container rather than the tile below it.
- **Ctrl+B** opens a direct Insert menu. Items that do not fit remain visible but
  disabled, with the actual pocket, capacity, watertightness, spill, or nesting
  failure reason shown instead of silently disappearing from the list.
- The washing selector shows water, cleanser, and estimated time before work
  begins.
- Item searches support `v:<body part>`: `v:hands` finds gloves and `v:eyes`
  finds eyewear. Press Up while editing an AIM/inventory filter to recall the
  shared item-filter history.
- Several books can be selected and scanned into an e-reader in one operation.
  Duplicate copies are scanned once; the activity reliably finishes every
  selected book even for a fast character. Battery use follows persisted page
  progress, so the displayed charge cost is independent of character speed,
  wall-clock alignment, or saving mid-scan. In-progress saves using the former
  single-book activity format remain readable.
- Scenario, profession, and overmap information can show which mod supplied
  the entry. Rural terrain outside cities is covered as well.
- Data authors can use snippet tags in item and variant descriptions. The
  chosen text is expanded when the item is created and retained afterward;
  this backport does not bulk-import later items merely to demonstrate it.
- 108 compatible net-new 0.H ASCII inspection-art IDs are added for ammunition,
  welding consumables, grenades, nails, and vehicle batteries. They provide
  124 direct bindings to existing 0.G items; exact IDs, source files, bindings,
  shared-art mappings, and exclusions are recorded in
  `doc/backports/H5-ASCII-MANIFEST.tsv`.
- Full H5 provenance, compatibility adaptations, exclusions, and validation
  boundaries are in `H5_INTERFACE_QOL_BACKPORT_REPORT.md`.

### Deliberate visual exclusions

- The 2026 colored-lighting PR chain is not included. Its first required PR
  depends on the post-0.G row-bucketed renderer, typed map coordinates, newer
  lightmap data, and later vehicle-part factories; the first bounded port
  attempt produced ten source conflicts before the mandatory follow-ups.
  Transplanting it safely would be a renderer/lightmap rewrite, not a small
  additive backport.
- Illustrated loading screens and loading hints are not included. Their donor
  chain is built on the later ImGui loading UI, while 0.G uses a curses/uilist
  loading path. No decorative mock was substituted for the missing engine
  support.
- The later map-memory refresh PR is not transplanted: it targets a newer
  multi-decoration memory cache absent from 0.G. This branch's 0.G single-slot
  memory path already redraws terrain before furniture, traps, and vehicles.
- Dropping items over ledges is not included. PR #65125 changes gameplay and
  target damage handling rather than being required for the multi-Z visual and
  visibility fixes, so it remains a separate optional backport.
- Full provenance, attempt counts, and validation boundaries are in
  `doc/VISUAL_UI_BACKPORT_REPORT.md`.

### Visual/UI regression suite

- Every bundled visual, animation, UI-theme, weather, sound, and NPC-footstep
  donor PR has its own named regression case (16 of 16 shipped donors).
- Pure C++ tests exercise occlusion calculations, lower-Z draw depth, weighted
  field variants, armor sprite overrides, and firearm/melee sound fallback
  behavior. Additional executable tests validate the tileset compatibility
  merger, packaged tiles, themes, font/license, and Structured Sidebar graph.
- The Python suite contains 25 passing tests, including direct, nested,
  cross-sheet, and exact follower-overlay sprite-rebasing cases. A compiled
  regression covers the normal-input blink threshold. The legacy 0.G renderer
  has no headless SDL or
  configured C++ coverage harness, so no invented project-wide C++ percentage
  is claimed. The final Windows Tiles+Sound build and packaged smoke test are
  pending the consolidated post-merge release run.
- Vehicle enchantment initialization no longer creates an actorless dialogue
  during prototype finalization, so the C++ test runner can finish and report
  failures normally.

## EOC scripting, missions, and NPC gimmicks

This release adds a bounded set of later **Effect On Condition (EOC)** APIs to
the 0.G engine. These are primarily compatibility tools for richer missions,
NPC behavior, mutations, monsters, and mods. Existing 0.G content does not
silently change merely because the scripting hooks exist.

### Events and activities

- EOCs can subscribe to game events instead of relying only on periodic polling.
  New-game and load events are supported, and subscription caches reset safely
  when data is reloaded.
- JSON activities can run EOCs on each turn or when they finish. The activity
  actor and its context remain available to the effect. If an activity EOC
  cancels or replaces its activity, the old activity is not left in the resume
  backlog. If a completion EOC
  replaces its activity, the replacement starts normally instead of being
  finished immediately.
- Event EOCs can receive a useful second talker for wield, wear, melee, and
  ranged events. This lets an effect address the weapon or other event object
  rather than only the character.
- NPC and avatar character-death events run before irreversible cleanup. A
  deliberately written EOC can prevent either death attempt by restoring vital
  HP; normal deaths, corpses, and overmap NPC cleanup remain unchanged when no
  such effect fires.

### Conditions, variables, and branching

- EOCs have scoped context variables that propagate through nested effects
  without leaking into unrelated dialogues.
- JSON can define named stored conditions once and reuse them from multiple
  effects.
- A compact `if` effect supports `then`, optional `else`, effect arrays, and
  nested branches.
- Mutation activation/deactivation EOCs receive scoped context. Mutation
  transformations may opt into normal conflict, prerequisite, and cancellation
  rules; a failed safe transform restores its source and charges no moves.
  Legacy direct transformation remains the default for old JSON.
- JSON monster special attacks can use dialogue conditions in addition to all
  their existing 0.G requirements. A new condition never bypasses range,
  cooldown, target, or other legacy checks.

### Inventory and map selectors

- Inventory EOCs can process every matching carried item, one random match, one
  manually chosen match, or several manually chosen matches.
- Filters include item ID, category, material, flags, worn state, and wielded
  state. Each chosen item is exposed as an item talker with the original EOC
  context intact.
- Cancelling a selector or finding no match runs its false branch once in the
  original context; an invalid variable-backed mode reports the value and runs
  the same false branch once. It does not repeatedly fire for rejected items.
- Nested EOC activation preserves computer terminals and dialogue metadata, so
  existing 0.G computer EOCs continue opening their terminal dialogue.
- Map-aware conditions can test terrain and furniture flags.
- Map effects can spawn direct items or item groups, including contained items,
  on the active map or an off-bubble tinymap. Off-bubble changes are saved.
- Map item selectors support all, random, manual, and multi-select modes. Invalid
  selector modes and impossible container insertion fail closed rather than
  reporting success or losing items.
- `foreach` effects can iterate explicit string/variable arrays, flag/trait/
  vitamin registries, item groups, and monster groups. Each value is written
  to the selected scoped variable before the nested effect runs.
- EOCs can ask the player to select any map tile, a visible tile within a
  configured range, or an adjacent tile. Confirmed selections are stored as
  absolute map-square coordinates; cancellation leaves the target unchanged.
- `run_eocs` and `queue_eocs` can choose an EOC ID from a scoped variable while
  retaining fixed IDs, inline EOCs, and mixed arrays. Immediate `run_eocs`
  entries preserve array order; equal-time queued entries retain normal 0.G
  queue ordering.
- `u_add_trait` and `npc_add_trait` can select a named cosmetic mutation
  variant from a literal or scoped variable. Existing effects that omit it keep
  normal automatic variant selection.

### Post-review hardening

- Indirect EOC variables now detect cycles and excessive nesting on both reads
  and writes instead of recursing until a stack overflow.
- Named stored conditions detect direct and mutual recursion and fail closed
  with one diagnostic instead of overflowing the stack.
- Terrain/furniture flag checks default to the alpha talker's position when
  `loc` is omitted. Off-bubble checks read existing saved submaps, return false
  for ungenerated locations, and never generate world content from a condition.
  An explicitly configured but empty/invalid `loc` fails closed instead of
  silently targeting the alpha talker's tile.
- Container item spawning keeps the container and every item already inserted
  when a later insertion fails; the failed insertion is reported.
- Monster flag checks recognize both the monster type's JSON flags and
  effect-granted flags. Routine checks no longer spam the debug log.
- Map-item selectors reject inventory-only `worn_only` and `wielded_only`
  filters while loading JSON instead of silently matching nothing.
- Event EOCs skip stale character IDs, continue to later resolvable event
  participants, and never substitute the avatar for a missing NPC. Event caches
  retain live EOC IDs and invalidate when EOC data reloads.
- `required_event` is rejected on non-EVENT EOCs. Activity completion and
  per-turn EOC references are checked for existence and ACTIVATION type during
  data consistency checks.
- Monster leap and spell EOC conditions are evaluated only after their normal
  legacy requirements, matching melee attacks without changing those gates.
- Processed mutation EOCs require a positive mutation interval and run on that
  interval; zero-cooldown mutations no longer execute them every turn.
- Resource exhaustion that forcibly deactivates a powered mutation stops its
  processing immediately; no processed EOC runs after that deactivation.
- Safe mutation transformations preflight rejected/intermediate-only targets
  before mutation side effects, so failed transforms cannot destroy or displace
  worn gear.
- Wield and wear event EOCs run after caller-side item bookkeeping. An EOC may
  remove the event item without leaving a stale item location or worn iterator.
- Wearing a wielded item emits the normal wear event with the worn item talker.
  It also keeps 0.G's empty-wield-state event for achievement/stat compatibility,
  without incorrectly attaching the worn item as that event's beta talker.
- Regression coverage includes cyclic variables, stale event participants,
  off-bubble map conditions, JSON monster flags, empty/partially-filled
  containers, mutation processing cadence, invalid JSON combinations, and
  computer/non-creature beta talker preservation.

### What this checkpoint deliberately stops before

- No missions, locations, monsters, spawn rates, combat balance, mutation
  progression, or item availability were replaced to demonstrate these APIs.
- Complete upstream provenance and the exact compatibility boundary are in
  `H3_EOC_BACKPORT_REPORT.md`.

## Additive anti-grind and preparation QoL

- Furniture marked for simple, tool-free deconstruction now takes 10 seconds
  instead of 10 minutes. The ordinary full-time deconstruction action is not
  offered for the same furniture, preventing a duplicate slow menu entry.
- Heavy vehicles are no longer rejected by a fixed mass cutoff when pushed or
  pulled by hand. Wheel count, terrain movement cost, traction, vehicle mass,
  and arm strength now determine whether the move succeeds; moving one still
  consumes proportionate time and stamina.
- The Safe Place scenario no longer selects the exposed freshwater research
  station. The previously hostile cabin and farm variants instead start with
  a generic human corpse, preserving atmosphere without an immediate
  zombie beside a scenario advertised as safe.
- Body weight has a smaller, linear effect on effective lifestyle: penalties
  begin above BMI 30 or below BMI 18.5 and remain bounded at -200. Positive
  daily-health effects keep the normal +200 cap instead of being discarded by
  the older BMI-specific maximum.
- Moving many compatible items in one operation no longer repeats the full
  hand-encumbrance and container-access overhead for every item. The first
  insert, unload, drop, or pet-stash pays the normal cost; consecutive items
  from the same stack or container pay their volume-based handling cost.
- Progress toward the next practical skill level now gives a proportional
  benefit in selected soft checks: crafting and repair rolls, melee hit/crit/
  attack speed, firearm aim and attack speed, vehicle security/hotwiring, and
  item stow speed. Recipe, construction, installation, quest, and other hard
  requirements still use completed integer levels exactly as in 0.G.

## Vehicles and the V-Jill road-home path

### Lockable and pickable vehicle doors

- Added the **door lock set** item and installable **door lock** vehicle part.
- Its recipe is automatically learned at Mechanics 4 and Traps 2, takes about
  25 minutes, and uses fine hammering, fine screwdriving, and fine metal sawing.
- Installing a lock requires Mechanics 2, Traps 1, screwdriving 1, and drilling
  2. Locks have separate removal and soldering-based repair requirements.
- Locks work with the normal vehicle door family, including standard and
  heavy-duty doors, transparent and opaque doors, hatches, trunk doors,
  shutters, and sliding/multisquare doors where those parts are marked
  lockable.
- A closed door can be locked or unlocked from inside the vehicle. An open
  door cannot be locked.
- A working lock blocks normal opening from outside. A character outside can
  examine the lock and use the standard lockpicking activity.
- Multisquare doors synchronize the whole connected line. Fake vehicle-part
  representations also synchronize their open and locked state.
- Door motors expose individual Lock/Unlock operations. “Open all doors” first
  unlocks the relevant doors and then opens them.
- Locked state is written to and restored from the save.
- NPC pathfinding understands whether opening or unlocking is permitted. New
  follower rules can make allies lock closed doors or avoid unlocking them.
- Monsters that merely know how to open doors cannot bypass a working lock in
  this fork. They can still smash a door, window, frame, or the lock itself.

### Furniture transport

- Vehicle cargo parts with furniture tie-down support can carry one adjacent
  furniture object, including practical appliances such as fridges.
- Furniture can be pushed directly onto a suitable loading vehicle and pulled
  back off it.
- The vehicle interaction menu has **Tie down or remove furniture**.
- The carried furniture contributes its mass and occupies the cargo space;
  ordinary cargo cannot share the tied-down slot.
- Strength/lifting assistance is checked. A **nose plate** provides tie-down
  and lift assistance and is used by the new **Hand Truck** vehicle.
- Vehicle/furniture dragging can cross z-levels where the move is valid.
- Unloading validates floor, trap, creature, furniture, and vehicle occupancy
  before placing the furniture, preventing silent loss or invalid placement.

### Driving, power, tools, and vehicle UI

- Added three craftable modular vehicle stations: **kitchen station**,
  **workshop station**, and the combined **mounted fabrication bay**. The
  fabrication bay is also a 1.2x workbench. These are new parts; the old 0.G
  FOODCO, kitchen, chemistry, and welding rigs remain available and unchanged.
- Compatible real tools can be attached from character inventory and detached
  again from the vehicle interaction menu. Their inventory letters, condition,
  and other item state survive normal vehicle save/load and rack/unrack. Their
  mass counts toward vehicle mass, they drop if their station or a temporary
  vehicle disappears, and exported/imported vehicle prototypes retain the full
  attached item state rather than only its type.
- Mounted tools use the vehicle as their utility source: electrical tools draw
  from batteries across the connected vehicle-power graph, propane tools draw
  from compatible vehicle tanks, and kitchen/fabrication faucets expose clean
  water and other usable liquids from onboard tanks. Repair kits, welders, and
  soldering tools remain usable for their normal repair activities.
- Mounted-tool interaction preserves useful hotkeys. Temporary pseudo-tools
  are guarded from starting pointer-retaining actions that require a handheld
  tool; a mounted repair kit can safely hacksaw, while prying still requires a
  handheld implement. Stateful towel/circular-saw transformations are not
  offered as attachments because 0.G cannot safely persist their transformed
  pseudo-item state.
- A smart engine controller can now operate a parked vehicle with one enabled
  combustion engine as a generator: it uses the real starter/immobilizer/fuel
  checks, starts below the configured battery threshold, and stops above it.
  A new option controls whether manually stopping the engine also disables the
  smart controller, keeps it enabled, or asks each time.
- The fixed-map **active backup generator** can now be converted in place
  through its examine action into a removable grid appliance. The normal
  appliance Remove action recovers its portable item; it can also be crafted,
  disassembled, carried, and placed through the appliance menu.
- The appliance contains its own 10 L watertight fuel tank, burns diesel-family
  fuel, and supplies up to **7.3 kW** to its connected grid when enabled.
- Building one uses a 7.5 kW generator, inline-four diesel engine, vehicle
  frame, large jerrycan, and heavy vehicle-wrench tooling. Disassembly returns
  the same four major components and requires wrenching 2.
- The original 0.G furniture's bash drops and deconstruction yields remain
  unchanged. This backport adds the portable conversion path; it does not
  obsolete the map furniture or rewrite generator spawn locations.
- Mounted turret items receive normal active-item processing while installed,
  allowing heat to dissipate instead of becoming permanently stuck hot.
- Vehicle loading no longer spills overflow onto the ground when cargo becomes
  full mid-transfer: remaining items stay in hand/inventory when possible.
- A broken part on a carried/racked vehicle must be unracked before replacement,
  preventing edits through the carrier. Dynamic tow and power-cable setup now
  validates both endpoints before installing either end, avoiding half-created
  links and reporting the actual mount failure.
- Atomic coffeepots, charcoal/gasoline/oil cookers, chemistry sets, coffee
  makers, hotplates, and wire-draw machines can participate in the established
  remote-use vehicle crafting path where their normal item definitions allow it.
- Added a second overmap routing choice: **efficient route** follows practical
  roads, while **direct route** asks autodrive for a straighter path.
- Added a **directed floodlight** appliance. Its facing can be chosen instead
  of illuminating equally in every direction.
- Added craftable/installable **small integrated heater** and **small
  integrated cooler** parts. Existing generated vehicles are not silently
  altered to contain them.
- Vehicle battery chargers now display their electrical draw.
- Vehicle battery charge has its own sidebar widget instead of being folded
  into the generic fuel display.
- Appliance cable connections can be shown on the map.
- Vehicle zones can be enabled or disabled quickly from the zone manager.
- The install UI explains why a selected part cannot be installed.
- Parts with visual variants have a shape chooser during installation.
- The additive fork's existing multiple-magazine-well vehicle plumbing is
  retained. This workshop release does not replace it with the much newer
  current-experimental turret subsystem.
- Vehicle-part attachment locations are data-defined (structure, armor, roof,
  axle, controls, cargo, fuel source, battery mount, windshield, ceiling,
  underbody, and related slots), enabling safer later content backports.
- Added infrastructure for vehicle enchantments/effects. Effects are refreshed
  after spawning, damage, and rack/unrack operations; broken, unavailable, or
  carried parts do not incorrectly grant them.
- The debug Vehicle menu can export a vehicle as a reusable JSON prototype.
  Export validates the result first and avoids leaving a malformed partial
  file on failure.

### Vehicle lighting and crafting hotfix

- Fixed the false **“You can't see to craft!”** result that could appear while
  the character's tile was visibly bright under enabled vehicle aisle lights.
- The cause was a mixed 0.G/0.H position-sentinel convention in the NPC
  crafting backport: the sidebar checked the character's real tile, while the
  crafting gate could query an invalid off-map coordinate.
- Player crafting, follower crafting, and explicit remote crafting positions
  now use the calculated lightmap consistently. Turning the vehicle light off
  still blocks ordinary crafting at night, and a distant dark work tile remains
  dark even when the character stands in light.
- This is a compatibility fix only. It does not increase lamp brightness,
  reduce power draw, change recipes, or grant dark crafting.

### Auto Drink from onboard tanks and liquid-container safety

- A vehicle-bound **Auto Drink** zone placed on a working faucet can now draw
  suitable drinks from fluid tanks anywhere on that vehicle. This is an
  adaptation of the later upstream faucet/tank Auto Drink feature for the 0.G
  activity and item-location APIs.
- The normal Auto Drink filters still apply: the liquid must be safe and
  consumable, sufficiently thirst-quenching, acceptable to the character, and
  owned or available to take. Auto Eat zones do not gain access to vehicle
  tanks, and a zone on an ordinary cargo tile does not act as a faucet.
- Existing vehicle Auto Drink zones need no save migration. Put or keep the
  zone on the tile containing the kitchen/fabrication faucet and keep a usable
  drink such as clean water in any available onboard fluid tank.
- Fixed `item_contents::only_item called with 0 items contained` while the
  crafting UI evaluates containers for a liquid result. A powered empty vessel
  such as a multi cooker can have a battery in its magazine well but no liquid
  in its container pocket; it is now correctly treated as an empty liquid
  container during sorting. No item or save repair is required.

### New core vehicle content and acquisition paths

- Engines and generators:
  - large 1-cylinder 200 cc diesel engine;
  - medium 1-cylinder 150 cc gasoline engine;
  - 0.5 L inline-1 diesel engine;
  - complete portable diesel generator vehicle.
- Refrigeration:
  - food truck fridge (250 L);
  - chest minifreezer (99 L);
  - food truck freezer (250 L);
  - refrigerated tank (100 L).
- Cargo and protection:
  - metal tray;
  - sedan trunk;
  - industrial trash can / integrated trash-can cargo part;
  - medium pressurized gas tank;
  - military composite ram;
  - reinforced security camera;
  - advanced Stirling radioisotope generator vehicle part.
- Small vehicles and movement:
  - Hand Truck and its nose plate;
  - medium casters;
  - reinforced yoke and harness for large draft animals;
  - skateboard, deck, trucks, wheels, and folded form.
- Crafting or other acquisition recipes were added for the imported
  refrigeration, camera, trash-can, caster, harness, skateboard, engine, and
  related parts where the part is intended to be obtainable.

## Followers, NPCs, and base camps

### NPC crafting and practical follower work

- The normal crafting menu can be opened for a friendly NPC and used to order
  an item they can actually make.
- The crafting screen can switch the active crafter between the player and
  eligible allies, recalculating skills, knowledge, proficiencies, recipes,
  speed, and component access for that crafter.
- NPCs cannot claim an already active/in-progress craft as if it were a loose
  component.
- NPCs can read books stored on e-readers/electronic devices.
- NPCs can reload magazines in their own inventory.
- NPC crafting can finish liquid products and prompt/place them correctly.
- Camp liquid crafts can place results into suitable containers in a
  `LIQUIDCONT` zone; corresponding camp liquid recipes are available.
- Camp crafting jobs use the normal crafting interface rather than the old
  narrow recipe selector.
- Items reserved by a camp worker are visibly marked **in use**.
- All job priorities for a companion can be assigned in one operation.

### Dedicated follower-rules screen

The new follower-rules window can reset settings, copy all or selected rule
groups between followers, edit the pickup list, select engagement and aiming
policies, and configure CBM recharge/reserve thresholds. Its individual
toggles are:

1. Ranged weapons.
2. Grenades.
3. Silent weapons only.
4. Avoid friendly fire.
5. Pick up items.
6. Bash obstacles.
7. Sleep when tired.
8. Report needs.
9. Pulp corpses.
10. Close doors.
11. Lock doors.
12. Stay close.
13. Follow at two tiles rather than four.
14. Avoid opening doors.
15. Avoid unlocking doors.
16. Hold the line.
17. Ignore noises.
18. Forbid autonomous engagement.

Engagement choices include no engagement, nearby/weak/attacked/all enemies,
free fire without moving, and no movement. Aiming choices range from quick fire
to strictly precise fire.

### Camps, food, storage, and communications

- Camp larders track nutrition rather than only a crude food number.
- The player can eat from the larder. Workers assigned to jobs consume from it
  when NPC needs are enabled and report an empty larder.
- Camp storage accepts medicines and mutagens in addition to ordinary food and
  supplies.
- Camp liquid storage and worker-crafted liquids use designated compatible
  containers.
- Camp radio handling was corrected and expanded: direct two-way-radio range,
  elevation, one-tower relay, and two-tower relay are considered. The follower
  screen tells you whether the NPC is nearby, in radio range, at a camp, on a
  mission, or unreachable.
- NPC selection screens for chat, guard, and follow show locations.
- Dialogue can estimate an NPC's personality.
- Static NPC settlements receive faction-camp identity and food storage rather
  than existing only as disconnected map locations.

### Brick camp expansion variants

Brick construction routes were added for the following modular camp families:

- Canteen: central kitchen, pantry, smoking area, dining hall, and brewery
  stages.
- Garage: initial bays, internal wall, long-vehicle extensions, and hangar-size
  extensions.
- Livestock: coops, feed/tool shacks, stables, and additional stalls.
- Saltworks: salt pan, storage shack, and brewery.
- Storehouse: both initial wings, corners, entrances, central floor, and the
  extended twelve-section storehouse path.
- Workshop: smithy, kilns, pottery, glassblowing, tannery, storage/work areas,
  and covered heavy-work areas.

### Character and follower transfer

- Debug Import/Export commands can export the protagonist or a selected
  follower and import a follower.
- Windows paths and non-ASCII character data are handled safely.
- A failed protagonist export restores the active avatar instead of leaving
  the game in a switched/broken character state.
- The Tacoma Ranch doctor can install or remove CBMs for an allied NPC, with
  the patient selected through the medical interaction flow.

<details>
<summary><strong>SPOILER — locations now treated as static faction camps</strong></summary>

Core locations:

- Refugee Center;
- Exodii base;
- giant bee hive;
- Cabin Lapin;
- island-prison Holdouts;
- New England Church Retreat;
- Tacoma Commune;
- Hub 01;
- Cody & Jay / isolated artisans;
- Isherwood cabin, stables, outcropping, and farms;
- wasteland-scavenger bunker merchant, occupied chemical lab, occupied scrap
  yard, and occupied lumbermill.

When their parent mods are enabled:

- Aftershock: PrepNet orchard;
- Magiclysm: Forge of Wonders, Healer's Respite, and the Old Wizard's lake
  retreat.

</details>

## Equipment repair

- Thermoplastic resin is now accepted by the plastic/metal repair actions on
  the soldering iron, firearm repair kit, gunsmith repair kit, and extended
  multitool.
- This makes the following previously frustrating thermoplastic equipment
  repairable with **thermoplastic resin chunks** and an appropriate powered
  tool: riot armor suit, riot chest guard, riot arm guards, riot leg guards,
  riot helmet with visor up, and riot helmet with visor down.
- The change is narrowly additive: it enables the existing repair path without
  replacing riot-armor stats or recipes.

## Restored CBM salvage loop

<details>
<summary><strong>MAJOR SPOILER — which corpses can yield CBMs</strong></summary>

Careful dissection can recover damaged CBMs from:

- scientist zombies;
- feral scientists, including the scalpel variant;
- zombie technicians;
- soldier and black-ops soldier zombies;
- bio-operators;
- elite bio-operators;
- the substation miniboss.

The scientific pool emphasizes tools, memory/vision, blood analysis,
radiation, and medical systems. The technician pool includes torsion-ratchet,
gasoline fuel-cell, memory, sunglasses, heatsink, watch, Faraday, weight, and
soporific CBMs. Military and bio-operator pools cover internal armor,
targeting, cloaking, power, weapons, mobility, senses, metabolism, hacking,
nanobots, UPS integration, and advanced combat systems. Elite bio-operators
draw separately from offensive, defensive, and utility pools.

Skill affects the result, with up to five recovered CBMs. Salvage is dirty,
nonsterile, unpackaged, and marked with the salvaged-bionic fault; Power
Storage has a separate chance to appear. This restores risk and preparation to
the old “dissect rare cyborg enemy for hardware” loop rather than handing out
ready-to-install implants.

</details>

## Classic exploration and practical solar power

- Standard solar panels produce 90 W while retaining seasonal, cloud, time-of-day,
  and obstruction effects; derived panels keep their proportional tiers.
- Compact ASRG power returns to the irradiator. Ordinary outposts and shipwrecks
  retain fuel-burning backup generators.
- Ordinary LMOEs are more discoverable and guarantee one hidden survival-firearm
  cache per underground layout. Occupied and quest LMOEs are unchanged.
- Classic, central, and ice labs are more likely but remain unique map specials.
  The autodoc finale guarantees one common CBM roll; existing maps are untouched.

## Dangerous military salvage sites

- Military field and road extras remain rare but are discoverable again.
- Military roadblocks can field damaged, partly loaded M249, M240, or M2 CROWS
  turrets; military outposts may replace two perimeter lights with damaged M249s.
- Police roadblocks still use riot-control platforms.

## Optional mod: Useful Helicopters Experimental

This is installed but **not enabled by default**. Enabling the mod adds:

- optional Piloting chargen hobby;
- optional Airframe & Powerplant Mechanic chargen hobby;
- removable/serviceable 15 m heavy-duty military rotor;
- 8 m small civilian rotor;
- 16 m Blackhawk rotor;
- 11 m Osprey rotor.

Only those implemented pieces are claimed. The donor README's proposed turbine
fuel changes, Pilot Package CBM, and recipe-taught aviation proficiencies are
not present in this package.

## Small but important compatibility and reliability changes

- Old vehicle saves remain compatible when a part has no saved lock state,
  location mass, or enchantment/effect cache.
- Vehicle part mass is deserialized correctly on Windows.
- Door, fake-part, multisquare-door, and vehicle-effect state are refreshed
  rather than left stale after load or vehicle manipulation.
- Camp ownership and lookup use exact camp positions; multiple camps and
  migrated/overflow food stores are handled without silently using the wrong
  camp.
- Existing 0.G vehicles are not retrofitted with imported parts, and optional
  mods are not silently enabled.
- The fork includes a fail-closed data audit that compares core and bundled-mod
  data against exact 0.G and rejects unintended deletion, replacement,
  duplicate IDs, or accidental default-enabling of an optional mod.

## What this document intentionally does not contain

This file lists what is present and playable. H1/H2 implementation boundaries,
validation evidence, and deliberately dropped adaptations are recorded in
`H1_H2_BACKPORT_REPORT.md` so they cannot be mistaken for working content.
