#include "cata_catch.h"

#include "cata_scope_helpers.h"
#include "character.h"
#include "faction.h"
#include "game.h"
#include "map_helpers.h"
#include "morale_types.h"
#include "npc.h"
#include "player_helpers.h"
#include "point.h"
#include "type_id.h"

static const faction_id faction_hells_raiders( "hells_raiders" );
static const faction_id faction_no_faction( "no_faction" );

TEST_CASE( "hostile NPC death does not cause innocent-kill morale",
           "[npc][morale][hostility]" )
{
    clear_map();
    clear_avatar();
    g->faction_manager_ptr->create_if_needed();

    Character &you = get_player_character();
    faction *raiders = g->faction_manager_ptr->get( faction_hells_raiders );
    REQUIRE( raiders != nullptr );

    restore_on_out_of_scope<int> restore_raider_likes( raiders->likes_u );
    raiders->likes_u = 0;

    SECTION( "a kill-on-sight raider is hostile before choosing NPCATT_KILL" ) {
        npc &raider = spawn_npc( you.pos().xy() + point_south, "thug" );
        raider.set_fac( faction_hells_raiders );
        raider.set_attitude( NPCATT_NULL );
        raider.hit_by_player = false;

        REQUIRE( raider.attitude_to( you ) == Creature::Attitude::HOSTILE );
        REQUIRE( raider.guaranteed_hostile() );

        raider.on_attacked( you );

        CHECK_FALSE( raider.hit_by_player );
        CHECK( raider.get_attitude() == NPCATT_NULL );

        raider.die( &you );
        CHECK( you.has_morale( MORALE_KILLED_INNOCENT ) == 0 );
    }

    SECTION( "a genuinely neutral NPC remains protected" ) {
        npc &neutral = spawn_npc( you.pos().xy() + point_south, "thug" );
        neutral.set_fac( faction_no_faction );
        neutral.set_attitude( NPCATT_NULL );
        neutral.hit_by_player = false;

        REQUIRE_FALSE( neutral.guaranteed_hostile() );

        neutral.on_attacked( you );

        CHECK( neutral.hit_by_player );
        neutral.die( &you );
        CHECK( you.has_morale( MORALE_KILLED_INNOCENT ) < 0 );
    }

    clear_npcs();
    you.clear_morale();
}
