# H3 Backport Report — Stable EOC Toolkit Checkpoint

This report defines the H3 compatibility slice shipped by the **Road Home +
EOC Toolkit** release candidate. It is layered on the current additive 0.G
branch, including H1/H2, the vehicle-lighting correction, and the visual/UI/audio
backports already merged to `main`.

The goal is engine compatibility for richer missions, NPCs, monsters,
mutations, and mods. It does not bulk-import later gameplay content or balance.

## Delivered donors

| Capability | Upstream source | Target result |
|---|---|---|
| Event-driven EOCs | PR #64426 `724542cc527c`, load/new-game support #65235 `1a8f8b4bd7e0`, correction #65694 `c76be47c7514` | Event subscriptions and cache reset adapted to 0.G. |
| Activity EOCs | PR #64943 `0d48286d3b6b`, correction #70195 `dfe4eb3d5374` | Completion/per-turn hooks with scoped dialogue context. |
| Monster-attack conditions | PR #65229 `e75cf058015b` | Dialogue conditions are added without bypassing legacy attack requirements. |
| Scoped EOC variables | PR #65307 `2c393f6d88f9`, correction #66138 `e2b75bd04915` | Nested context propagation on the 0.G dialogue architecture. |
| Mutation EOCs | PR #65434 `baff3913de79` | Activation/deactivation effects receive persistent scoped context. |
| Stored conditions | PR #65556 `09ec27d51fe7` | Named reusable conditions in JSON. |
| Safe mutation transforms | PR #66181 `17c8a9d48283` | Normal mutation-rule handling is opt-in; old direct transforms remain default. |
| Item talkers and automatic inventory selectors | PRs #68244 `957bbcafba08` and #68289 `9a4b2e0417eb`, correction #71953 `1c518f35ceea` | All/random matching carried items with false-once semantics. |
| Event beta talkers | PR #68399 `8852b696f81c`, correction #68916 `4592e8719beb` | Useful item/creature talkers for wield, wear, melee, and ranged events. |
| Manual inventory selectors | PR #68423 `1286d69756c5`, correction #71953 `1c518f35ceea` | Single and multiple selection with cancellation handled once. |
| Simple EOC branching | PR #68550 `c3c5b3ef592d` | `if`, `then`, optional `else`, arrays, and nesting. |
| Preventable NPC death | PR #68600 `ce661358907e` | Death EOCs may restore vital HP before corpse/overmap cleanup. |
| Map-aware EOCs | PR #68663 `dbb76ed70115`, corrections #71953 `1c518f35ceea`, #71014 `84fc61ee8657`, and `8d72f8d27f51` | Terrain/furniture conditions, item spawning, inventory selection, off-bubble persistence, and fail-closed invalid modes. |
| EOC `foreach` | PR #68829 `75945363447c` | Iterates arrays, ID registries, item groups, and monster groups into a scoped variable; unsupported types and targets fail during JSON loading. |
| Tile selection | PR #69006 `3219033191da6` | `u_query_tile`/`npc_query_tile` select anywhere, within line of sight, or on an adjacent tile and store an absolute coordinate. |
| Variable-selected EOCs | PR #69857 `f0a1245dca472`, correction #71017 `0595641fe2fb` | `run_eocs` and `queue_eocs` accept variable objects without masking malformed inline EOCs; immediate `run_eocs` entries retain array order while queued entries keep normal 0.G queue ordering. |
| Trait variants from EOCs | PR #70086 `e9463eb30616` | `u_add_trait` and `npc_add_trait` accept an optional literal or variable-selected cosmetic variant without changing omitted-field behavior; unknown explicit variants fail closed. |

Commit `cf4954dbbea21` only corrects a regression fixture to use the real preserved
0.G `knife_combat` item. Commit `1b9a4673fc079` extends the additive audit with
the already-delivered H1/H2 remote-tool fingerprints; neither changes gameplay.

## Post-review correctness fixes

- Child EOC dialogues preserve computer, mutable character/item, and const
  character talkers plus `reason`, `cur_item`, radio state, stored conditions,
  and scoped context. Existing shelter, nursing-home, retirement-community,
  LMOE, and laboratory computer EOCs continue opening their dialogue.
- Variable-backed inventory selector modes validate at runtime, emit a debug
  message on invalid input, and execute the false branch once.
- Activity EOCs may cancel or replace their activity without suspending the old
  activity; a replacement starts on the next turn.
- Safe mutation transforms preflight rejected and prerequisite-only targets
  before mutation effects, preserving source state, moves, and worn gear.
- `character_dies` EVENT EOCs run for the avatar as well as NPCs and may prevent
  either death attempt before irreversible handling.
- Indirect variable chains are cycle- and depth-guarded for both reads and
  writes. Invalid recursive references fail closed rather than overflowing the
  stack.
- Direct and mutual stored-condition recursion is guarded per dialogue and
  fails closed with one diagnostic.
- Map terrain/furniture flag conditions support omitted `loc` and read existing
  off-bubble submaps without generating unexplored world content. Container
  spawns retain the empty or partially filled container if a later insertion fails.
- Monster talkers expose JSON monster-type flags as well as effect flags without
  emitting a debug line for every routine check.
- Map selectors reject inventory-only worn/wielded filters at load time.
- Event participant resolution skips stale IDs without substituting the avatar;
  cached subscriptions retain EOC IDs and invalidate on factory reload.
- Non-EVENT `required_event` declarations are rejected. Activity EOC references
  are checked for existence and ACTIVATION type during consistency validation.
- Mutation process EOCs require and follow a positive cooldown interval.
- Forced mutation deactivation due to hunger, thirst, or fatigue returns before
  any processed EOC can run.
- Wield/wear events run after their caller-side bookkeeping; scripts may remove
  the event item without leaving a stale item location or worn iterator.
- Leap and spell attack conditions now run after their unchanged legacy gates.
  Wearing a wielded item preserves 0.G's empty-wield-state event without
  misreporting the newly worn item as its beta talker.

## Compatibility boundary

- Existing 0.G JSON remains valid; the new fields and effects are opt-in.
- Existing items, recipes, monsters, mutations, spawn tables, professions,
  vehicle parts, and world options are retained.
- Monster conditions are additive to existing range, cooldown, target, and
  effect requirements.
- Legacy mutation transformation remains the default.
- Selector cancellation/no-match paths execute the false EOC once.
- Invalid variable-backed inventory selector modes also execute the false EOC
  once and report the invalid value.
- Invalid selector modes, absent map targets, and failed container insertion
  fail closed.
- Omitted map `loc` still defaults to the alpha talker; an explicit empty or
  malformed location never does.
- Off-bubble map writes explicitly save the tinymap.
- Save compatibility is retained; no mandatory migration is introduced.

## Scope boundary

No H4/H5/H6 backlog item is implied by this report. Visual/UI/audio work already
merged independently to `main` is documented in
`doc/VISUAL_UI_BACKPORT_REPORT.md`.

## Local validation contract

- MXE GCC 11 static Windows x64 Tiles+Sound production build.
- Focused EOC, event, monster-special-attack, mutation, H1/H2 vehicle-tool, and
  visual/UI C++ regression selections.
- Visual/UI Python contract and packaged-asset tests.
- Full JSON parse and core/optional-mod load checks.
- Fail-closed additive baseline audit, whitespace checks, and independent code
  review.
- No GitHub Actions or hosted CI consumers.

Historical package evidence and current source-only limitations are recorded
in `BUILD_INFO.txt`. Exact final package commands and hashes are pending the
consolidated post-merge release run.
