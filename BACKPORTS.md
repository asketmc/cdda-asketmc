# Backport Index

This is the concise provenance index. Detailed behavior, exclusions, and test
evidence remain in the linked reports and player patch notes.

| Area | Status | Documentation |
| --- | --- | --- |
| H1/H2 vehicle workshop and energy | Integrated | [H1/H2 report](H1_H2_BACKPORT_REPORT.md) |
| Visual, UI, sound, and tilesets | Integrated | [Visual/UI report](doc/VISUAL_UI_BACKPORT_REPORT.md) |
| H3 EOC compatibility | Integrated selected APIs | [H3 report](H3_EOC_BACKPORT_REPORT.md) |
| H4 visual multi-Z | Integrated selected behavior | [Patch notes](PATCHNOTES_ADDITIVE_0G.md) |
| H5 interface and ASCII-art QoL | Integrated selected behavior | [H5 report](H5_INTERFACE_QOL_BACKPORT_REPORT.md) |
| H6 anti-grind QoL | Integrated selected behavior | [H6 report](H6_ANTIGRIND_BACKPORT_REPORT.md) |
| Backup generator | Integrated | [Generator report](H6_BACKUP_GENERATOR_BACKPORT_REPORT.md) |
| Crafting, inventory, and repair performance | Integrated selected behavior | [BN #917](https://github.com/cataclysmbnteam/Cataclysm-BN/pull/917), [BN #1117](https://github.com/cataclysmbnteam/Cataclysm-BN/pull/1117), [BN #8221](https://github.com/cataclysmbnteam/Cataclysm-BN/pull/8221) |
| Contained NPC activity items | Fixed locally | [Patch notes](PATCHNOTES_ADDITIVE_0G.md) |
| Windows audio recovery | Adapted for 0.G SDL2 | [DDA #76782](https://github.com/CleverRaven/Cataclysm-DDA/pull/76782) merge `1c24d320625841301dbde926da1e1c9eb0c4dbf1` (donors `effacd0bf5a6d3f746f26fc28493a98d2cd34617`, `4ba6ea94fc565326d17bb41640a4828c8ef8993f`); SDL3 excluded; policy executable-tested and Windows source compiled, but broken-endpoint hardware injection remains a local runtime limit |
| H3-H6 delivery ledger | Resolved; exclusions recorded | Reports above |

Primary donor provenance is recorded per feature in the reports above and in
[the detailed additive ledger](doc/ADDITIVE_BACKPORTS.md). The project rule is
additive transplantation: import the selected feature and its direct fixes,
not the donor branch's unrelated gameplay or architecture changes.
