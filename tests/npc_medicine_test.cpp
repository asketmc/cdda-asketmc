#include <cmath>

#include "avatar.h"
#include "calendar.h"
#include "cata_catch.h"
#include "faction.h"
#include "game.h"
#include "item.h"
#include "json.h"
#include "json_loader.h"
#include "map_helpers.h"
#include "npc.h"
#include "player_helpers.h"
#include "type_id.h"
#include "vitamin.h"

static const activity_id ACT_FIRSTAID( "ACT_FIRSTAID" );
static const activity_id ACT_WAIT_NPC( "ACT_WAIT_NPC" );

static const efftype_id effect_nausea( "nausea" );

static const faction_id faction_your_followers( "your_followers" );

static const itype_id itype_bandages( "bandages" );
static const itype_id itype_aspirin( "aspirin" );
static const itype_id itype_flour( "flour" );
static const itype_id itype_knife_chef( "knife_chef" );
static const itype_id itype_meat_cooked( "meat_cooked" );
static const itype_id itype_meat_frond( "meat_frond" );
static const itype_id itype_orange( "orange" );
static const itype_id itype_vitamins( "vitamins" );

static const skill_id skill_firstaid( "firstaid" );

static const vitamin_id vitamin_iron( "iron" );
static const vitamin_id vitamin_vitC( "vitC" );

namespace
{
npc &setup_medicine_npc()
{
    clear_avatar();
    clear_map();
    get_avatar().setpos( tripoint( 5, 5, 0 ) );

    npc &guy = spawn_npc( point( 60, 60 ), "test_talker" );
    clear_character( guy );
    get_avatar().setpos( guy.pos() + tripoint_west );
    guy.set_fac( faction_your_followers );
    guy.set_attitude( NPCATT_FOLLOW );
    guy.set_skill_level( skill_firstaid, 4 );
    guy.set_hunger( 0 );
    guy.set_thirst( 0 );
    guy.set_fatigue( 0 );
    guy.set_stored_kcal( guy.get_healthy_kcal() );
    guy.stomach.empty();
    guy.moves = 100;
    REQUIRE( guy.is_player_ally() );
    return guy;
}

bool start_selected_healing( npc &guy, float danger )
{
    for( int attempt = 0; attempt < 100 && guy.activity.id() != ACT_FIRSTAID; ++attempt ) {
        const npc_action action = guy.address_needs( danger );
        if( static_cast<int>( action ) != 0 ) {
            guy.execute_action( action );
        }
        guy.moves = 100;
    }
    return guy.activity.id() == ACT_FIRSTAID;
}

void finish_firstaid_only( npc &guy )
{
    while( guy.activity.id() == ACT_FIRSTAID ) {
        guy.moves += guy.get_speed();
        guy.activity.do_turn( guy );
    }
}
} // namespace

TEST_CASE( "NPC first aid starts only when safe", "[npc][needs][medicine]" )
{
    npc &guy = setup_medicine_npc();
    const bodypart_id arm( "arm_r" );
    guy.apply_damage( nullptr, arm, 25 );
    item_location bandages = guy.i_add( item( itype_bandages ) );
    REQUIRE( bandages );

    SECTION( "danger blocks self healing" ) {
        CHECK_FALSE( start_selected_healing( guy, 10.0f ) );
        CHECK_FALSE( guy.activity.id() == ACT_FIRSTAID );
    }

    SECTION( "self healing starts when safe" ) {
        CHECK( start_selected_healing( guy, 0.0f ) );
        process_activity( guy );
        CHECK( guy.has_effect( efftype_id( "bandaged" ), arm ) );
    }
}

TEST_CASE( "NPC ally healing follows the follower rule", "[npc][needs][medicine][rules]" )
{
    npc &guy = setup_medicine_npc();
    avatar &patient = get_avatar();
    const bodypart_id arm( "arm_r" );
    patient.apply_damage( nullptr, arm, 25 );
    item_location bandages = guy.i_add( item( itype_bandages ) );
    REQUIRE( bandages );

    SECTION( "ally healing disabled" ) {
        guy.rules.clear_flag( ally_rule::heal_others );
        CHECK_FALSE( start_selected_healing( guy, 0.0f ) );
        CHECK_FALSE( patient.has_effect( efftype_id( "bandaged" ), arm ) );
    }

    SECTION( "ally healing enabled" ) {
        guy.rules.set_flag( ally_rule::heal_others );
        CHECK( start_selected_healing( guy, 0.0f ) );
        process_activity( guy );
        CHECK( patient.has_effect( efftype_id( "bandaged" ), arm ) );
    }
}

TEST_CASE( "NPC self healing is independent of the ally rule",
           "[npc][needs][medicine][rules]" )
{
    npc &guy = setup_medicine_npc();
    const bodypart_id arm( "arm_r" );
    guy.apply_damage( nullptr, arm, 25 );
    guy.i_add( item( itype_bandages ) );
    guy.rules.clear_flag( ally_rule::heal_others );

    CHECK( start_selected_healing( guy, 0.0f ) );
    finish_firstaid_only( guy );
    CHECK( guy.has_effect( efftype_id( "bandaged" ), arm ) );
}

TEST_CASE( "NPC does not start ally healing while threatened",
           "[npc][needs][medicine][rules]" )
{
    npc &guy = setup_medicine_npc();
    avatar &patient = get_avatar();
    const bodypart_id arm( "arm_r" );
    patient.apply_damage( nullptr, arm, 25 );
    guy.i_add( item( itype_bandages ) );
    guy.rules.set_flag( ally_rule::heal_others );

    CHECK_FALSE( start_selected_healing( guy, 10.0f ) );
    CHECK_FALSE( patient.has_effect( efftype_id( "bandaged" ), arm ) );
}

TEST_CASE( "NPC ally healing rule preserves old-save behavior", "[npc][rules][save]" )
{
    CHECK( static_cast<int>( ally_rule::lock_doors ) == 65536 );
    CHECK( static_cast<int>( ally_rule::avoid_locks ) == 131072 );
    CHECK( static_cast<int>( ally_rule::heal_others ) == 262144 );
    CHECK( static_cast<int>( ally_rule::hold_the_line ) == 4096 );
    CHECK( static_cast<int>( ally_rule::forbid_engage ) == 16384 );
    CHECK( static_cast<int>( ally_rule::follow_distance_2 ) == 32768 );

    SECTION( "new followers heal allies by default" ) {
        npc_follower_rules rules;
        CHECK( rules.has_flag( ally_rule::heal_others ) );
    }

    SECTION( "a save without the new field retains legacy ally healing" ) {
        npc_follower_rules rules;
        rules.clear_flag( ally_rule::heal_others );
        rules.deserialize( json_loader::from_string( R"({"engagement":0,"aim":0})" ).get_object() );
        CHECK( rules.has_flag( ally_rule::heal_others ) );
        CHECK_FALSE( rules.has_override_enable( ally_rule::heal_others ) );
        CHECK_FALSE( rules.has_override( ally_rule::heal_others ) );
    }

    SECTION( "an explicit disabled rule remains disabled" ) {
        npc_follower_rules rules;
        rules.deserialize( json_loader::from_string(
                               R"({"engagement":0,"aim":0,"rule_heal_others":false})" ).get_object() );
        CHECK_FALSE( rules.has_flag( ally_rule::heal_others ) );
    }
}

TEST_CASE( "NPC healing resumes an interrupted activity", "[npc][needs][medicine][activity]" )
{
    npc &guy = setup_medicine_npc();
    const bodypart_id arm( "arm_r" );
    guy.apply_damage( nullptr, arm, 25 );
    guy.i_add( item( itype_bandages ) );
    guy.assign_activity( ACT_WAIT_NPC, 5000 );
    REQUIRE( guy.activity.id() == ACT_WAIT_NPC );

    REQUIRE( start_selected_healing( guy, 0.0f ) );
    REQUIRE( guy.activity.id() == ACT_FIRSTAID );
    finish_firstaid_only( guy );
    CHECK( guy.activity.id() == ACT_WAIT_NPC );
    CHECK( guy.current_activity_id == ACT_WAIT_NPC );
}

TEST_CASE( "NPC resumes work after healing an ally", "[npc][needs][medicine][activity]" )
{
    npc &guy = setup_medicine_npc();
    avatar &patient = get_avatar();
    const bodypart_id arm( "arm_r" );
    patient.apply_damage( nullptr, arm, 25 );
    guy.i_add( item( itype_bandages ) );
    guy.rules.set_flag( ally_rule::heal_others );
    guy.assign_activity( ACT_WAIT_NPC, 5000 );
    REQUIRE( guy.activity.id() == ACT_WAIT_NPC );

    REQUIRE( start_selected_healing( guy, 0.0f ) );
    REQUIRE( guy.activity.id() == ACT_FIRSTAID );
    finish_firstaid_only( guy );
    CHECK( patient.has_effect( efftype_id( "bandaged" ), arm ) );
    CHECK( guy.activity.id() == ACT_WAIT_NPC );
    CHECK( guy.current_activity_id == ACT_WAIT_NPC );
}

TEST_CASE( "NPC uses vitamin medicine only for a deficiency", "[npc][needs][vitamins]" )
{
    npc &guy = setup_medicine_npc();
    const vitamin_id deficient = GENERATE( vitamin_vitC, vitamin_iron );
    CAPTURE( deficient.str() );
    guy.vitamin_set( deficient, deficient == vitamin_vitC ? -3000 : -10000 );
    REQUIRE( deficient->severity( guy.vitamin_get( deficient ) ) > 0 );
    const int before = guy.vitamin_get( deficient );
    item_location vitamins = guy.i_add( item( itype_vitamins ) );
    item_location aspirin = guy.i_add( item( itype_aspirin ) );
    REQUIRE( vitamins );
    REQUIRE( aspirin );
    const int aspirin_charges = aspirin->charges;

    CHECK( guy.consume_food() );
    CHECK( guy.vitamin_get( deficient ) > before );
    CHECK( aspirin->charges == aspirin_charges );

    guy.vitamin_set( vitamin_vitC, 0 );
    guy.vitamin_set( vitamin_iron, 0 );
    CHECK_FALSE( guy.consume_food() );
}

TEST_CASE( "Well-fed NPC treats vitamin deficiency through the needs cascade",
           "[npc][needs][vitamins]" )
{
    npc &guy = setup_medicine_npc();
    guy.vitamin_set( vitamin_vitC, -3000 );
    const int before = guy.vitamin_get( vitamin_vitC );
    guy.i_add( item( itype_vitamins ) );

    bool consumed = false;
    for( int attempt = 0; attempt < 20 && !consumed; ++attempt ) {
        guy.address_needs( 0.0f );
        consumed = guy.vitamin_get( vitamin_vitC ) > before;
    }
    CHECK( consumed );
}

TEST_CASE( "NPC rejects hazardous food as a vitamin treatment",
           "[npc][needs][vitamins][food]" )
{
    npc &guy = setup_medicine_npc();
    guy.vitamin_set( vitamin_vitC, -3000 );
    item_location frond = guy.i_add( item( itype_meat_frond ) );
    REQUIRE( frond );

    CHECK_FALSE( guy.consume_food() );
    CHECK( guy.has_amount( itype_meat_frond, 1 ) );
}

TEST_CASE( "NPC prefers food containing a deficient vitamin", "[npc][needs][vitamins][food]" )
{
    npc &guy = setup_medicine_npc();
    guy.set_hunger( 200 );
    guy.vitamin_set( vitamin_vitC, -3000 );
    guy.i_add( item( itype_meat_cooked ) );
    guy.i_add( item( itype_orange ) );
    REQUIRE( guy.has_amount( itype_orange, 1 ) );

    CHECK( guy.consume_food() );
    CHECK_FALSE( guy.has_amount( itype_orange, 1 ) );
    CHECK( guy.has_amount( itype_meat_cooked, 1 ) );
}

TEST_CASE( "NPC does not consume vitamin medicine without a deficiency",
           "[npc][needs][vitamins]" )
{
    npc &guy = setup_medicine_npc();
    guy.vitamin_set( vitamin_vitC, 0 );
    guy.vitamin_set( vitamin_iron, 0 );
    item_location vitamins = guy.i_add( item( itype_vitamins ) );
    REQUIRE( vitamins );
    const int charges = vitamins->charges;

    CHECK_FALSE( guy.consume_food() );
    CHECK( vitamins->charges == charges );
}

TEST_CASE( "NPC avoids unpleasant food without choosing starvation",
           "[npc][needs][food][nausea]" )
{
    npc &guy = setup_medicine_npc();
    guy.set_hunger( 200 );
    item_location flour = guy.i_add( item( itype_flour ) );
    REQUIRE( flour );

    SECTION( "normal food is preferred" ) {
        item_location meat = guy.i_add( item( itype_meat_cooked ) );
        REQUIRE( meat );
        const int flour_charges = flour->charges;
        CHECK( guy.consume_food() );
        CHECK( flour->charges == flour_charges );
    }

    SECTION( "unpleasant food remains a last resort" ) {
        guy.set_stored_kcal( guy.get_healthy_kcal() / 3 );
        const int flour_charges = flour->charges;
        CHECK( guy.consume_food() );
        CHECK( flour->charges < flour_charges );
    }
}

TEST_CASE( "NPC with nausea eats only to avoid critical starvation",
           "[npc][needs][food][nausea]" )
{
    npc &guy = setup_medicine_npc();
    guy.set_hunger( 200 );
    guy.add_effect( effect_nausea, 30_minutes );
    item_location meat = guy.i_add( item( itype_meat_cooked ) );
    REQUIRE( meat );

    CHECK_FALSE( guy.consume_food() );
    guy.set_stored_kcal( guy.get_healthy_kcal() / 3 );
    CHECK( guy.consume_food() );
}

TEST_CASE( "Critically hungry NPC with nausea still prefers palatable food",
           "[npc][needs][food][nausea]" )
{
    npc &guy = setup_medicine_npc();
    guy.set_hunger( 300 );
    guy.set_stored_kcal( guy.get_healthy_kcal() / 3 );
    guy.add_effect( effect_nausea, 30_minutes );
    item_location flour = guy.i_add( item( itype_flour ) );
    item_location meat = guy.i_add( item( itype_meat_cooked ) );
    REQUIRE( flour );
    REQUIRE( meat );
    const int flour_charges = flour->charges;

    CHECK( guy.consume_food() );
    CHECK( flour->charges == flour_charges );
}

TEST_CASE( "NPC weapon evaluation is initialized and favors a real weapon",
           "[npc][weapon][correctness]" )
{
    npc &guy = setup_medicine_npc();
    const item bare_hands;
    const item chef_knife( itype_knife_chef );
    const item irrelevant( itype_aspirin );

    CHECK( guy.gun_value( bare_hands ) == 0.0 );
    CHECK( std::isfinite( guy.weapon_value( bare_hands, 0 ) ) );
    CHECK( std::isfinite( guy.weapon_value( irrelevant, 0 ) ) );
    CHECK( std::isfinite( guy.weapon_value( chef_knife, 0 ) ) );
    CHECK( guy.weapon_value( irrelevant, 0 ) <= guy.weapon_value( chef_knife, 0 ) );
    CHECK( guy.weapon_value( chef_knife, 0 ) > guy.weapon_value( bare_hands, 0 ) );
}

TEST_CASE( "NPC selects a useful inventory weapon over empty hands",
           "[npc][weapon][correctness]" )
{
    npc &guy = setup_medicine_npc();
    REQUIRE_FALSE( guy.get_wielded_item() );
    guy.i_add( item( itype_knife_chef ) );

    CHECK( guy.wield_better_weapon() );
    REQUIRE( guy.get_wielded_item() );
    CHECK( guy.get_wielded_item()->typeId() == itype_knife_chef );
}
#include <cmath>
