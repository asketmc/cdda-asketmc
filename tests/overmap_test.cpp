#include <memory>
#include <set>
#include <sstream>
#include <string>
#include <utility>
#include <vector>

#include "all_enum_values.h"
#include "avatar.h"
#include "basecamp.h"
#include "calendar.h"
#include "cata_catch.h"
#include "common_types.h"
#include "coordinates.h"
#include "enums.h"
#include "faction.h"
#include "game.h"
#include "game_constants.h"
#include "global_vars.h"
#include "json.h"
#include "json_loader.h"
#include "map.h"
#include "mapbuffer.h"
#include "omdata.h"
#include "npc.h"
#include "overmap.h"
#include "overmap_types.h"
#include "overmapbuffer.h"
#include "stomach.h"
#include "type_id.h"

static const oter_str_id oter_cabin( "cabin" );
static const oter_str_id oter_cabin_east( "cabin_east" );
static const oter_str_id oter_cabin_north( "cabin_north" );
static const oter_str_id oter_cabin_south( "cabin_south" );
static const oter_str_id oter_cabin_west( "cabin_west" );

static const oter_type_str_id oter_type_ants_lab( "ants_lab" );
static const oter_type_str_id oter_type_ants_lab_stairs( "ants_lab_stairs" );
static const oter_type_str_id oter_type_bunker_shop_b( "bunker_shop_b" );
static const oter_type_str_id oter_type_bunker_shop_g( "bunker_shop_g" );
static const oter_type_str_id oter_type_ravine( "ravine" );
static const oter_type_str_id oter_type_ravine_edge( "ravine_edge" );
static const oter_type_str_id oter_type_ravine_floor( "ravine_floor" );
static const oter_type_str_id oter_type_ravine_floor_edge( "ravine_floor_edge" );
static const oter_type_str_id oter_type_rock_border( "rock_border" );
static const oter_type_str_id oter_type_s_gas_b11( "s_gas_b11" );
static const oter_type_str_id oter_type_s_gas_b20( "s_gas_b20" );
static const oter_type_str_id oter_type_s_gas_b21( "s_gas_b21" );
static const oter_type_str_id oter_type_s_gas_g0( "s_gas_g0" );
static const oter_type_str_id oter_type_s_gas_g0_roof( "s_gas_g0_roof" );
static const oter_type_str_id oter_type_s_gas_g1( "s_gas_g1" );
static const oter_type_str_id oter_type_s_gas_g1_roof( "s_gas_g1_roof" );
static const oter_type_str_id oter_type_s_restaurant_deserted_test( "s_restaurant_deserted_test" );

static const overmap_special_id overmap_special_Cabin( "Cabin" );
static const overmap_special_id overmap_special_Lab( "Lab" );

TEST_CASE( "camp_migration_uses_the_exact_representative_omt", "[overmap][camp]" )
{
    overmap *const test_overmap = overmap_buffer.get_existing( point_abs_om() );
    REQUIRE( test_overmap != nullptr );

    const tripoint_om_omt center( 90, 90, 0 );
    const tripoint_abs_omt center_abs = project_combine( test_overmap->pos(), center );
    const tripoint_abs_omt nearby_abs = project_combine( test_overmap->pos(),
                                            center + point( -3, 0 ) );

    std::vector<std::pair<tripoint_om_omt, oter_id>> previous_terrain;
    std::vector<tripoint_abs_omt> hive_points;
    for( int y = -1; y <= 1; ++y ) {
        for( int x = -1; x <= 1; ++x ) {
            const tripoint_om_omt local = center + point( x, y );
            previous_terrain.emplace_back( local, test_overmap->ter( local ) );
            test_overmap->ter_set( local, oter_id( "hive" ) );
            hive_points.push_back( project_combine( test_overmap->pos(), local ) );
        }
    }

    std::vector<basecamp> previous_camps = std::move( test_overmap->camps );
    test_overmap->camps.clear();
    const std::set<tripoint_abs_omt> previous_camp_index = get_avatar().camps;

    basecamp nearby_camp( "nearby camp", nearby_abs );
    nearby_camp.set_owner( faction_id( "your_followers" ) );
    overmap_buffer.add_camp( nearby_camp );

    test_overmap->migrate_camps( hive_points );

    const cata::optional<basecamp *> migrated = test_overmap->find_camp( center_abs.xy() );
    CHECK( migrated );
    if( migrated ) {
        CHECK( ( *migrated )->get_owner() == faction_id( "apis_hive" ) );
        CHECK( ( *migrated )->camp_name() == "???" );
    }
    CHECK( test_overmap->camps.size() == 2 );

    const cata::optional<basecamp *> nearby = test_overmap->find_camp( nearby_abs.xy() );
    CHECK( nearby );
    if( nearby ) {
        CHECK( ( *nearby )->get_owner() == faction_id( "your_followers" ) );
        CHECK( ( *nearby )->camp_name() == "nearby camp" );
    }

    test_overmap->camps = std::move( previous_camps );
    get_avatar().camps = previous_camp_index;
    for( const std::pair<tripoint_om_omt, oter_id> &entry : previous_terrain ) {
        test_overmap->ter_set( entry.first, entry.second );
    }
}

TEST_CASE( "camp_validation_rebuilds_the_index_from_loaded_overmaps", "[overmap][camp]" )
{
    overmap *const test_overmap = overmap_buffer.get_existing( point_abs_om() );
    REQUIRE( test_overmap != nullptr );

    const tripoint_abs_omt camp_pos = project_combine( test_overmap->pos(),
                                          tripoint_om_omt( 80, 80, 0 ) );
    std::vector<basecamp> previous_camps = std::move( test_overmap->camps );
    test_overmap->camps.clear();
    const std::set<tripoint_abs_omt> previous_camp_index = get_avatar().camps;

    overmap_buffer.add_camp( basecamp( "loaded camp", camp_pos ) );
    get_avatar().camps.erase( camp_pos );
    g->validate_camps();

    CHECK( get_avatar().camps.count( camp_pos ) == 1 );

    test_overmap->camps = std::move( previous_camps );
    get_avatar().camps = previous_camp_index;
}

TEST_CASE( "serialized_camps_are_indexed_when_an_overmap_loads", "[overmap][camp][savegame]" )
{
    const point_abs_om overmap_pos( 5, 5 );
    const tripoint_abs_omt camp_pos = project_combine( overmap_pos,
                                          tripoint_om_omt( 75, 75, 0 ) );
    basecamp serialized_camp( "serialized camp", camp_pos );
    serialized_camp.set_owner( faction_id( "your_followers" ) );

    std::ostringstream data;
    JsonOut json( data );
    json.start_object();
    json.member( "camps" );
    json.start_array();
    json.write( serialized_camp );
    json.end_array();
    json.end_object();

    const std::set<tripoint_abs_omt> previous_camp_index = get_avatar().camps;
    get_avatar().camps.erase( camp_pos );
    std::unique_ptr<overmap> loaded_overmap = std::make_unique<overmap>( overmap_pos );
    JsonValue value = json_loader::from_string( data.str() );
    loaded_overmap->unserialize( value.get_object() );

    CHECK( get_avatar().camps.count( camp_pos ) == 1 );
    CHECK( loaded_overmap->find_camp( camp_pos.xy() ) );

    get_avatar().camps = previous_camp_index;
}

TEST_CASE( "npc checks each nearby camp for accessible food and water", "[overmap][camp][npc]" )
{
    overmap *const test_overmap = overmap_buffer.get_existing( point_abs_om() );
    faction *const followers = get_avatar().get_faction();
    faction *const scavengers =
        g->faction_manager_ptr->get( faction_id( "wasteland_scavengers" ), false );
    REQUIRE( test_overmap != nullptr );
    REQUIRE( followers != nullptr );
    REQUIRE( scavengers != nullptr );

    const tripoint_abs_omt restricted_pos = project_combine( test_overmap->pos(),
            tripoint_om_omt( 70, 70, 0 ) );
    const tripoint_abs_omt accessible_pos = restricted_pos + point( 1, 0 );
    basecamp restricted_camp( "restricted camp", restricted_pos );
    restricted_camp.set_owner( scavengers->id );
    basecamp accessible_camp( "accessible camp", accessible_pos );
    accessible_camp.set_owner( followers->id );
    accessible_camp.add_expansion( "faction_base_camp_12", accessible_pos );
    REQUIRE( accessible_camp.has_water() );

    standard_npc hungry_npc( "hungry camp visitor" );
    hungry_npc.set_fac( followers->id );
    hungry_npc.spawn_at_omt( accessible_pos );
    hungry_npc.set_thirst( 81 );
    hungry_npc.set_hunger( 0 );
    hungry_npc.set_stored_kcal( hungry_npc.get_healthy_kcal() );
    REQUIRE_FALSE( restricted_camp.allowed_access_by( hungry_npc ) );
    REQUIRE( accessible_camp.allowed_access_by( hungry_npc ) );

    std::vector<basecamp> previous_camps = std::move( test_overmap->camps );
    test_overmap->camps.clear();
    const std::set<tripoint_abs_omt> previous_camp_index = get_avatar().camps;
    const nutrients previous_food_supply = followers->food_supply;
    const bool previously_consumed_food = followers->consumes_food;

    overmap_buffer.add_camp( restricted_camp );
    overmap_buffer.add_camp( accessible_camp );
    get_avatar().camps.clear();
    get_avatar().camps.insert( restricted_pos );
    get_avatar().camps.insert( accessible_pos );
    followers->food_supply = nutrients();
    followers->food_supply.calories = 5000 * 1000;
    followers->consumes_food = true;
    const int calories_before = followers->food_supply.calories;

    CHECK( hungry_npc.consume_food_from_camp() );
    CHECK( hungry_npc.get_thirst() <= 40 );
    CHECK_FALSE( hungry_npc.consume_food_from_camp() );

    hungry_npc.set_thirst( 0 );
    hungry_npc.set_hunger( 100 );
    hungry_npc.set_stored_kcal( hungry_npc.get_healthy_kcal() / 2 );
    CHECK( hungry_npc.consume_food_from_camp() );
    CHECK( followers->food_supply.calories < calories_before );

    test_overmap->camps = std::move( previous_camps );
    get_avatar().camps = previous_camp_index;
    followers->food_supply = previous_food_supply;
    followers->consumes_food = previously_consumed_food;
}

TEST_CASE( "npc camp water uses stomach capacity", "[overmap][camp][npc][needs]" )
{
    overmap *const test_overmap = overmap_buffer.get_existing( point_abs_om() );
    faction *const followers = get_avatar().get_faction();
    REQUIRE( test_overmap != nullptr );
    REQUIRE( followers != nullptr );

    const tripoint_abs_omt camp_pos = project_combine( test_overmap->pos(),
                                        tripoint_om_omt( 75, 75, 0 ) );
    basecamp water_camp( "water camp", camp_pos );
    water_camp.define_camp( camp_pos, "faction_base_bare_bones_NPC_camp_0", false );
    water_camp.set_owner( followers->id );
    REQUIRE( water_camp.has_water() );

    standard_npc thirsty_npc( "thirsty camp visitor" );
    thirsty_npc.set_fac( followers->id );
    thirsty_npc.spawn_at_omt( camp_pos );
    thirsty_npc.stomach.empty();
    thirsty_npc.guts.empty();
    thirsty_npc.set_hunger( 0 );

    std::vector<basecamp> previous_camps = std::move( test_overmap->camps );
    test_overmap->camps.clear();
    const std::set<tripoint_abs_omt> previous_camp_index = get_avatar().camps;
    overmap_buffer.add_camp( water_camp );
    get_avatar().camps.clear();
    get_avatar().camps.insert( camp_pos );

    SECTION( "water enters the stomach" ) {
        thirsty_npc.set_thirst( 200 );
        const units::volume before = thirsty_npc.stomach.get_water();

        CHECK( thirsty_npc.consume_food_from_camp() );
        CHECK( thirsty_npc.stomach.get_water() > before );
        CHECK( thirsty_npc.stomach.contains() <= thirsty_npc.stomach.capacity( thirsty_npc ) );
    }

    SECTION( "a full stomach refuses more water" ) {
        const units::volume room = thirsty_npc.stomach.stomach_remaining( thirsty_npc );
        thirsty_npc.stomach.ingest( { room, 0_ml, {} } );
        thirsty_npc.set_thirst( 600 );
        REQUIRE( thirsty_npc.get_thirst() > 40 );

        CHECK_FALSE( thirsty_npc.consume_food_from_camp() );
        CHECK( thirsty_npc.stomach.contains() <= thirsty_npc.stomach.capacity( thirsty_npc ) );
    }

    test_overmap->camps = std::move( previous_camps );
    get_avatar().camps = previous_camp_index;
}

TEST_CASE( "set_and_get_overmap_scents", "[overmap]" )
{
    std::unique_ptr<overmap> test_overmap = std::make_unique<overmap>( point_abs_om() );

    // By default there are no scents set.
    for( int x = 0; x < 180; ++x ) {
        for( int y = 0; y < 180; ++y ) {
            for( int z = -10; z < 10; ++z ) {
                REQUIRE( test_overmap->scent_at( { x, y, z } ).creation_time ==
                         calendar::before_time_starts );
            }
        }
    }

    time_point creation_time = calendar::turn_zero + 50_turns;
    scent_trace test_scent( creation_time, 90 );
    test_overmap->set_scent( { 75, 85, 0 }, test_scent );
    REQUIRE( test_overmap->scent_at( { 75, 85, 0} ).creation_time == creation_time );
    REQUIRE( test_overmap->scent_at( { 75, 85, 0} ).initial_strength == 90 );
}

TEST_CASE( "default_overmap_generation_always_succeeds", "[overmap][slow]" )
{
    int overmaps_to_construct = 10;
    for( const point_abs_om &candidate_addr : closest_points_first( point_abs_om(), 10 ) ) {
        // Skip populated overmaps.
        if( overmap_buffer.has( candidate_addr ) ) {
            continue;
        }
        overmap_special_batch test_specials = overmap_specials::get_default_batch( candidate_addr );
        overmap_buffer.create_custom_overmap( candidate_addr, test_specials );
        for( const overmap_special_placement &special_placement : test_specials ) {
            const overmap_special *special = special_placement.special_details;
            INFO( "In attempt #" << overmaps_to_construct
                  << " failed to place " << special->id.str() );
            int min_occur = special->get_constraints().occurrences.min;
            CHECK( min_occur <= special_placement.instances_placed );
        }
        if( --overmaps_to_construct <= 0 ) {
            break;
        }
    }
    overmap_buffer.clear();
}

TEST_CASE( "default_overmap_generation_has_non_mandatory_specials_at_origin", "[overmap][slow]" )
{
    const point_abs_om origin{};

    overmap_special mandatory;
    overmap_special optional;

    // Get some specific overmap specials so we can assert their presence later.
    // This should probably be replaced with some custom specials created in
    // memory rather than tying this test to these, but it works for now...
    for( const overmap_special &elem : overmap_specials::get_all() ) {
        if( elem.id == overmap_special_Cabin ) {
            optional = elem;
        } else if( elem.id == overmap_special_Lab ) {
            mandatory = elem;
        }
    }

    // Make this mandatory special impossible to place.
    const_cast<int &>( mandatory.get_constraints().city_size.min ) = 999;

    // Construct our own overmap_special_batch containing only our single mandatory
    // and single optional special, so we can make some assertions.
    std::vector<const overmap_special *> specials;
    specials.push_back( &mandatory );
    specials.push_back( &optional );
    overmap_special_batch test_specials = overmap_special_batch( origin, specials );

    // Run the overmap creation, which will try to place our specials.
    overmap_buffer.create_custom_overmap( origin, test_specials );

    // Get the origin overmap...
    overmap *test_overmap = overmap_buffer.get_existing( origin );

    // ...and assert that the optional special exists on this map.
    bool found_optional = false;
    for( int x = 0; x < OMAPX; ++x ) {
        for( int y = 0; y < OMAPY; ++y ) {
            const oter_id t = test_overmap->ter( { x, y, 0 } );
            if( t->id == oter_cabin ||
                t->id == oter_cabin_north || t->id == oter_cabin_east ||
                t->id == oter_cabin_south || t->id == oter_cabin_west ) {
                found_optional = true;
            }
        }
    }

    INFO( "Failed to place optional special on origin " );
    CHECK( found_optional == true );
    overmap_buffer.clear();
}

TEST_CASE( "is_ot_match", "[overmap][terrain]" )
{
    SECTION( "exact match" ) {
        // Matches the complete string
        // NOLINTNEXTLINE(cata-ot-match)
        CHECK( is_ot_match( "forest", oter_id( "forest" ), ot_match_type::exact ) );
        // NOLINTNEXTLINE(cata-ot-match)
        CHECK( is_ot_match( "central_lab", oter_id( "central_lab" ), ot_match_type::exact ) );

        // Does not exactly match if rotation differs
        // NOLINTNEXTLINE(cata-ot-match)
        CHECK_FALSE( is_ot_match( "sub_station", oter_id( "sub_station_north" ), ot_match_type::exact ) );
        // NOLINTNEXTLINE(cata-ot-match)
        CHECK_FALSE( is_ot_match( "sub_station", oter_id( "sub_station_south" ), ot_match_type::exact ) );
    }

    SECTION( "type match" ) {
        // Matches regardless of rotation
        // NOLINTNEXTLINE(cata-ot-match)
        CHECK( is_ot_match( "sub_station", oter_id( "sub_station_north" ), ot_match_type::type ) );
        // NOLINTNEXTLINE(cata-ot-match)
        CHECK( is_ot_match( "sub_station", oter_id( "sub_station_south" ), ot_match_type::type ) );
        // NOLINTNEXTLINE(cata-ot-match)
        CHECK( is_ot_match( "sub_station", oter_id( "sub_station_east" ), ot_match_type::type ) );
        // NOLINTNEXTLINE(cata-ot-match)
        CHECK( is_ot_match( "sub_station", oter_id( "sub_station_west" ), ot_match_type::type ) );

        // Does not match if base type does not match
        // NOLINTNEXTLINE(cata-ot-match)
        CHECK_FALSE( is_ot_match( "lab", oter_id( "central_lab" ), ot_match_type::type ) );
        // NOLINTNEXTLINE(cata-ot-match)
        CHECK_FALSE( is_ot_match( "sub_station", oter_id( "sewer_sub_station" ), ot_match_type::type ) );
    }

    SECTION( "prefix match" ) {
        // Matches the complete string
        CHECK( is_ot_match( "forest", oter_id( "forest" ), ot_match_type::prefix ) );
        CHECK( is_ot_match( "central_lab", oter_id( "central_lab" ), ot_match_type::prefix ) );

        // Prefix matches when an underscore separator exists
        CHECK( is_ot_match( "central", oter_id( "central_lab" ), ot_match_type::prefix ) );
        CHECK( is_ot_match( "central", oter_id( "central_lab_stairs" ), ot_match_type::prefix ) );

        // Prefix itself may contain underscores
        CHECK( is_ot_match( "central_lab", oter_id( "central_lab_stairs" ), ot_match_type::prefix ) );
        CHECK( is_ot_match( "central_lab_train", oter_id( "central_lab_train_depot" ),
                            ot_match_type::prefix ) );

        // Prefix does not match without an underscore separator
        CHECK_FALSE( is_ot_match( "fore", oter_id( "forest" ), ot_match_type::prefix ) );
        CHECK_FALSE( is_ot_match( "fore", oter_id( "forest_thick" ), ot_match_type::prefix ) );

        // Prefix does not match the middle or end
        CHECK_FALSE( is_ot_match( "lab", oter_id( "central_lab" ), ot_match_type::prefix ) );
        CHECK_FALSE( is_ot_match( "lab", oter_id( "central_lab_stairs" ), ot_match_type::prefix ) );
    }

    SECTION( "contains match" ) {
        // Matches the complete string
        CHECK( is_ot_match( "forest", oter_id( "forest" ), ot_match_type::contains ) );
        CHECK( is_ot_match( "central_lab", oter_id( "central_lab" ), ot_match_type::contains ) );

        // Matches the beginning/middle/end of an underscore-delimited id
        CHECK( is_ot_match( "central", oter_id( "central_lab_stairs" ), ot_match_type::contains ) );
        CHECK( is_ot_match( "lab", oter_id( "central_lab_stairs" ), ot_match_type::contains ) );
        CHECK( is_ot_match( "stairs", oter_id( "central_lab_stairs" ), ot_match_type::contains ) );

        // Matches the beginning/middle/end without undercores as well
        CHECK( is_ot_match( "cent", oter_id( "central_lab_stairs" ), ot_match_type::contains ) );
        CHECK( is_ot_match( "ral_lab", oter_id( "central_lab_stairs" ), ot_match_type::contains ) );
        CHECK( is_ot_match( "_lab_", oter_id( "central_lab_stairs" ), ot_match_type::contains ) );
        CHECK( is_ot_match( "airs", oter_id( "central_lab_stairs" ), ot_match_type::contains ) );

        // Does not match if substring is not contained
        CHECK_FALSE( is_ot_match( "forest", oter_id( "central_lab" ), ot_match_type::contains ) );
        CHECK_FALSE( is_ot_match( "forestry", oter_id( "forest" ), ot_match_type::contains ) );
    }
}

TEST_CASE( "mutable_overmap_placement", "[overmap][slow]" )
{
    const overmap_special &special =
        *overmap_special_id( GENERATE( "test_anthill", "test_crater", "test_microlab" ) );
    const city cit;

    constexpr int num_overmaps = 100;
    constexpr int num_trials_per_overmap = 100;

    global_variables &globvars = get_globals();
    globvars.clear_global_values();

    for( int j = 0; j < num_overmaps; ++j ) {
        // overmap objects are really large, so we don't want them on the
        // stack.  Use unique_ptr and put it on the heap
        std::unique_ptr<overmap> om = std::make_unique<overmap>( point_abs_om( point_zero ) );
        om_direction::type dir = om_direction::type::north;

        int successes = 0;

        for( int i = 0; i < num_trials_per_overmap; ++i ) {
            tripoint_om_omt try_pos( rng( 0, OMAPX - 1 ), rng( 0, OMAPY - 1 ), 0 );

            // This test can get very spammy, so abort once an error is
            // observed
            if( debug_has_error_been_observed() ) {
                return;
            }

            if( om->can_place_special( special, try_pos, dir, false ) ) {
                std::vector<tripoint_om_omt> placed_points =
                    om->place_special( special, try_pos, dir, cit, false, false );
                CHECK( !placed_points.empty() );
                ++successes;
            }
        }

        CHECK( successes > num_trials_per_overmap / 2 );
    }
}

TEST_CASE( "overmap_terrain_coverage", "[overmap][slow]" )
{
    // The goal of this test is to generate a lot of overmaps, and count up how
    // many times we see each terrain, so that we can check that everything
    // generates at least sometimes.

    struct omt_stats {
        explicit omt_stats( const tripoint_abs_omt &p ) : first_observed( p ) {}

        tripoint_abs_omt first_observed;
        int count = 0;
    };
    std::unordered_map<oter_type_id, omt_stats> stats;
    point_abs_omt origin;
    map &main_map = get_map();

    for( const point_abs_omt &p : closest_points_first( origin, 0, 10 * OMAPX - 1 ) ) {
        // We need to avoid OMTs that overlap with the 'main' map, so we start at a
        // non-zero minimum radius and ensure that the 'main' map is inside that
        // minimum radius.
        if( main_map.inbounds( tripoint_abs_ms( project_to<coords::ms>( p ), 0 ) ) ) {
            continue;
        }
        for( int z = -OVERMAP_DEPTH; z <= OVERMAP_HEIGHT; ++z ) {
            tripoint_abs_omt tp( p, z );
            oter_type_id id = overmap_buffer.ter( tp )->get_type_id();
            auto it = stats.emplace( id, tp ).first;
            ++it->second.count;
        }
    }

    std::unordered_set<oter_type_id> whitelist = {
        oter_type_ants_lab.id(), // ant lab is a very improbable spawn
        oter_type_ants_lab_stairs.id(),
        oter_type_bunker_shop_b.id(),
        oter_type_bunker_shop_g.id(),
        oter_type_ravine.id(), // ravine only in desert & Aftershock
        oter_type_ravine_edge.id(),
        oter_type_ravine_floor_edge.id(),
        oter_type_ravine_floor.id(),
        oter_type_rock_border.id(), // only in the bordered scenario
        oter_type_s_gas_b11.id(),
        oter_type_s_gas_b20.id(),
        oter_type_s_gas_b21.id(),
        oter_type_s_gas_g0.id(),
        oter_type_s_gas_g0_roof.id(),
        oter_type_s_gas_g1.id(),
        oter_type_s_gas_g1_roof.id(),
        oter_type_s_restaurant_deserted_test.id(), // only in the desert test region
    };

    std::unordered_set<oter_type_id> done;
    std::vector<oter_type_id> missing;

    global_variables &globvars = get_globals();
    globvars.clear_global_values();

    for( const oter_t &ter : overmap_terrains::get_all() ) {
        oter_type_id id = ter.get_type_id();
        oter_type_str_id id_s = id.id();
        if( id_s.is_empty() || id_s.is_null() ) {
            continue;
        }
        if( done.insert( id ).second ) {
            CAPTURE( id );
            auto it = stats.find( id );
            const bool found = it != stats.end();
            const bool should_be_found = !id->has_flag( oter_flags::should_not_spawn );

            if( found == should_be_found ) {
                continue;
            }

            // We also want to skip any terrain that's the result of a faction
            // camp construction recipe
            const recipe_id recipe( id_s.c_str() );
            if( recipe.is_valid() && recipe->is_blueprint() ) {
                continue;
            }

            if( found ) {
                FAIL( "oter_type_id was found in map but had SHOULD_NOT_SPAWN flag" );
            } else if( !whitelist.count( id ) ) {
                missing.push_back( id );
            }
        }
    }

    {
        size_t num_missing = missing.size();
        CAPTURE( num_missing );
        constexpr size_t max_to_report = 100;
        if( num_missing > max_to_report ) {
            std::shuffle( missing.begin(), missing.end(), rng_get_engine() );
            missing.erase( missing.begin() + max_to_report, missing.end() );
        }
        std::sort( missing.begin(), missing.end() );
        CAPTURE( missing );
        INFO( "To resolve errors about missing terrains you can either give the terrain the "
              "SHOULD_NOT_SPAWN flag (intended for terrains that should never spawn, for example "
              "test terrains or work in progress), or tweak the constraints so that the terrain "
              "can spawn more reliably, or add them to the whitelist above in this function "
              "(inteded for terrains that sometimes spawn, but cannot be expected to spawn "
              "reliably enough for this test)" );
        CHECK( num_missing == 0 );
    }

    // The second phase of this test is to perform the tile-level mapgen once
    // for each oter_type, in hopes of triggering any errors that might arise
    // with that.
    int num_generated_since_last_clear = 0;
    for( const std::pair<const oter_type_id, omt_stats> &p : stats ) {
        const tripoint_abs_omt pos = p.second.first_observed;
        tinymap tm;
        tm.load( project_to<coords::sm>( pos ), false );

        // Periodically clear the generated maps to save memory
        if( ++num_generated_since_last_clear >= 64 ) {
            MAPBUFFER.clear_outside_reality_bubble();
            num_generated_since_last_clear = 0;
        }
    }
}
