#include "cata_catch.h"

#include "avatar.h"
#include "creature_tracker.h"
#include "game.h"
#include "json.h"
#include "json_loader.h"
#include "map.h"
#include "map_extras.h"
#include "map_helpers.h"
#include "mapgen_helpers.h"
#include "monster.h"
#include "mtype.h"
#include "player_helpers.h"

static const itype_id itype_556( "556" );
static const mtype_id mon_crows_m240( "mon_crows_m240" );
static const mtype_id mon_turret_bmg( "mon_turret_bmg" );
static const mtype_id mon_turret_rifle( "mon_turret_rifle" );
static const update_mapgen_id update_mapgen_test_update_place_damaged_turret(
    "test_update_place_damaged_turret" );

TEST_CASE( "military roadblock turret distribution", "[mapgen][monster][progression]" )
{
    const auto check_loadout = []( int roll, const mtype_id & monster, int ammo_min, int ammo_max ) {
        const auto actual = MapExtras::military_turret_for_roll( roll );
        CHECK( actual.monster == monster );
        CHECK( actual.ammo_min == ammo_min );
        CHECK( actual.ammo_max == ammo_max );
    };
    check_loadout( 1, mon_turret_rifle, 80, 240 );
    check_loadout( 70, mon_turret_rifle, 80, 240 );
    check_loadout( 71, mon_crows_m240, 50, 150 );
    check_loadout( 95, mon_crows_m240, 50, 150 );
    check_loadout( 96, mon_turret_bmg, 20, 60 );
    check_loadout( 100, mon_turret_bmg, 20, 60 );
    map &here = get_map();
    clear_map();
    clear_avatar();
    const int z = get_avatar().posz();
    const std::vector<std::pair<point, point>> positions = {
        { point( 12, 6 ), point( 12, 5 ) }, { point( 18, 12 ), point( 19, 12 ) },
        { point( 12, 18 ), point( 12, 19 ) }, { point( 6, 12 ), point( 5, 12 ) }
    };
    const int rolls[] = { 1, 71, 96, 1 };
    for( size_t i = 0; i < positions.size(); ++i ) {
        MapExtras::add_military_turrets( here, positions[i].first, z, rolls[i] );
    }
    here.spawn_monsters( true );
    for( size_t i = 0; i < positions.size(); ++i ) {
        const auto &entry = positions[i];
        const auto loadout = MapExtras::military_turret_for_roll( rolls[i] );
        const monster *riot = get_creature_tracker().creature_at<monster>( tripoint( entry.first, z ) );
        const monster *armed = get_creature_tracker().creature_at<monster>( tripoint( entry.second, z ) );
        REQUIRE( riot != nullptr );
        CHECK( riot->type->id.str() == "mon_turret_riot" );
        REQUIRE( armed != nullptr );
        CHECK( armed->type->id == loadout.monster );
        CHECK( armed->get_hp() >= armed->get_hp_max() * 30 / 100 );
        CHECK( armed->get_hp() <= armed->get_hp_max() * 70 / 100 );
        REQUIRE_FALSE( armed->ammo.empty() );
        for( const auto &ammo : armed->ammo ) {
            CHECK( ammo.second >= loadout.ammo_min );
            CHECK( ammo.second <= loadout.ammo_max );
        }
    }
}

TEST_CASE( "mapgen range compatibility", "[mapgen][monster][progression]" )
{
    const JsonObject empty = json_loader::from_string( R"({ "value": [] })" ).get_object();
    const jmapgen_int empty_defaulted( empty, "value", 100, 100 );
    CHECK( empty_defaulted.val == 100 );
    CHECK( empty_defaulted.valmax == 100 );
    CHECK_THROWS_AS( jmapgen_int( empty, "value" ), JsonError );
}

TEST_CASE( "spawn_data rejects invalid ranges", "[mapgen][monster][progression]" )
{
    spawn_data data;
    const auto check_rejected = [&data]( const std::string & source ) {
        const JsonObject object = json_loader::from_string( source ).get_object();
        CHECK_THROWS_AS( data.deserialize( object ), JsonError );
    };
    check_rejected( R"({ "ammo_qty": -1 })" );
    check_rejected( R"({ "hp_percent": [] })" );
    check_rejected( R"({ "ammo": [], "ammo_qty": 80 })" );
    check_rejected( R"({ "ammo": [ { "ammo_id": "556", "qty": 80 } ], "ammo_qty": 80 })" );
}

TEST_CASE( "mapgen monster uses spawn_data", "[mapgen][monster][progression]" )
{
    map &here = get_map();
    clear_map();
    clear_avatar();
    const tripoint_abs_omt omt = project_to<coords::omt>( get_avatar().get_location() );
    const tripoint origin = here.getlocal( project_to<coords::ms>( omt ) );
    const tripoint turret_pos = origin + point( 5, 5 );
    manual_mapgen( omt, manual_update_mapgen, update_mapgen_test_update_place_damaged_turret );
    here.spawn_monsters( true );
    monster *const turret = get_creature_tracker().creature_at<monster>( turret_pos );
    REQUIRE( turret != nullptr );
    CHECK( turret->type->id == mon_turret_rifle );
    CHECK( turret->get_hp() == turret->get_hp_max() / 2 );
    REQUIRE( turret->ammo.count( itype_556 ) == 1 );
    CHECK( turret->ammo.at( itype_556 ) == 80 );
}
