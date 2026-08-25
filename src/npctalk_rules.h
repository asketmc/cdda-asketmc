#pragma once
#ifndef CATA_SRC_NPCTALK_RULES_H
#define CATA_SRC_NPCTALK_RULES_H

class npc;

/**
 * Opens the curses-compatible follower rules manager.
 *
 * This is intentionally separate from the dialogue rule topics.  The dialogue
 * topics remain available as a compatibility path for existing saves and mods.
 */
void show_follower_rules_ui( npc &follower );

#endif // CATA_SRC_NPCTALK_RULES_H
