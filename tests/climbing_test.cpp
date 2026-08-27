#include "cata_catch.h"

#include "avatar.h"
#include "cata_scope_helpers.h"
#include "character.h"
#include "iexamine.h"
#include "item.h"
#include "map.h"
#include "map_helpers.h"
#include "map_iterator.h"
#include "player_helpers.h"
#include "point.h"
#include "type_id.h"
#include "units.h"
#include "vehicle.h"

static const ter_str_id ter_open_air( "t_open_air" );
static const ter_str_id ter_pavement( "t_pavement" );
static const ter_str_id ter_rock( "t_rock" );
static const ter_str_id ter_wall( "t_wall" );
static const ter_str_id ter_chain_fence( "t_chainfence" );
static const ter_str_id ter_downspout( "t_gutter_downspout" );
static const furn_str_id furn_ladder( "f_ladder" );
static const furn_str_id furn_rope( "f_rope_up" );
static const furn_str_id furn_web( "f_web_up" );
static const trap_str_id trap_ledge( "tr_ledge" );
static const trait_id trait_web_rappel( "WEB_RAPPEL" );
static const json_character_flag json_flag_web_rappel( "WEB_RAPPEL" );
static const itype_id itype_grapnel_test( "grapnel" );
static const vproto_id vehicle_shopping_cart( "shopping_cart" );

static const tripoint drop_top( 60, 60, 0 );

static void prepare_drop( const int height )
{
    clear_map( -3, 0 );
    map &here = get_map();
    for( int z = 0; z >= -height; --z ) {
        for( const tripoint &p : here.points_in_radius( tripoint( drop_top.xy(), z ), 2 ) ) {
            here.set( p, ter_open_air.id(), furn_str_id( "f_null" ).id() );
        }
    }
    here.trap_set( drop_top, trap_ledge.id() );
    here.ter_set( tripoint( drop_top.xy(), -height ), ter_pavement.id() );
    here.ter_set( tripoint( drop_top.xy(), -height - 1 ), ter_rock.id() );
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
        here.ter_set( drop_top + tripoint_below + tripoint_east, ter_downspout.id() );
        CHECK( you.can_climb_down_safely( drop_top, 1 ) );
    }

    SECTION( "a ladder supports a safe descent" ) {
        prepare_drop( 1 );
        here.furn_set( drop_top + tripoint_below, furn_ladder.id() );
        CHECK( you.can_climb_down_safely( drop_top, 1 ) );
    }

    SECTION( "a fence supports a safe descent" ) {
        prepare_drop( 1 );
        here.ter_set( drop_top + tripoint_below + tripoint_east, ter_chain_fence.id() );
        CHECK( you.can_climb_down_safely( drop_top, 1 ) );
    }

    SECTION( "braced walls support a safe descent" ) {
        prepare_drop( 1 );
        const tripoint lower = drop_top + tripoint_below;
        for( const tripoint &offset : { tripoint_north, tripoint_south, tripoint_east,
                                       tripoint_west, tripoint_north_east } ) {
            here.ter_set( lower + offset, ter_wall.id() );
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
    here.ter_set( upper_support, ter_downspout.id() );
    CHECK_FALSE( you.can_climb_down_safely( drop_top, 2 ) );

    here.ter_set( lower_support, ter_downspout.id() );
    CHECK( you.can_climb_down_safely( drop_top, 2 ) );
}

TEST_CASE( "supported ledge descent action is safe and preserves climbing tools",
           "[climbing][z-level][iexamine]" )
{
    avatar &you = get_avatar();
    map &here = get_map();
    here.vertical_shift( 0 );
    clear_character( you );
    on_out_of_scope reset_you( [&here, &you]() {
        here.vertical_shift( 0 );
        clear_character( you );
    } );

    const tripoint start = drop_top + tripoint_west;
    you.setpos( start );
    you.moves = 1000;

    SECTION( "an unsupported ledge leaves the risky action untouched" ) {
        prepare_drop( 1 );
        const int starting_moves = you.moves;

        CHECK_FALSE( iexamine_helper::climb_down_supported_ledge(
                         you, drop_top, 1, 1.0f, 0.0f ) );
        CHECK( you.pos() == start );
        CHECK( you.moves == starting_moves );
    }

    SECTION( "one supported level descends without consuming a grapnel or deploying webs" ) {
        prepare_drop( 1 );
        here.ter_set( drop_top + tripoint_below + tripoint_east, ter_downspout.id() );
        you.i_add( item( itype_grapnel_test ) );
        you.set_mutation( trait_web_rappel );
        you.activate_mutation( trait_web_rappel );
        REQUIRE( you.has_amount( itype_grapnel_test, 1 ) );
        REQUIRE( you.has_active_mutation( trait_web_rappel ) );
        REQUIRE( you.has_flag( json_flag_web_rappel ) );

        CHECK( iexamine_helper::climb_down_supported_ledge(
                   you, drop_top, 1, 1.0f, 0.0f ) );
        CHECK( you.pos() == drop_top + tripoint_below );
        CHECK( you.has_amount( itype_grapnel_test, 1 ) );
        CHECK( here.furn( you.pos() ) != furn_rope.id() );
        CHECK( here.furn( you.pos() ) != furn_web.id() );
    }

    SECTION( "multi-level support descends the exact supported height" ) {
        prepare_drop( 2 );
        here.ter_set( drop_top + tripoint_below + tripoint_east, ter_downspout.id() );
        here.ter_set( drop_top + tripoint_below + tripoint_below + tripoint_east,
                      ter_downspout.id() );

        CHECK( iexamine_helper::climb_down_supported_ledge(
                   you, drop_top, 2, 1.0f, 0.0f ) );
        CHECK( you.pos() == drop_top + tripoint_below + tripoint_below );
        CHECK( here.furn( drop_top + tripoint_below ) != furn_web.id() );
    }
}
