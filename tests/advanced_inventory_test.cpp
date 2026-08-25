#include "catch/catch.hpp"

#include "activity_actor_definitions.h"
#include "advanced_inv_area.h"
#include "advanced_inv_pane.h"
#include "avatar.h"
#include "inventory_ui.h"
#include "item.h"
#include "item_pocket.h"
#include "json.h"
#include "json_loader.h"
#include "map_helpers.h"
#include "player_activity.h"
#include "player_helpers.h"
#include "uistate.h"

TEST_CASE( "advanced inventory state preserves 0.G numeric locations",
           "[advanced_inventory][save][backport]" )
{
    CHECK( static_cast<int>( AIM_WORN ) == 13 );

    advanced_inv_pane_save_state state;
    JsonObject old_state = json_loader::from_string(
                               R"({"pane_area_idx":13,"pane_selected_idx":2})" ).get_object();
    state.deserialize( old_state, "pane_" );

    CHECK( state.area_idx == AIM_WORN );
    CHECK( state.selected_idx == 2 );
    CHECK( state.container == item_location::nowhere );
    CHECK( state.container_base_loc == NUM_AIM_LOCATIONS );
}

TEST_CASE( "advanced inventory container state falls back instead of opening a blank pane",
           "[advanced_inventory][container][save][backport]" )
{
    clear_avatar();
    avatar &dummy = get_avatar();
    advanced_inv_pane_save_state state;
    advanced_inventory_pane pane;
    pane.save_state = &state;

    SECTION( "missing old-save container falls back to all locations" ) {
        state.area_idx = AIM_CONTAINER;
        CHECK( pane.load_container_settings( AIM_CONTAINER ) == AIM_ALL );
        CHECK_FALSE( pane.container );
    }

    SECTION( "invalid saved container falls back to its base location" ) {
        state.area_idx = AIM_CONTAINER;
        state.container_base_loc = AIM_INVENTORY;
        state.container = dummy.i_add( item( "test_baseball" ) );

        CHECK( pane.load_container_settings( AIM_CONTAINER ) == AIM_INVENTORY );
        CHECK_FALSE( pane.container );
    }

    SECTION( "valid saved container restores container view" ) {
        state.area_idx = AIM_CONTAINER;
        state.container_base_loc = AIM_INVENTORY;
        state.container = dummy.i_add( item( "test_backpack" ) );

        CHECK( pane.load_container_settings( AIM_CONTAINER ) == AIM_CONTAINER );
        CHECK( pane.container == state.container );
        CHECK( pane.container_base_loc == AIM_INVENTORY );
    }

    SECTION( "saved container is not restored for a non-container pane" ) {
        state.container_base_loc = AIM_INVENTORY;
        state.container = dummy.i_add( item( "test_backpack" ) );

        CHECK( pane.load_container_settings( AIM_INVENTORY ) == AIM_INVENTORY );
        CHECK_FALSE( pane.container );
    }
}

TEST_CASE( "advanced inventory uses the selected container capacity",
           "[advanced_inventory][container][capacity][backport]" )
{
    clear_avatar();
    clear_map();
    avatar &dummy = get_avatar();
    item_location container = dummy.i_add( item( "test_backpack" ) );

    advanced_inventory_pane pane;
    pane.container = container;
    advanced_inv_area container_area( AIM_CONTAINER );
    pane.set_area( container_area );

    CHECK( pane.free_volume( container_area ) == container->get_remaining_capacity() );

    pane.container = item_location::nowhere;
    CHECK( pane.free_volume( container_area ) == 0_ml );
    pane.container = container;

    advanced_inv_area tile_area( AIM_CENTER );
    tile_area.pos = dummy.pos();
    pane.set_area( tile_area );
    CHECK( pane.free_volume( tile_area ) == tile_area.free_volume() );
    CHECK( pane.free_volume( tile_area ) != container->get_remaining_capacity() );
}

static void finish_insert_activity( avatar &dummy, const item_location &container,
                                    const item_location &candidate, int count )
{
    dummy.activity = player_activity( insert_item_activity_actor(
                                          container, { { candidate, count } } ) );
    dummy.activity.start_or_resume( dummy, false );
    dummy.moves = 100000;
    dummy.activity.do_turn( dummy );
}

TEST_CASE( "direct Insert selector and activity share containment rules",
           "[inventory][insert][container][backport]" )
{
    clear_avatar();
    avatar &dummy = get_avatar();

    SECTION( "direct rigid insertion is offered and succeeds" ) {
        item_location container = dummy.i_add( item( "test_briefcase" ) );
        item_location candidate = dummy.i_add( item( "test_baseball" ) );
        inventory_holster_preset preset( container, &dummy );

        REQUIRE( can_insert_item_directly( container, candidate ).success() );
        CHECK( preset.is_shown( candidate ) );
        CHECK( preset.get_denial( candidate ).empty() );
        finish_insert_activity( dummy, container, candidate, 0 );
        CHECK_FALSE( candidate );
        CHECK( container->num_item_stacks() == 1 );
    }

    SECTION( "non-rigid nested insertion is denied when its parent is full" ) {
        item outer( "test_mini_backpack" );
        REQUIRE( outer.put_in( item( "test_backpack" ),
                               item_pocket::pocket_type::CONTAINER ).success() );
        for( int i = 0; i < 4; ++i ) {
            REQUIRE( outer.put_in( item( "test_baseball" ),
                                   item_pocket::pocket_type::CONTAINER ).success() );
        }
        item_location outer_loc = dummy.i_add( outer );
        item *nested_ptr = nullptr;
        for( item *entry : outer_loc->all_items_top() ) {
            if( entry->typeId() == itype_id( "test_backpack" ) ) {
                nested_ptr = entry;
                break;
            }
        }
        REQUIRE( nested_ptr );
        item_location container( outer_loc, nested_ptr );
        item_location candidate = dummy.i_add( item( "test_baseball" ) );
        inventory_holster_preset preset( container, &dummy );

        REQUIRE_FALSE( can_insert_item_directly( container, candidate ).success() );
        CHECK( preset.is_shown( candidate ) );
        CHECK_FALSE( preset.get_denial( candidate ).empty() );
        finish_insert_activity( dummy, container, candidate, 0 );
        CHECK( candidate );
        CHECK( container->is_container_empty() );
    }

    SECTION( "charge insertion is offered when a parent permits a partial move" ) {
        item outer( "test_mini_backpack" );
        REQUIRE( outer.put_in( item( "test_backpack" ),
                               item_pocket::pocket_type::CONTAINER ).success() );
        for( int i = 0; i < 3; ++i ) {
            REQUIRE( outer.put_in( item( "test_baseball" ),
                                   item_pocket::pocket_type::CONTAINER ).success() );
        }
        item_location outer_loc = dummy.i_add( outer );
        item *nested_ptr = nullptr;
        for( item *entry : outer_loc->all_items_top() ) {
            if( entry->typeId() == itype_id( "test_backpack" ) ) {
                nested_ptr = entry;
                break;
            }
        }
        REQUIRE( nested_ptr );
        item_location container( outer_loc, nested_ptr );
        item charge_item( "battery" );
        charge_item.charges = 100000;
        item_location candidate = dummy.i_add( charge_item );
        const int initial_charges = candidate->charges;
        const int parent_limit = container.max_charges_by_parent_recursive( *candidate );
        REQUIRE( parent_limit > 0 );
        REQUIRE( parent_limit < initial_charges );
        inventory_holster_preset preset( container, &dummy );

        REQUIRE( can_insert_item_directly( container, candidate ).success() );
        CHECK( preset.is_shown( candidate ) );
        CHECK( preset.get_denial( candidate ).empty() );
        finish_insert_activity( dummy, container, candidate, initial_charges );
        REQUIRE( candidate );
        CHECK( candidate->charges == initial_charges - parent_limit );
        CHECK_FALSE( container->is_container_empty() );
    }

    SECTION( "a container cannot be inserted into itself" ) {
        item_location container = dummy.i_add( item( "test_backpack" ) );
        inventory_holster_preset preset( container, &dummy );

        CHECK_FALSE( preset.is_shown( container ) );
        REQUIRE_FALSE( can_insert_item_directly( container, container ).success() );
        finish_insert_activity( dummy, container, container, 0 );
        CHECK( container );
        CHECK( container.where() == item_location::type::character );
    }
}
