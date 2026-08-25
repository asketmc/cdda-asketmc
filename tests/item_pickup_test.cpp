#include <algorithm>
#include <sstream>

#include "activity_actor_definitions.h"
#include "avatar.h"
#include "cata_catch.h"
#include "cata_utility.h"
#include "item.h"
#include "json.h"
#include "json_loader.h"
#include "map.h"
#include "map_helpers.h"
#include "messages.h"
#include "player_activity.h"
#include "player_helpers.h"
#include "pickup.h"
#include "rng.h"
#include "vehicle.h"
#include "vehicle_selector.h"
#include "veh_type.h"
#include "vpart_position.h"

static const itype_id itype_backpack_hiking( "backpack_hiking" );
static const itype_id itype_m4_carbine( "m4_carbine" );
static const itype_id itype_rope_6( "rope_6" );
static const vproto_id vehicle_prototype_test_cargo_space( "test_cargo_space" );

// This test case exists by way of documenting and exhibiting some potentially unexpected behavior
// of the following functions for transferring items into inventory:
//
// - Character::wear_item
// - Character::pick_up
// - Character::i_add
// - item::put_in
//
// namely, that these functions create *copies* of the items, and the original item
// references will not refer to the items placed in inventory.
TEST_CASE( "putting items into inventory with put_in or i_add", "[pickup][inventory]" )
{
    avatar &they = get_avatar();
    map &here = get_map();
    clear_avatar();
    clear_map();

    // Spawn items on the map at this location
    const tripoint ground = they.pos();
    item &rope_map = here.add_item( ground, item( itype_rope_6 ) );
    item &backpack_map = here.add_item( ground, item( itype_backpack_hiking ) );

    // Set unique IDs on the items, to verify their copies later
    std::string backpack_uid = random_string( 10 );
    std::string rope_uid = random_string( 10 );
    backpack_map.set_var( "uid", backpack_uid );
    rope_map.set_var( "uid", rope_uid );

    // Ensure avatar does not currently possess these items, or items with their uid
    REQUIRE_FALSE( they.has_item( backpack_map ) );
    REQUIRE_FALSE( they.has_item( rope_map ) );
    REQUIRE_FALSE( character_has_item_with_var_val( they, "uid", backpack_uid ) );
    REQUIRE_FALSE( character_has_item_with_var_val( they, "uid", rope_uid ) );

    WHEN( "avatar wears a hiking backpack from the ground with wear_item" ) {
        they.worn.clear();
        // Get the backpack from the iterator returned by wear_item,
        // for the reference to the backpack that the avatar is wearing now
        cata::optional<std::list<item>::iterator> worn = they.wear_item( backpack_map );
        item &backpack = **worn;

        THEN( "they have a copy of the backpack" ) {
            // They have the same type
            CHECK( backpack.typeId() == backpack_map.typeId() );
            // They have the same uid
            CHECK( backpack.get_var( "uid" ) == backpack_uid );
            CHECK( character_has_item_with_var_val( they, "uid", backpack_uid ) );
            // New one is in avatar's possession
            CHECK( they.has_item( backpack ) );
            // Original backpack from the ground is not
            CHECK_FALSE( they.has_item( backpack_map ) );
        }

        WHEN( "using put_in to put a rope directly into the backpack" ) {
            REQUIRE( backpack.put_in( rope_map, item_pocket::pocket_type::CONTAINER ).success() );

            THEN( "the original rope is not in inventory or the backpack" ) {
                CHECK_FALSE( they.has_item( rope_map ) );
                CHECK_FALSE( backpack.has_item( rope_map ) );
            }
            THEN( "they have a copy of the rope in inventory" ) {
                CHECK( character_has_item_with_var_val( they, "uid", rope_uid ) );
            }
            // FIXME: After put_in, there is no way to get the new copied item reference(?)
        }

        WHEN( "using i_add to put the rope into inventory" ) {
            // Add the rope to the inventory (goes in backpack, as it's the only thing worn)
            item_location rope_new = they.i_add( rope_map );

            THEN( "a copy of the rope item is in inventory and in the backpack" ) {
                CHECK( they.has_item( *rope_new ) );
                CHECK( backpack.has_item( *rope_new ) );
                CHECK( character_has_item_with_var_val( they, "uid", rope_uid ) );
            }
            THEN( "the original rope is not in inventory or the backpack" ) {
                CHECK_FALSE( they.has_item( rope_map ) );
                CHECK_FALSE( backpack.has_item( rope_map ) );
            }
        }
    }

    // The Character::pick_up function assigns an item pick-up activity to the character,
    // which can be executed with the process_activity() helper.
    // But Character::pick_up cannot wield or wear items in the act of picking them up;
    // the available storage needs to be worn ahead of time.
    GIVEN( "avatar is not wearing anything that can store items" ) {
        they.worn.clear();

        WHEN( "avatar tries to get the backpack with pick_up" ) {
            item_location backpack_loc( map_cursor( ground ), &backpack_map );
            const drop_locations &pack_droplocs = { std::make_pair( backpack_loc, 1 ) };
            they.pick_up( pack_droplocs );
            process_activity( they );

            THEN( "they fail to acquire the backpack" ) {
                CHECK_FALSE( character_has_item_with_var_val( they, "uid", backpack_uid ) );
            }
        }

        WHEN( "avatar tries to get the rope with pick_up" ) {
            item_location rope_loc( map_cursor( ground ), &rope_map );
            const drop_locations &rope_droplocs = { std::make_pair( rope_loc, 1 ) };
            they.pick_up( rope_droplocs );
            process_activity( they );

            THEN( "they fail to acquire the rope" ) {
                CHECK_FALSE( character_has_item_with_var_val( they, "uid", rope_uid ) );
            }
        }
    }
}

// The below incredibly-specific test case is designed as a regression test for #52422 in which
// picking up items from the ground could result in inventory items being dropped.
//
// One such case is when an "inner container" (container within a container) would be selected as
// the "best pocket" for a picked up item, but inserting the item makes it too big or heavy for its
// outer container, forcing it to be dropped on the ground (along with whatever was inserted).
//
// The reproduction use case here is: Wearing only a backpack containing a rope, when picking up
// an M4 from the ground, the M4 should go into the backpack, not into the rope, and neither the
// rope nor the M4 should be dropped.
TEST_CASE( "pickup m4 with a rope in a hiking backpack", "[pickup][container]" )
{
    avatar &they = get_avatar();
    map &here = get_map();
    clear_avatar();
    clear_map();

    // Spawn items on the map at this location
    const tripoint ground = they.pos();
    item &m4a1 = here.add_item( ground, item( itype_m4_carbine ) );
    item &rope_map = here.add_item( ground, item( itype_rope_6 ) );
    item &backpack_map = here.add_item( ground, item( itype_backpack_hiking ) );

    // Ensure that rope and backpack are containers, both capable of holding the M4
    REQUIRE( rope_map.is_container() );
    REQUIRE( backpack_map.is_container() );
    REQUIRE( rope_map.can_contain( m4a1 ).success() );
    REQUIRE( backpack_map.can_contain( m4a1 ).success() );
    REQUIRE( backpack_map.can_contain( rope_map ).success() );

    // Give the M4 a serial number (and the rope too, it's also a deadly weapon)
    std::string m4_uid = random_string( 10 );
    std::string rope_uid = random_string( 10 );
    m4a1.set_var( "uid", m4_uid );
    rope_map.set_var( "uid", rope_uid );

    GIVEN( "avatar is wearing a backpack with a short rope in it" ) {
        // What happens to the stuff on the ground?
        CAPTURE( here.i_at( ground ).size() );
        // Wear backpack from map and get the new item reference
        cata::optional<std::list<item>::iterator> worn = they.wear_item( backpack_map );
        item &backpack = **worn;
        REQUIRE( they.has_item( backpack ) );
        // Put the rope in
        item_location rope = they.i_add( rope_map );
        REQUIRE( they.has_item( *rope ) );

        WHEN( "they pick up the M4" ) {
            // Get item_location for m4 on the map
            item_location m4_loc( map_cursor( they.pos() ), &m4a1 );
            const drop_locations &thing = { std::make_pair( m4_loc, 1 ) };
            CHECK_FALSE( backpack.has_item( m4a1 ) );
            // Now pick up the M4
            they.pick_up( thing );
            process_activity( they );

            // Neither the rope nor the M4 should have been dropped
            THEN( "they should have the rope and M4 still in possession" ) {
                CHECK( character_has_item_with_var_val( they, "uid", rope_uid ) );
                CHECK( character_has_item_with_var_val( they, "uid", m4_uid ) );
            }
        }
    }
}

TEST_CASE( "lost pickup targets survive serialization without retargeting",
           "[pickup][activity][serialization]" )
{
    avatar &they = get_avatar();
    map &here = get_map();
    clear_avatar();
    clear_map();
    const tripoint ground = they.pos();
    REQUIRE( they.wear_item( item( itype_backpack_hiking ) ) );

    item &lost_jeans = here.add_item( ground, item( "jeans" ) );
    item &lost_shirt = here.add_item( ground, item( "tshirt" ) );
    item &surviving_target = here.add_item( ground, item( "rag" ) );
    item &unrelated = here.add_item( ground, item( "rock" ) );
    surviving_target.set_var( "uid", "pickup-survivor" );
    unrelated.set_var( "uid", "must-not-retarget" );

    std::vector<item_location> targets {
        item_location( map_cursor( ground ), &lost_jeans ),
        item_location( map_cursor( ground ), &lost_shirt ),
        item_location( map_cursor( ground ), &surviving_target )
    };
    they.activity = player_activity( pickup_activity_actor( targets, { 1, 1, 1 }, ground, false ) );

    here.i_rem( ground, &lost_jeans );
    here.i_rem( ground, &lost_shirt );

    std::ostringstream saved;
    JsonOut json( saved );
    they.activity.serialize( json );
    CHECK( saved.str().find( "jeans" ) != std::string::npos );
    CHECK( saved.str().find( "t-shirt" ) != std::string::npos );
    CHECK( saved.str().find( "on the ground" ) != std::string::npos );

    JsonObject saved_activity = json_loader::from_string( saved.str() ).get_object();
    they.activity.deserialize( saved_activity );
    they.activity.start_or_resume( they, true );
    Messages::clear_messages();
    const std::string debug_message = capture_debugmsg_during( [&they]() {
        process_activity( they );
    } );

    CHECK( debug_message.empty() );
    CHECK( character_has_item_with_var_val( they, "uid", "pickup-survivor" ) );
    CHECK_FALSE( character_has_item_with_var_val( they, "uid", "must-not-retarget" ) );
    REQUIRE( here.i_at( ground ).size() == 1 );
    CHECK( here.i_at( ground ).begin()->get_var( "uid" ) == "must-not-retarget" );

    const std::vector<std::pair<std::string, std::string>> messages =
        Messages::recent_messages( 0 );
    CHECK( std::any_of( messages.begin(), messages.end(), []( const auto & message ) {
        return message.second.find( "2 items you were picking up are no longer there" ) !=
               std::string::npos;
    } ) );
}

TEST_CASE( "never-resolved pickup target remains a debug error", "[pickup][activity]" )
{
    avatar &they = get_avatar();
    clear_avatar();
    std::vector<item_location> targets { item_location::nowhere };
    std::vector<int> quantities { 1 };
    bool stash_successful = true;
    they.moves = 100;

    const std::string debug_message = capture_debugmsg_during( [&]() {
        Pickup::do_pickup( targets, quantities, false, stash_successful );
    } );

    CHECK( debug_message.find( "had an invalid location" ) != std::string::npos );
}

TEST_CASE( "pickup target descriptions cover non-map locations",
           "[pickup][activity][serialization]" )
{
    avatar &they = get_avatar();
    map &here = get_map();
    clear_avatar();
    clear_map();
    npc &container_owner = spawn_npc( they.pos().xy() + point_west, "test_talker" );

    item rag( "rag" );
    REQUIRE( they.wield( rag ) );
    item_location character_item = they.get_wielded_item();
    item_location container = container_owner.i_add( item( itype_backpack_hiking ) );
    REQUIRE( character_item );
    REQUIRE( container );
    REQUIRE( container->put_in( item( "tshirt" ),
                                item_pocket::pocket_type::CONTAINER ).success() );
    item_location contained_item( container, &container->only_item() );
    REQUIRE( contained_item );

    const tripoint vehicle_pos = they.pos() + tripoint_east;
    vehicle *veh = here.add_vehicle( vehicle_prototype_test_cargo_space, vehicle_pos,
                                     0_degrees, 0, 0 );
    REQUIRE( veh != nullptr );
    const cata::optional<vpart_reference> cargo =
        here.veh_at( vehicle_pos ).part_with_feature( "CARGO", true );
    REQUIRE( cargo );
    const cata::optional<vehicle_stack::iterator> added =
        veh->add_item( cargo->part(), item( "rock" ) );
    REQUIRE( added );
    item_location vehicle_item( vehicle_cursor( cargo->vehicle(), cargo->part_index() ), & **added );
    REQUIRE( vehicle_item );

    player_activity activity( pickup_activity_actor(
                                  { character_item, contained_item, vehicle_item },
                                  { 1, 1, 1 }, cata::nullopt, false ) );
    std::ostringstream saved;
    JsonOut json( saved );
    activity.serialize( json );

    CHECK( saved.str().find( "in a character's inventory" ) != std::string::npos );
    CHECK( saved.str().find( "in a container" ) != std::string::npos );
    CHECK( saved.str().find( "in a vehicle" ) != std::string::npos );

    item_location loaded_character;
    JsonValue character_json = json_loader::from_string( serialize( character_item ) );
    REQUIRE( character_json.read( loaded_character ) );
    REQUIRE( loaded_character );
    CHECK( loaded_character.where() == item_location::type::character );
    CHECK( loaded_character->typeId() == itype_id( "rag" ) );

    item_location loaded_contained;
    JsonValue contained_json = json_loader::from_string( serialize( contained_item ) );
    REQUIRE( contained_json.read( loaded_contained ) );
    REQUIRE( loaded_contained );
    CHECK( loaded_contained.where() == item_location::type::container );
    CHECK( loaded_contained.where_recursive() == item_location::type::character );
    CHECK( loaded_contained->typeId() == itype_id( "tshirt" ) );

    item_location loaded_vehicle;
    JsonValue vehicle_json = json_loader::from_string( serialize( vehicle_item ) );
    REQUIRE( vehicle_json.read( loaded_vehicle ) );
    REQUIRE( loaded_vehicle );
    CHECK( loaded_vehicle.where() == item_location::type::vehicle );
    CHECK( loaded_vehicle->typeId() == itype_id( "rock" ) );
}

