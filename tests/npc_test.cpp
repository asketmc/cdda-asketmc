#include <map>
#include <memory>
#include <set>
#include <sstream>
#include <string>
#include <utility>
#include <vector>

#include "calendar.h"
#include "cata_catch.h"
#include "character.h"
#include "common_types.h"
#include "creature_tracker.h"
#include "faction.h"
#include "field.h"
#include "field_type.h"
#include "game.h"
#include "game_constants.h"
#include "json.h"
#include "json_loader.h"
#include "line.h"
#include "map.h"
#include "map_helpers.h"
#include "memory_fast.h"
#include "npc.h"
#include "npc_class.h"
#include "optional.h"
#include "overmapbuffer.h"
#include "pimpl.h"
#include "player_helpers.h"
#include "point.h"
#include "text_snippets.h"
#include "type_id.h"
#include "units.h"
#include "veh_type.h"
#include "vehicle.h"
#include "vpart_position.h"
#include "weather.h"

class Creature;

static const efftype_id effect_bouldering( "bouldering" );
static const efftype_id effect_sleep( "sleep" );

static const trait_id trait_WEB_WEAVER( "WEB_WEAVER" );

static const vpart_id vpart_frame( "frame" );
static const vpart_id vpart_seat( "seat" );

static const vproto_id vehicle_prototype_none( "none" );

static void on_load_test( npc &who, const time_duration &from, const time_duration &to )
{
    calendar::turn = calendar::turn_zero + from;
    who.on_unload();
    calendar::turn = calendar::turn_zero + to;
    who.on_load();
}

static void test_needs( const npc &who, const numeric_interval<int> &hunger,
                        const numeric_interval<int> &thirst,
                        const numeric_interval<int> &fatigue )
{
    CHECK( who.get_hunger() <= hunger.max );
    CHECK( who.get_hunger() >= hunger.min );
    CHECK( who.get_thirst() <= thirst.max );
    CHECK( who.get_thirst() >= thirst.min );
    CHECK( who.get_fatigue() <= fatigue.max );
    CHECK( who.get_fatigue() >= fatigue.min );
}

static npc create_model()
{
    npc model_npc;
    model_npc.normalize();
    model_npc.randomize( NC_NONE );
    for( const trait_id &tr : model_npc.get_mutations() ) {
        model_npc.unset_mutation( tr );
    }
    model_npc.set_hunger( 0 );
    model_npc.set_thirst( 0 );
    model_npc.set_fatigue( 0 );
    model_npc.remove_effect( effect_sleep );
    // An ugly hack to prevent NPC falling asleep during testing due to massive fatigue
    model_npc.set_mutation( trait_WEB_WEAVER );

    return model_npc;
}

static std::string get_list_of_npcs( const std::string &title )
{

    std::ostringstream npc_list;
    npc_list << title << ":\n";
    for( const npc &n : g->all_npcs() ) {
        npc_list << "  " << &n << ": " << n.name << '\n';
    }
    return npc_list.str();
}

TEST_CASE( "on_load-sane-values", "[.]" )
{
    SECTION( "Awake for 10 minutes, gaining hunger/thirst/fatigue" ) {
        npc test_npc = create_model();
        const int five_min_ticks = 2;
        on_load_test( test_npc, 0_turns, 5_minutes * five_min_ticks );
        const int margin = 2;

        const numeric_interval<int> hunger( five_min_ticks / 4, margin, margin );
        const numeric_interval<int> thirst( five_min_ticks / 4, margin, margin );
        const numeric_interval<int> fatigue( five_min_ticks, margin, margin );

        test_needs( test_npc, hunger, thirst, fatigue );
    }

    SECTION( "Awake for 2 days, gaining hunger/thirst/fatigue" ) {
        npc test_npc = create_model();
        const double five_min_ticks = 2_days / 5_minutes;
        on_load_test( test_npc, 0_turns, 5_minutes * five_min_ticks );

        const int margin = 20;
        const numeric_interval<int> hunger( five_min_ticks / 4, margin, margin );
        const numeric_interval<int> thirst( five_min_ticks / 4, margin, margin );
        const numeric_interval<int> fatigue( five_min_ticks, margin, margin );

        test_needs( test_npc, hunger, thirst, fatigue );
    }

    SECTION( "Sleeping for 6 hours, gaining hunger/thirst (not testing fatigue due to lack of effects processing)" ) {
        npc test_npc = create_model();
        test_npc.add_effect( effect_sleep, 6_hours );
        test_npc.set_fatigue( 1000 );
        const double five_min_ticks = 6_hours / 5_minutes;
        /*
        // Fatigue regeneration starts at 1 per 5min, but linearly increases to 2 per 5min at 2 hours or more
        const int expected_fatigue_change =
            ((1.0f + 2.0f) / 2.0f * 2_hours / 5_minutes ) +
            (2.0f * (6_hours - 2_hours) / 5_minutes);
        */
        on_load_test( test_npc, 0_turns, 5_minutes * five_min_ticks );

        const int margin = 10;
        const numeric_interval<int> hunger( five_min_ticks / 8, margin, margin );
        const numeric_interval<int> thirst( five_min_ticks / 8, margin, margin );
        const numeric_interval<int> fatigue( test_npc.get_fatigue(), 0, 0 );

        test_needs( test_npc, hunger, thirst, fatigue );
    }
}

TEST_CASE( "on_load-similar-to-per-turn", "[.]" )
{
    SECTION( "Awake for 10 minutes, gaining hunger/thirst/fatigue" ) {
        npc on_load_npc = create_model();
        npc iterated_npc = create_model();
        const int five_min_ticks = 2;
        on_load_test( on_load_npc, 0_turns, 5_minutes * five_min_ticks );
        for( time_duration turn = 0_turns; turn < 5_minutes * five_min_ticks; turn += 1_turns ) {
            iterated_npc.update_body( calendar::turn_zero + turn,
                                      calendar::turn_zero + turn + 1_turns );
        }

        const int margin = 2;
        const numeric_interval<int> hunger( iterated_npc.get_hunger(), margin, margin );
        const numeric_interval<int> thirst( iterated_npc.get_thirst(), margin, margin );
        const numeric_interval<int> fatigue( iterated_npc.get_fatigue(), margin, margin );

        test_needs( on_load_npc, hunger, thirst, fatigue );
    }

    SECTION( "Awake for 6 hours, gaining hunger/thirst/fatigue" ) {
        npc on_load_npc = create_model();
        npc iterated_npc = create_model();
        const double five_min_ticks = 6_hours / 5_minutes;
        on_load_test( on_load_npc, 0_turns, 5_minutes * five_min_ticks );
        for( time_duration turn = 0_turns; turn < 5_minutes * five_min_ticks; turn += 1_turns ) {
            iterated_npc.update_body( calendar::turn_zero + turn,
                                      calendar::turn_zero + turn + 1_turns );
        }

        const int margin = 10;
        const numeric_interval<int> hunger( iterated_npc.get_hunger(), margin, margin );
        const numeric_interval<int> thirst( iterated_npc.get_thirst(), margin, margin );
        const numeric_interval<int> fatigue( iterated_npc.get_fatigue(), margin, margin );

        test_needs( on_load_npc, hunger, thirst, fatigue );
    }
}

TEST_CASE( "snippet-tag-test" )
{
    // Actually used tags
    static const std::set<std::string> npc_talk_tags = {
        {
            "<name_b>", "<thirsty>", "<swear!>",
            "<sad>", "<greet>", "<no>",
            "<im_leaving_you>", "<ill_kill_you>", "<ill_die>",
            "<wait>", "<no_faction>", "<name_g>",
            "<keep_up>", "<yawn>", "<very>",
            "<okay>", "<really>",
            "<let_me_pass>", "<done_mugging>", "<happy>",
            "<drop_it>", "<swear>", "<lets_talk>",
            "<hands_up>", "<move>", "<hungry>",
            "<fuck_you>",
        }
    };

    for( const auto &tag : npc_talk_tags ) {
        for( int i = 0; i < 100; i++ ) {
            CHECK( SNIPPET.random_from_category( tag ).has_value() );
        }
    }

    // Special tags, those should have no replacements
    static const std::set<std::string> special_tags = {
        {
            "<yrwp>", "<mywp>", "<ammo>"
        }
    };

    for( const std::string &tag : special_tags ) {
        for( int i = 0; i < 100; i++ ) {
            CHECK( !SNIPPET.random_from_category( tag ).has_value() );
        }
    }
}

/* Test setup. Player should always be at top-left.
 *
 * U is the player, V is vehicle, # is wall, R is rubble & acid with NPC on it,
 * A is acid with NPC on it, W/M is vehicle & acid with (follower/non-follower) NPC on it,
 * B/C is acid with (follower/non-follower) NPC on it.
 */
static constexpr int height = 5, width = 17;
// NOLINTNEXTLINE(cata-use-mdarray,modernize-avoid-c-arrays)
static constexpr char setup[height][width + 1] = {
    "U ###############",
    "V #R#AAA#W# # #C#",
    "  #A#A#A# #M#B# #",
    "  ###AAA#########",
    "    #####        ",
};

static void check_npc_movement( const tripoint &origin )
{
    INFO( "Should not crash from infinite recursion" );
    creature_tracker &creatures = get_creature_tracker();
    for( int y = 0; y < height; ++y ) {
        for( int x = 0; x < width; ++x ) {
            switch( setup[y][x] ) {
                case 'A':
                case 'R':
                case 'W':
                case 'M':
                case 'B':
                case 'C':
                    tripoint p = origin + point( x, y );
                    npc *guy = creatures.creature_at<npc>( p );
                    REQUIRE( guy != nullptr );
                    guy->move();
                    break;
            }
        }
    }

    INFO( "NPC on acid should not acquire unstable footing status" );
    for( int y = 0; y < height; ++y ) {
        for( int x = 0; x < width; ++x ) {
            if( setup[y][x] == 'A' ) {
                tripoint p = origin + point( x, y );
                npc *guy = creatures.creature_at<npc>( p );
                REQUIRE( guy != nullptr );
                CHECK( !guy->has_effect( effect_bouldering ) );
            }
        }
    }

    INFO( "NPC on rubbles should not lose unstable footing status" );
    for( int y = 0; y < height; ++y ) {
        for( int x = 0; x < width; ++x ) {
            if( setup[y][x] == 'R' ) {
                tripoint p = origin + point( x, y );
                npc *guy = creatures.creature_at<npc>( p );
                REQUIRE( guy != nullptr );
                CHECK( guy->has_effect( effect_bouldering ) );
            }
        }
    }

    INFO( "NPC in vehicle should not escape from dangerous terrain" );
    for( int y = 0; y < height; ++y ) {
        for( int x = 0; x < width; ++x ) {
            switch( setup[y][x] ) {
                case 'W':
                case 'M':
                    CAPTURE( setup[y][x] );
                    tripoint p = origin + point( x, y );
                    npc *guy = creatures.creature_at<npc>( p );
                    CHECK( guy != nullptr );
                    break;
            }
        }
    }

    INFO( "NPC not in vehicle should escape from dangerous terrain" );
    for( int y = 0; y < height; ++y ) {
        for( int x = 0; x < width; ++x ) {
            switch( setup[y][x] ) {
                case 'B':
                case 'C':
                    tripoint p = origin + point( x, y );
                    npc *guy = creatures.creature_at<npc>( p );
                    CHECK( guy == nullptr );
                    break;
            }
        }
    }
}

TEST_CASE( "npc-movement" )
{
    const ter_id t_wall_metal( "t_wall_metal" );
    const ter_id t_floor( "t_floor" );
    const furn_id f_rubble( "f_rubble" );
    const furn_id f_null( "f_null" );

    g->place_player( tripoint( 60, 60, 0 ) );

    clear_map();

    creature_tracker &creatures = get_creature_tracker();
    Character &player_character = get_player_character();
    map &here = get_map();
    for( int y = 0; y < height; ++y ) {
        for( int x = 0; x < width; ++x ) {
            const char type = setup[y][x];
            const tripoint p = player_character.pos() + point( x, y );
            // create walls
            if( type == '#' ) {
                here.ter_set( p, t_wall_metal );
            } else {
                here.ter_set( p, t_floor );
            }
            // spawn acid
            // a copy is needed because we will remove elements from it
            const field fs = here.field_at( p );
            for( const auto &f : fs ) {
                here.remove_field( p, f.first );
            }
            if( type == 'A' || type == 'R' || type == 'W' || type == 'M'
                || type == 'B' || type == 'C' ) {

                here.add_field( p, fd_acid, 3 );
            }
            // spawn rubbles
            if( type == 'R' ) {
                here.furn_set( p, f_rubble );
            } else {
                here.furn_set( p, f_null );
            }
            // create vehicles
            if( type == 'V' || type == 'W' || type == 'M' ) {
                vehicle *veh = here.add_vehicle( vehicle_prototype_none, p, 270_degrees, 0, 0 );
                REQUIRE( veh != nullptr );
                veh->install_part( point_zero, vpart_frame );
                veh->install_part( point_zero, vpart_seat );
                here.add_vehicle_to_cache( veh );
            }
            // spawn npcs
            if( type == 'A' || type == 'R' || type == 'W' || type == 'M'
                || type == 'B' || type == 'C' ) {

                shared_ptr_fast<npc> guy = make_shared_fast<npc>();
                do {
                    guy->normalize();
                    guy->randomize();
                    // Repeat until we get an NPC vulnerable to acid
                } while( guy->is_immune_field( fd_acid ) );
                guy->spawn_at_precise( tripoint_abs_ms( get_map().getabs( p ) ) );
                // Set the shopkeep mission; this means that
                // the NPC deems themselves to be guarding and stops them
                // wandering off in search of distant ammo caches, etc.
                guy->mission = NPC_MISSION_SHOPKEEP;
                overmap_buffer.insert_npc( guy );
                g->load_npcs();
                guy->set_attitude( ( type == 'M' || type == 'C' ) ? NPCATT_NULL : NPCATT_FOLLOW );
            }
        }
    }

    // check preconditions
    for( int y = 0; y < height; ++y ) {
        for( int x = 0; x < width; ++x ) {
            const char type = setup[y][x];
            const tripoint p = player_character.pos() + point( x, y );
            if( type == '#' ) {
                REQUIRE( !here.passable( p ) );
            } else {
                REQUIRE( here.passable( p ) );
            }
            if( type == 'R' ) {
                REQUIRE( here.has_flag( "UNSTABLE", p ) );
            } else {
                REQUIRE( !here.has_flag( "UNSTABLE", p ) );
            }
            if( type == 'V' || type == 'W' || type == 'M' ) {
                REQUIRE( here.veh_at( p ).part_with_feature( VPFLAG_BOARDABLE, true ).has_value() );
            } else {
                REQUIRE( !here.veh_at( p ).part_with_feature( VPFLAG_BOARDABLE, true ).has_value() );
            }
            npc *guy = creatures.creature_at<npc>( p );
            if( type == 'A' || type == 'R' || type == 'W' || type == 'M'
                || type == 'B' || type == 'C' ) {

                REQUIRE( guy != nullptr );
                REQUIRE( guy->is_dangerous_fields( here.field_at( p ) ) );
            } else {
                REQUIRE( guy == nullptr );
            }
        }
    }

    SECTION( "NPCs escape dangerous terrain by pushing other NPCs" ) {
        check_npc_movement( player_character.pos() );
    }

    SECTION( "Player in vehicle & NPCs escaping dangerous terrain" ) {
        const tripoint origin = player_character.pos();

        for( int y = 0; y < height; ++y ) {
            for( int x = 0; x < width; ++x ) {
                if( setup[y][x] == 'V' ) {
                    g->place_player( player_character.pos() + point( x, y ) );
                    break;
                }
            }
        }

        check_npc_movement( origin );
    }
}

TEST_CASE( "npc_can_target_player" )
{
    set_time_to_day();

    g->faction_manager_ptr->create_if_needed();

    g->place_player( tripoint_zero );

    clear_npcs();
    clear_creatures();

    Character &player_character = get_player_character();
    npc &hostile = spawn_npc( player_character.pos().xy() + point_south, "thug" );
    REQUIRE( rl_dist( player_character.pos(), hostile.pos() ) <= 1 );
    hostile.set_attitude( NPCATT_KILL );
    hostile.name = "Enemy NPC";

    INFO( get_list_of_npcs( "NPCs after spawning one" ) );

    hostile.regen_ai_cache();
    REQUIRE( hostile.current_target() != nullptr );
    CHECK( hostile.current_target() == static_cast<Creature *>( &player_character ) );
}

TEST_CASE( "npc environmental updates preserve turn semantics", "[npc][needs][temperature]" )
{
    clear_map();
    const bodypart_id torso( "torso" );
    const efftype_id effect_cold( "cold" );

    SECTION( "temperature effects refresh away from the ten-second boundary" ) {
        calendar::turn = calendar::turn_zero + 3_seconds;
        npc guy = create_model();
        guy.set_all_parts_temp_cur( BODYTEMP_FREEZING );
        guy.set_all_parts_temp_conv( BODYTEMP_FREEZING );

        guy.npc_update_body();

        CHECK( guy.has_effect( effect_cold, torso ) );
    }

    SECTION( "elapsed drying advances by the supplied duration" ) {
        npc guy = create_model();
        w_point dry_weather = *get_weather().weather_precise;
        dry_weather.temperature = units::from_fahrenheit( 90 );
        dry_weather.humidity = 0;
        dry_weather.windpower = 10;
        guy.set_part_wetness( torso, guy.get_part_drench_capacity( torso ) );
        const int before = guy.get_part_wetness( torso );

        guy.update_body_wetness( dry_weather, 30_minutes );

        CHECK( guy.get_part_wetness( torso ) < before );
    }

    SECTION( "on-load catch-up applies elapsed drying" ) {
        npc guy = create_model();
        weather_manager &weather = get_weather();
        weather.weather_precise->temperature = units::from_fahrenheit( 90 );
        weather.weather_precise->humidity = 0;
        weather.weather_precise->windpower = 10;
        guy.set_part_wetness( torso, guy.get_part_drench_capacity( torso ) );
        const int before = guy.get_part_wetness( torso );

        on_load_test( guy, 0_turns, 30_minutes );

        CHECK( guy.get_part_wetness( torso ) < before );
    }

    SECTION( "long catch-up stops evaporative cooling when drying finishes" ) {
        npc bulk = create_model();
        npc iterated = create_model();
        w_point dry_weather = *get_weather().weather_precise;
        dry_weather.temperature = units::from_fahrenheit( 90 );
        dry_weather.humidity = 0;
        dry_weather.windpower = 10;
        for( npc *guy : { &bulk, &iterated } ) {
            guy->set_all_parts_temp_cur( BODYTEMP_NORM );
            guy->set_part_wetness( torso, guy->get_part_drench_capacity( torso ) );
        }

        bulk.update_body_wetness( dry_weather, 2_days );
        int turns_until_dry = 0;
        while( iterated.get_part_wetness( torso ) > 0 && turns_until_dry < to_turns<int>( 2_days ) ) {
            iterated.update_body_wetness( dry_weather );
            ++turns_until_dry;
        }

        CHECK( bulk.get_part_wetness( torso ) == 0 );
        CHECK( iterated.get_part_wetness( torso ) == 0 );
        CHECK( std::abs( bulk.get_part_temp_cur( torso ) -
                         iterated.get_part_temp_cur( torso ) ) < 500 );
    }

    SECTION( "low-risk frostbite catch-up saturates at the frostnip ceiling" ) {
        npc guy = create_model();
        const bodypart_id hand( "hand_l" );
        weather_manager &weather = get_weather();
        weather.temperature = units::from_fahrenheit( 20 );
        weather.weather_precise->temperature = units::from_fahrenheit( 20 );
        weather.weather_precise->windpower = 0;
        guy.set_all_parts_temp_cur( BODYTEMP_FREEZING );
        guy.set_all_parts_temp_conv( BODYTEMP_FREEZING );
        guy.set_part_frostbite_timer( hand, 1999 );

        guy.update_bodytemp( 2_days );

        CHECK( guy.get_part_frostbite_timer( hand ) <= 2000 );
    }
}

TEST_CASE( "legacy NPC job priorities gain mopping without overwriting saves",
           "[npc][save][jobs]" )
{
    const activity_id butcher( "ACT_MULTIPLE_BUTCHER" );
    const activity_id mop( "ACT_MULTIPLE_MOP" );

    SECTION( "missing mopping priority is inserted at zero" ) {
        JsonValue json = json_loader::from_string(
                             R"({"task_priorities":{"ACT_MULTIPLE_BUTCHER":7}})" );
        job_data jobs;
        jobs.deserialize( json );

        CHECK( jobs.get_priority_of_job( butcher ) == 7 );
        CHECK( jobs.get_priority_of_job( mop ) == 0 );
        CHECK( jobs.set_task_priority( mop, 3 ) );
    }

    SECTION( "saved mopping priority is preserved" ) {
        JsonValue json = json_loader::from_string(
                             R"({"task_priorities":{"ACT_MULTIPLE_BUTCHER":4,"ACT_MULTIPLE_MOP":9}})" );
        job_data jobs;
        jobs.deserialize( json );

        CHECK( jobs.get_priority_of_job( butcher ) == 4 );
        CHECK( jobs.get_priority_of_job( mop ) == 9 );
    }
}

TEST_CASE( "tired non-allied NPCs use the sleep action", "[npc][needs][sleep]" )
{
    clear_map();
    calendar::turn = calendar::turn_zero + 1_hours;
    npc guy = create_model();
    guy.unset_mutation( trait_WEB_WEAVER );
    guy.set_fatigue( fatigue_levels::MASSIVE_FATIGUE + 100 );
    guy.set_hunger( 0 );
    guy.set_thirst( 0 );
    REQUIRE_FALSE( guy.is_player_ally() );

    for( int attempt = 0; attempt < 100 && !guy.has_effect( effect_sleep ); ++attempt ) {
        guy.execute_action( guy.address_needs( 0.0f ) );
    }

    CHECK( guy.has_effect( effect_sleep ) );
    CHECK( guy.get_fatigue() > 0 );
}
