# CDDA 0.G Additive — what this fork changes

A catalogue of every way this fork differs from vanilla Cataclysm: DDA 0.G "Gaiman".
It is grouped by what you touch in game, not by when the work landed.

## How to read this file

- `New` did not exist in 0.G. `Improved` existed and now behaves differently. `Fixed` was
  broken in 0.G and now works.
- A defect this fork introduced and corrected before shipping gets no entry, because no
  release ever had it. This file describes the distance from 0.G, not the path taken.
- Dated per-release notes, with the fork's own pull-request numbers, live in `CHANGELOG.md`.
- Upstream provenance, and what each transplant deliberately left behind, live in
  `BACKPORTS.md` and the linked backport reports.
- Spoiler lists are collapsed. Ordinary entries explain mechanics without revealing
  locations or rare loot pools.

## Vehicles and mobile bases

- `New` Three craftable modular stations: **kitchen station**, **workshop station**, and the
  combined **mounted fabrication bay**, which doubles as a 1.2x workbench. The 0.G FOODCO,
  kitchen, chemistry, and welding rigs remain available and unchanged.
- `New` Real tools attach to and detach from those stations. Inventory letters, condition,
  and other item state survive save/load and racking, and mass counts toward the vehicle.
- `New` Mounted tools draw on the vehicle: electrical tools from batteries across the
  connected power graph, propane tools from compatible tanks, and kitchen or fabrication
  faucets from onboard liquids. Repair kits, welders, and soldering tools work normally.
- `New` A **door lock set** item and installable **door lock** part. A closed door locks from
  inside; from outside a working lock blocks opening and invites the normal lockpicking
  activity. Multisquare doors synchronise, door motors expose Lock and Unlock, and locked
  state is saved. Door-opening monsters cannot bypass a lock, but can still smash it.
- `New` Follower rules can make allies lock closed doors or avoid unlocking them, and NPC
  pathfinding understands whether opening or unlocking is permitted.
- `New` Cargo parts with tie-down support carry one adjacent furniture object, including
  appliances such as fridges. Furniture pushes on and pulls off, contributes its mass,
  occupies the slot, and can be dragged across z-levels. Unloading validates the
  destination first. A **nose plate** grants tie-down and lift assistance.
- `New` A smart engine controller can run a parked vehicle with one enabled combustion
  engine as a generator, using the real starter, immobiliser, and fuel checks, starting
  below a configured battery threshold and stopping above it.
- `New` The fixed-map **active backup generator** converts in place into a removable grid
  appliance with its own 10 L fuel tank, supplying up to **7.3 kW**. It can be crafted,
  disassembled, carried, and placed. The original furniture's bash and deconstruct yields
  are unchanged.
- `New` A vehicle **Auto Drink** zone on a working faucet draws suitable drinks from fluid
  tanks anywhere on that vehicle. The normal Auto Drink filters still apply, and Auto Eat
  zones gain no tank access.
- `New` A **directed floodlight** whose facing can be chosen, plus craftable **small
  integrated heater** and **small integrated cooler** parts.
- `New` Overmap routing offers a second choice: **efficient route** follows practical roads,
  **direct route** asks autodrive for a straighter path.
- `New` Vehicle content: three small diesel and gasoline engines and a portable diesel
  generator; food-truck fridge and freezer, chest minifreezer, and refrigerated tank; metal
  tray, sedan trunk, integrated trash can, pressurised gas tank, composite ram, reinforced
  security camera, and Stirling radioisotope generator; Hand Truck, medium casters, draft
  harness, and skateboard. Recipes were added wherever a part is meant to be obtainable.
- `Improved` Vehicle interface: battery chargers show their draw, battery charge has its own
  sidebar widget, cable connections can be shown on the map, zones toggle from the zone
  manager, the install UI explains why a part is refused, and variant parts get a shape
  chooser during installation.
- `Improved` Remote vehicle crafting accepts atomic coffeepots, charcoal, gasoline and oil
  cookers, chemistry sets, coffee makers, hotplates, and wire-draw machines where their
  item definitions allow it.
- `Improved` Heavy vehicles pushed or pulled by hand are no longer refused by a fixed mass
  cutoff. Wheel count, terrain cost, traction, mass, and arm strength decide, and the move
  still costs proportionate time and stamina.
- `Fixed` Loading a vehicle no longer spills the overflow on the ground when cargo fills
  mid-transfer; remaining items stay in hand or inventory where possible.
- `Fixed` Mounted turret items receive normal active-item processing while installed, so
  heat dissipates instead of becoming permanently stuck.
- `Fixed` A broken part on a carried or racked vehicle must be unracked before replacement,
  and tow or power-cable setup validates both endpoints before installing either end.

## Followers, NPCs, and camps

- `New` Followers in dangerous cold equip warm clothing from their inventory or permitted
  nearby ground and vehicle storage, then seek indoor shelter.
- `New` Hungry and thirsty followers use permitted food and clean water from the ground or
  unlocked owned vehicle cargo, respecting ownership, pickup rules, personal zones, and
  no-NPC-pickup zones. Seriously starving followers may forage nearby wild plants; farms
  and protected zones are never foraged.
- `New` Followers start first aid only when it is safe. A follower rule controls whether
  they spend supplies on allies, and interrupted work resumes after treatment.
- `New` Followers treat data-defined nutrient deficiencies with non-addictive food or
  medicine. Treatment is throttled, never starts in combat, and stops once the deficiency
  clears.
- `New` The normal crafting menu opens for a friendly NPC, and the crafting screen switches
  the active crafter between the player and eligible allies, recalculating skills,
  knowledge, proficiencies, recipes, speed, and component access.
- `New` A dedicated follower-rules window resets settings, copies all or selected rule
  groups between followers, edits the pickup list, sets engagement and aiming policies, and
  configures CBM recharge and reserve thresholds, across eighteen individual toggles.
- `New` Camp larders track nutrition rather than a crude food number. The player can eat
  from the larder, assigned workers consume from it, and an empty larder is reported. Camp
  storage also accepts medicines and mutagens, and liquids use designated containers.
- `New` Camp crafting uses the normal crafting interface, recognises recipes from physical
  books and powered e-readers in storage, and offers only on-duty workers at that camp.
- `New` Camp residents can be assigned mopping from the job-priority menu, fetching either
  legacy mop from loot storage first.
- `New` Camp radio handling considers direct two-way range, elevation, and one- and
  two-tower relay. The follower screen reports whether an NPC is nearby, in radio range, at
  a camp, on a mission, or unreachable, and selection screens show locations.
- `New` Brick construction routes for six modular camp families: canteen, garage, livestock,
  saltworks, storehouse, and workshop.
- `New` Static NPC settlements gain faction-camp identity and food storage instead of
  existing only as disconnected map locations.
- `New` Debug Import and Export commands move the protagonist or a selected follower between
  saves, handling Windows paths and non-ASCII data. The Tacoma Ranch doctor can install or
  remove CBMs for an allied NPC.
- `Improved` Practical follower work: NPCs read books from e-readers, reload magazines in
  their own inventory, finish and place liquid crafts, and mark reserved camp items **in
  use**. Every job priority for a companion can be set in one operation.
- `Improved` Camp workers keep their job through ordinary hunger, tiredness, and minor
  wounds; serious bleeding, infection, injury, or starvation interrupts it and it resumes
  once. Camp assignment survives temporary follow and guard orders, and an unreachable
  route takes the worker off duty instead of retrying every turn.
- `Improved` NPC body temperature and wetness update while active and reconcile after an
  unloaded NPC returns, so weather and shelter matter consistently. Camp water is ingested
  into the stomach instead of instantly resetting thirst.
- `Fixed` Followers fall asleep when tired instead of repeatedly lying down without
  recovering, and non-following NPCs no longer erase their fatigue.
- `Fixed` Killing an NPC whose faction is already guaranteed hostile no longer applies the
  innocent-kill morale penalty merely because they had not yet switched to their active
  attitude. Attacking a genuinely neutral NPC is still murder. A dialogue crash when
  closing the final categorised talk topic is also gone.

<details>
<summary><strong>SPOILER — locations now treated as static faction camps</strong></summary>

Refugee Center; Exodii base; giant bee hive; Cabin Lapin; island-prison Holdouts; New
England Church Retreat; Tacoma Commune; Hub 01; Cody &amp; Jay and isolated artisans; the
Isherwood cabin, stables, outcropping, and farms; and the wasteland-scavenger bunker
merchant, occupied chemical lab, occupied scrap yard, and occupied lumbermill. With their
parent mods enabled: the Aftershock PrepNet orchard, and Magiclysm's Forge of Wonders,
Healer's Respite, and Old Wizard's lake retreat.

</details>

## Survival, crafting, and equipment

- `New` Bleeding, quick and full butchery, field dressing, skinning, quartering,
  dismembering, and dissecting retain fractional progress on the corpse. Interrupted work
  resumes after moving the corpse, changing to another valid tool, or reloading. Each
  method tracks progress independently and the butchery menu shows partial completion.
- `New` A ledge can be climbed down safely when the same one-level route is climbable upward
  or has strong nearby support such as a downspout, fence, ladder, braced wall, or vehicle.
  A multi-level descent is safe only when every level has support.
- `New` EMP-damaged electronics receive repairable faults instead of permanent breakage, and
  game-style EMP rules can use temporary reboots with a small failure chance.
- `New` Thermoplastic resin is accepted by the plastic and metal repair actions on the
  soldering iron, firearm repair kit, gunsmith repair kit, and extended multitool. This
  makes the riot armour suit, chest guard, arm and leg guards, and both helmet states
  repairable with **thermoplastic resin chunks** and a suitable powered tool.
- `New` Careful dissection can recover damaged CBMs from certain rare corpses again. Salvage
  is dirty, nonsterile, unpackaged, and carries the salvaged-bionic fault; skill affects the
  result, up to five recovered CBMs.
- `Improved` Furniture marked for simple, tool-free deconstruction takes 10 seconds instead
  of 10 minutes, and the duplicate slow menu entry is no longer offered.
- `Improved` Progress toward the next practical skill level gives a proportional benefit in
  soft checks: crafting and repair rolls, melee hit, crit and attack speed, firearm aim and
  attack speed, vehicle security and hotwiring, and item stow speed. Recipe, construction,
  installation, and quest requirements still use completed integer levels exactly as in 0.G.
- `Improved` Body weight has a smaller, linear effect on effective lifestyle. Penalties begin
  above BMI 30 or below BMI 18.5 and stay bounded at -200, while positive daily-health
  effects keep the normal +200 cap.
- `Improved` Moving many compatible items in one operation no longer repeats the full
  hand-encumbrance and container-access overhead for every item. The first move pays the
  normal cost; consecutive items from the same stack pay only their volume-based cost.
- `Improved` The Safe Place scenario no longer selects the exposed freshwater research
  station, and its previously hostile cabin and farm variants start with a generic human
  corpse rather than a zombie beside a scenario advertised as safe.

<details>
<summary><strong>MAJOR SPOILER — which corpses can yield CBMs</strong></summary>

Scientist zombies, feral scientists including the scalpel variant, zombie technicians,
soldier and black-ops soldier zombies, bio-operators, elite bio-operators, and the
substation miniboss. The scientific pool emphasises tools, memory and vision, blood
analysis, radiation, and medical systems. The technician pool covers torsion-ratchet,
gasoline fuel-cell, memory, sunglasses, heatsink, watch, Faraday, weight, and soporific
CBMs. Military and bio-operator pools cover internal armour, targeting, cloaking, power,
weapons, mobility, senses, metabolism, hacking, nanobots, UPS integration, and advanced
combat systems. Elite bio-operators draw separately from offensive, defensive, and utility
pools. Power Storage has its own separate chance to appear.

</details>

## Interface and quality of life

- `New` The Advanced Inventory Manager adds **amount**, **barter value per volume**, and
  **barter value per weight** sorting.
- `New` Capacity-limited **Move All** checks volume, pocket limits, and character carry
  weight, warns about the active limit, and tries smaller items first.
- `New` Classic pickup and drop selectors sort stacks within their existing categories by
  total weight or total volume with **Ctrl+S**.
- `New` The Advanced Inventory Manager opens and transfers between several containers. The
  other pane's container is highlighted, nested containers are handled, and **X** leaves a
  container for its parent. Transfer limits come from the selected container, not the tile.
- `New` **Ctrl+B** opens a direct Insert menu. Items that do not fit stay visible but
  disabled, showing the actual pocket, capacity, watertightness, spill, or nesting reason
  instead of silently vanishing from the list.
- `New` Item searches support `v:<body part>`, so `v:hands` finds gloves and `v:eyes` finds
  eyewear. Pressing Up while editing a filter recalls the shared item-filter history.
- `New` Several books can be selected and scanned into an e-reader in one operation.
  Duplicates are scanned once, and battery use follows persisted page progress rather than
  character speed or wall-clock alignment.
- `New` The washing selector shows water, cleanser, and estimated time before work begins.
- `New` Recipe details show the exact **minor failure chance** for the fork's unchanged 0.G
  crafting roll. This is information only; nothing about the roll is rebalanced.
- `New` Scenario, profession, and overmap information can show which mod supplied an entry,
  including rural terrain outside cities.
- `New` 108 compatible ASCII inspection-art identifiers for ammunition, welding consumables,
  grenades, nails, and vehicle batteries, providing 124 bindings to existing 0.G items.
- `New` In the character-information screen, **Shift+W** makes one worn armour item use
  another armour item's sprite, or restores its default. Protection, encumbrance, pockets,
  and item identity are untouched.
- `Improved` Right Arrow and Numpad 6 with NumLock off confirm numeric quantity input when
  the cursor sits at the end of the field. Ordinary text editing is unaffected.
- `Fixed` Windows builds declare PerMonitorV2 awareness and rescale runtime fonts for the
  monitor holding the window, so moving between mixed-DPI monitors rebuilds fonts and
  layout without changing saved options. Windowed mode keeps a complete 80x24 terminal
  inside the usable work area.

## Visuals, sound, and fonts

- `New` Tall walls and other high sprites can become translucent or retract near the
  character instead of hiding important tiles. **Handle occlusion by high sprites** offers
  Off, On, and Auto; transparency and retraction toggle independently, and a keybinding can
  cycle the mode.
- `New` Experimental 3D field of view draws visible lower Z-levels with distance fog, and
  creatures standing above cast a shadow onto the level below, making vertical threats
  easier to read.
- `New` Isometric tilesets join the same bounded multi-Z drawing. Each declares its own
  vertical pixel spacing, so lower floors, fog, vehicles, fields, and creature indicators
  stay aligned instead of collapsing onto one plane, and scale together with zoom. Legacy
  isometric tilesets without it log a warning and keep safe single-Z drawing.
- `New` **Look Up** and **Look Down** work even when experimental 3D field of view is
  disabled, rebuilding the relevant caches without enabling through-floor vision in play.
- `New` Running and smashing have visible tile animations, drawn asynchronously so they add
  no blocking pause to each action.
- `New` Visible monster-on-monster melee flashes the actual target, reusing the hit feedback
  already shown when the player strikes a monster.
- `New` Fields and weather can select weighted sprite variants, so rain tiles vary and
  animate wherever the chosen tileset supplies those sprites.
- `New` Eight optional colour themes: Abyss, Blood Moon, Empyrium, Oxygen, Shogun, Spark,
  Sun, and Vector.
- `New` JetBrains Mono is bundled under the SIL Open Font License as the first-choice
  sidebar, map, and overmap font, with Terminus and Unifont retained for glyph coverage.
  Blended text is on for new configurations, and **Font hinting** offers Normal, Light,
  Monochrome, or None.
- `New` Soundpacks can define firearm sounds by exact weapon, ammunition calibre, and
  suppressed state, and melee sounds by exact weapon. Packs without those entries keep the
  normal generic fallback rather than falling silent.
- `Improved` UltiCa and SurveyorsMap are updated from the tileset project's current composed
  release without discarding 0.G coverage: compatibility sheets retain 388 UltiCa and 65
  SurveyorsMap identifiers that were removed upstream after 0.G.
- `Improved` A reviewed high-resolution pilot sharpens common summer grass, pavement, and
  the yellow pavement marker while the map keeps its 32x32 logical tile footprint.
- `Improved` Ledges provide coverage in the cross-Z visibility cache, with stance and
  furniture at the target affecting that occlusion. The 0.G creature detection and stealth
  formulas are unchanged, and open or irrelevant ledges do not invent cover.
- `Fixed` East and west mirroring for vehicles, diagonal pavement and grass edges, connected
  terrain, furniture, fields, and overmap art, by normalising modern directional sprites to
  the 0.G rotation contract. Existing vehicle map memory stays save-compatible.
- `Fixed` Old hair and equipment overlays no longer sample opaque modern sprites and draw a
  grey square behind followers.
- `Fixed` The lower-level visibility cache is recalculated per Z-level, so a visible upper
  tile can no longer expose an unseen lower tile.
- `Fixed` NPC footsteps use the NPC's own position, terrain, direction, and footwear instead
  of accidentally sampling the player's tile.
- `Fixed` Audio initialisation retries a transient endpoint failure once and, on Windows,
  falls back to DirectSound when the default backend is unavailable. Soundpacks load only
  after the mixer opens, so one device error no longer cascades into soundpack errors. An
  explicitly selected `SDL_AUDIODRIVER` remains authoritative.

## Modding and scripting

- `New` Effect On Condition scripts can subscribe to game events, including new-game and
  load, instead of relying only on periodic polling. Subscription caches reset safely when
  data is reloaded.
- `New` JSON activities can run scripts each turn or on completion, with the activity actor
  and its context available to the effect.
- `New` Character-death events for both NPCs and the avatar run before irreversible cleanup,
  so a deliberately written effect can prevent a death by restoring vital HP. Normal deaths,
  corpses, and overmap cleanup are unchanged when no such effect fires.
- `New` Scripts have scoped context variables that propagate through nested effects without
  leaking into unrelated dialogues.
- `New` Named stored conditions can be defined once and reused from several effects, and a
  compact `if` effect supports `then`, optional `else`, effect arrays, and nested branches.
- `New` Inventory scripts process every matching carried item, one random match, one chosen
  match, or several chosen matches, filtering by item ID, category, material, flags, and
  worn or wielded state. Each chosen item becomes an item talker with context intact.
- `New` Map-aware conditions test terrain and furniture flags. Map effects spawn items or
  item groups, including contained items, on the active map or an off-bubble tinymap, and
  off-bubble changes are saved.
- `New` Map item selectors support all, random, manual, and multi-select modes, failing
  closed on an invalid mode or impossible container insertion rather than losing items.
- `New` `foreach` effects iterate explicit string and variable arrays, flag, trait and
  vitamin registries, item groups, and monster groups.
- `New` Scripts can ask the player to select any map tile, a visible tile within a
  configured range, or an adjacent tile, storing confirmed selections as absolute
  coordinates and leaving the target unchanged on cancellation.
- `New` `run_eocs` and `queue_eocs` can choose a script ID from a scoped variable while
  retaining fixed IDs, inline scripts, and mixed arrays, preserving normal ordering.
- `New` `u_add_trait` and `npc_add_trait` can select a named cosmetic mutation variant from a
  literal or scoped variable; effects that omit it keep automatic variant selection.
- `New` Mutation activation and deactivation scripts receive scoped context, and mutation
  transformations may opt into normal conflict, prerequisite, and cancellation rules. Legacy
  direct transformation stays the default for existing JSON.
- `New` JSON monster special attacks can use dialogue conditions alongside every existing
  0.G requirement. A new condition never bypasses range, cooldown, target, or legacy checks.
- `New` Data authors can use snippet tags in item and variant descriptions. The chosen text
  is expanded when the item is created and retained afterwards.
- `New` Vehicle-part attachment locations are data-defined, and vehicle enchantment and
  effect infrastructure is present, so later content backports land more safely.
- `New` The debug Vehicle menu exports a vehicle as a reusable JSON prototype, validating
  the result first rather than leaving a malformed partial file behind.

## Optional mods

- `New` **Useful Helicopters Experimental** ships bundled but disabled. Enabling it adds
  optional Piloting and Airframe &amp; Powerplant Mechanic chargen hobbies, plus removable and
  serviceable 15 m heavy-duty military, 8 m small civilian, 16 m Blackhawk, and 11 m Osprey
  rotors. The donor's proposed turbine fuel changes, Pilot Package CBM, and recipe-taught
  aviation proficiencies are not present.
- `New` Additional static faction camps activate only when their parent Aftershock or
  Magiclysm mod is enabled. No bundled mod is ever enabled for you.

## Stability and save compatibility

- Existing 0.G additive saves keep loading. Old vehicle saves are accepted when a part has
  no stored lock state, location mass, or enchantment cache, and door, fake-part,
  multisquare-door, and vehicle-effect state refresh after load rather than going stale.
- A new world is recommended only when complete exposure to the added map content matters.
- Interrupted follower and prisoner activities no longer emit cascades of missing-owner,
  lost-target, and invalid-parent errors across a save, because contained items carried by
  unloaded NPCs now resolve once their owner is registered.
- Multi-turn pickup reports items removed by other activity instead of raising a debug
  error. Names and safe location descriptions survive saves, a lost location cannot retarget
  another item, and a location that never resolved still fails loudly.
- NPC butchery jobs quietly cancel when their corpse vanished before the save.
- Recipe lookup, inventory-letter assignment, and repair selection use bounded caches and
  early filtering without changing any displayed success, damage, or component value.
- Vehicle part mass deserialises correctly on Windows, and camp ownership and lookup use
  exact camp positions, so multiple camps and migrated food stores cannot silently resolve
  to the wrong camp.
- A fail-closed audit compares core and bundled-mod data against exact 0.G on every change
  and rejects unintended deletion, replacement, duplicate identifiers, or an accidentally
  default-enabled optional mod.

## Known limits

- Offline follower temperature catch-up is capped and uses conditions at load time, because
  0.G stores no historical per-NPC weather.
- Autonomous follower survival uses only owned, accessible supplies. With the **Allow
  pickup** follower rule enabled, unowned ground supplies are deliberately eligible; disable
  it or use a protected zone to reserve dropped supplies.
- Windows audio recovery stays on the bundled SDL 2 stack, and the automatic fallback was
  never exercised against an injected hardware failure.
- Missing tileset sprites still use the normal fallback. Exact-release and legacy-identifier
  preservation is not a claim that every entity has bespoke artwork.
- Existing 0.G vehicles are not retrofitted with imported parts.
- The legacy 0.G renderer has no headless SDL harness, so no project-wide C++ coverage
  figure is claimed for the visual work.

## Non-goals

- This is not an upgrade to 0.H, 0.I, or current experimental. It is 0.G plus selected later
  mechanics and content, and the 0.G items, monsters, recipes, spawn tables, vehicle parts,
  and combat balance remain the foundation.
- No missions, locations, monsters, spawn rates, mutation progression, or item availability
  were replaced merely to demonstrate the scripting APIs.
- The colored-lighting chain is not included. It depends on the post-0.G row-bucketed
  renderer, typed map coordinates, newer lightmap data, and later vehicle-part factories, so
  transplanting it would be a renderer and lightmap rewrite rather than an additive backport.
- Illustrated loading screens and hints are not included; their donor chain is built on the
  later ImGui loading UI. No decorative mock was substituted for the missing engine support.
- The later map-memory refresh is not transplanted, and dropping items over ledges is left
  out because it changes gameplay rather than supporting the multi-Z visual fixes.
- The modern global follower behaviour tree, mission scheduler, and walking sorter are not
  imported; this keeps the 0.G needs cascade and legacy sorter.
- The current-experimental turret subsystem does not replace the fork's existing
  multiple-magazine-well vehicle plumbing.
- SDL 3 is not transplanted, because its modern implementation is coupled to full tiles,
  input, build, and packaging migrations.
- The inventory donor's unrelated bucket and container rewrites are excluded.
