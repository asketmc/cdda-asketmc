# H6 Backport Report — Anti-Grind Mechanics

This report records the selected H6 mechanics layered on the additive 0.G
branch. Each behavior is independently revertible. Existing 0.G content and
hard skill requirements remain the default outside the explicitly listed
changes.

## Faster simple deconstruction

- Donor: PR #63656, `208c16e4c0122aea47deaeceb775925d4ab2ffca`.
- Correctness follow-up: PR #70494,
  `77b2f00618d48b5693e25758e0ef8b7c0ccc36bf`.
- Tool-free `EASY_DECONSTRUCT` work takes 10 seconds.
- The regular deconstruction predicate rejects that same furniture, so only
  the intended fast entry is offered.
- Focused regression: `[h6][construction][antigrind]`.

## Heavier vehicle dragging

- Donor: PR #64867, `0bc9651560f696dce58a9ce5833e5b09bd36dc3d`.
- Formula follow-up: PR #72515,
  `94b74cf5b0ac1a0661488876c846205ff969b314`.
- Integer-precision correction:
  `ec520a2d9f6a45dc44fbf66311fa647637bd17a5`.
- The fixed 0.G mass cutoff is replaced by a mass ceiling adjusted for wheel
  count, terrain cost, and traction. Multiplication precedes division so small
  per-wheel values are not truncated to zero.
- Successful movement has proportional move and stamina cost; wheel-less
  dragging retains the full mass requirement and scraping noise.

## Safer Safe Place starts

- Donor: PR #68920, `79a1b6bbd480b9c65c472007610e96520f350fe1`.
- The affected cabin and farm mapgen variants replace their guaranteed zombie
  group with a guaranteed generic human corpse. The 0.G adaptation uses
  `place_item` because `corpse_generic_human` is an item, not an item group.
- `sloc_freshwater_research_station` is removed only from the `isolationist`
  scenario. The additive branch's `sloc_cabin_lake` option is retained.
- Focused data regression: `python tools/test_h6_antigrind.py`.

## Smaller BMI health effect

- Donor: PR #66494, `e4105523d44e91d884bcf4b117033ad86626d041`.
- Effective lifestyle now subtracts a small linear overweight penalty and the
  donor's stronger underweight penalty, with a -200 floor.
- Positive daily health is capped at +200 rather than at the old nonlinear
  BMI-specific maximum. Existing health sources and update cadence are intact.
- Healing and health fixtures explicitly normalize stored calories so their
  lifestyle assertions continue to test lifestyle rather than body weight.
- Focused regression: `[h6][health][antigrind]`, plus the existing `[health]`
  and `[heal]` suites.

## Bulk loading and unloading time savings

- Donors: PR #68214 feature commits
  `9fae32259c4ba` and `dd5be8d82649d`; PR #69202,
  `aaec4424598f467f682b68b6cfea94892212164f`.
- The handling-cost API accepts an optional charge count and bulk flag. All
  existing callers keep their 0.G defaults.
- Container insertion becomes bulk only for compatible stacks at the same map
  tile, vehicle tile, or parent container. Container unloading becomes bulk
  only for consecutive compatible contents.
- Drop and pet-stash activities retain bulk state across turns and saves, with
  `false` as the backward-compatible default for old activity data. Only
  consecutive items from the same parent container qualify.
- Direct comparison with the 0.I branch found the same core behavior and no
  additional correctness patch in these donor functions.
- Focused regression: `[h6][items][antigrind]`.

## Fractional practical-skill progress in soft checks

- Donor: PR #65004, `dbd8cd966a60996d3cfa7413f05d1219c57893f3`.
- This is a selective adaptation rather than the donor's global return-type
  change. `get_skill_level()` remains the 0.G integer API, while the new
  `get_skill_level_with_progress()` API adds normalized exercise progress only
  where a continuous bonus is intended.
- Skill enchantments are applied once to the completed level plus progress, as
  in the donor. The soft API adds no global skill cap; formula-specific caps
  remain local to their existing callers.
- Soft progress is used by crafting success, repair success/damage, melee hit,
  critical chance and attack speed, firearm aim/attack speed, vehicle-security
  smashing and hotwiring time, and item stow time.
- Recipe availability, construction and vehicle-part requirements, quest and
  dialogue gates, learning caps, and every unlisted check retain completed
  integer levels. No crafting probability formula changed beyond feeding it
  the fractional practical level.
- Focused regression: `[h6][skill][antigrind]` verifies the fractional value,
  the unchanged integer gate value at the same XP state, and fractional
  progress above the normal maximum after a positive skill enchantment.
