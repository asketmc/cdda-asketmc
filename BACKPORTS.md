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
| Inventory transfer QoL | Adapted for 0.G | [DDA #75104](https://github.com/CleverRaven/Cataclysm-DDA/pull/75104), selected [DDA #68226](https://github.com/CleverRaven/Cataclysm-DDA/pull/68226), [TLG #1201](https://github.com/Cataclysm-TLG/Cataclysm-TLG/pull/1201), and [BN #9020](https://github.com/cataclysmbn/Cataclysm-BN/pull/9020); bucket/container rewrites are excluded, and classic pickup/drop sorting is a local 0.G adaptation |
| Repairable EMP faults | Integrated | [CDDA 73bcb0a](https://github.com/CleverRaven/Cataclysm-DDA/commit/73bcb0a906b7a8d5b38257d9d11cf53b79f6aa83), [game EMP 6c45556](https://github.com/CleverRaven/Cataclysm-DDA/commit/6c4555671cd1d8ae102bd81d36d107058e5d1c8e) |
| Supported ledge descent | Adapted for 0.G | [BN #2879](https://github.com/cataclysmbnteam/Cataclysm-BN/pull/2879), selected logic from [DDA #68120](https://github.com/CleverRaven/Cataclysm-DDA/pull/68120) and [DDA #68190](https://github.com/CleverRaven/Cataclysm-DDA/pull/68190); unsupported drops keep existing climbing-tool behavior while supported routes preserve those tools; the modern climbing JSON framework is excluded |
| Hostile NPC kill morale | Adapted for 0.G | [DDA #78371](https://github.com/CleverRaven/Cataclysm-DDA/pull/78371), commit `c5e8a7a1cd53921ad0d12bce89944a5ad8e50c5b`; kill-on-sight faction hostility is recognized before `NPCATT_KILL`, while neutral-NPC guilt remains unchanged |
| Contained NPC activity items | Fixed locally | [Patch notes](PATCHNOTES_ADDITIVE_0G.md) |
| Multi-turn pickup target loss | Fixed locally; no donor code | [Patch notes](PATCHNOTES_ADDITIVE_0G.md) |
| Windows audio recovery | Adapted for 0.G SDL2 | [DDA #76782](https://github.com/CleverRaven/Cataclysm-DDA/pull/76782) merge `1c24d320625841301dbde926da1e1c9eb0c4dbf1` (donors `effacd0bf5a6d3f746f26fc28493a98d2cd34617`, `4ba6ea94fc565326d17bb41640a4828c8ef8993f`); SDL3 excluded; policy executable-tested and Windows objects compiled from source commit `028a83ba97dbdfcecaf46b2c035e106aea7007ca`, but broken-endpoint hardware injection remains a local runtime limit |
| H3-H6 delivery ledger | Resolved; exclusions recorded | Reports above |

Primary donor provenance is recorded per feature in the reports above and in
[the detailed additive ledger](doc/ADDITIVE_BACKPORTS.md). The project rule is
additive transplantation: import the selected feature and its direct fixes,
not the donor branch's unrelated gameplay or architecture changes.
