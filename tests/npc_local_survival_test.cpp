#include <algorithm>
#include <vector>

#include "calendar.h"
#include "cata_catch.h"
#include "clzones.h"
#include "faction.h"
#include "game.h"
#include "item.h"
#include "map.h"
#include "map_helpers.h"
#include "npc.h"
#include "player_helpers.h"
#include "point.h"
#include "stomach.h"
#include "type_id.h"
#include "units.h"
#include "veh_type.h"
#include "vehicle.h"
#include "weather.h"

static const faction_id faction_free_merchants( "free_merchants" );
static const faction_id faction_your_followers( "your_followers" );

static const itype_id itype_meat_fatty_cooked( "meat_fatty_cooked" );
static const itype_id itype_sandwich_cheese_grilled( "sandwich_cheese_grilled" );
static const itype_id itype_sweater( "sweater" );
static const itype_id itype_water_clean( "water_clean" );

static const ter_str_id ter_t_dirt( "t_dirt" );
static const ter_str_id ter_t_floor( "t_floor" );
static const ter_str_id ter_t_shrub( "t_shrub" );
static const ter_str_id ter_t_wall_metal( "t_wall_metal" );
static const ter_str_id ter_t_water_sh( "t_water_sh" );

static const vpart_id vpart_box( "box" );
static const vpart_id vpart_cargo_lock( "cargo_lock" );
static const vpart_id vpart_frame( "frame" );
static const vproto_id vehicle_prototype_none( "none" );

static const zone_type_id zone_type_FARM_PLOT( "FARM_PLOT" );
static const zone_type_id zone_type_LOOT_UNSORTED( "LOOT_UNSORTED" );
static const zone_type_id zone_type_NO_NPC_PICKUP( "NO_NPC_PICKUP" );

namespace
{
npc &setup_survival_npc()
{
    clear_avatar();
    clear_map();
    get_avatar().setpos( tripoint( 5, 5, 0 ) );

    npc &guy = spawn_npc( point( 60, 60 ), "test_talker" );
    clear_character( guy );
    guy.set_fac( faction_your_followers );
    guy.set_attitude( NPCATT_FOLLOW );
    guy.rules.set_flag( ally_rule::allow_pick_up );
    guy.set_hunger( 0 );
    guy.set_thirst( 0 );
    guy.set_fatigue( 0 );
    guy.stomach.empty();
    REQUIRE( guy.is_player_ally() );
    return guy;
}

void add_tile_zone( const std::string &name, const zone_type_id &type, const tripoint &p,
                    bool personal = false )
{
    const tripoint abs = get_map().getglobal( p ).raw();
    zone_manager &mgr = zone_manager::get_manager();
    mgr.add( name, type, faction_your_followers, false, true, abs, abs, nullptr, personal );
    mgr.cache_data();
}

vehicle &add_cargo_vehicle( const tripoint &p, npc &owner, bool locked )
{
    map &here = get_map();
    vehicle *veh = here.add_vehicle( vehicle_prototype_none, p, 0_degrees, 0, 0 );
    REQUIRE( veh != nullptr );
    REQUIRE( veh->install_part( point_zero, vpart_frame ) >= 0 );
    const int cargo = veh->install_part( point_zero, vpart_box );
    REQUIRE( cargo >= 0 );
    if( locked ) {
        REQUIRE( veh->install_part( point_zero, vpart_cargo_lock ) >= 0 );
    }
    veh->set_owner( owner );
    here.add_vehicle_to_cache( veh );
    return *veh;
}

bool contains_candidate( const std::vector<npc::local_item_candidate> &items,
                         const itype_id &type )
{
    return std::any_of( items.begin(), items.end(), [&]( const npc::local_item_candidate &candidate ) {
        return candidate.loc && candidate.loc->typeId() == type;
    } );
}
} // namespace

TEST_CASE( "NPC acquires local food and clean water", "[npc][needs][food]" )
{
    npc &guy = setup_survival_npc();
    map &here = get_map();
    const tripoint food_pos = guy.pos() + tripoint_east;

    SECTION( "ground food is found and consumed" ) {
        guy.set_hunger( 300 );
        guy.set_stored_kcal( 5000 );
        here.add_item_or_charges( food_pos, item( itype_sandwich_cheese_grilled ) );

        REQUIRE( contains_candidate( guy.find_local_food(), itype_sandwich_cheese_grilled ) );
        CHECK( guy.consume_local_food( false ) );
        CHECK_FALSE( here.has_items( food_pos ) );
    }

    SECTION( "clean water uses normal consumption" ) {
        guy.set_thirst( 200 );
        item clean_water( itype_water_clean, calendar::turn, 1 );
        here.add_item_or_charges( food_pos, clean_water );
        const units::volume water_before = guy.stomach.get_water();

        REQUIRE( contains_candidate( guy.find_local_food(), itype_water_clean ) );
        CHECK( guy.consume_local_food( false ) );
        CHECK( guy.stomach.get_water() > water_before );
    }

    SECTION( "untreated terrain water is not directly ingested" ) {
        guy.set_thirst( 200 );
        here.ter_set( food_pos, ter_t_water_sh );
        CHECK( guy.find_local_clean_water().empty() );
        CHECK_FALSE( guy.drink_local_clean_water( false ) );
        CHECK( guy.stomach.get_water() == 0_ml );
    }
}

TEST_CASE( "NPC local acquisition respects ownership and follower rules", "[npc][needs][rules]" )
{
    npc &guy = setup_survival_npc();
    map &here = get_map();
    const tripoint target = guy.pos() + tripoint_east;
    guy.set_hunger( 300 );

    SECTION( "pickup disabled" ) {
        guy.rules.clear_flag( ally_rule::allow_pick_up );
        here.add_item_or_charges( target, item( itype_sandwich_cheese_grilled ) );
        CHECK( guy.find_local_food().empty() );
    }

    SECTION( "another faction owns the food" ) {
        item owned_food( itype_sandwich_cheese_grilled );
        owned_food.set_owner( faction_free_merchants );
        here.add_item_or_charges( target, owned_food );
        CHECK( guy.find_local_food().empty() );
    }

    SECTION( "unowned food remains available" ) {
        here.add_item_or_charges( target, item( itype_sandwich_cheese_grilled ) );
        CHECK( contains_candidate( guy.find_local_food(), itype_sandwich_cheese_grilled ) );
    }
}

TEST_CASE( "NPC local acquisition respects protected zones", "[npc][needs][zones]" )
{
    npc &guy = setup_survival_npc();
    map &here = get_map();
    const tripoint target = guy.pos() + tripoint_east;
    guy.set_hunger( 300 );
    here.add_item_or_charges( target, item( itype_sandwich_cheese_grilled ) );

    SECTION( "personal zone" ) {
        add_tile_zone( "Personal supplies", zone_type_LOOT_UNSORTED, target, true );
        REQUIRE( zone_manager::get_manager().has_personal( here.getglobal( target ) ) );
        CHECK( guy.find_local_food().empty() );
    }

    SECTION( "no NPC pickup zone" ) {
        add_tile_zone( "Protected supplies", zone_type_NO_NPC_PICKUP, target );
        CHECK( guy.find_local_food().empty() );
    }
}

TEST_CASE( "NPC local acquisition uses only unlocked owned vehicle cargo",
           "[npc][needs][vehicle]" )
{
    npc &guy = setup_survival_npc();
    const tripoint target = guy.pos() + tripoint_east;
    guy.set_hunger( 300 );
    const bool locked = GENERATE( false, true );
    CAPTURE( locked );

    vehicle &veh = add_cargo_vehicle( target, guy, locked );
    const int cargo = veh.part_with_feature( 0, VPFLAG_CARGO, true );
    REQUIRE( cargo >= 0 );
    REQUIRE( veh.add_item( cargo, item( itype_sandwich_cheese_grilled ) ) );

    if( locked ) {
        CHECK( guy.find_local_food().empty() );
    } else {
        CHECK( contains_candidate( guy.find_local_food(), itype_sandwich_cheese_grilled ) );
    }
}

TEST_CASE( "NPC warmth response uses inventory ground cargo and shelter", "[npc][needs][warmth]" )
{
    npc &guy = setup_survival_npc();
    map &here = get_map();
    const tripoint target = guy.pos() + tripoint_east;
    guy.set_all_parts_temp_conv( BODYTEMP_VERY_COLD );
    REQUIRE( guy.needs_warmth() );

    SECTION( "inventory clothing" ) {
        guy.i_add( item( itype_sweater ) );
        CHECK( guy.wear_warmest_inventory_item() );
        CHECK( guy.is_wearing( itype_sweater ) );
    }

    SECTION( "ground clothing" ) {
        here.add_item_or_charges( target, item( itype_sweater ) );
        CHECK( guy.wear_local_clothing( false ) );
        CHECK( guy.is_wearing( itype_sweater ) );
    }

    SECTION( "unlocked cargo clothing" ) {
        vehicle &veh = add_cargo_vehicle( target, guy, false );
        const int cargo = veh.part_with_feature( 0, VPFLAG_CARGO, true );
        REQUIRE( cargo >= 0 );
        REQUIRE( veh.add_item( cargo, item( itype_sweater ) ) );
        CHECK( guy.wear_local_clothing( false ) );
        CHECK( guy.is_wearing( itype_sweater ) );
    }

    SECTION( "nearby indoor shelter" ) {
        here.ter_set( guy.pos(), ter_t_dirt );
        here.ter_set( target, ter_t_floor );
        CHECK( guy.take_local_shelter() );
        CHECK( guy.pos() == target );
    }
}

TEST_CASE( "NPC local search skips an unreachable best food candidate", "[npc][needs][pathing]" )
{
    npc &guy = setup_survival_npc();
    map &here = get_map();
    guy.set_hunger( 300 );
    guy.set_stored_kcal( 5000 );

    const tripoint unreachable = guy.pos() + tripoint( 4, 0, 0 );
    for( const tripoint &wall : here.points_in_radius( unreachable, 1 ) ) {
        if( wall != unreachable ) {
            here.ter_set( wall, ter_t_wall_metal );
        }
    }
    here.add_item_or_charges( unreachable, item( itype_meat_fatty_cooked ) );

    const tripoint fallback = guy.pos() + tripoint_east;
    here.add_item_or_charges( fallback, item( itype_sandwich_cheese_grilled ) );

    REQUIRE( guy.find_local_food().size() == 2 );
    CHECK( guy.consume_local_food( true ) );
    CHECK( here.has_items( unreachable ) );
    CHECK_FALSE( here.has_items( fallback ) );
}

TEST_CASE( "NPC emergency foraging excludes protected land", "[npc][needs][foraging]" )
{
    npc &guy = setup_survival_npc();
    map &here = get_map();
    const tripoint target = guy.pos() + tripoint_east;
    here.ter_set( target, ter_t_shrub );

    SECTION( "ordinary hunger does not trigger foraging" ) {
        CHECK_FALSE( guy.forage_local_food() );
    }

    SECTION( "severe hunger permits wild forage" ) {
        guy.set_stored_kcal( 5000 );
        const std::vector<tripoint> harvest = guy.find_local_harvest();
        CHECK( std::find( harvest.begin(), harvest.end(), target ) != harvest.end() );
    }

    SECTION( "farm plot is excluded" ) {
        guy.set_stored_kcal( 5000 );
        add_tile_zone( "Farm", zone_type_FARM_PLOT, target );
        CHECK( guy.find_local_harvest().empty() );
    }

    SECTION( "personal zone is excluded" ) {
        guy.set_stored_kcal( 5000 );
        add_tile_zone( "Personal forage", zone_type_LOOT_UNSORTED, target, true );
        CHECK( guy.find_local_harvest().empty() );
    }

    SECTION( "no NPC pickup zone is excluded" ) {
        guy.set_stored_kcal( 5000 );
        add_tile_zone( "Protected forage", zone_type_NO_NPC_PICKUP, target );
        CHECK( guy.find_local_harvest().empty() );
    }
}
