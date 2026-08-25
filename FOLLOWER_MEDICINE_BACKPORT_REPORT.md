# Follower Medicine Backport

This change adapts three narrow follower improvements to the existing 0.G NPC
action cascade.  It does not import a modern behavior tree, mission scheduler,
or combat rebalance.

## Included

- First aid is selected only when the local danger assessment is clear.
- Self treatment remains automatic.
- A save-compatible follower rule enables or disables treatment of allies.
- A camp or ordered activity suspended by first aid is marked for automatic
  resumption after treatment finishes.
- Food and medication containing iron or vitamin C are considered while the
  follower has anemia or scurvy-level deficiency.
- Supplements stop being candidates after the relevant deficiency clears.
- Strongly unpleasant food receives a large preference penalty rather than a
  hard ban.  Active nausea blocks ordinary eating, with a forced-consumption
  fallback only at critical calorie shortage.
- Empty hands and non-guns receive initialized, finite weapon comparison data.

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

Focused tests cover safe and blocked healing, the ally rule and old-save
default, activity restoration, vitamin food and medication, supplement bounds,
nausea preferences and starvation fallback, and finite weapon comparison.
