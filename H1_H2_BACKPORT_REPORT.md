# H1/H2 Backport Report — Vehicle Workshop and Energy

This report is the engineering boundary for the single H1/H2 delivery on top
of the published CDDA 0.G additive fork. It is intentionally additive: no 0.G
vehicle rig, recipe, item, or save field was removed or obsoleted.

## H1 — mounted workshop and kitchen

Shipped end to end:

- Craftable/installable **kitchen station**, **workshop station**, and fork-local
  **mounted fabrication bay**. The fabrication bay is also a 1.2x workbench.
- Equivalent placeable appliances for a stationary workshop or base grid.
- Per-station whitelists and inventory UI for attaching and detaching real
  tools. The original item is moved, not replaced by a blank copy.
- Full attached-item persistence: inventory letter, damage, charges, pockets,
  item variables, save/load, rack/unrack, mass, station removal, temporary
  vehicle expiry, and JSON vehicle prototype export/import.
- Crafting sees attached tool qualities through powered pseudo copies.
- Electrical tools draw from the local battery or any vehicle connected through
  the vehicle-power graph. Supported fuel tools draw from matching vehicle
  tanks; the propane cooker uses propane. Kitchen and fabrication faucets expose
  clean water and compatible liquids from onboard tanks.
- Repair-kit/welder/soldering paths are available. The deferred hacksaw bridge
  stores the tool type and vehicle position instead of a pointer to a temporary
  item. A repair kit whose HACKSAW charge multiplier is zero works even with an
  empty vehicle battery.
- Both keyboard hotkey modes receive the attached tool's useful inventory key.
- The old FOODCO, kitchen unit, chemistry lab, welding rig, and other integrated
  0.G rigs remain valid alternatives.

## H2 — vehicle power and reliability

The H1 stations are integrated with the additive fork's existing connected
power, appliance, multi-pocket, install-reason, and autodrive foundations. This
delivery also closes these concrete reliability gaps:

- Remote-use flags cover the relevant 0.G coffeepots, cookers, chemistry set,
  coffee maker, hotplates, and wire-draw machine. Mounted copies consume actual
  vehicle battery/tank resources instead of creating charges.
- Active turret items are processed while mounted, so heat can dissipate.
- A full destination cargo part keeps overflow with the character when possible
  instead of silently scattering the remainder on the ground.
- A broken part on a racked vehicle cannot be replaced through its carrier.
- Tow, vehicle-power, and appliance-cord links validate both endpoints before
  creating either endpoint. Dynamic `NOINSTALL` link parts remain unavailable
  in the normal install menu but are permitted through this validated link path.
- A smart controller can manage one parked combustion engine as a generator.
  It uses the actual starter/fuel/fault checks, starts below the low battery
  threshold, stops above the high threshold, and remains armed after a normal
  high-charge stop.
- Appliance UI refresh and electrical draw display remain live after changes.

## Post-H1/H2 faucet Auto Drink follow-up

- A vehicle-bound Auto Drink zone on a working faucet can consume suitable
  liquids from available fluid tanks anywhere on that vehicle. The 0.G
  adaptation preserves ordinary Auto Drink safety and ownership checks and
  does not expose vehicle tanks to Auto Eat zones.
- The liquid-output container comparator now uses the same eligible-content
  definition as `only_item()`. This prevents a loaded battery pocket in an
  otherwise empty multi cooker from triggering a zero-content debug error when
  the crafting UI ranks output containers.
- Focused regression coverage exercises both a faucet-bound and ordinary
  cargo-bound vehicle zone, tank charge consumption, and the loaded-battery
  empty-container case.

## Deliberate compatibility limits and dropped adaptations

- The later standalone item-link/cabled-tool API was not imported: this 0.G
  branch has no compatible `can_link_up()` item-power infrastructure. Vehicle
  batteries and tanks are the supported station sources.
- `microwave` and disconnected `oven` are generic appliance chassis in this
  0.G data set, not usable handheld tools. Whitelisting them would create a
  misleading inert attachment. The oven keeps its normal standalone appliance
  route; the 0.G microwave remains salvage-only. Usable hotplates and chemistry
  devices are attachable.
- Transforming or consumable-state tools such as the circular saw and towel are
  not attachable because invoking a temporary 0.G pseudo copy would discard the
  transformed state. This avoids duplication or silent item-state loss.
- No later vehicle-rig removal/replacement patch was taken.
- A current-upstream dedicated multiple-magazine turret test expansion was
  dropped after more than three old-harness adaptation failures (fixture
  preload failure, hang, then access violation). Production multi-pocket code
  already present in the additive baseline was left unchanged. The legacy
  generic turret test still cannot preload its synthetic multi-pocket
  flamethrower with `ammo_set`; this is recorded as an unvalidated baseline
  boundary, not reported as a passing H1/H2 test.
- Selective hauling, full appliance-grid merging, multi-Z camp work, and later
  item-power refactors are separate roadmap slices, not hidden dependencies of
  this release.

## Validation contract

- Windows x64 tiles/sound production build with the MXE GCC 11 static toolchain.
- Focused modular-tool, persistence, prototype, rack/unrack, drop, connected
  power, safe activity, and single-generator controller tests.
- Existing vehicle power-cable test.
- Core `dda` and bundled `useful_helicopters` data/mod checks.
- JSON parse and `git diff --check` on the exact delivery tree.
- No live save, user configuration, or existing installation is modified by
  build or validation.
