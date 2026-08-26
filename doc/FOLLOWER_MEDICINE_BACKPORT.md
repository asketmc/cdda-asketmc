# Follower Medicine Backport

This change adapts three narrow follower improvements to the existing 0.G NPC
action cascade. It does not import a modern behavior tree, mission scheduler,
or combat rebalance.

## Included

- First aid and nanobot healing stop while an immediate threat is present.
- Self treatment remains automatic.
- A save-compatible `allow_heal_others` follower rule controls allied treatment.
  Non-followers continue treating members of their own faction independently.
- Camp or ordered activities interrupted by first aid resume with their NPC
  activity attitude and mission restored.
- Food and medication can treat any data-defined vitamin deficiency.
- Treatment is throttled, excludes addictive or effect-bearing consumables,
  preserves spoilage urgency, and stops after the deficiency clears.
- Strongly unpleasant food remains a last resort. Active nausea blocks normal
  eating, with a narrowly scoped fallback only at critical calorie shortage.
- Unarmed followers no longer inflate the empty-hand threshold when selecting
  a useful carried weapon. Offered non-guns use zero rather than sentinel ammo.
- Missing saved override fields no longer inherit a prior rule's value.

## Donors

- Cataclysm-TLG #1603, `5fd614b81aeb7de418b4ed239e5b7e8f93828cba`
- Cataclysm-TLG #2982, `87448bac93398575e854128d00840b73d3f7c7ac`
- Cataclysm-TLG #2746, `336d552d6df48f73ddfd1f63f7572cd3ad15238b`

## Deliberate exclusions

- No global NPC behavior or mission framework.
- No melee, ranged, accuracy, dodge, stamina, or damage coefficient changes.
- No change to loud/silent follower rules.
- No automatic search for superior combat equipment on the map.
- No changes to general food, vitamin, or disease balance.
