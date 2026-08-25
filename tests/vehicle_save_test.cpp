#include <functional>
#include <sstream>
#include <string>
#include <vector>

#include "cata_catch.h"
#include "effect_source.h"
#include "json.h"
#include "json_loader.h"
#include "map.h"
#include "map_helpers.h"
#include "type_id.h"
#include "vehicle.h"
#include "veh_type.h"

static const efftype_id effect_debugged( "debugged" );

static const vproto_id vehicle_prototype_test_locked_door( "test_locked_door" );
static const vproto_id vehicle_prototype_none( "none" );

static const itype_id itype_welder( "welder" );
static const vpart_id vpart_tools_fabrication( "veh_tools_fabrication" );

static std::string serialize_part( const vehicle_part &part )
{
    std::ostringstream output;
    JsonOut json( output );
    part.serialize( json );
    return output.str();
}

static std::string serialize_vehicle( const vehicle &veh )
{
    std::ostringstream output;
    JsonOut json( output );
    veh.serialize( json );
    return output.str();
}

TEST_CASE( "vehicle_part_lock_state_save_compatibility", "[vehicle][savegame][lock]" )
{
    clear_map();
    vehicle *veh = get_map().add_vehicle( vehicle_prototype_test_locked_door, tripoint_zero,
                                          0_degrees, 100, 0, false, "", false );
    REQUIRE( veh != nullptr );
    REQUIRE( veh->num_true_parts() == 3 );

    const int door_index = veh->part_with_feature( point_zero, "LOCKABLE_DOOR", true );
    REQUIRE( door_index >= 0 );
    vehicle_part &door = veh->part( door_index );
    REQUIRE( veh->part_flag( door_index, "LOCKABLE_DOOR" ) );
    REQUIRE_FALSE( door.locked );

    SECTION( "locked state round-trips" ) {
        door.locked = true;
        JsonValue saved = json_loader::from_string( serialize_part( door ) );
        vehicle_part loaded;
        loaded.deserialize( saved.get_object() );

        CHECK( loaded.locked );
    }

    SECTION( "missing locked member defaults to false" ) {
        std::string legacy_save = serialize_part( door );
        const std::string locked_member = ",\"locked\":false";
        const size_t locked_pos = legacy_save.find( locked_member );
        REQUIRE( locked_pos != std::string::npos );
        legacy_save.erase( locked_pos, locked_member.size() );

        JsonValue saved = json_loader::from_string( legacy_save );
        JsonObject saved_part = saved.get_object();
        REQUIRE_FALSE( saved_part.has_member( "locked" ) );

        vehicle_part loaded;
        loaded.deserialize( saved_part );
        CHECK_FALSE( loaded.locked );
    }
}

TEST_CASE( "vehicle_effects_save_round_trip", "[vehicle][savegame][effect]" )
{
    clear_map();
    vehicle *veh = get_map().add_vehicle( vehicle_prototype_test_locked_door, tripoint_zero,
                                          0_degrees, 100, 0, false, "", false );
    REQUIRE( veh != nullptr );

    veh->add_effect( effect_source::empty(), effect_debugged, 37_turns, false, 4 );
    REQUIRE( veh->has_effect( effect_debugged ) );

    JsonValue saved = json_loader::from_string( serialize_vehicle( *veh ) );
    vehicle loaded;
    loaded.deserialize( saved.get_object() );

    REQUIRE( loaded.has_effect( effect_debugged ) );
    const std::vector<std::reference_wrapper<const effect>> effects = loaded.get_effects();
    REQUIRE( effects.size() == 1 );
    const effect &loaded_effect = effects.front().get();
    CHECK( loaded_effect.get_id() == effect_debugged );
    CHECK( loaded_effect.get_duration() == 37_turns );
    CHECK( loaded_effect.get_intensity() == 4 );
    CHECK_FALSE( loaded_effect.is_permanent() );
}

TEST_CASE( "vehicle_attached_tools_save_round_trip", "[vehicle][savegame][tools]" )
{
    clear_map();
    vehicle *veh = get_map().add_vehicle( vehicle_prototype_none, tripoint_zero,
                                          0_degrees, 100, 0, false, "", false );
    REQUIRE( veh != nullptr );

    const int station_index = veh->install_part( point_zero, vpart_tools_fabrication, "", true );
    REQUIRE( station_index >= 0 );
    item attached_welder( itype_welder, calendar::turn_zero );
    attached_welder.invlet = 'w';
    veh->get_tools( veh->part( station_index ) ).push_back( attached_welder );

    JsonValue saved = json_loader::from_string( serialize_vehicle( *veh ) );
    vehicle loaded;
    loaded.deserialize( saved.get_object() );

    const int loaded_station = loaded.part_with_feature( point_zero, "VEH_TOOLS", true );
    REQUIRE( loaded_station >= 0 );
    const std::vector<item> &loaded_tools = loaded.get_tools( loaded.part( loaded_station ) );
    REQUIRE( loaded_tools.size() == 1 );
    CHECK( loaded_tools.front().typeId() == itype_welder );
    CHECK( loaded_tools.front().invlet == 'w' );
}
