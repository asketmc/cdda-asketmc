#include <functional>
#include <functional>
#include <list>
#include <string>

#include "cata_catch.h"
#include "cata_utility.h"
#include "character.h"
#include "game.h"
#include "item.h"
#include "item_location.h"
#include "item_pocket.h"
#include "json_loader.h"
#include "map.h"
#include "map_helpers.h"
#include "map_selector.h"
#include "memory_fast.h"
#include "npc.h"
#include "optional.h"
#include "overmapbuffer.h"
#include "player_helpers.h"
#include "point.h"
#include "ret_val.h"
#include "rng.h"
#include "type_id.h"
#include "visitable.h"

static const itype_id itype_jeans( "jeans" );
static const itype_id itype_tshirt( "tshirt" );

TEST_CASE( "item_location_can_maintain_reference_despite_item_removal", "[item][item_location]" )
{
    clear_map();
    map &m = get_map();
    tripoint pos( 60, 60, 0 );
    m.i_clear( pos );
    m.add_item( pos, item( "jeans" ) );
    m.add_item( pos, item( "jeans" ) );
    m.add_item( pos, item( "tshirt" ) );
    m.add_item( pos, item( "jeans" ) );
    m.add_item( pos, item( "jeans" ) );
    map_cursor cursor( pos );
    item *tshirt = nullptr;
    cursor.visit_items( [&tshirt]( item * i, item * ) {
        if( i->typeId() == itype_tshirt ) {
            tshirt = i;
            return VisitResponse::ABORT;
        }
        return VisitResponse::NEXT;
    } );
    REQUIRE( tshirt != nullptr );
    item_location item_loc( cursor, tshirt );
    REQUIRE( item_loc->typeId() == itype_tshirt );
    for( int j = 0; j < 4; ++j ) {
        // Delete up to 4 random jeans
        map_stack stack = m.i_at( pos );
        REQUIRE( !stack.empty() );
        item *i = &random_entry_opt( stack )->get();
        if( i->typeId() == itype_jeans ) {
            m.i_rem( pos, i );
        }
    }
    CAPTURE( m.i_at( pos ) );
    REQUIRE( item_loc );
    CHECK( item_loc->typeId() == itype_tshirt );
}

TEST_CASE( "item_location_doesnt_return_stale_map_item", "[item][item_location]" )
{
    clear_map();
    map &m = get_map();
    tripoint pos( 60, 60, 0 );
    m.i_clear( pos );
    m.add_item( pos, item( "tshirt" ) );
    item_location item_loc( map_cursor( pos ), &m.i_at( pos ).only_item() );
    REQUIRE( item_loc->typeId() == itype_tshirt );
    m.i_rem( pos, &*item_loc );
    m.add_item( pos, item( "jeans" ) );
    CHECK( !item_loc );
}

TEST_CASE( "item_in_container", "[item][item_location]" )
{
    Character &dummy = get_player_character();
    clear_avatar();
    item_location backpack = dummy.i_add( item( "backpack" ) );
    item jeans( "jeans" );

    REQUIRE( dummy.has_item( *backpack ) );

    backpack->put_in( jeans, item_pocket::pocket_type::CONTAINER );

    item_location backpack_loc( dummy, & **dummy.wear_item( *backpack ) );

    REQUIRE( dummy.has_item( *backpack_loc ) );

    item_location jeans_loc( backpack_loc, &backpack_loc->only_item() );

    REQUIRE( backpack_loc.where() == item_location::type::character );
    REQUIRE( jeans_loc.where() == item_location::type::container );
    const int obtain_cost_calculation = dummy.item_handling_cost( *jeans_loc, true,
                                        backpack_loc->obtain_cost( *jeans_loc ) );
    CHECK( obtain_cost_calculation == jeans_loc.obtain_cost( dummy ) );

    CHECK( jeans_loc.parent_item() == backpack_loc );
}

TEST_CASE( "contained_npc_item_location_loads_before_owner_registration",
           "[item][item_location][npc][serialization]" )
{
    shared_ptr_fast<npc> owner = make_shared_fast<npc>();
    owner->setID( g->assign_npc_id(), true );
    owner->spawn_at_omt( get_player_character().global_omt_location() );

    item_location backpack = owner->i_add( item( "backpack" ) );
    backpack->put_in( item( "jeans" ), item_pocket::pocket_type::CONTAINER );
    item_location jeans( backpack, &backpack->only_item() );
    const std::string saved_location = serialize( jeans );

    item_location loaded;
    JsonValue loaded_json = json_loader::from_string( saved_location );
    REQUIRE( loaded_json.read( loaded ) );
    CHECK( loaded.where_recursive() == item_location::type::character );

    std::string invalid_location = saved_location;
    const size_t child_index = invalid_location.find( "\"idx\":0" );
    REQUIRE( child_index != std::string::npos );
    invalid_location.replace( child_index, 7, "\"idx\":9999" );
    item_location invalid;
    JsonValue invalid_json = json_loader::from_string( invalid_location );
    REQUIRE( invalid_json.read( invalid ) );

    overmap_buffer.insert_npc( owner );
    REQUIRE( loaded );
    CHECK( loaded->typeId() == itype_jeans );
    const std::string invalid_error = capture_debugmsg_during( [&invalid]() {
        CHECK_FALSE( invalid );
    } );
    CHECK( invalid_error.find( "lost its target item" ) != std::string::npos );

    CHECK( overmap_buffer.remove_npc( owner->getID() ) == owner );
}
