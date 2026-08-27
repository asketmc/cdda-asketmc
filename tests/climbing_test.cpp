#include "cata_catch.h"

#include "avatar.h"
#include "character.h"
#include "map.h"
#include "map_helpers.h"
#include "map_iterator.h"
#include "point.h"
#include "type_id.h"
#include "units.h"
#include "vehicle.h"

static const ter_id ter_open_air( "t_open_air" );
static const ter_id ter_pavement( "t_pavement" );
static const ter_id ter_rock( "t_rock" );
static const ter_id ter_wall( "t_wall" );
static const ter_id ter_chain_fence( "t_chainfence" );
static const ter_id ter_downspout( "t_gutter_downspout" );
static const furn_id furn_ladder( "f_ladder" );
static const trap_id trap_ledge( "tr_ledge" );
static const vproto_id vehicle_shopping_cart( "shopping_cart" );

static const tripoint drop_top( 60, 60, 0 );

static void prepare_drop( const int height )
{
    clear_map( -3, 0 );
    map &here = get_map();
    for( int z = 0; z >= -height; --z ) {
        for( const tripoint &p : here.points_in_radius( tripoint( drop_top.xy(), z ), 2 ) ) {
            here.set( p, ter_open_air, furn_id( "f_null" ) );
        }
    }
    here.trap_set( drop_top, trap_ledge );
    here.ter_set( tripoint( drop_top.xy(), -height ), ter_pavement );
    here.ter_set( tripoint( drop_top.xy(), -height - 1 ), ter_rock );
}

TEST_CASE( "supported ledge descent mirrors upward climbing", "[climbing][z-level]" )
{
    Character &you = get_avatar();
    map &here = get_map();

    SECTION( "a bare ledge remains risky" ) {
        prepare_drop( 1 );
        CHECK_FALSE( you.can_climb_down_safely( drop_top, 1 ) );
    }

    SECTION( "a downspout supports a safe descent" ) {
        prepare_drop( 1 );
        here.ter_set( drop_top + tripoint_below + tripoint_east, ter_downspout );
        CHECK( you.can_climb_down_safely( drop_top, 1 ) );
    }

    SECTION( "a ladder supports a safe descent" ) {
        prepare_drop( 1 );
        here.furn_set( drop_top + tripoint_below, furn_ladder );
        CHECK( you.can_climb_down_safely( drop_top, 1 ) );
    }

    SECTION( "a fence supports a safe descent" ) {
        prepare_drop( 1 );
        here.ter_set( drop_top + tripoint_below + tripoint_east, ter_chain_fence );
        CHECK( you.can_climb_down_safely( drop_top, 1 ) );
    }

    SECTION( "braced walls support a safe descent" ) {
        prepare_drop( 1 );
        const tripoint lower = drop_top + tripoint_below;
        for( const tripoint &offset : { tripoint_north, tripoint_south, tripoint_east,
                                       tripoint_west, tripoint_north_east } ) {
            here.ter_set( lower + offset, ter_wall );
        }
        CHECK( you.can_climb_down_safely( drop_top, 1 ) );
    }

    SECTION( "a vehicle supports a safe descent" ) {
        prepare_drop( 1 );
        const tripoint vehicle_pos = drop_top + tripoint_below + tripoint_east;
        REQUIRE( here.add_vehicle( vehicle_shopping_cart, vehicle_pos, 0_degrees ) );
        CHECK( you.can_climb_down_safely( drop_top, 1 ) );
    }
}

TEST_CASE( "multi-level ledge descent requires support on every level", "[climbing][z-level]" )
{
    Character &you = get_avatar();
    map &here = get_map();
    prepare_drop( 2 );

    const tripoint upper_support = drop_top + tripoint_below + tripoint_east;
    const tripoint lower_support = upper_support + tripoint_below;
    here.ter_set( upper_support, ter_downspout );
    CHECK_FALSE( you.can_climb_down_safely( drop_top, 2 ) );

    here.ter_set( lower_support, ter_downspout );
    CHECK( you.can_climb_down_safely( drop_top, 2 ) );
}
