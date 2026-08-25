# CDDA 0.G Additive

Personal experimental fork of **Cataclysm: Dark Days Ahead 0.G “Gaiman”**.
It selectively backports later bug fixes, quality-of-life improvements, and
technical features while retaining the 0.G gameplay and content baseline.

The design priorities are vehicles and mobile bases, followers and camps,
useful interface improvements, and compatible visual upgrades. Backports are
kept narrow: wholesale later-version merges, removals, and unrelated balance
changes are deliberately avoided.

This is not an official CDDA release. Compatibility with existing 0.G saves is
best-effort, and there are no support guarantees.

## Current feature areas

- Modular vehicle workshops, kitchens, power, appliances, locks, and reliability.
- NPC, follower, camp, crafting, and equipment-repair improvements.
- Additive EOC scripting support and selected anti-grind quality-of-life changes.
- Updated UltiCa/SurveyorsMap assets, multi-Z rendering, UI, and sound polish.
- Restored CBM salvage and an optional Useful Helicopters package.

See [PATCHNOTES_ADDITIVE_0G.md](PATCHNOTES_ADDITIVE_0G.md) for player-facing
changes, [BACKPORTS.md](BACKPORTS.md) for donor provenance, and
[CURRENT_STATE.md](CURRENT_STATE.md) for build and validation status.

## Development

Read [AGENTS.md](AGENTS.md) before changing the fork. The authoritative branch
is `main`; historical 0.G foundation commits are provenance, not reset targets.
Local build and validation commands are recorded in `CURRENT_STATE.md`.

## License and credits

This fork derives from [CleverRaven/Cataclysm-DDA](https://github.com/CleverRaven/Cataclysm-DDA).
Upstream credits and attribution files are retained; this public snapshot starts
new Git history. See [LICENSE.txt](LICENSE.txt) and the bundled licenses.
