#include <algorithm>
#include <utility>

#include "avatar.h"
#include "calendar.h"
#include "cata_catch.h"
#include "computer.h"
#include "condition.h"
#include "debug.h"
#include "effect_on_condition.h"
#include "event_bus.h"
#include "game.h"
#include "global_vars.h"
#include "item.h"
#include "json_loader.h"
#include "map.h"
#include "mapbuffer.h"
#include "mapdata.h"
#include "map_helpers.h"
#include "monster.h"
#include "mutation.h"
#include "npc.h"
#include "timed_event.h"
#include "player_helpers.h"
#include "point.h"
#include "submap.h"

static const activity_id ACT_TEST_EOC_CANCEL( "ACT_TEST_EOC_CANCEL" );
static const activity_id ACT_TEST_EOC_COMPLETE_CANCEL( "ACT_TEST_EOC_COMPLETE_CANCEL" );
static const activity_id ACT_TEST_EOC_COMPLETE( "ACT_TEST_EOC_COMPLETE" );
static const activity_id ACT_TEST_EOC_COMPLETE_REPLACE( "ACT_TEST_EOC_COMPLETE_REPLACE" );
static const activity_id ACT_TEST_EOC_COMPLETE_REPLACE_SAME(
    "ACT_TEST_EOC_COMPLETE_REPLACE_SAME" );
static const activity_id ACT_TEST_EOC_DURING( "ACT_TEST_EOC_DURING" );
static const activity_id ACT_TEST_EOC_DURING_REPLACE( "ACT_TEST_EOC_DURING_REPLACE" );

static const effect_on_condition_id
effect_on_condition_EOC_TEST_ACTIVATE_MUTATION( "EOC_TEST_ACTIVATE_MUTATION" );
static const effect_on_condition_id
effect_on_condition_EOC_TEST_ADD_TRAIT_VARIANTS( "EOC_TEST_ADD_TRAIT_VARIANTS" );
static const effect_on_condition_id
effect_on_condition_EOC_TEST_CONTEXT_ROOT( "EOC_TEST_CONTEXT_ROOT" );
static const effect_on_condition_id
effect_on_condition_EOC_TEST_COMPUTER_TALKER( "EOC_TEST_COMPUTER_TALKER" );
static const effect_on_condition_id effect_on_condition_EOC_TEST_IF_ELSE( "EOC_TEST_IF_ELSE" );
static const effect_on_condition_id effect_on_condition_EOC_TEST_FOREACH_ARRAY(
    "EOC_TEST_FOREACH_ARRAY" );
static const effect_on_condition_id effect_on_condition_EOC_TEST_FOREACH_GROUPS(
    "EOC_TEST_FOREACH_GROUPS" );
static const effect_on_condition_id effect_on_condition_EOC_TEST_FOREACH_REGISTRIES(
    "EOC_TEST_FOREACH_REGISTRIES" );
static const effect_on_condition_id effect_on_condition_EOC_TEST_MAP_FLAGS( "EOC_TEST_MAP_FLAGS" );
static const effect_on_condition_id effect_on_condition_EOC_TEST_MAP_FLAGS_DEFAULT(
    "EOC_TEST_MAP_FLAGS_DEFAULT" );
static const effect_on_condition_id effect_on_condition_EOC_TEST_MAP_RUN_ALL(
    "EOC_TEST_MAP_RUN_ALL" );
static const effect_on_condition_id effect_on_condition_EOC_TEST_MAP_RUN_NO_MATCH(
    "EOC_TEST_MAP_RUN_NO_MATCH" );
static const effect_on_condition_id effect_on_condition_EOC_TEST_MAP_RUN_RANDOM(
    "EOC_TEST_MAP_RUN_RANDOM" );
static const effect_on_condition_id effect_on_condition_EOC_TEST_MAP_SPAWN_CONTAINER(
    "EOC_TEST_MAP_SPAWN_CONTAINER" );
static const effect_on_condition_id effect_on_condition_EOC_TEST_MAP_SPAWN_GROUP(
    "EOC_TEST_MAP_SPAWN_GROUP" );
static const effect_on_condition_id effect_on_condition_EOC_TEST_MAP_SPAWN_INVALID_CONTAINER(
    "EOC_TEST_MAP_SPAWN_INVALID_CONTAINER" );
static const effect_on_condition_id effect_on_condition_EOC_TEST_MAP_SPAWN_PARTIAL_CONTAINER(
    "EOC_TEST_MAP_SPAWN_PARTIAL_CONTAINER" );
static const effect_on_condition_id effect_on_condition_EOC_TEST_MAP_SPAWN_NONCHARGE_CONTAINER(
    "EOC_TEST_MAP_SPAWN_NONCHARGE_CONTAINER" );
static const effect_on_condition_id effect_on_condition_EOC_TEST_MAP_SPAWN_DEFAULT(
    "EOC_TEST_MAP_SPAWN_DEFAULT" );
static const effect_on_condition_id effect_on_condition_EOC_TEST_MAP_SPAWN_DIRECT(
    "EOC_TEST_MAP_SPAWN_DIRECT" );
static const effect_on_condition_id effect_on_condition_EOC_TEST_NPC_MAP_RUN_ALL(
    "EOC_TEST_NPC_MAP_RUN_ALL" );
static const effect_on_condition_id effect_on_condition_EOC_TEST_NPC_DEATH_NO_PREVENT(
    "EOC_TEST_NPC_DEATH_NO_PREVENT" );
static const effect_on_condition_id effect_on_condition_EOC_TEST_NPC_PREVENT_DEATH(
    "EOC_TEST_NPC_PREVENT_DEATH" );
static const effect_on_condition_id effect_on_condition_EOC_TEST_QUERY_TILE_NON_AVATAR(
    "EOC_TEST_QUERY_TILE_NON_AVATAR" );
static const effect_on_condition_id effect_on_condition_EOC_TEST_QUERY_TILE_AVATAR(
    "EOC_TEST_QUERY_TILE_AVATAR" );
static const effect_on_condition_id
effect_on_condition_EOC_TEST_STRING_VAR_INDIRECTION( "EOC_TEST_STRING_VAR_INDIRECTION" );
static const effect_on_condition_id effect_on_condition_EOC_TEST_MONSTER_TYPE_FLAG(
    "EOC_TEST_MONSTER_TYPE_FLAG" );
static const effect_on_condition_id
effect_on_condition_EOC_TEST_STORED_CONDITION_ROOT( "EOC_TEST_STORED_CONDITION_ROOT" );
static const effect_on_condition_id
effect_on_condition_EOC_TEST_RUN_INV_ALL( "EOC_TEST_RUN_INV_ALL" );
static const effect_on_condition_id
effect_on_condition_EOC_TEST_RUN_INV_FLAG( "EOC_TEST_RUN_INV_FLAG" );
static const effect_on_condition_id
effect_on_condition_EOC_TEST_RUN_INV_INVALID( "EOC_TEST_RUN_INV_INVALID" );
static const effect_on_condition_id
effect_on_condition_EOC_TEST_RUN_INV_NO_MATCH( "EOC_TEST_RUN_INV_NO_MATCH" );
static const effect_on_condition_id effect_on_condition_EOC_TEST_RUN_INV_MANUAL_NO_MATCH(
    "EOC_TEST_RUN_INV_MANUAL_NO_MATCH" );
static const effect_on_condition_id effect_on_condition_EOC_TEST_RUN_INV_MANUAL_MULT_NO_MATCH(
    "EOC_TEST_RUN_INV_MANUAL_MULT_NO_MATCH" );
static const effect_on_condition_id
effect_on_condition_EOC_TEST_RUN_INV_RANDOM( "EOC_TEST_RUN_INV_RANDOM" );
static const effect_on_condition_id
effect_on_condition_EOC_TEST_RUN_INV_WOOD( "EOC_TEST_RUN_INV_WOOD" );
static const effect_on_condition_id
effect_on_condition_EOC_TEST_RUN_INV_WORN( "EOC_TEST_RUN_INV_WORN" );
static const effect_on_condition_id
effect_on_condition_EOC_TEST_TRANSFORM_LINE( "EOC_TEST_TRANSFORM_LINE" );
static const effect_on_condition_id
effect_on_condition_EOC_TEST_TRANSFORM_RADIUS( "EOC_TEST_TRANSFORM_RADIUS" );
static const effect_on_condition_id
effect_on_condition_EOC_TEST_VAR_INDIRECTION( "EOC_TEST_VAR_INDIRECTION" );
static const effect_on_condition_id effect_on_condition_EOC_teleport_test( "EOC_teleport_test" );

static const itype_id itype_backpack( "backpack" );
static const itype_id itype_bottle_plastic( "bottle_plastic" );
static const itype_id itype_bow_saw( "bow_saw" );
static const itype_id itype_hammer( "hammer" );
static const itype_id itype_jug_plastic( "jug_plastic" );
static const itype_id itype_sword_wood( "sword_wood" );
static const itype_id itype_knife_combat( "knife_combat" );
static const itype_id itype_water( "water" );

static const trait_id trait_TEST_EOC_MUTATION_ONESHOT( "TEST_EOC_MUTATION_ONESHOT" );
static const trait_id trait_TEST_EOC_MUTATION_PROCESSED( "TEST_EOC_MUTATION_PROCESSED" );
static const trait_id trait_TEST_EOC_MUTATION_PROCESSED_ZERO(
    "TEST_EOC_MUTATION_PROCESSED_ZERO" );
static const trait_id trait_TEST_EOC_MUTATION_STARVING( "TEST_EOC_MUTATION_STARVING" );
static const trait_id trait_TEST_EOC_MUTATION_DEHYDRATED( "TEST_EOC_MUTATION_DEHYDRATED" );
static const trait_id trait_TEST_EOC_MUTATION_EXHAUSTED( "TEST_EOC_MUTATION_EXHAUSTED" );
namespace
{
int complete_activity( Character &who )
{
    int turns = 0;
    while( !who.activity.is_null() ) {
        who.set_moves( who.get_speed() );
        who.activity.do_turn( who );
        ++turns;
    }
    return turns;
}

void check_ter_in_radius( tripoint_abs_ms const &center, int range, ter_id const &ter )
{
    map tm;
    tm.load( project_to<coords::sm>( center - point{ range, range } ), false, false );
    tripoint_bub_ms const center_local = tm.bub_from_abs( center );
    for( tripoint_bub_ms p : tm.points_in_radius( center_local, range ) ) {
        if( trig_dist( center_local, p ) <= range ) {
            REQUIRE( tm.ter( p ) == ter );
        }
    }
}

void check_ter_in_line( tripoint_abs_ms const &first, tripoint_abs_ms const &second,
                        ter_id const &ter )
{
    map tm;
    tripoint_abs_ms const orig = coord_min( first, second );
    tm.load( project_to<coords::sm>( orig ), false, false );
    for( tripoint_abs_ms p : line_to( first, second ) ) {
        REQUIRE( tm.ter( tm.getlocal( p ) ) == ter );
    }
}

} // namespace

TEST_CASE( "event_EOC_runs_for_game_load", "[eoc][event]" )
{
    avatar &you = get_avatar();
    global_variables &globals = get_globals();
    clear_avatar();
    const std::string variable = "npctalk_var_test_eoc_event_fired";
    const std::string version_variable = "npctalk_var_test_event_cdda_version";
    you.remove_value( variable );
    globals.remove_global_value( version_variable );

    get_event_bus().send<event_type::game_load>( "test-version" );

    CHECK( you.get_value( variable ) == "yes" );
    CHECK( globals.get_global_value( version_variable ) == "test-version" );
    you.remove_value( variable );
    globals.remove_global_value( version_variable );
}

TEST_CASE( "event_EOC_character_resolution_skips_stale_ids", "[eoc][event]" )
{
    avatar &you = get_avatar();
    clear_avatar();
    clear_npcs();
    clear_map();
    const std::string variable = "npctalk_var_test_npc_death_event_count";

    npc &resolved = spawn_npc( you.pos().xy() + point_south, "thug" );
    resolved.remove_value( variable );
    you.remove_value( variable );

    eoc_events subscriber;
    cata::event::data_type recoverable_data;
    recoverable_data.emplace( "character",
                              cata_variant::make<cata_variant_type::character_id>( character_id( 1000000 ) ) );
    recoverable_data.emplace( "attacker",
                              cata_variant::make<cata_variant_type::character_id>( resolved.getID() ) );
    subscriber.notify( cata::event( event_type::character_dies, calendar::turn,
                                   std::move( recoverable_data ) ) );
    CHECK( resolved.get_value( variable ) == "1" );
    CHECK( you.get_value( variable ).empty() );

    cata::event::data_type stale_data;
    stale_data.emplace( "character",
                        cata_variant::make<cata_variant_type::character_id>( character_id( 1000001 ) ) );
    const std::string error = capture_debugmsg_during( [&]() {
        subscriber.notify( cata::event( event_type::character_dies, calendar::turn,
                                       std::move( stale_data ) ) );
    } );
    CHECK( error.find( "could not resolve any referenced character" ) != std::string::npos );
    CHECK( you.get_value( variable ).empty() );

    clear_npcs();
}

TEST_CASE( "event_EOCs_receive_item_and_creature_talkers", "[eoc][event][talker]" )
{
    avatar &you = get_avatar();
    const std::string variable = "npctalk_var_test_event_talker_last_event";
    clear_avatar();
    clear_npcs();
    clear_map();

    item weapon_item( itype_knife_combat );
    REQUIRE( you.wield( weapon_item ) );
    item_location wielded = you.get_wielded_item();
    CHECK( you.get_value( variable ) == "character_wields_item" );
    CHECK( wielded->get_var( variable ) == "character_wields_item" );

    const auto worn = you.worn.wear_item( you, item( itype_backpack ), false, false );
    REQUIRE( worn );
    CHECK( you.get_value( variable ) == "character_wears_item" );
    CHECK( ( *worn )->get_var( variable ) == "character_wears_item" );

    npc &melee_npc = spawn_npc( you.pos().xy() + point_south, "thug" );
    you.melee_attack( melee_npc, false );
    CHECK( you.get_value( variable ) == "character_melee_attacks_character" );
    CHECK( melee_npc.get_value( variable ) == "character_melee_attacks_character" );

    clear_map();
    monster &melee_monster = spawn_test_monster( "mon_zombie", you.pos() + tripoint_east );
    you.melee_attack( melee_monster, false );
    CHECK( you.get_value( variable ) == "character_melee_attacks_monster" );
    CHECK( melee_monster.get_value( variable ) == "character_melee_attacks_monster" );

    clear_map();
    clear_npcs();
    const tripoint ranged_target = you.pos() + tripoint_east;
    npc &ranged_npc = spawn_npc( ranged_target.xy(), "thug" );
    you.remove_value( variable );
    ranged_npc.remove_value( variable );
    for( const bodypart_id &part : ranged_npc.get_all_body_parts() ) {
        ranged_npc.set_part_hp_max( part, 10000 );
        ranged_npc.set_part_hp_cur( part, 10000 );
    }
    for( int attempt = 0; attempt < 100 && ranged_npc.get_value( variable ).empty(); ++attempt ) {
        arm_shooter( you, "shotgun_s" );
        you.recoil = 0;
        you.fire_gun( ranged_target, 1, *you.get_wielded_item() );
    }
    CHECK( you.get_value( variable ) == "character_ranged_attacks_character" );
    CHECK( ranged_npc.get_value( variable ) == "character_ranged_attacks_character" );

    clear_map();
    clear_npcs();
    monster &ranged_monster = spawn_test_monster( "mon_zombie", ranged_target );
    you.remove_value( variable );
    ranged_monster.remove_value( variable );
    ranged_monster.set_hp( 10000 );
    for( int attempt = 0; attempt < 100 && ranged_monster.get_value( variable ).empty(); ++attempt ) {
        arm_shooter( you, "shotgun_s" );
        you.recoil = 0;
        you.fire_gun( ranged_target, 1, *you.get_wielded_item() );
    }
    CHECK( you.get_value( variable ) == "character_ranged_attacks_monster" );
    CHECK( ranged_monster.get_value( variable ) == "character_ranged_attacks_monster" );

    clear_map();
    clear_npcs();
    clear_avatar();
    item wielded_backpack( itype_backpack );
    REQUIRE( you.wield( wielded_backpack ) );
    const std::string unwield_variable = "npctalk_var_test_event_talker_unwield";
    you.remove_value( unwield_variable );
    REQUIRE( you.wear( you.get_wielded_item(), false ) );
    CHECK( you.get_value( unwield_variable ) == "yes" );
}

TEST_CASE( "item_EVENT_EOCs_can_remove_wielded_and_worn_items_safely",
           "[eoc][event][item_lifetime]" )
{
    avatar &you = get_avatar();
    clear_avatar();
    clear_map();

    const std::string remove_wielded = "npctalk_var_test_event_talker_remove_wielded";
    you.set_value( remove_wielded, "yes" );
    item combat_knife( itype_knife_combat );
    REQUIRE( you.wield( combat_knife ) );
    CHECK_FALSE( you.get_wielded_item() );
    you.remove_value( remove_wielded );

    item backpack( itype_backpack );
    REQUIRE( you.wield( backpack ) );
    const std::string remove_worn = "npctalk_var_test_event_talker_remove_worn";
    you.set_value( remove_worn, "yes" );
    CHECK_FALSE( you.wear( you.get_wielded_item(), false ) );
    CHECK_FALSE( you.get_wielded_item() );
    CHECK( you.amount_worn( itype_backpack ) == 0 );
    you.remove_value( remove_worn );

    clear_npcs();
    npc &ally = spawn_npc( you.pos().xy() + point_east, "thug" );
    ally.set_value( remove_wielded, "yes" );
    item npc_knife( itype_knife_combat );
    REQUIRE( ally.wield( npc_knife ) );
    CHECK_FALSE( ally.get_wielded_item() );
    clear_npcs();
}

TEST_CASE( "EOC_activation_preserves_computer_and_dialogue_context", "[eoc][talker][computer]" )
{
    avatar &you = get_avatar();
    clear_avatar();
    clear_map();

    computer terminal( "Test computer", 0, you.pos() );
    const std::string terminal_var = "npctalk_var_test_eoc_computer_talker";
    terminal.remove_value( terminal_var );

    dialogue d( get_talker_for( you ), get_talker_for( terminal ) );
    d.reason = "computer test";
    d.cur_item = itype_knife_combat;
    d.by_radio = true;

    const std::string debug_message = capture_debugmsg_during( [&]() {
        CHECK( effect_on_condition_EOC_TEST_COMPUTER_TALKER->activate( d ) );
    } );
    CHECK( debug_message.empty() );
    CHECK( terminal.get_value( terminal_var ) == "yes" );

    dialogue copied = copy_dialogue( d );
    REQUIRE( copied.has_beta );
    CHECK( copied.actor( true )->get_computer() == &terminal );
    CHECK( copied.reason == d.reason );
    CHECK( copied.cur_item == d.cur_item );
    CHECK( copied.by_radio == d.by_radio );

    const Creature &const_you = you;
    dialogue const_dialogue( get_talker_for( const_you ), nullptr );
    dialogue const_copy = copy_dialogue( const_dialogue );
    const talker *const_alpha = const_copy.actor( false );
    CHECK( const_alpha->get_creature() == &you );
}

TEST_CASE( "NPC_death_EOCs_run_before_cleanup_and_can_prevent_death", "[eoc][event][death]" )
{
    clear_avatar();
    clear_npcs();
    clear_map();

    const std::string eoc_count = "npctalk_var_test_npc_death_eoc_count";
    const std::string event_count = "npctalk_var_test_npc_death_event_count";
    const std::string event_prevent = "npctalk_var_test_npc_death_event_prevent_count";
    const std::string prevent_via_event = "npctalk_var_test_npc_death_prevent_via_event";
    const auto make_mortally_wounded = []( npc & guy ) {
        for( const bodypart_id &bp : guy.get_all_body_parts( get_body_part_flags::only_main ) ) {
            if( bp->is_vital ) {
                guy.set_part_hp_cur( bp, 0 );
            }
        }
    };
    const auto count_corpses = []( const tripoint & pos ) {
        int result = 0;
        for( const item &it : get_map().i_at( pos ) ) {
            if( it.is_corpse() ) {
                ++result;
            }
        }
        return result;
    };

    npc &survivor = spawn_npc( get_avatar().pos().xy() + point_south, "thug" );
    survivor.death_eocs.push_back( effect_on_condition_EOC_TEST_NPC_PREVENT_DEATH );
    survivor.remove_value( eoc_count );
    survivor.remove_value( event_count );
    survivor.marked_for_death = true;
    make_mortally_wounded( survivor );
    REQUIRE( survivor.is_dead_state() );
    const tripoint survivor_pos = survivor.pos();

    survivor.die( nullptr );

    CHECK_FALSE( survivor.is_dead() );
    CHECK_FALSE( survivor.marked_for_death );
    CHECK( survivor.get_value( eoc_count ) == "1" );
    CHECK( survivor.get_value( event_count ) == "1" );
    CHECK( count_corpses( survivor_pos ) == 0 );

    survivor.death_eocs.clear();
    clear_npcs();
    clear_map();

    npc &event_survivor = spawn_npc( get_avatar().pos().xy() + point_south, "thug" );
    event_survivor.set_value( prevent_via_event, "yes" );
    event_survivor.remove_value( event_count );
    event_survivor.remove_value( event_prevent );
    make_mortally_wounded( event_survivor );
    REQUIRE( event_survivor.is_dead_state() );
    const tripoint event_survivor_pos = event_survivor.pos();

    event_survivor.die( nullptr );

    CHECK_FALSE( event_survivor.is_dead() );
    CHECK( event_survivor.get_value( event_count ) == "1" );
    CHECK( event_survivor.get_value( event_prevent ) == "1" );
    CHECK( count_corpses( event_survivor_pos ) == 0 );

    event_survivor.remove_value( prevent_via_event );
    clear_npcs();
    clear_map();

    npc &victim = spawn_npc( get_avatar().pos().xy() + point_south, "thug" );
    victim.death_eocs.push_back( effect_on_condition_EOC_TEST_NPC_DEATH_NO_PREVENT );
    victim.remove_value( eoc_count );
    victim.remove_value( event_count );
    make_mortally_wounded( victim );
    REQUIRE( victim.is_dead_state() );
    const tripoint victim_pos = victim.pos();

    victim.die( nullptr );

    CHECK( victim.is_dead() );
    CHECK( victim.get_value( eoc_count ) == "1" );
    CHECK( victim.get_value( event_count ) == "1" );
    CHECK( count_corpses( victim_pos ) == 1 );

    clear_npcs();
    clear_map();
}

TEST_CASE( "character_dies_EVENT_fires_for_avatar_and_can_prevent_death",
           "[eoc][event][death]" )
{
    avatar &you = get_avatar();
    clear_avatar();
    clear_map();

    const std::string event_count = "npctalk_var_test_npc_death_event_count";
    const std::string event_prevent = "npctalk_var_test_npc_death_event_prevent_count";
    const std::string prevent_via_event = "npctalk_var_test_npc_death_prevent_via_event";
    you.remove_value( event_count );
    you.remove_value( event_prevent );
    you.set_value( prevent_via_event, "yes" );
    for( const bodypart_id &bp : you.get_all_body_parts( get_body_part_flags::only_main ) ) {
        if( bp->is_vital ) {
            you.set_part_hp_cur( bp, 0 );
        }
    }
    REQUIRE( you.is_dead_state() );

    g->uquit = QUIT_NO;
    CHECK_FALSE( g->is_game_over() );

    CHECK_FALSE( you.is_dead_state() );
    CHECK( g->uquit == QUIT_NO );
    CHECK( you.get_value( event_count ) == "1" );
    CHECK( you.get_value( event_prevent ) == "1" );
    you.remove_value( prevent_via_event );
}

TEST_CASE( "prevented_overmap_NPC_death_still_activates_the_NPC", "[eoc][event][death]" )
{
    clear_avatar();
    clear_npcs();
    clear_map();

    npc &survivor = spawn_npc( get_avatar().pos().xy() + point_south, "thug" );
    const character_id survivor_id = survivor.getID();
    survivor.death_eocs.push_back( effect_on_condition_EOC_TEST_NPC_PREVENT_DEATH );
    survivor.marked_for_death = true;
    for( const bodypart_id &bp : survivor.get_all_body_parts( get_body_part_flags::only_main ) ) {
        if( bp->is_vital ) {
            survivor.set_part_hp_cur( bp, 0 );
        }
    }
    REQUIRE( survivor.is_dead_state() );
    const auto survivor_is_active = [&]() {
        for( const npc &guy : g->all_npcs() ) {
            if( guy.getID() == survivor_id ) {
                return true;
            }
        }
        return false;
    };

    g->reload_npcs();

    npc *loaded_survivor = g->find_npc( survivor_id );
    REQUIRE( loaded_survivor != nullptr );
    CHECK_FALSE( loaded_survivor->is_dead() );
    CHECK_FALSE( loaded_survivor->marked_for_death );
    CHECK( survivor_is_active() );

    loaded_survivor->death_eocs.clear();
    clear_npcs();
    clear_map();
}

TEST_CASE( "EOC_context_is_inherited_but_not_returned", "[eoc][context]" )
{
    clear_avatar();
    clear_map();

    dialogue d( get_talker_for( get_avatar() ), nullptr );
    global_variables &globals = get_globals();
    const std::vector<std::string> variables = {
        "npctalk_var_test_context_simple",
        "npctalk_var_test_context_nested",
        "npctalk_var_test_context_not_returned"
    };
    for( const std::string &variable : variables ) {
        globals.remove_global_value( variable );
    }

    CHECK( effect_on_condition_EOC_TEST_CONTEXT_ROOT->activate( d ) );
    CHECK( globals.get_global_value( variables[0] ) == "12" );
    CHECK( globals.get_global_value( variables[1] ) == "7" );
    CHECK( globals.get_global_value( variables[2] ) == "0" );
    CHECK( d.get_value( "npctalk_var_simple" ).empty() );

    for( const std::string &variable : variables ) {
        globals.remove_global_value( variable );
    }
}

TEST_CASE( "run_and_queue_EOCs_accept_variable_selected_ids", "[eoc][context][queue]" )
{
    avatar &you = get_avatar();
    clear_avatar();
    clear_map();
    effect_on_conditions::clear( you );

    const std::string run_fixed = "npctalk_var_test_dynamic_run_fixed";
    const std::string run_variable = "npctalk_var_test_dynamic_run_variable";
    const std::string queue_fixed = "npctalk_var_test_dynamic_queue_fixed";
    const std::string queue_variable = "npctalk_var_test_dynamic_queue_variable";
    for( const std::string &variable : { run_fixed, run_variable, queue_fixed, queue_variable } ) {
        you.remove_value( variable );
    }

    dialogue d( get_talker_for( you ), nullptr );
    CHECK( effect_on_condition_EOC_TEST_DYNAMIC_RUN_ROOT->activate( d ) );
    CHECK( you.get_value( run_fixed ) == "1" );
    CHECK( you.get_value( run_variable ) == "1" );

    CHECK( effect_on_condition_EOC_TEST_DYNAMIC_QUEUE_ROOT->activate( d ) );
    CHECK( you.get_value( queue_fixed ).empty() );
    CHECK( you.get_value( queue_variable ).empty() );
    CHECK( you.queued_effect_on_conditions.size() == 2 );

    effect_on_conditions::process_effect_on_conditions( you );
    CHECK( you.get_value( queue_fixed ) == "1" );
    CHECK( you.get_value( queue_variable ) == "1" );
    CHECK( you.queued_effect_on_conditions.empty() );

    for( const std::string &variable : { run_fixed, run_variable, queue_fixed, queue_variable } ) {
        you.remove_value( variable );
    }
    effect_on_conditions::clear( you );
}

TEST_CASE( "malformed_inline_EOC_is_not_reinterpreted_as_a_variable", "[eoc][json]" )
{
    JsonValue value = json_loader::from_string( R"({
        "run_eocs": {
            "id": "EOC_TEST_MALFORMED_INLINE",
            "context_val": "fallback_id",
            "effect": 7
        }
    })" );
    JsonObject object = value.get_object();
    talk_effect_fun_t<dialogue> effect;

    CHECK_THROWS_AS( effect.set_run_eocs( object, "run_eocs" ), JsonError );
}

TEST_CASE( "run_EOCs_accept_inline_objects_and_reject_invalid_dynamic_ids", "[eoc][json]" )
{
    avatar &you = get_avatar();
    clear_avatar();
    dialogue d( get_talker_for( you ), nullptr );

    JsonValue inline_value = json_loader::from_string( R"({
        "run_eocs": {
            "id": "EOC_TEST_INLINE_RUN_DIRECT",
            "effect": {
                "u_adjust_var": "inline_count",
                "type": "test",
                "context": "dynamic_run",
                "adjustment": 1
            }
        }
    })" );
    talk_effect_fun_t<dialogue> inline_effect;
    inline_effect.set_run_eocs( inline_value.get_object(), "run_eocs" );
    inline_effect( d );
    CHECK( you.get_value( "npctalk_var_test_dynamic_run_inline_count" ) == "1" );

    JsonValue dynamic_value = json_loader::from_string( R"({
        "run_eocs": { "context_val": "selected_eoc" }
    })" );
    talk_effect_fun_t<dialogue> dynamic_effect;
    dynamic_effect.set_run_eocs( dynamic_value.get_object(), "run_eocs" );
    d.set_value( "npctalk_var_selected_eoc", "EOC_TEST_DOES_NOT_EXIST" );
    const std::string error = capture_debugmsg_during( [&]() {
        dynamic_effect( d );
    } );
    CHECK( error.find( "resolved invalid effect_on_condition id EOC_TEST_DOES_NOT_EXIST" ) !=
           std::string::npos );
    CHECK( you.get_value( "npctalk_var_test_dynamic_run_inline_count" ) == "1" );

    you.remove_value( "npctalk_var_test_dynamic_run_inline_count" );
}

TEST_CASE( "EOC_indirect_variable_resolution", "[eoc][context]" )
{
    avatar &you = get_avatar();
    clear_avatar();
    clear_map();

    dialogue d( get_talker_for( you ), nullptr );
    global_variables &globals = get_globals();
    const std::vector<std::string> numeric_variables = {
        "npctalk_var_key1",
        "npctalk_var_test_var_global",
        "npctalk_var_test_var_u",
        "npctalk_var_test_var_context",
        "npctalk_var_test_var_nested"
    };
    for( const std::string &variable : numeric_variables ) {
        globals.remove_global_value( variable );
    }
    you.remove_value( "npctalk_var_key1" );

    CHECK( effect_on_condition_EOC_TEST_VAR_INDIRECTION->activate( d ) );
    CHECK( globals.get_global_value( "npctalk_var_key1" ) == "5" );
    CHECK( globals.get_global_value( "npctalk_var_test_var_global" ) == "10" );
    CHECK( you.get_value( "npctalk_var_key1" ) == "3" );
    CHECK( globals.get_global_value( "npctalk_var_test_var_u" ) == "6" );
    CHECK( globals.get_global_value( "npctalk_var_test_var_context" ) == "4" );
    CHECK( globals.get_global_value( "npctalk_var_test_var_nested" ) == "2" );

    globals.remove_global_value( "npctalk_var_test_string_key1" );
    globals.remove_global_value( "npctalk_var_test_string_key2" );
    CHECK( effect_on_condition_EOC_TEST_STRING_VAR_INDIRECTION->activate( d ) );
    CHECK( globals.get_global_value( "npctalk_var_test_string_key1" ) == "Works" );
    CHECK( globals.get_global_value( "npctalk_var_test_string_key2" ) == "Works" );

    for( const std::string &variable : numeric_variables ) {
        globals.remove_global_value( variable );
    }
    globals.remove_global_value( "npctalk_var_test_string_key1" );
    globals.remove_global_value( "npctalk_var_test_string_key2" );
    you.remove_value( "npctalk_var_key1" );
}

TEST_CASE( "EOC_indirect_variable_cycles_fail_closed", "[eoc][context]" )
{
    avatar &you = get_avatar();
    clear_avatar();
    dialogue d( get_talker_for( you ), nullptr );
    const std::string indirect_name = "npctalk_var_loop";
    d.set_value( indirect_name, "v_loop" );
    const var_info indirect( var_type::var, indirect_name );

    std::string read_result;
    const std::string read_error = capture_debugmsg_during( [&]() {
        read_result = read_var_value( indirect, d );
    } );
    CHECK( read_result.empty() );
    CHECK( read_error.find( "Indirect variable cycle detected" ) != std::string::npos );

    const std::string write_error = capture_debugmsg_during( [&]() {
        write_var_value( indirect.type, indirect.name, d.actor( false ), &d, "overwritten" );
    } );
    CHECK( write_error.find( "Indirect variable cycle detected" ) != std::string::npos );
    CHECK( d.get_value( indirect_name ) == "v_loop" );
}

TEST_CASE( "EOC_load_rejects_contextually_invalid_fields", "[eoc][json]" )
{
    effect_on_condition non_event;
    JsonObject required_event = json_loader::from_string(
                                    R"({"id":"EOC_TEST_INVALID_REQUIRED_EVENT","required_event":"game_load","effect":{"u_message":"invalid"}})" );
    CHECK_THROWS( non_event.load( required_event, "test" ) );

    effect_on_condition map_worn;
    JsonObject worn_only = json_loader::from_string(
                               R"({"id":"EOC_TEST_INVALID_MAP_WORN","effect":{"u_map_run_item_eocs":"all","search_data":[{"worn_only":true}]}})" );
    CHECK_THROWS( map_worn.load( worn_only, "test" ) );
}

TEST_CASE( "EOC_stored_conditions_are_available_to_nested_EOCs", "[eoc][condition]" )
{
    avatar &you = get_avatar();
    global_variables &globals = get_globals();
    const std::string fixed_result = "npctalk_var_test_stored_condition_fixed";
    const std::string variable_result = "npctalk_var_test_stored_condition_variable";
    clear_avatar();
    clear_map();

    dialogue d( get_talker_for( you ), nullptr );
    auto clear_results = [&]() {
        globals.remove_global_value( fixed_result );
        globals.remove_global_value( variable_result );
    };

    clear_results();
    d.set_value( "npctalk_var_stored_input", "0" );
    CHECK( effect_on_condition_EOC_TEST_STORED_CONDITION_ROOT->activate( d ) );
    CHECK( globals.get_global_value( fixed_result ) == "0" );
    CHECK( globals.get_global_value( variable_result ) == "0" );
    CHECK( d.get_conditionals().empty() );

    clear_results();
    d.set_value( "npctalk_var_stored_input", "10" );
    CHECK( effect_on_condition_EOC_TEST_STORED_CONDITION_ROOT->activate( d ) );
    CHECK( globals.get_global_value( fixed_result ) == "1" );
    CHECK( globals.get_global_value( variable_result ) == "1" );
    CHECK( d.get_conditionals().empty() );

    clear_results();
}

TEST_CASE( "recursive_stored_conditions_fail_closed", "[eoc][condition]" )
{
    clear_avatar();
    dialogue d( get_talker_for( get_avatar() ), nullptr );
    d.set_conditional( "recursive", []( const dialogue & nested ) {
        return nested.evaluate_conditional( "recursive" );
    } );

    bool result = true;
    const std::string error = capture_debugmsg_during( [&]() {
        result = d.evaluate_conditional( "recursive" );
    } );
    CHECK_FALSE( result );
    CHECK( error.find( "Recursive stored condition" ) != std::string::npos );

    // The guard is scoped to one evaluation and must not poison later checks.
    CHECK_FALSE( capture_debugmsg_during( [&]() {
        result = d.evaluate_conditional( "recursive" );
    } ).empty() );
    CHECK_FALSE( result );
}

TEST_CASE( "EOC_if_else_selects_and_nests_branches", "[eoc][if_else]" )
{
    clear_avatar();
    clear_map();

    dialogue d( get_talker_for( get_avatar() ), nullptr );
    global_variables &globals = get_globals();
    const std::string branch = "npctalk_var_test_if_else_branch";
    const std::string nested = "npctalk_var_test_if_else_nested";
    const std::string no_else = "npctalk_var_test_if_else_no_else";
    auto check_input = [&]( const std::string & input, const std::string & expected_branch,
    const std::string & expected_nested ) {
        d.set_value( "npctalk_var_if_input", input );
        globals.remove_global_value( branch );
        globals.remove_global_value( nested );
        globals.remove_global_value( no_else );
        CHECK( effect_on_condition_EOC_TEST_IF_ELSE->activate( d ) );
        CHECK( globals.get_global_value( branch ) == expected_branch );
        CHECK( globals.get_global_value( nested ) == expected_nested );
        CHECK( globals.get_global_value( no_else ).empty() );
    };

    check_input( "10", "true", "high" );
    check_input( "2", "true", "low" );
    check_input( "0", "false", "zero" );
    check_input( "-2", "false", "negative" );

    globals.remove_global_value( branch );
    globals.remove_global_value( nested );
    globals.remove_global_value( no_else );
}

TEST_CASE( "inventory_EOCs_select_items_and_preserve_context", "[eoc][inventory]" )
{
    avatar &you = get_avatar();
    clear_avatar();
    clear_map();

    you.set_wielded_item( item( itype_knife_combat ) );
    you.worn.wear_item( you, item( itype_backpack ), false, false );
    REQUIRE( you.i_add( item( itype_knife_combat ) ) != item_location::nowhere );
    REQUIRE( you.i_add( item( itype_backpack ) ) != item_location::nowhere );

    dialogue d( get_talker_for( you ), nullptr );
    const auto count_marked = [&you]( const std::string &name ) {
        const std::string variable = "npctalk_var_test_inventory_eoc_" + name;
        const std::vector<item_location> items = you.all_items_loc();
        return std::count_if( items.begin(), items.end(), [&variable]( const item_location & loc ) {
            return loc.get_item() != nullptr && loc->get_var( variable ) == "yes";
        } );
    };

    REQUIRE( you.all_items_loc().size() == 4 );

    CHECK( effect_on_condition_EOC_TEST_RUN_INV_ALL->activate( d ) );
    CHECK( count_marked( "all" ) == 4 );

    CHECK( effect_on_condition_EOC_TEST_RUN_INV_WORN->activate( d ) );
    CHECK( count_marked( "worn" ) == 1 );

    CHECK( effect_on_condition_EOC_TEST_RUN_INV_RANDOM->activate( d ) );
    CHECK( count_marked( "random" ) == 1 );

    const std::string no_match_var = "npctalk_var_test_inventory_eoc_no_match";
    you.remove_value( no_match_var );
    CHECK( effect_on_condition_EOC_TEST_RUN_INV_NO_MATCH->activate( d ) );
    CHECK( you.get_value( no_match_var ) == "yes" );

    you.remove_value( no_match_var );
    CHECK( effect_on_condition_EOC_TEST_RUN_INV_MANUAL_NO_MATCH->activate( d ) );
    CHECK( you.get_value( no_match_var ) == "yes" );

    you.remove_value( no_match_var );
    CHECK( effect_on_condition_EOC_TEST_RUN_INV_MANUAL_MULT_NO_MATCH->activate( d ) );
    CHECK( you.get_value( no_match_var ) == "yes" );

    const std::string false_count = "npctalk_var_test_inventory_eoc_false_count";
    you.remove_value( false_count );
    d.set_value( "npctalk_var_mode", "invalid" );
    const std::string invalid_mode_error = capture_debugmsg_during( [&]() {
        CHECK( effect_on_condition_EOC_TEST_RUN_INV_DYNAMIC->activate( d ) );
    } );
    CHECK( invalid_mode_error.find( "Invalid inventory item EOC selection mode" ) !=
           std::string::npos );
    CHECK( you.get_value( false_count ) == "1" );

    std::vector<item_location> items = you.all_items_loc();
    const auto worn_backpack = std::find_if( items.begin(), items.end(), [&you]( const item_location & loc ) {
        return loc.get_item() != nullptr && loc->typeId() == itype_backpack && you.is_worn( *loc );
    } );
    REQUIRE( worn_backpack != items.end() );
    std::unique_ptr<talker> alpha = get_talker_for( you );
    std::unique_ptr<talker> beta = get_talker_for( *worn_backpack );
    std::string tagged = "<u_name>|<npc_name>|<npc_val:test_inventory_eoc_worn>";
    parse_tags( tagged, *alpha, *beta );
    CHECK( tagged == you.get_name() + "|" + worn_backpack->get_item()->type_name() + "|yes" );

    CHECK( effect_on_condition_EOC_TEST_RUN_INV_WOOD->activate( d ) );
    CHECK( count_marked( "wood" ) == 0 );
    you.set_wielded_item( item( itype_sword_wood ) );
    CHECK( effect_on_condition_EOC_TEST_RUN_INV_WOOD->activate( d ) );
    CHECK( count_marked( "wood" ) == 1 );

    CHECK( effect_on_condition_EOC_TEST_RUN_INV_FLAG->activate( d ) );
    CHECK( count_marked( "flag" ) == 1 );

    you.remove_value( no_match_var );
    d.set_value( "npctalk_var_mode", "invalid" );
    const std::string invalid_mode_error = capture_debugmsg_during( [&]() {
        CHECK( effect_on_condition_EOC_TEST_RUN_INV_INVALID->activate( d ) );
    } );
    CHECK( invalid_mode_error.find( "Invalid inventory EOC selection mode" ) != std::string::npos );
    CHECK( you.get_value( no_match_var ) == "yes" );
}

TEST_CASE( "map_EOC_conditions_and_furniture_context", "[eoc][map]" )
{
    avatar &you = get_avatar();
    global_variables &globals = get_globals();
    clear_avatar();
    clear_map();
    globals.clear_global_values();

    map &here = get_map();
    const tripoint positive = you.pos() + tripoint_east;
    const tripoint negative = you.pos() + tripoint_south;
    here.ter_set( positive, ter_id( "t_floor" ) );
    here.furn_set( positive, furn_id( "test_f_eoc" ) );
    here.ter_set( negative, ter_id( "t_rock" ) );
    here.furn_set( negative, furn_id( "test_f_boltcut1" ) );
    REQUIRE( here.ter( positive )->has_flag( "TRANSPARENT" ) );
    REQUIRE( here.furn( positive )->has_flag( "TRANSPARENT" ) );
    REQUIRE_FALSE( here.ter( negative )->has_flag( "TRANSPARENT" ) );
    REQUIRE_FALSE( here.furn( negative )->has_flag( "TRANSPARENT" ) );

    dialogue d( get_talker_for( you ), nullptr );
    d.set_value( "npctalk_var_loc", here.getglobal( positive ).to_string() );
    CHECK( effect_on_condition_EOC_TEST_MAP_FLAGS->activate( d ) );
    CHECK( globals.get_global_value( "npctalk_var_test_map_terrain_flag" ) == "yes" );
    CHECK( globals.get_global_value( "npctalk_var_test_map_furniture_flag" ) == "yes" );

    d.set_value( "npctalk_var_loc", here.getglobal( negative ).to_string() );
    CHECK( effect_on_condition_EOC_TEST_MAP_FLAGS->activate( d ) );
    CHECK( globals.get_global_value( "npctalk_var_test_map_terrain_flag" ) == "no" );
    CHECK( globals.get_global_value( "npctalk_var_test_map_furniture_flag" ) == "no" );

    here.ter_set( you.pos(), ter_id( "t_floor" ) );
    here.furn_set( you.pos(), furn_id( "test_f_eoc" ) );
    CHECK( effect_on_condition_EOC_TEST_MAP_FLAGS_DEFAULT->activate( d ) );
    CHECK( globals.get_global_value( "npctalk_var_test_map_terrain_flag" ) == "yes" );
    CHECK( globals.get_global_value( "npctalk_var_test_map_furniture_flag" ) == "yes" );

    d.remove_value( "npctalk_var_loc" );
    const std::string missing_loc_error = capture_debugmsg_during( [&]() {
        CHECK( effect_on_condition_EOC_TEST_MAP_FLAGS->activate( d ) );
    } );
    CHECK( missing_loc_error.find( "Explicit EOC location variable" ) != std::string::npos );
    CHECK( globals.get_global_value( "npctalk_var_test_map_terrain_flag" ) == "no" );
    CHECK( globals.get_global_value( "npctalk_var_test_map_furniture_flag" ) == "no" );

    d.set_value( "npctalk_var_loc", "not a tripoint" );
    const std::string malformed_loc_error = capture_debugmsg_during( [&]() {
        CHECK( effect_on_condition_EOC_TEST_MAP_FLAGS->activate( d ) );
    } );
    CHECK( malformed_loc_error.find( "Could not convert EOC location" ) != std::string::npos );
    CHECK( globals.get_global_value( "npctalk_var_test_map_terrain_flag" ) == "no" );
    CHECK( globals.get_global_value( "npctalk_var_test_map_furniture_flag" ) == "no" );

    const tripoint_abs_ms far_target = you.get_location() + tripoint{ 1000, 1000, 0 };
    REQUIRE_FALSE( here.inbounds( far_target ) );
    tinymap target_bay;
    target_bay.load( project_to<coords::sm>( far_target ), false );
    const tripoint far_local = target_bay.getlocal( far_target );
    const ter_id old_terrain = target_bay.ter( far_local );
    const furn_id old_furniture = target_bay.furn( far_local );
    target_bay.ter_set( far_local, ter_id( "t_floor" ) );
    target_bay.furn_set( far_local, furn_id( "test_f_eoc" ) );
    target_bay.save();

    d.set_value( "npctalk_var_loc", far_target.to_string() );
    CHECK( effect_on_condition_EOC_TEST_MAP_FLAGS->activate( d ) );
    CHECK( globals.get_global_value( "npctalk_var_test_map_terrain_flag" ) == "yes" );
    CHECK( globals.get_global_value( "npctalk_var_test_map_furniture_flag" ) == "yes" );

    const tripoint_abs_ms ungenerated_target = you.get_location() + tripoint{ 100000, 100000, 0 };
    const tripoint_abs_sm ungenerated_submap = project_to<coords::sm>( ungenerated_target );
    REQUIRE( MAPBUFFER.lookup_submap( ungenerated_submap ) == nullptr );
    d.set_value( "npctalk_var_loc", ungenerated_target.to_string() );
    CHECK( effect_on_condition_EOC_TEST_MAP_FLAGS->activate( d ) );
    CHECK( globals.get_global_value( "npctalk_var_test_map_terrain_flag" ) == "no" );
    CHECK( globals.get_global_value( "npctalk_var_test_map_furniture_flag" ) == "no" );
    CHECK( MAPBUFFER.lookup_submap( ungenerated_submap ) == nullptr );

    target_bay.ter_set( far_local, old_terrain );
    target_bay.furn_set( far_local, old_furniture );
    target_bay.save();

    monster &flagged_monster = spawn_test_monster( "mon_zombie", positive + tripoint_east );
    dialogue monster_dialogue( get_talker_for( flagged_monster ), nullptr );
    CHECK( effect_on_condition_EOC_TEST_MONSTER_TYPE_FLAG->activate( monster_dialogue ) );
    CHECK( globals.get_global_value( "npctalk_var_test_monster_type_flag" ) == "yes" );

    here.furn( positive )->examine( you, positive );
    CHECK( globals.get_global_value( "npctalk_var_test_furniture_this" ) == "test_f_eoc" );
    CHECK( globals.get_global_value( "npctalk_var_test_furniture_pos" ) ==
           here.getglobal( positive ).to_string() );

    globals.clear_global_values();
    clear_map();
}

TEST_CASE( "map_spawn_item_EOC_places_items_and_containers", "[eoc][map]" )
{
    avatar &you = get_avatar();
    clear_avatar();
    clear_map();

    map &here = get_map();
    dialogue d( get_talker_for( you ), nullptr );
    const tripoint direct = you.pos() + tripoint_east;
    d.set_value( "npctalk_var_loc", here.getglobal( direct ).to_string() );
    CHECK( effect_on_condition_EOC_TEST_MAP_SPAWN_DIRECT->activate( d ) );
    CHECK( std::count_if( here.i_at( direct ).begin(), here.i_at( direct ).end(), []( const item & it ) {
        return it.typeId() == itype_knife_combat;
    } ) == 2 );

    d.remove_value( "npctalk_var_loc" );
    const std::string missing_spawn_loc_error = capture_debugmsg_during( [&]() {
        CHECK( effect_on_condition_EOC_TEST_MAP_SPAWN_DIRECT->activate( d ) );
    } );
    CHECK( missing_spawn_loc_error.find( "Explicit EOC location variable" ) != std::string::npos );
    CHECK( std::none_of( here.i_at( you.pos() ).begin(), here.i_at( you.pos() ).end(),
    []( const item & it ) {
        return it.typeId() == itype_knife_combat;
    } ) );

    const tripoint contained = you.pos() + tripoint_south;
    d.set_value( "npctalk_var_loc", here.getglobal( contained ).to_string() );
    CHECK( effect_on_condition_EOC_TEST_MAP_SPAWN_CONTAINER->activate( d ) );
    REQUIRE( here.i_at( contained ).size() == 1 );
    item &bottle = here.i_at( contained ).only_item();
    CHECK( bottle.typeId() == itype_jug_plastic );
    REQUIRE( bottle.all_items_top().size() == 1 );
    CHECK( bottle.only_item().typeId() == itype_water );
    CHECK( bottle.only_item().charges == 5 );

    const tripoint noncharge_container = you.pos() + tripoint_west;
    d.set_value( "npctalk_var_loc", here.getglobal( noncharge_container ).to_string() );
    CHECK( effect_on_condition_EOC_TEST_MAP_SPAWN_NONCHARGE_CONTAINER->activate( d ) );
    REQUIRE( here.i_at( noncharge_container ).size() == 1 );
    item &backpack = here.i_at( noncharge_container ).only_item();
    CHECK( backpack.typeId() == itype_backpack );
    const auto backpack_contents = backpack.all_items_top();
    CHECK( std::count_if( backpack_contents.begin(), backpack_contents.end(), []( const item * it ) {
        return it->typeId() == itype_knife_combat;
    } ) == 2 );

    const tripoint invalid_container = you.pos() + tripoint_north;
    d.set_value( "npctalk_var_loc", here.getglobal( invalid_container ).to_string() );
    const std::string insertion_error = capture_debugmsg_during( [&]() {
        CHECK( effect_on_condition_EOC_TEST_MAP_SPAWN_INVALID_CONTAINER->activate( d ) );
    } );
    CHECK_FALSE( insertion_error.empty() );
    REQUIRE( here.i_at( invalid_container ).size() == 1 );
    CHECK( here.i_at( invalid_container ).only_item().typeId() == itype_bottle_plastic );
    CHECK( here.i_at( invalid_container ).only_item().empty_container() );

    const tripoint partial_container = you.pos() + tripoint{ -1, -1, 0 };
    d.set_value( "npctalk_var_loc", here.getglobal( partial_container ).to_string() );
    const std::string partial_error = capture_debugmsg_during( [&]() {
        CHECK( effect_on_condition_EOC_TEST_MAP_SPAWN_PARTIAL_CONTAINER->activate( d ) );
    } );
    CHECK_FALSE( partial_error.empty() );
    REQUIRE( here.i_at( partial_container ).size() == 1 );
    item &partial_backpack = here.i_at( partial_container ).only_item();
    CHECK( partial_backpack.typeId() == itype_backpack );
    CHECK( partial_backpack.all_items_top().size() > 0 );
    CHECK( partial_backpack.all_items_top().size() < 200 );

    const tripoint group = you.pos() + tripoint{ 2, 1, 0 };
    d.set_value( "npctalk_var_loc", here.getglobal( group ).to_string() );
    CHECK( effect_on_condition_EOC_TEST_MAP_SPAWN_GROUP->activate( d ) );
    CHECK( std::count_if( here.i_at( group ).begin(), here.i_at( group ).end(), []( const item & it ) {
        return it.typeId() == itype_hammer;
    } ) == 1 );
    CHECK( std::count_if( here.i_at( group ).begin(), here.i_at( group ).end(), []( const item & it ) {
        return it.typeId() == itype_bow_saw;
    } ) == 1 );
    CHECK( std::none_of( here.i_at( group ).begin(), here.i_at( group ).end(), []( const item & it ) {
        return it.typeId() == itype_bottle_plastic;
    } ) );
    CHECK( std::all_of( here.i_at( group ).begin(), here.i_at( group ).end(), []( const item & it ) {
        return it.birthday() == calendar::turn;
    } ) );

    CHECK( effect_on_condition_EOC_TEST_MAP_SPAWN_DEFAULT->activate( d ) );
    CHECK( std::count_if( here.i_at( you.pos() ).begin(), here.i_at( you.pos() ).end(),
    []( const item & it ) {
        return it.typeId() == itype_knife_combat;
    } ) == 1 );

    // Keep the verification tinymap well clear of the active reality bubble.
    // A 100-tile offset can be out of bounds yet still overlap the edge of the
    // main map, which makes tinymap::load deliberately refuse the test load.
    const tripoint_abs_ms far_target = you.get_location() + tripoint{ 1000, 1000, 0 };
    REQUIRE_FALSE( here.inbounds( far_target ) );
    d.set_value( "npctalk_var_loc", far_target.to_string() );
    CHECK( effect_on_condition_EOC_TEST_MAP_SPAWN_DIRECT->activate( d ) );
    tinymap target_bay;
    target_bay.load( project_to<coords::sm>( far_target ), false );
    const tripoint far_local = target_bay.getlocal( far_target );
    CHECK( std::count_if( target_bay.i_at( far_local ).begin(), target_bay.i_at( far_local ).end(),
    []( const item & it ) {
        return it.typeId() == itype_knife_combat;
    } ) == 2 );
    target_bay.i_clear( far_local );
    target_bay.save();

    clear_map();
}

TEST_CASE( "map_item_EOCs_filter_radius_and_use_false_once", "[eoc][map]" )
{
    avatar &you = get_avatar();
    clear_avatar();
    clear_npcs();
    clear_map();

    map &here = get_map();
    const tripoint center = you.pos();
    const std::vector<tripoint> backpack_points = {
        center, center + tripoint_east, center + tripoint{ 2, 0, 0 },
        center + tripoint{ 3, 0, 0 }
    };
    for( const tripoint &pos : backpack_points ) {
        here.add_item_or_charges( pos, item( itype_backpack ) );
    }
    here.add_item_or_charges( center + tripoint_north, item( itype_knife_combat ) );

    dialogue d( get_talker_for( you ), nullptr );
    d.set_value( "npctalk_var_loc", here.getglobal( center ).to_string() );
    CHECK( effect_on_condition_EOC_TEST_MAP_RUN_ALL->activate( d ) );
    const auto count_marked = [&here, &backpack_points]( const std::string &name ) {
        const std::string variable = "npctalk_var_test_map_eoc_" + name;
        int result = 0;
        for( const tripoint &pos : backpack_points ) {
            for( const item &it : here.i_at( pos ) ) {
                result += it.typeId() == itype_backpack && it.get_var( variable ) == "yes" ? 1 : 0;
            }
        }
        return result;
    };
    CHECK( count_marked( "all" ) == 2 );
    CHECK( here.i_at( backpack_points[0] ).only_item().get_var(
               "npctalk_var_test_map_eoc_all" ).empty() );
    CHECK( here.i_at( backpack_points[3] ).only_item().get_var(
               "npctalk_var_test_map_eoc_all" ).empty() );

    CHECK( effect_on_condition_EOC_TEST_MAP_RUN_RANDOM->activate( d ) );
    CHECK( count_marked( "random" ) == 1 );

    const std::string false_count = "npctalk_var_test_map_eoc_false_count";
    for( const std::string &mode : { "all", "random", "manual", "manual_mult" } ) {
        you.remove_value( false_count );
        d.set_value( "npctalk_var_mode", mode );
        CHECK( effect_on_condition_EOC_TEST_MAP_RUN_NO_MATCH->activate( d ) );
        CHECK( you.get_value( false_count ) == "1" );
    }
    you.remove_value( false_count );
    d.set_value( "npctalk_var_mode", "invalid" );
    const std::string invalid_mode_error = capture_debugmsg_during( [&]() {
        CHECK( effect_on_condition_EOC_TEST_MAP_RUN_NO_MATCH->activate( d ) );
    } );
    CHECK( invalid_mode_error.find( "Invalid map item EOC selection mode" ) != std::string::npos );
    CHECK( you.get_value( false_count ) == "1" );

    npc &ally = spawn_npc( center.xy() + point_south, "thug" );
    dialogue npc_dialogue( get_talker_for( you ), get_talker_for( ally ) );
    npc_dialogue.set_value( "npctalk_var_loc", here.getglobal( center ).to_string() );
    const std::string actor_mark = "npctalk_var_test_map_eoc_actor";
    you.remove_value( actor_mark );
    ally.remove_value( actor_mark );
    CHECK( effect_on_condition_EOC_TEST_NPC_MAP_RUN_ALL->activate( npc_dialogue ) );
    CHECK( you.get_value( actor_mark ).empty() );
    CHECK( ally.get_value( actor_mark ) == "yes" );
    CHECK( count_marked( "npc" ) >= 1 );

    clear_npcs();
    clear_map();
}

TEST_CASE( "foreach_EOC_iterates_arrays_registries_and_groups", "[eoc][foreach]" )
{
    avatar &you = get_avatar();
    clear_avatar();
    clear_npcs();
    clear_map();

    npc &ally = spawn_npc( you.pos().xy() + point_south, "thug" );
    dialogue d( get_talker_for( you ), get_talker_for( ally ) );
    d.set_value( "npctalk_var_dynamic", "beta" );

    CHECK( effect_on_condition_EOC_TEST_FOREACH_ARRAY->activate( d ) );
    CHECK( ally.get_value( "npctalk_var_test_foreach_array_count" ) == "3" );
    CHECK( ally.get_value( "npctalk_var_test_foreach_iterator" ) == "omega" );
    CHECK( ally.get_value( "npctalk_var_test_foreach_saw_beta" ) == "yes" );
    CHECK( you.get_value( "npctalk_var_test_foreach_iterator" ).empty() );

    CHECK( effect_on_condition_EOC_TEST_FOREACH_REGISTRIES->activate( d ) );
    CHECK( you.get_value( "npctalk_var_test_foreach_saw_flag" ) == "yes" );
    CHECK( you.get_value( "npctalk_var_test_foreach_saw_trait" ) == "yes" );
    CHECK( you.get_value( "npctalk_var_test_foreach_saw_vitamin" ) == "yes" );

    CHECK( effect_on_condition_EOC_TEST_FOREACH_GROUPS->activate( d ) );
    CHECK( you.get_value( "npctalk_var_test_foreach_item_count" ) == "2" );
    CHECK( you.get_value( "npctalk_var_test_foreach_saw_hammer" ) == "yes" );
    CHECK( you.get_value( "npctalk_var_test_foreach_saw_bow_saw" ) == "yes" );
    CHECK( you.get_value( "npctalk_var_test_foreach_monster_count" ) == "6" );
    CHECK( you.get_value( "npctalk_var_test_foreach_saw_direct_monster" ) == "yes" );
    CHECK( you.get_value( "npctalk_var_test_foreach_saw_nested_monster" ) == "yes" );

    clear_npcs();
    clear_map();
}

TEST_CASE( "query_tile_EOC_fails_closed_for_non_avatar_talkers", "[eoc][query_tile]" )
{
    avatar &you = get_avatar();
    clear_avatar();
    clear_npcs();
    clear_map();

    npc &ally = spawn_npc( you.pos().xy() + point_south, "thug" );
    dialogue d( get_talker_for( you ), get_talker_for( ally ) );

    CHECK( effect_on_condition_EOC_TEST_QUERY_TILE_NON_AVATAR->activate( d ) );
    CHECK( ally.get_value( "npctalk_var_test_query_tile_false_count" ) == "3" );
    CHECK( ally.get_value( "npctalk_var_test_query_tile_true_count" ).empty() );
    CHECK( ally.get_value( "npctalk_var_test_query_tile_target" ).empty() );

    clear_npcs();
    clear_map();
}

TEST_CASE( "query_tile_EOC_selects_and_stores_avatar_tiles", "[eoc][query_tile]" )
{
    avatar &you = get_avatar();
    clear_avatar();
    clear_map();

    const std::vector<std::string> variables = {
        "npctalk_var_test_query_tile_anywhere_target",
        "npctalk_var_test_query_tile_los_target",
        "npctalk_var_test_query_tile_around_target",
        "npctalk_var_test_query_tile_true_count",
        "npctalk_var_test_query_tile_false_count"
    };
    for( const std::string &variable : variables ) {
        you.remove_value( variable );
    }

    const tripoint anywhere = you.pos() + tripoint{ 2, 3, 1 };
    const tripoint los = you.pos() + tripoint{ 4, 0, 0 };
    const tripoint around = you.pos() + tripoint_south;
    std::vector<std::string> calls;
    restore_on_out_of_scope<dialogue_data::query_tile_selector_for_test> restore_selector(
        dialogue_data::query_tile_selector_for_tests() );
    dialogue_data::query_tile_selector_for_tests() =
    [&]( const std::string & mode, avatar & actor, const tripoint & center,
         const std::string & message, int range, bool z_level ) -> cata::optional<tripoint> {
        CHECK( &actor == &you );
        CHECK( center == you.pos() );
        CHECK_FALSE( message.empty() );
        calls.push_back( mode );
        if( mode == "anywhere" ) {
            CHECK( range == 0 );
            CHECK( z_level );
            return anywhere;
        }
        if( mode == "line_of_sight" ) {
            CHECK( range == 7 );
            CHECK_FALSE( z_level );
            return los;
        }
        CHECK( mode == "around" );
        CHECK( range == 0 );
        CHECK_FALSE( z_level );
        return around;
    };

    const tripoint sentinel_target = you.pos() + tripoint_west;
    restore_on_out_of_scope<cata::optional<tripoint>> restore_last_target_pos(
        you.last_target_pos );
    const shared_ptr_fast<Creature> previous_last_target = you.last_target.lock();
    you.last_target_pos = sentinel_target;
    dialogue d( get_talker_for( you ), nullptr );
    CHECK( effect_on_condition_EOC_TEST_QUERY_TILE_AVATAR->activate( d ) );

    CHECK( calls == std::vector<std::string>{ "anywhere", "line_of_sight", "around" } );
    CHECK( you.get_value( variables[0] ) == get_map().getglobal( anywhere ).to_string() );
    CHECK( you.get_value( variables[1] ) == get_map().getglobal( los ).to_string() );
    CHECK( you.get_value( variables[2] ) == get_map().getglobal( around ).to_string() );
    CHECK( you.get_value( variables[3] ) == "3" );
    CHECK( you.get_value( variables[4] ).empty() );
    REQUIRE( you.last_target_pos );
    CHECK( *you.last_target_pos == sentinel_target );
    CHECK( you.last_target.lock().get() == previous_last_target.get() );

    for( const std::string &variable : variables ) {
        you.remove_value( variable );
    }
    clear_map();
}

TEST_CASE( "query_tile_EOC_cancellation_does_not_store_tiles", "[eoc][query_tile]" )
{
    avatar &you = get_avatar();
    clear_avatar();
    clear_map();

    restore_on_out_of_scope<dialogue_data::query_tile_selector_for_test> restore_selector(
        dialogue_data::query_tile_selector_for_tests() );
    dialogue_data::query_tile_selector_for_tests() =
    []( const std::string &, avatar &, const tripoint &, const std::string &, int,
        bool ) -> cata::optional<tripoint> {
        return cata::nullopt;
    };

    const tripoint sentinel_target = you.pos() + tripoint_east;
    restore_on_out_of_scope<cata::optional<tripoint>> restore_last_target_pos(
        you.last_target_pos );
    const shared_ptr_fast<Creature> previous_last_target = you.last_target.lock();
    you.last_target_pos = sentinel_target;
    dialogue d( get_talker_for( you ), nullptr );
    CHECK( effect_on_condition_EOC_TEST_QUERY_TILE_AVATAR->activate( d ) );
    CHECK( you.get_value( "npctalk_var_test_query_tile_true_count" ).empty() );
    CHECK( you.get_value( "npctalk_var_test_query_tile_false_count" ) == "3" );
    CHECK( you.get_value( "npctalk_var_test_query_tile_anywhere_target" ).empty() );
    CHECK( you.get_value( "npctalk_var_test_query_tile_los_target" ).empty() );
    CHECK( you.get_value( "npctalk_var_test_query_tile_around_target" ).empty() );
    REQUIRE( you.last_target_pos );
    CHECK( *you.last_target_pos == sentinel_target );
    CHECK( you.last_target.lock().get() == previous_last_target.get() );

    you.remove_value( "npctalk_var_test_query_tile_false_count" );
    clear_map();
}

TEST_CASE( "query_tile_EOC_rejects_invalid_selector_configuration", "[eoc][query_tile][json]" )
{
    JsonValue invalid_mode = json_loader::from_string( R"({
        "u_query_tile": "nearby",
        "target_var": { "u_val": "target" }
    })" );
    CHECK_THROWS_AS( conditional_t<dialogue>( invalid_mode.get_object() ), JsonError );

    JsonValue missing_range = json_loader::from_string( R"({
        "u_query_tile": "line_of_sight",
        "target_var": { "u_val": "target" }
    })" );
    CHECK_THROWS_AS( conditional_t<dialogue>( missing_range.get_object() ), JsonError );
}

TEST_CASE( "mutation_EOCs_receive_context_and_can_control_activation", "[eoc][mutations]" )
{
    avatar &you = get_avatar();
    global_variables &globals = get_globals();
    const std::string result = "npctalk_var_test_mutation_eoc";
    const std::string context = "npctalk_var_test_mutation_context";
    clear_avatar();
    clear_map();

    auto clear_results = [&]() {
        globals.remove_global_value( result );
        globals.remove_global_value( context );
    };
    auto check_results = [&]( const trait_id & expected ) {
        CHECK( globals.get_global_value( result ) == "1" );
        CHECK( globals.get_global_value( context ) == expected.str() );
    };

    you.toggle_trait( trait_TEST_EOC_MUTATION_ONESHOT );
    dialogue d( get_talker_for( you ), nullptr );
    clear_results();
    CHECK( effect_on_condition_EOC_TEST_ACTIVATE_MUTATION->activate( d ) );
    check_results( trait_TEST_EOC_MUTATION_ONESHOT );
    CHECK_FALSE( you.has_active_mutation( trait_TEST_EOC_MUTATION_ONESHOT ) );

    you.toggle_trait( trait_TEST_EOC_MUTATION_PROCESSED );
    clear_results();
    you.activate_mutation( trait_TEST_EOC_MUTATION_PROCESSED );
    check_results( trait_TEST_EOC_MUTATION_PROCESSED );
    CHECK( you.has_active_mutation( trait_TEST_EOC_MUTATION_PROCESSED ) );

    clear_results();
    you.suffer();
    CHECK( globals.get_global_value( result ).empty() );
    CHECK( globals.get_global_value( context ).empty() );

    clear_results();
    you.suffer();
    check_results( trait_TEST_EOC_MUTATION_PROCESSED );

    clear_results();
    you.suffer();
    CHECK( globals.get_global_value( result ).empty() );
    CHECK( globals.get_global_value( context ).empty() );

    clear_results();
    you.deactivate_mutation( trait_TEST_EOC_MUTATION_PROCESSED );
    check_results( trait_TEST_EOC_MUTATION_PROCESSED );
    CHECK_FALSE( you.has_active_mutation( trait_TEST_EOC_MUTATION_PROCESSED ) );

    you.toggle_trait( trait_TEST_EOC_MUTATION_PROCESSED_ZERO );
    you.activate_mutation( trait_TEST_EOC_MUTATION_PROCESSED_ZERO );
    clear_results();
    you.suffer();
    CHECK( globals.get_global_value( result ).empty() );
    CHECK( globals.get_global_value( context ).empty() );
    you.deactivate_mutation( trait_TEST_EOC_MUTATION_PROCESSED_ZERO );

    clear_results();
    you.toggle_trait( trait_TEST_EOC_MUTATION_ONESHOT );
    you.toggle_trait( trait_TEST_EOC_MUTATION_PROCESSED );
    you.toggle_trait( trait_TEST_EOC_MUTATION_PROCESSED_ZERO );
}

TEST_CASE( "forced_mutation_deactivation_stops_before_process_EOCs", "[eoc][mutations]" )
{
    avatar &you = get_avatar();
    const std::string count = "npctalk_var_test_mutation_eoc_count";
    trait_id tested;
    clear_avatar();

    SECTION( "malnutrition" ) {
        tested = trait_TEST_EOC_MUTATION_STARVING;
    }
    SECTION( "dehydration" ) {
        tested = trait_TEST_EOC_MUTATION_DEHYDRATED;
    }
    SECTION( "exhaustion" ) {
        tested = trait_TEST_EOC_MUTATION_EXHAUSTED;
    }

    you.toggle_trait( tested );
    you.activate_mutation( tested );
    REQUIRE( you.has_active_mutation( tested ) );
    you.remove_value( count );
    if( tested == trait_TEST_EOC_MUTATION_STARVING ) {
        you.set_stored_kcal( 0 );
    } else if( tested == trait_TEST_EOC_MUTATION_DEHYDRATED ) {
        you.set_thirst( 260 );
    } else {
        you.set_fatigue( fatigue_levels::EXHAUSTED );
    }

    you.suffer();

    CHECK_FALSE( you.has_active_mutation( tested ) );
    CHECK( you.get_value( count ) == "1" );
}

TEST_CASE( "add_trait_EOCs_can_select_mutation_variants", "[eoc][mutations][variant]" )
{
    avatar &you = get_avatar();
    clear_avatar();
    clear_npcs();
    clear_map();

    const trait_id eye_color( "eye_color" );
    you.unset_mutation( eye_color );
    npc &other = spawn_npc( you.pos().xy() + point_south, "thug" );
    other.unset_mutation( eye_color );

    dialogue d( get_talker_for( you ), get_talker_for( other ) );
    d.set_value( "npctalk_var_npc_variant", "green" );
    CHECK( effect_on_condition_EOC_TEST_ADD_TRAIT_VARIANTS->activate( d ) );
    CHECK( you.has_trait_variant( trait_and_var( eye_color, "brown" ) ) );
    CHECK( other.has_trait_variant( trait_and_var( eye_color, "green" ) ) );

    you.unset_mutation( eye_color );
    other.unset_mutation( eye_color );
    d.set_value( "npctalk_var_npc_variant", "not_a_variant" );
    const std::string invalid_variant_error = capture_debugmsg_during( [&]() {
        CHECK( effect_on_condition_EOC_TEST_ADD_TRAIT_VARIANTS->activate( d ) );
    } );
    CHECK( invalid_variant_error.find( "Mutation eye_color has no variant not_a_variant" ) !=
           std::string::npos );
    CHECK( you.has_trait_variant( trait_and_var( eye_color, "brown" ) ) );
    CHECK_FALSE( other.has_trait( eye_color ) );

    you.unset_mutation( eye_color );
    clear_npcs();
    clear_map();
}

TEST_CASE( "activity_EOCs_run_on_completion_and_each_turn", "[eoc][activity]" )
{
    avatar &you = get_avatar();
    const std::string variable = "npctalk_var_test_activity_eoc_counter";

    SECTION( "completion EOC runs once" ) {
        clear_avatar();
        you.remove_value( variable );
        you.assign_activity( ACT_TEST_EOC_COMPLETE, 10 );

        complete_activity( you );

        CHECK( you.get_value( variable ) == "1" );
    }

    SECTION( "do-turn EOC runs once per activity turn" ) {
        clear_avatar();
        you.remove_value( variable );
        you.assign_activity( ACT_TEST_EOC_DURING, 300 );

        const int turns = complete_activity( you );

        REQUIRE_FALSE( you.get_value( variable ).empty() );
        CHECK( std::stoi( you.get_value( variable ) ) == turns );
    }
}

TEST_CASE( "activity_EOC_can_cancel_its_activity", "[eoc][activity]" )
{
    avatar &you = get_avatar();
    clear_avatar();
    you.assign_activity( ACT_TEST_EOC_CANCEL, 300 );
    you.set_moves( you.get_speed() );

    you.activity.do_turn( you );

    CHECK( you.activity.is_null() );
}

TEST_CASE( "completion_EOC_can_cancel_or_replace_its_activity", "[eoc][activity]" )
{
    avatar &you = get_avatar();

    SECTION( "completion EOC cancels the completed activity" ) {
        clear_avatar();
        you.assign_activity( ACT_TEST_EOC_COMPLETE_CANCEL, 10 );
        you.set_moves( you.get_speed() );

        you.activity.do_turn( you );

        CHECK( you.activity.is_null() );
    }

    SECTION( "completion EOC replacement is not immediately finished" ) {
        clear_avatar();
        you.assign_activity( ACT_TEST_EOC_COMPLETE_REPLACE, 10 );
        you.set_moves( you.get_speed() );

        you.activity.do_turn( you );

        REQUIRE_FALSE( you.activity.is_null() );
        CHECK( you.activity.id() == ACT_TEST_EOC_DURING );
        CHECK( you.activity.moves_left > 0 );
        CHECK( you.backlog.empty() );
    }

    SECTION( "same-id completion EOC replacement starts next turn" ) {
        clear_avatar();
        you.assign_activity( ACT_TEST_EOC_COMPLETE_REPLACE_SAME, 10 );
        you.set_moves( you.get_speed() );

        you.activity.do_turn( you );

        REQUIRE_FALSE( you.activity.is_null() );
        CHECK( you.activity.id() == ACT_TEST_EOC_COMPLETE_REPLACE_SAME );
        CHECK( you.activity.moves_left == to_moves<int>( 3_seconds ) );
        CHECK( you.backlog.empty() );
    }

    SECTION( "per-turn EOC replacement starts on the next turn without backlog" ) {
        clear_avatar();
        const std::string variable = "npctalk_var_test_activity_eoc_counter";
        you.remove_value( variable );
        you.assign_activity( ACT_TEST_EOC_DURING_REPLACE, 300 );
        you.set_moves( you.get_speed() );

        you.activity.do_turn( you );

        REQUIRE( you.activity.id() == ACT_TEST_EOC_DURING );
        CHECK( you.backlog.empty() );
        CHECK( you.get_value( variable ).empty() );

        you.set_moves( you.get_speed() );
        you.activity.do_turn( you );
        CHECK( you.get_value( variable ) == "1" );
    }
}

TEST_CASE( "EOC_teleport", "[eoc]" )
{
    clear_avatar();
    clear_map();
    tripoint_abs_ms before = get_avatar().get_location();
    dialogue newDialog( get_talker_for( get_avatar() ), nullptr );
    effect_on_condition_EOC_teleport_test->activate( newDialog );
    tripoint_abs_ms after = get_avatar().get_location();

    CHECK( before + tripoint_south_east == after );
}

TEST_CASE( "EOC_transform_radius", "[eoc][timed_event]" )
{
    // no introspection :(
    constexpr int eoc_range = 5;
    constexpr time_duration delay = 30_seconds;
    clear_avatar();
    clear_map();
    tripoint_abs_ms const start = get_avatar().get_location();
    dialogue newDialog( get_talker_for( get_avatar() ), nullptr );
    check_ter_in_radius( start, eoc_range, t_grass );
    effect_on_condition_EOC_TEST_TRANSFORM_RADIUS->activate( newDialog );
    check_ter_in_radius( start, eoc_range, t_dirt );

    g->place_player_overmap( project_to<coords::omt>( start ) + point{ 60, 60 } );
    REQUIRE( !get_map().inbounds( start ) );

    calendar::turn += delay - 1_seconds;
    get_timed_events().process();
    check_ter_in_radius( start, eoc_range, t_dirt );
    calendar::turn += 2_seconds;
    get_timed_events().process();
    check_ter_in_radius( start, eoc_range, t_grass );
}

TEST_CASE( "EOC_transform_line", "[eoc][timed_event]" )
{
    clear_avatar();
    clear_map();
    standard_npc npc( "Mr. Testerman" );
    cata::optional<tripoint> const dest = random_point( get_map(), []( tripoint const & p ) {
        return p.xy() != get_avatar().pos().xy();
    } );
    REQUIRE( dest.has_value() );
    npc.setpos( { dest.value().xy(), get_avatar().pos().z } );

    tripoint_abs_ms const start = get_avatar().get_location();
    tripoint_abs_ms const end = npc.get_location();
    dialogue newDialog( get_talker_for( get_avatar() ), get_talker_for( npc ) );
    check_ter_in_line( start, end, t_grass );
    effect_on_condition_EOC_TEST_TRANSFORM_LINE->activate( newDialog );
    check_ter_in_line( start, end, t_dirt );
}
