### effect_on_condition
An effect_on_condition is an object allowing the combination of dialog conditions and effects with their usage outside of a dialog.  When invoked, they will test their condition; on a pass, they will cause their effect. They can be activated automatically with any given frequency.  (Note: effect_on_conditions use the npc dialog conditions and effects syntax, which allows checking related to, or targeting an effect at, an npc (for example: `npc_has_trait`).  Using these commands in an effect_on_condition is not supported.)

## Fields

|Identifier|Type|Description|
|-|-|-|
| `recurrence`| int or variable object or array | The effect_on_condition is automatically invoked (activated) with this many seconds in-between. If it is an object it must have strings `name`, `type`, and `context`. `default` can be either an int or a string describing a time span. `global` is an optional bool (default false), if it is true the variable used will always be from the player character rather than the target of the dialog.  If it is an array it must have two values which are either ints or varible_objects.
| `condition`| condition | The condition(s) under which this effect_on_condition, upon activation, will cause its effect.  See the "Dialogue conditions" section of [NPCs](NPCs.md) for the full syntax.
| `deactivate_condition`| condition | *optional* When an effect_on_condition is automatically activated (invoked) and fails its condition(s), `deactivate_condition` will be tested if it exists and there is no `false_effect` entry.  If it returns true, this effect_on_condition will no longer be invoked automatically every `recurrence` seconds.  Whenever the player/npc gains/loses a trait or bionic all deactivated effect_on_conditions will have `deactivate_condition` run; on a return of false, the effect_on_condition will start being run again.  This is to allow adding effect_on_conditions for specific traits or bionics that don't waste time running when you don't have the target bionic/trait.  See the "Dialogue conditions" section of [NPCs](NPCs.md) for the full syntax.
| `required_event` | cata_event | Event that triggers an `EVENT` EOC. Required for `EVENT` EOCs and rejected on every other EOC type.
| `effect`| effect | The effect(s) caused if `condition` returns true upon activation.  See the "Dialogue Effects" section of [NPCs](NPCs.md) for the full syntax.
| `false_effect`| effect | The effect(s) caused if `condition` returns false upon activation.  See the "Dialogue Effects" section of [NPCs](NPCs.md) for the full syntax.
| `global`| bool | If this is true, this recurring eoc will be run on the player and every npc from a global queue.  Deactivate conditions will work based on the avatar. If it is false the avatar and every character will have their own copy and their own deactivated list. Defaults to false.
| `run_for_npcs`| bool | Can only be true if global is true. If false the eoc will only be run against the avatar. If true the eoc will be run against the avatar and all npcs.  Defaults to false.
| `EOC_TYPE`| string | The effect_on_condition is automatically invoked once on scenario start.
 Can be any of:ACTIVATION, RECURRING, SCENARIO_SPECIFIC, AVATAR_DEATH, NPC_DEATH, OM_MOVE, PREVENT_DEATH, EVENT. It defaults to ACTIVATION unless `recurrence` is provided in which case it defaults to RECURRING.  If it is SCENARIO_SPECIFIC it is automatically invoked once on scenario start. If it is PREVENT_DEATH whenever the current avatar dies it will be run with the avatar as u, if after it the player is no longer dead they will not die, if there are multiple they all be run until the player is not dead. If it is AVATAR_DEATH whenever the current avatar dies it will be run with the avatar as u and the killer as npc. NPC_DEATH EOCs run before irreversible NPC-death cleanup, with the dying NPC as u and its killer as npc; calling `u_prevent_death` can keep the NPC alive. OM_MOVE EOCs trigger when the player moves overmap tiles. EVENT EOCs trigger when their `required_event` occurs.

EVENT EOCs expose every field from the triggering event as a dialogue `context_val` with the same field name. Values are converted to strings. Nested EOCs inherit those values, while their context changes remain local to the child activation. When an event names a character, EOCs run only after that character is resolved; a stale character ID is not silently replaced with the avatar.

`character_dies` is emitted for both the avatar and NPCs before irreversible death handling. It describes a death attempt, so EVENT EOCs may call `u_prevent_death`; subscribers still observe the event even when death is prevented.

Events that wield or wear an item provide that item as the beta talker. The empty-wield-state event emitted after wearing a wielded item has no item beta. Melee and ranged attack events provide the target character or monster as beta, while the acting character is alpha.

Mutation `activated_eocs`, `processed_eocs`, and `deactivated_eocs` expose the
mutation ID as the dialogue `context_val` named `this`. `processed_eocs` run on
the mutation's positive `time`/cost interval; a zero-time mutation has no
processing interval and does not fire them every turn.

`u_add_trait` and `npc_add_trait` accept an optional `variant` string or
variable object.  It selects a cosmetic mutation variant; omitting the field
keeps the existing automatic variant behavior.  An unknown explicit variant
fails instead of silently selecting a random one.

EOCs can store a named dialogue condition with `set_condition` and evaluate it
later with `get_condition`.  Stored conditions follow context variables into
nested EOCs, but changes made by a child activation do not flow back to its
parent.

Map-aware EOCs can inspect terrain and furniture flags, place items, and run
item EOCs over a bounded area.  `map_spawn_item` accepts an item ID (or an item
group when `use_item_group` is true), optional `count`, `container`, and `loc`.
Item groups preserve their own collection counts and containers, so `count`
and `container` are ignored for them. If a requested item does not fit, the
empty or partially filled container is still placed. Without `loc`, it uses
the alpha character's position. Terrain/furniture flag checks also default to
alpha and load the target submap when `loc` is outside the active map.
`u_map_run_item_eocs`
and `npc_map_run_item_eocs` accept `all`, `random`, `manual`, or `manual_mult`,
plus optional `loc`, `min_radius`, `max_radius`, `search_data`, and `title`.
The selected character is alpha and each matching map item is beta.  If no
item matches, or a manual selector is canceled, `false_eocs` runs exactly once.
Map selectors reject `worn_only` and `wielded_only`; those filters are valid
only for inventory selectors.

Furniture `examine_action` EOCs expose the furniture ID as context value
`this` and its global map-square coordinate as context value `pos`.

`foreach` repeats a nested `effect` while writing each value to `var`.  It can
iterate `ids` (target `flag`, `trait`, or `vitamin`), every possible item in an
`item_group`, every monster in a `monstergroup` including subgroups, or an
`array` of strings and variable objects.

`u_query_tile` and `npc_query_tile` are dialogue conditions that ask the player
to select a map tile and write its absolute map-square coordinate to the
mandatory `target_var`.  The selection mode is `anywhere`, `line_of_sight`, or
`around`.  `line_of_sight` uses the mandatory `range`; `anywhere` may set
`z_level` to allow changing elevation.  An optional `message` is shown while
selecting.  The condition is true only after the avatar confirms a tile;
canceling, or evaluating it for a non-avatar talker, returns false and leaves
`target_var` unchanged.

`run_eocs` and `queue_eocs` accept fixed EOC IDs, inline EOCs, variable objects,
or arrays mixing those forms.  A variable object is evaluated when the effect
runs and its string value selects the EOC ID.  `queue_eocs` resolves the ID when
it adds the entry to the queue; as before, the queued EOC itself runs later.

```json
{
  "if": {
    "u_query_tile": "line_of_sight",
    "target_var": { "context_val": "selected_pos" },
    "range": 10,
    "message": "Select a point"
  },
  "then": { "u_message": "Selected <context_val:selected_pos>" },
  "else": { "u_message": "Selection canceled" }
}
```

## Examples:
```JSON
  {
    "type": "effect_on_condition",
    "id": "test_deactivate",
    "recurrence": 1,
    "condition": { "u_has_trait": "SPIRITUAL" },
    "deactivate_condition": {"not":{ "u_has_trait": "SPIRITUAL" } },
    "effect": { "u_add_effect": "infection", "duration": 1 }
  },
  {
    "type": "effect_on_condition",
    "id": "test_stats",
    "recurrence": [ 1, 10 ],
    "condition": { "not": { "u_has_strength": 7 } },
    "effect": { "u_add_effect": "infection", "duration": 1 }
  }
