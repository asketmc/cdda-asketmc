#include <iosfwd>
#include <vector>

#include "activity_actor_definitions.h"
#include "cata_catch.h"
#include "clzones.h"
#include "field_type.h"
#include "item.h"
#include "item_category.h"
#include "item_pocket.h"
#include "map_helpers.h"
#include "npc.h"
#include "player_helpers.h"
#include "point.h"
#include "ret_val.h"
#include "type_id.h"

static const activity_id ACT_MOVE_LOOT( "ACT_MOVE_LOOT" );
static const activity_id ACT_MULTIPLE_MOP( "ACT_MULTIPLE_MOP" );
static const faction_id faction_your_followers( "your_followers" );

static const itype_id itype_556( "556" );
static const itype_id itype_ammolink223( "ammolink223" );
static const itype_id itype_belt223( "belt223" );

static const vproto_id vehicle_prototype_shopping_cart( "shopping_cart" );

static const zone_type_id zone_type_LOOT_DRINK( "LOOT_DRINK" );
static const zone_type_id zone_type_LOOT_FOOD( "LOOT_FOOD" );
static const zone_type_id zone_type_LOOT_PDRINK( "LOOT_PDRINK" );
static const zone_type_id zone_type_LOOT_PFOOD( "LOOT_PFOOD" );
static const zone_type_id zone_type_LOOT_UNSORTED( "LOOT_UNSORTED" );
static const zone_type_id zone_type_LOOT_CUSTOM( "LOOT_CUSTOM" );
static const zone_type_id zone_type_LOOT_TOOLS( "LOOT_TOOLS" );
static const zone_type_id zone_type_MOPPING( "MOPPING" );
static const zone_type_id zone_type_zone_unload_all( "zone_unload_all" );

namespace
{
template <class T>
int _count_items_or_charges( const T &items, const itype_id &id )
{
    int n = 0;
    for( const item &it : items ) {
        if( it.typeId() == id ) {
            n += it.count();
        }
    }
    return n;
}

int count_items_or_charges( const tripoint src, const itype_id &id,
                            const cata::optional<vpart_reference> &vp )
{
    if( vp ) {
        return _count_items_or_charges( vp->vehicle().get_items( vp->part_index() ), id );
    }
    return _count_items_or_charges( get_map().i_at( src ), id );
}

void create_tile_zone( const std::string &name, const zone_type_id &zone_type, tripoint pos,
                       bool veh = false, bool personal = false )
{
    zone_manager &zm = zone_manager::get_manager();
    zm.add( name, zone_type, faction_your_followers, false, true, pos, pos, nullptr, personal, veh );
}

} // namespace

TEST_CASE( "NPC work ignores personal zones", "[zones][npc][basecamp]" )
{
    clear_avatar();
    clear_map();
    zone_manager &zm = zone_manager::get_manager();
    const tripoint personal_pos = tripoint_east;
    const tripoint shared_pos = tripoint_west;

    create_tile_zone( "Personal", zone_type_LOOT_UNSORTED, personal_pos, false, true );
    create_tile_zone( "Shared", zone_type_LOOT_UNSORTED, shared_pos );

    CHECK_FALSE( zm.has_nonpersonal( zone_type_LOOT_UNSORTED,
                                    get_map().getglobal( personal_pos ) ) );
    CHECK( zm.has_nonpersonal( zone_type_LOOT_UNSORTED, get_map().getglobal( shared_pos ) ) );
}

TEST_CASE( "NPC loot sorting cannot use personal zones", "[zones][npc][activities]" )
{
    clear_avatar();
    clear_map();
    get_avatar().setpos( tripoint_zero );
    map &here = get_map();
    standard_npc worker( "zone worker", tripoint_zero );
    worker.set_fac( faction_your_followers );
    const tripoint source = tripoint_east;
    const tripoint personal_destination = tripoint_west;
    const tripoint shared_destination = tripoint_north;
    item food( "test_bitter_almond" );

    SECTION( "a personal source is ignored" ) {
        create_tile_zone( "Personal source", zone_type_LOOT_UNSORTED, source, false, true );
        create_tile_zone( "Shared food", zone_type_LOOT_FOOD, shared_destination );
        here.add_item_or_charges( source, food );

        worker.assign_activity( player_activity( ACT_MOVE_LOOT ) );
        process_activity( worker );

        CHECK( _count_items_or_charges( here.i_at( source ), food.typeId() ) == 1 );
        CHECK( _count_items_or_charges( here.i_at( shared_destination ), food.typeId() ) == 0 );
    }

    SECTION( "a shared destination is used instead of a personal destination" ) {
        create_tile_zone( "Shared source", zone_type_LOOT_UNSORTED, source );
        create_tile_zone( "Personal food", zone_type_LOOT_FOOD, personal_destination, false, true );
        create_tile_zone( "Shared food", zone_type_LOOT_FOOD, shared_destination );
        here.add_item_or_charges( source, food );

        worker.assign_activity( player_activity( ACT_MOVE_LOOT ) );
        process_activity( worker );

        CHECK( _count_items_or_charges( here.i_at( personal_destination ), food.typeId() ) == 0 );
        CHECK( _count_items_or_charges( here.i_at( shared_destination ), food.typeId() ) == 1 );
    }

    SECTION( "a personal custom destination does not shadow a shared category destination" ) {
        shared_ptr_fast<loot_options> custom_options = make_shared_fast<loot_options>();
        custom_options->set_mark( "test_bitter_almond" );
        zone_manager::get_manager().add( "Personal custom", zone_type_LOOT_CUSTOM,
                                         faction_your_followers, false, true,
                                         personal_destination, personal_destination,
                                         custom_options, true, true );
        create_tile_zone( "Shared source", zone_type_LOOT_UNSORTED, source );
        create_tile_zone( "Shared food", zone_type_LOOT_FOOD, shared_destination );
        here.add_item_or_charges( source, food );

        worker.assign_activity( player_activity( ACT_MOVE_LOOT ) );
        process_activity( worker );

        CHECK( _count_items_or_charges( here.i_at( personal_destination ), food.typeId() ) == 0 );
        CHECK( _count_items_or_charges( here.i_at( shared_destination ), food.typeId() ) == 1 );
    }

    SECTION( "a shared vehicle destination remains available" ) {
        vehicle *cart = here.add_vehicle( vehicle_prototype_shopping_cart, shared_destination,
                                          0_degrees, 0, 0 );
        REQUIRE( cart != nullptr );
        cart->set_owner( worker );
        const optional_vpart_position cargo = here.veh_at( shared_destination );
        REQUIRE( cargo );
        create_tile_zone( "Shared source", zone_type_LOOT_UNSORTED, source );
        create_tile_zone( "Vehicle food", zone_type_LOOT_FOOD, shared_destination, true );
        here.add_item_or_charges( source, food );

        worker.assign_activity( player_activity( ACT_MOVE_LOOT ) );
        process_activity( worker );

        const cata::optional<vpart_reference> cargo_part = cargo.part_with_feature( "CARGO", true );
        REQUIRE( cargo_part );
        CHECK( _count_items_or_charges(
                   cargo_part->vehicle().get_items( cargo_part->part_index() ), food.typeId() ) == 1 );
    }
}

TEST_CASE( "NPC mopping fetches a stored mop", "[zones][npc][activities][mopping]" )
{
    clear_avatar();
    clear_map();
    map &here = get_map();
    standard_npc worker( "mopping worker", tripoint_zero );
    worker.set_fac( faction_your_followers );
    const tripoint target = tripoint_east;
    const tripoint tool_storage = tripoint_west;
    create_tile_zone( "Mopping", zone_type_MOPPING, target );
    create_tile_zone( "Tools", zone_type_LOOT_TOOLS, tool_storage );
    here.add_item_or_charges( tool_storage, item( "mop" ) );
    here.add_field( target, field_type_id( "fd_blood" ), 1 );
    REQUIRE( here.terrain_moppable( tripoint_bub_ms( target ) ) );
    REQUIRE_FALSE( worker.has_item_with( []( const item & it ) {
        return it.has_flag( flag_id( "MOP" ) );
    } ) );

    worker.assign_activity( player_activity( ACT_MULTIPLE_MOP ) );
    process_activity( worker );

    CHECK_FALSE( here.terrain_moppable( tripoint_bub_ms( target ) ) );
    CHECK( worker.has_item_with( []( const item & it ) {
        return it.has_flag( flag_id( "MOP" ) );
    } ) );
}

TEST_CASE( "zone unloading ammo belts", "[zones][items][ammo_belt][activities][unload]" )
{
    avatar &dummy = get_avatar();
    map &here = get_map();
    cata::optional<vpart_reference> vp;
    bool const in_vehicle = GENERATE( false, true );
    CAPTURE( in_vehicle );

    clear_avatar();
    clear_map();

    tripoint_abs_ms const start = here.getglobal( tripoint_east );
    bool const move_act = GENERATE( true, false );
    dummy.set_location( start );

    if( in_vehicle ) {
        REQUIRE(
            here.add_vehicle( vehicle_prototype_shopping_cart, tripoint_east, 0_degrees, 0, 0 ) );
        vp = here.veh_at( start ).part_with_feature( "CARGO", true );
        REQUIRE( vp );
        vp->vehicle().set_owner( dummy );
    }

    create_tile_zone( "Unsorted", zone_type_LOOT_UNSORTED, start.raw(), in_vehicle );
    create_tile_zone( "Unload All", zone_type_zone_unload_all, start.raw(), in_vehicle );

    item ammo_belt = item( itype_belt223, calendar::turn );
    ammo_belt.ammo_set( ammo_belt.ammo_default() );
    int belt_ammo_count_before_unload = ammo_belt.ammo_remaining();

    REQUIRE( belt_ammo_count_before_unload > 0 );

    WHEN( "unloading ammo belts using zone_unload_all " ) {
        if( in_vehicle ) {
            vp->vehicle().add_item( vp->part_index(), ammo_belt );
        } else {
            here.add_item_or_charges( tripoint_east, ammo_belt );
        }
        if( move_act ) {
            dummy.assign_activity( player_activity( ACT_MOVE_LOOT ) );
        } else {
            dummy.assign_activity( player_activity( unload_loot_activity_actor() ) );
        }
        CAPTURE( dummy.activity.id() );
        process_activity( dummy );

        THEN( "check that the ammo and linkages are both unloaded and the ammo belt is removed" ) {
            CHECK( count_items_or_charges( tripoint_east, itype_belt223, vp ) == 0 );
            CHECK( count_items_or_charges( tripoint_east,
                                           itype_ammolink223, vp ) == belt_ammo_count_before_unload );
            CHECK( count_items_or_charges( tripoint_east, itype_556, vp ) == belt_ammo_count_before_unload );
        }
    }
}

// Comestibles sorting is a bit awkward. Unlike other loot, they're almost
// always inside of a container, and their sort zone changes based on their
// shelf life and whether the container prevents rotting.
TEST_CASE( "zone sorting comestibles ", "[zones][items][food][activities]" )
{
    clear_map();
    zone_manager &zm = zone_manager::get_manager();

    const tripoint_abs_ms origin_pos;
    create_tile_zone( "Food", zone_type_LOOT_FOOD, tripoint_east );
    create_tile_zone( "Drink", zone_type_LOOT_DRINK, tripoint_west );

    SECTION( "without perishable zones" ) {
        GIVEN( "a non-perishable food" ) {
            item nonperishable_food( "test_bitter_almond" );
            REQUIRE_FALSE( nonperishable_food.goes_bad() );

            WHEN( "sorting without a container" ) {
                THEN( "should put in the food zone" ) {
                    CHECK( zm.get_near_zone_type_for_item( nonperishable_food, origin_pos ) == zone_type_LOOT_FOOD );
                }
            }
        }

        GIVEN( "a non-perishable drink" ) {
            item nonperishable_drink( "test_wine" );
            REQUIRE_FALSE( nonperishable_drink.goes_bad() );

            WHEN( "sorting without a container" ) {
                THEN( "should put in the drink zone" ) {
                    CHECK( zm.get_near_zone_type_for_item( nonperishable_drink, origin_pos ) == zone_type_LOOT_DRINK );
                }
            }
        }

        GIVEN( "a perishable food" ) {
            item perishable_food( "test_apple" );
            REQUIRE( perishable_food.goes_bad() );

            WHEN( "sorting without a container" ) {
                THEN( "should put in the food zone" ) {
                    CHECK( zm.get_near_zone_type_for_item( perishable_food, origin_pos ) == zone_type_LOOT_FOOD );
                }
            }
        }

        GIVEN( "a perishable drink" ) {
            item perishable_drink( "test_milk" );
            REQUIRE( perishable_drink.goes_bad() );

            WHEN( "sorting without a container" ) {
                THEN( "should put in the drink zone" ) {
                    CHECK( zm.get_near_zone_type_for_item( perishable_drink, origin_pos ) == zone_type_LOOT_DRINK );
                }
            }
        }
    }

    SECTION( "with perishable zones" ) {
        create_tile_zone( "PFood", zone_type_LOOT_PFOOD, tripoint_north );
        create_tile_zone( "PDrink", zone_type_LOOT_PDRINK, tripoint_south );

        GIVEN( "a non-perishable food" ) {
            item nonperishable_food( "test_bitter_almond" );
            REQUIRE_FALSE( nonperishable_food.goes_bad() );

            WHEN( "sorting without a container" ) {
                THEN( "should put in the food zone" ) {
                    CHECK( zm.get_near_zone_type_for_item( nonperishable_food, origin_pos ) == zone_type_LOOT_FOOD );
                }
            }

            WHEN( "sorting within an unsealed container" ) {
                item container( "test_watertight_open_sealed_container_250ml" );
                REQUIRE( container.put_in( nonperishable_food, item_pocket::pocket_type::CONTAINER ).success() );
                REQUIRE( !container.any_pockets_sealed() );

                THEN( "should put in the food zone" ) {
                    CHECK( zm.get_near_zone_type_for_item( container, origin_pos ) == zone_type_LOOT_FOOD );
                }
            }

            WHEN( "sorting within a sealed container" ) {
                item container( "test_watertight_open_sealed_container_250ml" );
                REQUIRE( container.put_in( nonperishable_food, item_pocket::pocket_type::CONTAINER ).success() );
                REQUIRE( container.seal() );
                REQUIRE( container.get_all_contained_pockets().front()->spoil_multiplier() ==
                         0.0f );
                REQUIRE( container.all_pockets_sealed() );

                THEN( "should put in the food zone" ) {
                    CHECK( zm.get_near_zone_type_for_item( container, origin_pos ) == zone_type_LOOT_FOOD );
                }
            }
        }

        GIVEN( "a non-perishable drink" ) {
            item nonperishable_drink( "test_wine" );
            REQUIRE_FALSE( nonperishable_drink.goes_bad() );

            WHEN( "sorting without a container" ) {
                THEN( "should put in the drink zone" ) {
                    CHECK( zm.get_near_zone_type_for_item( nonperishable_drink, origin_pos ) == zone_type_LOOT_DRINK );
                }
            }

            WHEN( "sorting within an unsealed container" ) {
                item container( "test_watertight_open_sealed_container_250ml" );
                REQUIRE( container.put_in( nonperishable_drink, item_pocket::pocket_type::CONTAINER ).success() );
                REQUIRE( !container.any_pockets_sealed() );

                THEN( "should put in the drink zone" ) {
                    CHECK( zm.get_near_zone_type_for_item( container, origin_pos ) == zone_type_LOOT_DRINK );
                }
            }

            WHEN( "sorting within a sealed container" ) {
                item container( "test_watertight_open_sealed_container_250ml" );
                REQUIRE( container.put_in( nonperishable_drink, item_pocket::pocket_type::CONTAINER ).success() );
                REQUIRE( container.seal() );
                REQUIRE( container.get_all_contained_pockets().front()->spoil_multiplier() ==
                         0.0f );
                REQUIRE( container.all_pockets_sealed() );

                THEN( "should put in the drink zone" ) {
                    CHECK( zm.get_near_zone_type_for_item( container, origin_pos ) == zone_type_LOOT_DRINK );
                }
            }
        }

        GIVEN( "a perishable food" ) {
            item perishable_food( "test_apple" );
            REQUIRE( perishable_food.goes_bad() );

            WHEN( "sorting without a container" ) {
                THEN( "should put in the perishable food zone" ) {
                    CHECK( zm.get_near_zone_type_for_item( perishable_food, origin_pos ) == zone_type_LOOT_PFOOD );
                }
            }

            WHEN( "sorting within an unsealed container" ) {
                item container( "test_watertight_open_sealed_container_250ml" );
                REQUIRE( container.put_in( perishable_food, item_pocket::pocket_type::CONTAINER ).success() );
                REQUIRE( !container.any_pockets_sealed() );

                THEN( "should put in the perishable food zone" ) {
                    CHECK( zm.get_near_zone_type_for_item( container, origin_pos ) == zone_type_LOOT_PFOOD );
                }
            }

            WHEN( "sorting within a sealed container" ) {
                item container( "test_watertight_open_sealed_container_250ml" );
                REQUIRE( container.put_in( perishable_food, item_pocket::pocket_type::CONTAINER ).success() );
                REQUIRE( container.seal() );
                REQUIRE( container.get_all_contained_pockets().front()->spoil_multiplier() ==
                         0.0f );
                REQUIRE( container.all_pockets_sealed() );

                THEN( "should put in the food zone" ) {
                    CHECK( zm.get_near_zone_type_for_item( container, origin_pos ) == zone_type_LOOT_FOOD );
                }
            }
        }

        GIVEN( "a perishable drink" ) {
            item perishable_drink( "test_milk" );
            REQUIRE( perishable_drink.goes_bad() );

            WHEN( "sorting without a container" ) {
                THEN( "should put in the perishable drink zone" ) {
                    CHECK( zm.get_near_zone_type_for_item( perishable_drink, origin_pos ) == zone_type_LOOT_PDRINK );
                }
            }

            WHEN( "sorting within an unsealed container" ) {
                item container( "test_watertight_open_sealed_container_250ml" );
                REQUIRE( container.put_in( perishable_drink, item_pocket::pocket_type::CONTAINER ).success() );
                REQUIRE( !container.any_pockets_sealed() );

                THEN( "should put in the perishable drink zone" ) {
                    CHECK( zm.get_near_zone_type_for_item( container, origin_pos ) == zone_type_LOOT_PDRINK );
                }
            }

            WHEN( "sorting within a sealed container" ) {
                item container( "test_watertight_open_sealed_container_250ml" );
                REQUIRE( container.put_in( perishable_drink, item_pocket::pocket_type::CONTAINER ).success() );
                REQUIRE( container.seal() );
                REQUIRE( container.get_all_contained_pockets().front()->spoil_multiplier() ==
                         0.0f );
                REQUIRE( container.all_pockets_sealed() );

                THEN( "should put in the drink zone" ) {
                    CHECK( zm.get_near_zone_type_for_item( container, origin_pos ) == zone_type_LOOT_DRINK );
                }
            }
        }
    }
}
