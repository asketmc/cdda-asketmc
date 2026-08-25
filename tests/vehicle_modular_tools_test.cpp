#include "cata_catch.h"

#include <algorithm>
#include <functional>
#include <list>
#include <map>
#include <string>

#include "activity_actor_definitions.h"
#include "avatar.h"
#include "debug.h"
#include "flag.h"
#include "input.h"
#include "inventory.h"
#include "item.h"
#include "item_pocket.h"
#include "iuse.h"
#include "map.h"
#include "map_helpers.h"
#include "player_activity.h"
#include "player_helpers.h"
#include "type_id.h"
#include "veh_type.h"
#include "vehicle.h"
#include "vpart_position.h"

static const itype_id itype_battery( "battery" );
static const itype_id itype_circsaw_off( "circsaw_off" );
static const itype_id itype_gasoline( "gasoline" );
static const itype_id itype_large_repairkit( "large_repairkit" );
static const itype_id itype_propane( "propane" );
static const itype_id itype_propane_cooker( "propane_cooker" );
static const itype_id itype_towel( "towel" );
static const itype_id itype_water_clean( "water_clean" );
static const itype_id itype_water_faucet( "water_faucet" );
static const itype_id itype_welder( "welder" );

static const vpart_id vpart_kitchen_unit( "kitchen_unit" );
static const vpart_id vpart_alternator_motorbike( "alternator_motorbike" );
static const vpart_id vpart_bike_rack( "bike_rack" );
static const vpart_id vpart_engine_1cyl_small( "engine_1cyl_small" );
static const vpart_id vpart_jumper_cable( "jumper_cable" );
static const vpart_id vpart_small_pressure_tank( "small_pressure_tank" );
static const vpart_id vpart_smart_engine_controller( "smart_engine_controller" );
static const vpart_id vpart_storage_battery( "storage_battery" );
static const vpart_id vpart_tank( "tank" );
static const vpart_id vpart_tools_fabrication( "veh_tools_fabrication" );
static const vpart_id vpart_tools_kitchen( "veh_tools_kitchen" );
static const vpart_id vpart_tools_workshop( "veh_tools_workshop" );
static const vpart_id vpart_welding_rig( "welding_rig" );

static const vproto_id vehicle_prototype_none( "none" );
static const vproto_id vehicle_prototype_car( "car" );
static const vproto_id vehicle_prototype_test_modular_tools( "test_modular_vehicle_tools" );

static const activity_id ACT_HACKSAW( "ACT_HACKSAW" );
static const furn_str_id furn_test_f_hacksaw3( "test_f_hacksaw3" );
static const furn_str_id furn_test_f_prying1( "test_f_prying1" );

static int install_tank( vehicle &veh, const vpart_id &tank_type, const itype_id &contents )
{
    const int tank_index = veh.install_part( point_zero, tank_type, "", true );
    REQUIRE( tank_index >= 0 );
    REQUIRE( veh.part( tank_index ).ammo_set( contents ) > 0 );
    return tank_index;
}

TEST_CASE( "modular_vehicle_tool_station_data_is_additive", "[vehicle][tools][data]" )
{
    for( const vpart_id &station_id : { vpart_tools_kitchen, vpart_tools_workshop,
                                       vpart_tools_fabrication } ) {
        CAPTURE( station_id.str() );
        REQUIRE( station_id.is_valid() );
        CHECK( station_id->has_flag( "VEH_TOOLS" ) );
        REQUIRE( station_id->get_toolkit_info() );
        CHECK_FALSE( station_id->get_toolkit_info()->allowed_types.empty() );
    }

    REQUIRE( vpart_tools_fabrication->get_workbench_info() );
    CHECK( vpart_tools_fabrication->get_workbench_info()->multiplier == Approx( 1.2f ) );
    CHECK( vpart_tools_fabrication->get_toolkit_info()->allowed_types.count( itype_welder ) == 1 );
    CHECK( vpart_tools_fabrication->get_toolkit_info()->allowed_types.count(
               itype_propane_cooker ) == 1 );
    // Transforming/consumable state must not be silently discarded by a temporary pseudo item.
    CHECK( vpart_tools_fabrication->get_toolkit_info()->allowed_types.count( itype_circsaw_off ) == 0 );
    CHECK( vpart_tools_fabrication->get_toolkit_info()->allowed_types.count( itype_towel ) == 0 );

    // The backport adds modular stations without obsoleting the original 0.G rigs.
    CHECK( vpart_kitchen_unit.is_valid() );
    CHECK( vpart_welding_rig.is_valid() );
}

TEST_CASE( "vehicle_prototype_spawns_attached_modular_tools", "[vehicle][tools][prototype]" )
{
    clear_map();
    vehicle *veh = get_map().add_vehicle( vehicle_prototype_test_modular_tools, tripoint_zero,
                                          0_degrees );
    REQUIRE( veh != nullptr );

    const int station = veh->part_with_feature( point_zero, "VEH_TOOLS", true );
    REQUIRE( station >= 0 );
    const std::vector<item> &tools = veh->get_tools( veh->part( station ) );
    REQUIRE( tools.size() == 1 );
    CHECK( tools.front().typeId() == itype_welder );
    CHECK( tools.front().get_var( "prototype_test" ) == "kept" );

    get_map().destroy_vehicle( veh );
}

TEST_CASE( "dynamic_vehicle_links_validate_mount_without_becoming_installable",
           "[vehicle][power][cable]" )
{
    clear_map();
    vehicle *veh = get_map().add_vehicle( vehicle_prototype_none, tripoint_zero, 0_degrees );
    REQUIRE( veh != nullptr );

    CHECK_FALSE( veh->can_mount( point_zero, vpart_jumper_cable ).success() );
    CHECK( veh->can_mount( point_zero, vpart_jumper_cable, true ).success() );

    get_map().destroy_vehicle( veh );
}

TEST_CASE( "modular_vehicle_tool_draws_from_connected_vehicle_battery",
           "[vehicle][tools][power][cable]" )
{
    clear_map();
    map &here = get_map();
    const tripoint workshop_pos( HALF_MAPSIZE_X + 2, HALF_MAPSIZE_Y + 2, 0 );
    const tripoint battery_pos( workshop_pos + tripoint( 2, 2, 0 ) );
    vehicle *workshop = here.add_vehicle( vehicle_prototype_none, workshop_pos, 0_degrees );
    vehicle *power_source = here.add_vehicle( vehicle_prototype_none, battery_pos, 0_degrees );
    REQUIRE( workshop != nullptr );
    REQUIRE( power_source != nullptr );

    const int station = workshop->install_part( point_zero, vpart_tools_fabrication, "", true );
    const int battery = power_source->install_part( point_zero, vpart_storage_battery, "", true );
    REQUIRE( station >= 0 );
    REQUIRE( battery >= 0 );
    REQUIRE( power_source->part( battery ).ammo_set( itype_battery ) > 0 );
    REQUIRE( power_source->fuel_left( itype_battery ) > 0 );
    workshop->get_tools( workshop->part( station ) ).emplace_back( itype_welder,
            calendar::turn_zero );
    // Vehicles created from the empty prototype need their newly installed parts registered.
    here.add_vehicle_to_cache( workshop );
    here.add_vehicle_to_cache( power_source );
    REQUIRE( workshop->fuel_left( itype_battery, true ) == 0 );

    workshop->connect( workshop_pos, battery_pos );
    REQUIRE( workshop->fuel_left( itype_battery, true ) > 0 );
    const int source_before = power_source->part( battery ).ammo_remaining();
    const vpart_position workshop_position( *workshop, station );
    int needed = 7;
    const auto accept_all = []( const item & ) {
        return true;
    };
    const std::list<item> used = workshop->use_charges( workshop_position, itype_welder,
                                 needed, accept_all, true );

    CHECK( needed == 0 );
    CHECK_FALSE( used.empty() );
    CHECK( power_source->part( battery ).ammo_remaining() == source_before - 7 );
}

TEST_CASE( "single_combustion_smart_controller_starts_and_stops_generator",
           "[vehicle][power][smart_controller]" )
{
    clear_map();
    map &here = get_map();
    vehicle *veh = here.add_vehicle( vehicle_prototype_none, tripoint_zero, 0_degrees );
    REQUIRE( veh != nullptr );

    const int engine = veh->install_part( point_zero, vpart_engine_1cyl_small, "", true );
    const int alternator = veh->install_part( point_zero, vpart_alternator_motorbike, "", true );
    const int battery = veh->install_part( point_zero, vpart_storage_battery, "", true );
    const int controller = veh->install_part( point_zero, vpart_smart_engine_controller, "", true );
    REQUIRE( engine >= 0 );
    REQUIRE( alternator >= 0 );
    REQUIRE( battery >= 0 );
    REQUIRE( controller >= 0 );
    install_tank( *veh, vpart_tank, itype_gasoline );

    REQUIRE( veh->part( battery ).ammo_set( itype_battery, 1 ) > 0 );
    veh->part( controller ).enabled = true;
    veh->has_enabled_smart_controller = true;
    veh->smart_controller_cfg = smart_controller_config();
    veh->engine_on = false;

    veh->smart_controller_handle_turn();
    CHECK( veh->engine_on );
    CHECK( veh->part( engine ).enabled );
    CHECK( veh->has_enabled_smart_controller );

    // Above the upper threshold, the same controller stops the parked generator but stays
    // armed so it can restart when charge falls again.
    REQUIRE( veh->part( battery ).ammo_set( itype_battery ) > 0 );
    veh->smart_controller_state = cata::nullopt;
    veh->smart_controller_handle_turn();
    CHECK_FALSE( veh->engine_on );
    CHECK( veh->has_enabled_smart_controller );

    here.destroy_vehicle( veh );
}

TEST_CASE( "modular_vehicle_tools_use_vehicle_battery_and_tanks", "[vehicle][tools][power]" )
{
    clear_map();
    map &here = get_map();
    vehicle *veh = here.add_vehicle( vehicle_prototype_none, tripoint_zero, 0_degrees );
    REQUIRE( veh != nullptr );

    const int station_index = veh->install_part( point_zero, vpart_tools_fabrication, "", true );
    REQUIRE( station_index >= 0 );

    const int battery_index = veh->install_part( point_zero, vpart_storage_battery, "", true );
    REQUIRE( battery_index >= 0 );
    REQUIRE( veh->part( battery_index ).ammo_set( itype_battery ) > 0 );

    const int propane_tank = install_tank( *veh, vpart_small_pressure_tank, itype_propane );
    const int water_tank = install_tank( *veh, vpart_tank, itype_water_clean );

    item welder( itype_welder, calendar::turn_zero );
    welder.invlet = 'w';
    item welder_battery( welder.magazine_default(), calendar::turn_zero );
    REQUIRE_FALSE( welder_battery.is_null() );
    welder_battery.ammo_set( welder_battery.ammo_default() );
    REQUIRE( welder_battery.ammo_remaining() > 0 );
    REQUIRE( welder.put_in( welder_battery,
                            item_pocket::pocket_type::MAGAZINE_WELL ).success() );
    const int attached_welder_charges = welder.ammo_remaining();
    item cooker( itype_propane_cooker, calendar::turn_zero );
    cooker.invlet = 'p';
    veh->get_tools( veh->part( station_index ) ).push_back( welder );
    veh->get_tools( veh->part( station_index ) ).push_back( cooker );

    std::map<item, input_event> prepared;
    const std::string debug_message = capture_debugmsg_during( [&]() {
        prepared = veh->prepare_tools( veh->part( station_index ) );
    } );
    CHECK( debug_message.empty() );
    REQUIRE_FALSE( veh->get_tools( veh->part( station_index ) ).empty() );
    CHECK( veh->get_tools( veh->part( station_index ) ).front().ammo_remaining() ==
           attached_welder_charges );
    const auto prepared_welder = std::find_if( prepared.begin(), prepared.end(), []( const auto &entry ) {
        return entry.first.typeId() == itype_welder;
    } );
    REQUIRE( prepared_welder != prepared.end() );
    CHECK( prepared_welder->first.has_flag( flag_PSEUDO ) );
    CHECK( prepared_welder->first.ammo_remaining() > 0 );
    const auto prepared_cooker = std::find_if( prepared.begin(), prepared.end(), []( const auto &entry ) {
        return entry.first.typeId() == itype_propane_cooker;
    } );
    REQUIRE( prepared_cooker != prepared.end() );
    CHECK( prepared_cooker->first.has_flag( flag_PSEUDO ) );
    CHECK( prepared_cooker->first.ammo_remaining() > 0 );

    const vpart_position station_position( *veh, station_index );
    REQUIRE( station_position.part_with_tool( itype_water_faucet ) );
    inventory nearby;
    station_position.form_inventory( nearby );
    CHECK( nearby.has_amount( itype_water_clean, 1 ) );
    const auto accept_all = []( const item & ) {
        return true;
    };

    const int battery_before = veh->fuel_left( itype_battery, true );
    int battery_needed = 5;
    const std::list<item> battery_used = veh->use_charges( station_position, itype_welder,
                                         battery_needed, accept_all, true );
    CHECK( battery_needed == 0 );
    CHECK_FALSE( battery_used.empty() );
    CHECK( veh->fuel_left( itype_battery, true ) == battery_before - 5 );

    const int propane_before = veh->part( propane_tank ).ammo_remaining();
    int propane_needed = 3;
    const std::list<item> propane_used = veh->use_charges( station_position,
                                         itype_propane_cooker, propane_needed, accept_all, true );
    CHECK( propane_needed == 0 );
    CHECK_FALSE( propane_used.empty() );
    CHECK( veh->part( propane_tank ).ammo_remaining() == propane_before - 3 );

    const int water_before = veh->part( water_tank ).ammo_remaining();
    int water_needed = 7;
    const std::list<item> water_used = veh->use_charges( station_position, itype_water_clean,
                                       water_needed, accept_all, true );
    CHECK( water_needed == 0 );
    CHECK_FALSE( water_used.empty() );
    CHECK( veh->part( water_tank ).ammo_remaining() == water_before - 7 );

    here.destroy_vehicle( veh );
}

TEST_CASE( "mounted_repair_kit_hacksaw_activity_keeps_no_temporary_item_pointer",
           "[vehicle][tools][activity][hacksaw]" )
{
    clear_map();
    clear_avatar();
    map &here = get_map();
    avatar &you = get_avatar();
    const tripoint vehicle_pos( HALF_MAPSIZE_X + 2, HALF_MAPSIZE_Y + 2, 0 );
    const tripoint target = vehicle_pos + tripoint_east;
    you.setpos( vehicle_pos );

    here.furn_set( target, furn_test_f_hacksaw3 );
    vehicle *veh = here.add_vehicle( vehicle_prototype_none, vehicle_pos, 0_degrees );
    REQUIRE( veh != nullptr );
    const int station = veh->install_part( point_zero, vpart_tools_fabrication, "", true );
    REQUIRE( station >= 0 );
    const int battery = veh->install_part( point_zero, vpart_storage_battery, "", true );
    REQUIRE( battery >= 0 );
    CHECK( veh->fuel_left( itype_battery, true ) == 0 );
    veh->get_tools( veh->part( station ) ).emplace_back( itype_large_repairkit,
            calendar::turn_zero );
    here.add_vehicle_to_cache( veh );
    const optional_vpart_position mounted_station = here.veh_at( vehicle_pos );
    REQUIRE( mounted_station );
    REQUIRE( mounted_station->part_with_tool( itype_large_repairkit ) );

    hacksaw_activity_actor actor( target, itype_large_repairkit, vehicle_pos );
    actor.testing = true;
    you.assign_activity( player_activity( actor ) );
    REQUIRE( you.activity.id() == ACT_HACKSAW );

    you.moves = you.get_speed();
    you.activity.do_turn( you );
    CHECK( you.activity.id() == ACT_HACKSAW );

    here.destroy_vehicle( veh );
}

TEST_CASE( "temporary_vehicle_pseudo_tool_cannot_start_pointer_retaining_prying",
           "[vehicle][tools][activity][prying]" )
{
    clear_map();
    clear_avatar();
    map &here = get_map();
    avatar &you = get_avatar();
    const tripoint target = tripoint_east;
    here.furn_set( target, furn_test_f_prying1 );
    item pseudo_repair_kit( itype_large_repairkit, calendar::turn_zero );
    pseudo_repair_kit.set_flag( flag_PSEUDO );

    iuse::crowbar( &you, &pseudo_repair_kit, false, target );
    CHECK( you.activity.is_null() );
}

TEST_CASE( "expiring_vehicle_drops_attached_modular_tools",
           "[vehicle][tools][summoned][drop]" )
{
    clear_map();
    map &here = get_map();
    vehicle *veh = here.add_vehicle( vehicle_prototype_none, tripoint_zero, 0_degrees );
    REQUIRE( veh != nullptr );
    const int station = veh->install_part( point_zero, vpart_tools_fabrication, "", true );
    REQUIRE( station >= 0 );
    veh->get_tools( veh->part( station ) ).emplace_back( itype_welder, calendar::turn_zero );
    veh->summon_time_limit = 0_turns;

    REQUIRE( veh->decrement_summon_timer() );
    CHECK_FALSE( here.veh_at( tripoint_zero ) );
    const map_stack dropped = here.i_at( tripoint_zero );
    CHECK( std::count_if( dropped.begin(), dropped.end(), []( const item & it ) {
        return it.typeId() == itype_welder;
    } ) == 1 );
}

TEST_CASE( "removing_modular_station_drops_its_attached_tools",
           "[vehicle][tools][remove][drop]" )
{
    clear_map();
    map &here = get_map();
    vehicle *veh = here.add_vehicle( vehicle_prototype_none, tripoint_zero, 0_degrees );
    REQUIRE( veh != nullptr );
    const int station = veh->install_part( point_zero, vpart_tools_fabrication, "", true );
    REQUIRE( station >= 0 );
    veh->get_tools( veh->part( station ) ).emplace_back( itype_welder, calendar::turn_zero );

    veh->remove_part( station );
    REQUIRE( veh->part( station ).removed );
    const map_stack dropped = here.i_at( tripoint_zero );
    CHECK( std::count_if( dropped.begin(), dropped.end(), []( const item & it ) {
        return it.typeId() == itype_welder;
    } ) == 1 );
}

TEST_CASE( "rack_and_unrack_preserves_attached_modular_tools",
           "[vehicle][tools][bike_rack]" )
{
    clear_map();
    map &here = get_map();
    const tripoint carrier_pos( 60, 60, 0 );
    const tripoint carried_pos( 56, 60, 0 );
    vehicle *carrier = here.add_vehicle( vehicle_prototype_car, carrier_pos, 0_degrees );
    vehicle *carried = here.add_vehicle( vehicle_prototype_test_modular_tools, carried_pos,
                                         0_degrees );
    REQUIRE( carrier != nullptr );
    REQUIRE( carried != nullptr );

    const int rack = carrier->install_part( point( -3, 0 ), vpart_bike_rack );
    REQUIRE( rack >= 0 );
    const std::vector<vehicle::rackable_vehicle> rackables = carrier->find_vehicles_to_rack( rack );
    const auto rackable = std::find_if( rackables.begin(), rackables.end(),
    [carried]( const vehicle::rackable_vehicle & candidate ) {
        return candidate.veh == carried;
    } );
    REQUIRE( rackable != rackables.end() );
    REQUIRE( carrier->merge_rackable_vehicle( carried, rackable->racks ) );

    const std::vector<vehicle::unrackable_vehicle> unrackables =
        carrier->find_vehicles_to_unrack( rack );
    REQUIRE( unrackables.size() == 1 );
    REQUIRE( carrier->remove_carried_vehicle( unrackables.front().parts,
             unrackables.front().racks ) );

    const optional_vpart_position unracked_position = here.veh_at( carried_pos );
    REQUIRE( unracked_position );
    vehicle &unracked = unracked_position->vehicle();
    const int station = unracked.part_with_feature( point_zero, "VEH_TOOLS", true );
    REQUIRE( station >= 0 );
    const std::vector<item> &tools = unracked.get_tools( unracked.part( station ) );
    REQUIRE( tools.size() == 1 );
    CHECK( tools.front().typeId() == itype_welder );
}
