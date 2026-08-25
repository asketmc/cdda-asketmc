#include <algorithm>
#include <cmath>
#include <vector>

#include "avatar.h"
#include "calendar.h"
#include "cata_catch.h"
#include "construction.h"
#include "item.h"
#include "map.h"
#include "map_helpers.h"
#include "player_helpers.h"
#include "skill.h"
#include "type_id.h"
#include "veh_appliance.h"
#include "vehicle.h"
#include "veh_type.h"

namespace
{
const construction &construction_by_id( const construction_str_id &id )
{
    const std::vector<construction> &all = get_constructions();
    const auto found = std::find_if( all.begin(), all.end(), [&id]( const construction &candidate ) {
        return candidate.str_id == id;
    } );
    REQUIRE( found != all.end() );
    return *found;
}
} // namespace

TEST_CASE( "simple deconstruction is fast and exclusive", "[h6][construction][antigrind]" )
{
    clear_map();
    map &here = get_map();
    const tripoint_bub_ms target;
    here.furn_set( target, furn_id( "f_chair" ) );

    const construction &simple = construction_by_id(
                                     construction_str_id( "constr_deconstruct_simple" ) );
    const construction &regular = construction_by_id(
                                      construction_str_id( "constr_deconstruct" ) );

    CHECK( simple.time == to_moves<int>( 10_seconds ) );
    CHECK( simple.pre_special( target ) );
    CHECK_FALSE( regular.pre_special( target ) );
}

TEST_CASE( "BMI has a bounded effect on lifestyle", "[h6][health][antigrind]" )
{
    avatar dummy;
    const int healthy_kcal = dummy.get_healthy_kcal();
    dummy.set_lifestyle( 100 );

    SECTION( "healthy weight does not change lifestyle" ) {
        dummy.set_stored_kcal( healthy_kcal );
        CHECK( dummy.get_bmi() == Approx( 25.0f ) );
        CHECK( dummy.get_lifestyle() == 100 );
    }

    SECTION( "obesity applies the smaller linear penalty" ) {
        // get_bmi() = 12 * kcal ratio + 13, so this is approximately BMI 35.
        dummy.set_stored_kcal( std::round( healthy_kcal * 22.0f / 12.0f ) );
        CHECK( dummy.get_bmi() == Approx( 35.0f ).margin( 0.01f ) );
        CHECK( dummy.get_lifestyle() == 75 );
    }

    SECTION( "severe underweight remains bounded" ) {
        dummy.set_lifestyle( -100 );
        dummy.set_stored_kcal( 0 );
        CHECK( dummy.get_lifestyle() == -200 );
    }
}

TEST_CASE( "bulk item handling charges only variable cost", "[h6][items][antigrind]" )
{
    avatar dummy;
    item water( itype_id( "water_clean" ), calendar::turn_zero, 100 );

    const int legacy_default = dummy.item_handling_cost( water, true, 0 );
    const int explicit_default = dummy.item_handling_cost( water, true, 0, -1, false );
    CHECK( legacy_default == explicit_default );

    const int one_charge_bulk = dummy.item_handling_cost( water, true, 0, 1, true );
    const int all_charges_bulk = dummy.item_handling_cost( water, true, 0, -1, true );
    CHECK( one_charge_bulk >= 0 );
    CHECK( one_charge_bulk < all_charges_bulk );
}

TEST_CASE( "backup generator converts, fuels, powers a grid, and preserves fuel",
           "[h6][vehicle][appliance][antigrind]" )
{
    clear_map();
    map &here = get_map();
    const tripoint generator_pos( HALF_MAPSIZE_X + 2, HALF_MAPSIZE_Y + 2, 0 );
    const tripoint battery_pos = generator_pos + tripoint_east;
    const vpart_id generator_part_id( "ap_active_backup_generator" );
    const itype_id generator_item_id( "active_backup_generator" );
    const itype_id diesel_id( "diesel" );

    here.furn_set( generator_pos, furn_id( "f_active_backup_generator" ) );
    convert_to_appliance( generator_pos, furn_str_id( "f_null" ), cata::nullopt,
                          generator_item_id );
    CHECK( here.furn( generator_pos ) == furn_id( "f_null" ) );

    optional_vpart_position generator_at = here.veh_at( generator_pos );
    REQUIRE( generator_at.has_value() );
    vehicle &generator = generator_at->vehicle();
    REQUIRE( generator.reactors.size() == 1 );
    const int reactor_index = generator.reactors.front();
    vehicle_part &reactor = generator.part( reactor_index );
    REQUIRE( reactor.info().get_id() == generator_part_id );

    item diesel( diesel_id, calendar::turn_zero, 12000 );
    const int tank_capacity = reactor.ammo_capacity( diesel.ammo_type() );
    REQUIRE( tank_capacity == 10000 );
    REQUIRE( reactor.fill_with( diesel ) );
    CHECK( reactor.ammo_remaining() == tank_capacity );
    CHECK( diesel.charges == 2000 );

    item battery_base( itype_id( "storage_battery" ) );
    battery_base.ammo_set( itype_id( "battery" ), 0 );
    place_appliance( battery_pos, vpart_id( "ap_battery" ), battery_base );
    optional_vpart_position battery_at = here.veh_at( battery_pos );
    REQUIRE( battery_at.has_value() );
    vehicle &battery = battery_at->vehicle();
    REQUIRE( battery.batteries.size() == 1 );
    vehicle_part &battery_part = battery.part( battery.batteries.front() );
    REQUIRE( battery_part.ammo_remaining() == 0 );

    // Connecting appliances appends cable parts and can reallocate the part vector.
    vehicle_part &connected_reactor = generator.part( reactor_index );
    REQUIRE( connected_reactor.enabled );
    CHECK( generator.max_reactor_epower_w() == 7300 );
    CHECK( generator.active_reactor_epower_w( true ) == 7300 );
    const int fuel_before = connected_reactor.ammo_remaining();
    generator.idle( false );
    CHECK( battery_part.ammo_remaining() > 0 );
    CHECK( connected_reactor.ammo_remaining() < fuel_before );

    const item recovered = connected_reactor.properties_to_item();
    REQUIRE( recovered.num_item_stacks() == 1 );
    const int recovered_fuel = recovered.only_item().charges;
    CHECK( recovered_fuel == connected_reactor.ammo_remaining() );

    const tripoint replacement_pos = generator_pos + tripoint( 5, 0, 0 );
    place_appliance( replacement_pos, generator_part_id, recovered );
    optional_vpart_position replacement_at = here.veh_at( replacement_pos );
    REQUIRE( replacement_at.has_value() );
    vehicle &replacement = replacement_at->vehicle();
    REQUIRE( replacement.reactors.size() == 1 );
    CHECK( replacement.part( replacement.reactors.front() ).ammo_remaining() == recovered_fuel );
}

TEST_CASE( "practical skill progress has a soft-check value", "[h6][skill][antigrind]" )
{
    avatar dummy;
    const skill_id fabrication( "fabrication" );
    dummy.set_skill_level( fabrication, 3 );

    CHECK( dummy.get_skill_level( fabrication ) == 3 );
    CHECK( dummy.get_skill_level_with_progress( fabrication ) == Approx( 3.0f ) );

    SkillLevel &level = dummy.get_skill_level_object( fabrication );
    const int halfway_raw_xp = 50 * 100 * 4 * 4;
    level.train( halfway_raw_xp, 1.0f, 0.0f );

    REQUIRE( level.level() == 3 );
    REQUIRE( level.exercise() == 50 );
    CHECK( dummy.get_skill_level( fabrication ) == 3 );
    CHECK( dummy.get_skill_level_with_progress( fabrication ) == Approx( 3.5f ) );
}

TEST_CASE( "general melee progress improves critical chance with weapon skill fixed",
           "[h6][skill][melee][antigrind]" )
{
    avatar dummy;
    clear_character( dummy );
    const skill_id melee( "melee" );
    item weapon( itype_id( "knife_combat" ) );
    const skill_id weapon_skill = weapon.melee_skill();
    dummy.set_skill_level( melee, 3 );
    dummy.set_skill_level( weapon_skill, 3 );

    const double base_critical_chance = dummy.crit_chance( 0.0f, 100.0f, weapon );
    SkillLevel &melee_level = dummy.get_skill_level_object( melee );
    const int halfway_raw_xp = 50 * 100 * 4 * 4;
    melee_level.train( halfway_raw_xp, 1.0f, 0.0f );

    REQUIRE( melee_level.level() == 3 );
    REQUIRE( melee_level.exercise() == 50 );
    REQUIRE( dummy.get_skill_level( weapon_skill ) == 3 );
    REQUIRE( dummy.get_skill_level_with_progress( weapon_skill ) == Approx( 3.0f ) );
    CHECK( dummy.crit_chance( 0.0f, 100.0f, weapon ) > base_critical_chance );
}

TEST_CASE( "skill enchantments preserve fractional progress", "[h6][skill][antigrind]" )
{
    avatar dummy;
    clear_character( dummy );
    const skill_id throwing( "throw" );
    const bionic_id throwing_assist( "bio_pitch_perfect" );
    dummy.set_skill_level( throwing, 8 );

    SkillLevel &level = dummy.get_skill_level_object( throwing );
    const int halfway_raw_xp = 50 * 100 * 9 * 9;
    level.train( halfway_raw_xp, 1.0f, 0.0f );
    give_and_activate_bionic( dummy, throwing_assist );
    dummy.recalculate_enchantment_cache();

    REQUIRE( level.level() == 8 );
    REQUIRE( level.exercise() == 50 );
    CHECK( dummy.get_skill_level( throwing ) == 13 );
    CHECK( dummy.get_skill_level_with_progress( throwing ) == Approx( 13.5f ) );
}
