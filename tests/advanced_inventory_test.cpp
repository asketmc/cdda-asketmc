#include "catch/catch.hpp"

#include "activity_actor_definitions.h"
#include "advanced_inv.h"
#include "advanced_inv_area.h"
#include "advanced_inv_pane.h"
#include "avatar.h"
#include "inventory_ui.h"
#include "item.h"
#include "item_pocket.h"
#include "json.h"
#include "json_loader.h"
#include "map_helpers.h"
#include "map_selector.h"
#include "player_activity.h"
#include "player_helpers.h"
#include "uistate.h"

TEST_CASE( "advanced inventory state preserves 0.G numeric locations",
           "[advanced_inventory][save][backport]" )
{
    CHECK( static_cast<int>( AIM_WORN ) == 13 );
    CHECK( static_cast<int>( SORTBY_PRICE ) == 9 );
    CHECK( static_cast<int>( SORTBY_PRICEPERVOLUME ) == 10 );
    CHECK( static_cast<int>( SORTBY_PRICEPERWEIGHT ) == 11 );
    CHECK( static_cast<int>( SORTBY_STACKS ) == 12 );

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
    CHECK( pane.free_weight_capacity() == container->get_remaining_weight_capacity() );

    pane.container = item_location::nowhere;
    CHECK( pane.free_volume( container_area ) == 0_ml );
    CHECK( pane.free_weight_capacity() == 0_gram );
    pane.container = container;

    advanced_inv_area tile_area( AIM_CENTER );
    tile_area.pos = dummy.pos();
    pane.set_area( tile_area );
    CHECK( pane.free_volume( tile_area ) == tile_area.free_volume() );
    CHECK( pane.free_volume( tile_area ) != container->get_remaining_capacity() );
    CHECK( pane.free_weight_capacity() == units::mass_max );
}

TEST_CASE( "advanced inventory capacity sorting moves small fitting items first",
           "[advanced_inventory][capacity][sorting][backport]" )
{
    clear_avatar();
    clear_map();
    avatar &dummy = get_avatar();
    map &here = get_map();
    item &baseball = here.add_item( dummy.pos(), item( "test_baseball" ) );
    item &rock = here.add_item( dummy.pos(), item( "test_rock" ) );
    item &briefcase = here.add_item( dummy.pos(), item( "test_briefcase" ) );
    item_location baseball_loc( map_cursor( dummy.pos() ), &baseball );
    item_location rock_loc( map_cursor( dummy.pos() ), &rock );
    item_location briefcase_loc( map_cursor( dummy.pos() ), &briefcase );

    CHECK( advanced_inv_most_limited_capacity( 1_liter, 2_liter, 1_kilogram, 2_kilogram ) ==
           advanced_inv_capacity_limit::none );
    CHECK( advanced_inv_most_limited_capacity( 3_liter, 1_liter, 1_kilogram, 2_kilogram ) ==
           advanced_inv_capacity_limit::volume );
    CHECK( advanced_inv_most_limited_capacity( 1_liter, 2_liter, 3_kilogram, 1_kilogram ) ==
           advanced_inv_capacity_limit::weight );
    CHECK( advanced_inv_most_limited_capacity( 4_liter, 2_liter, 6_kilogram, 1_kilogram ) ==
           advanced_inv_capacity_limit::weight );
    CHECK( advanced_inv_most_limited_capacity( 6_liter, 1_liter, 4_kilogram, 2_kilogram ) ==
           advanced_inv_capacity_limit::volume );

    std::vector<drop_or_stash_item_info> items = {
        { rock_loc, 1 }, { baseball_loc, 1 }
    };
    REQUIRE( baseball.weight() < rock.weight() );

    SECTION( "front-processing activities receive the light item first" ) {
        sort_advanced_inv_move_all_items( items, advanced_inv_capacity_limit::weight, false );
        CHECK( items.front().loc() == baseball_loc );
    }

    SECTION( "back-processing activities receive the light item first" ) {
        sort_advanced_inv_move_all_items( items, advanced_inv_capacity_limit::weight, true );
        CHECK( items.back().loc() == baseball_loc );
    }

    SECTION( "front-processing activities receive the smaller item first" ) {
        std::vector<drop_or_stash_item_info> volume_items = {
            { briefcase_loc, 1 }, { baseball_loc, 1 }
        };
        REQUIRE( baseball.volume() < briefcase.volume() );
        sort_advanced_inv_move_all_items( volume_items, advanced_inv_capacity_limit::volume, false );
        CHECK( volume_items.front().loc() == baseball_loc );
    }
}

TEST_CASE( "advanced inventory filters incompatible container candidates before insertion",
           "[advanced_inventory][capacity][container][backport]" )
{
    clear_avatar();
    clear_map();
    avatar &dummy = get_avatar();
    map &here = get_map();
    item &container_item = here.add_item( dummy.pos(), item( "test_tool_belt" ) );
    item_location container( map_cursor( dummy.pos() ), &container_item );
    item_location incompatible = dummy.i_add( item( "test_baseball" ) );
    item_location fitting = dummy.i_add( item( "hammer_pocket_test" ) );

    REQUIRE_FALSE( can_insert_item_directly( container, incompatible ).success() );
    REQUIRE( can_insert_item_directly( container, fitting ).success() );
    REQUIRE( incompatible->weight() < fitting->weight() );

    std::vector<drop_or_stash_item_info> candidates = {
        { fitting, 1 }, { incompatible, 1 }
    };
    sort_advanced_inv_move_all_items( candidates, advanced_inv_capacity_limit::weight, false );
    REQUIRE( candidates.front().loc() == incompatible );
    filter_advanced_inv_container_items( candidates, container );
    REQUIRE( candidates.size() == 1 );
    CHECK( candidates.front().loc() == fitting );

    drop_locations inserts;
    inserts.emplace_back( fitting, 1 );
    dummy.assign_activity( player_activity( insert_item_activity_actor( container, inserts ) ) );
    dummy.activity.start_or_resume( dummy, false );
    dummy.moves = 100000;
    dummy.activity.do_turn( dummy );

    CHECK( incompatible );
    CHECK_FALSE( fitting );
    CHECK( container->num_item_stacks() == 1 );
}

TEST_CASE( "numeric quantity input accepts right only at the end",
           "[inventory][numeric][backport]" )
{
    CHECK( numeric_input_accepts_right( true, true, 2, 2 ) );
    CHECK( numeric_input_accepts_right( true, true, 3, 2 ) );
    CHECK_FALSE( numeric_input_accepts_right( false, true, 2, 2 ) );
    CHECK_FALSE( numeric_input_accepts_right( true, false, 2, 2 ) );
    CHECK_FALSE( numeric_input_accepts_right( true, true, 1, 2 ) );
}

TEST_CASE( "advanced inventory exposes amount and value-density sorts",
           "[advanced_inventory][sorting][backport]" )
{
    clear_avatar();
    clear_map();
    avatar &dummy = get_avatar();
    map &here = get_map();
    item &baseball = here.add_item( dummy.pos(), item( "test_baseball" ) );
    item &briefcase = here.add_item( dummy.pos(), item( "test_briefcase" ) );
    item_location baseball_loc( map_cursor( dummy.pos() ), &baseball );
    item_location briefcase_loc( map_cursor( dummy.pos() ), &briefcase );
    advanced_inventory_pane pane;

    SECTION( "amount" ) {
        pane.items.emplace_back( baseball_loc, 0, 1, AIM_CENTER, false );
        pane.items.emplace_back( baseball_loc, 1, 3, AIM_CENTER, false );
        pane.sortby = SORTBY_STACKS;
        pane.sort_items();
        CHECK( pane.items.front().stacks == 3 );
    }

    const auto value_per_volume = []( const item_location & loc ) {
        return static_cast<double>( loc->price( true ) ) / loc->volume().value();
    };
    const auto value_per_weight = []( const item_location & loc ) {
        return static_cast<double>( loc->price( true ) ) / loc->weight().value();
    };

    SECTION( "value per volume" ) {
        REQUIRE( value_per_volume( baseball_loc ) != value_per_volume( briefcase_loc ) );
        pane.items.emplace_back( baseball_loc, 0, 1, AIM_CENTER, false );
        pane.items.emplace_back( briefcase_loc, 1, 1, AIM_CENTER, false );
        pane.sortby = SORTBY_PRICEPERVOLUME;
        pane.sort_items();
        const item_location expected = value_per_volume( baseball_loc ) >
                                       value_per_volume( briefcase_loc ) ? baseball_loc : briefcase_loc;
        CHECK( pane.items.front().items.front() == expected );
    }

    SECTION( "value per weight" ) {
        REQUIRE( value_per_weight( baseball_loc ) != value_per_weight( briefcase_loc ) );
        pane.items.emplace_back( baseball_loc, 0, 1, AIM_CENTER, false );
        pane.items.emplace_back( briefcase_loc, 1, 1, AIM_CENTER, false );
        pane.sortby = SORTBY_PRICEPERWEIGHT;
        pane.sort_items();
        const item_location expected = value_per_weight( baseball_loc ) >
                                       value_per_weight( briefcase_loc ) ? baseball_loc : briefcase_loc;
        CHECK( pane.items.front().items.front() == expected );
    }
}

TEST_CASE( "classic pickup and drop columns sort by total weight or volume",
           "[inventory][pickup][drop][sorting][backport]" )
{
    clear_avatar();
    clear_map();
    avatar &dummy = get_avatar();
    map &here = get_map();
    item &briefcase = here.add_item( dummy.pos(), item( "test_briefcase" ) );
    item_location briefcase_loc( map_cursor( dummy.pos() ), &briefcase );
    std::vector<item_location> baseballs;
    for( int i = 0; i < 20; ++i ) {
        item &baseball = here.add_item( dummy.pos(), item( "test_baseball" ) );
        baseballs.emplace_back( map_cursor( dummy.pos() ), &baseball );
    }
    REQUIRE( baseballs.front()->weight() * baseballs.size() > briefcase.weight() );
    REQUIRE( baseballs.front()->volume() * baseballs.size() < briefcase.volume() );

    const item_category *shared_category = &briefcase.get_category_of_contents();
    inventory_column column;
    REQUIRE( column.add_entry( inventory_entry( baseballs, shared_category ) ) );
    REQUIRE( column.add_entry( inventory_entry( { briefcase_loc }, shared_category ) ) );

    column.set_sort_mode( inventory_sort_mode::weight );
    column.prepare_paging();
    auto entries = column.get_entries( []( const inventory_entry & entry ) {
        return entry.is_item();
    } );
    REQUIRE( entries.size() == 2 );
    CHECK( entries.front()->locations.size() == baseballs.size() );

    column.set_sort_mode( inventory_sort_mode::volume );
    column.prepare_paging();
    entries = column.get_entries( []( const inventory_entry & entry ) {
        return entry.is_item();
    } );
    REQUIRE( entries.size() == 2 );
    CHECK( entries.front()->any_item() == briefcase_loc );
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
