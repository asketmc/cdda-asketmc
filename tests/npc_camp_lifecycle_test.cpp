#include <set>
#include <sstream>
#include <string>
#include <utility>
#include <vector>

#include "avatar.h"
#include "basecamp.h"
#include "calendar.h"
#include "cata_catch.h"
#include "clzones.h"
#include "coordinates.h"
#include "faction.h"
#include "game.h"
#include "inventory.h"
#include "item.h"
#include "json.h"
#include "json_loader.h"
#include "map.h"
#include "map_helpers.h"
#include "npc.h"
#include "npctalk.h"
#include "overmap.h"
#include "overmapbuffer.h"
#include "player_helpers.h"
#include "recipe.h"
#include "type_id.h"

static const activity_id ACT_FIRSTAID( "ACT_FIRSTAID" );
static const activity_id ACT_MOVE_LOOT( "ACT_MOVE_LOOT" );
static const activity_id ACT_WAIT_NPC( "ACT_WAIT_NPC" );

static const faction_id faction_your_followers( "your_followers" );

static const furn_str_id furn_f_bathtub( "f_bathtub" );

static const itype_id itype_bandages( "bandages" );
static const itype_id itype_manual_electronics( "manual_electronics" );
static const itype_id itype_rock( "rock" );
static const itype_id itype_test_battery_disposable( "test_battery_disposable" );
static const itype_id itype_test_ebook_reader( "test_ebook_reader" );

static const recipe_id recipe_test_soldering_iron( "test_soldering_iron" );
static const recipe_id recipe_water_clean( "water_clean" );

static const skill_id skill_electronics( "electronics" );
static const skill_id skill_firstaid( "firstaid" );

static const ter_str_id ter_t_floor( "t_floor" );

static const zone_type_id zone_type_CAMP_STORAGE( "CAMP_STORAGE" );

namespace
{
npc &setup_camp_worker()
{
    clear_avatar();
    clear_map();
    get_avatar().setpos( tripoint( 5, 5, 0 ) );

    npc &worker = spawn_npc( point( 60, 60 ), "test_talker" );
    clear_character( worker );
    get_avatar().setpos( worker.pos() + tripoint_west );
    worker.set_fac( faction_your_followers );
    worker.set_attitude( NPCATT_FOLLOW );
    worker.set_hunger( 0 );
    worker.set_thirst( 0 );
    worker.set_fatigue( 0 );
    worker.set_stored_kcal( worker.get_healthy_kcal() );
    worker.stomach.empty();
    worker.moves = 100;
    REQUIRE( worker.is_player_ally() );
    return worker;
}

class test_camp_scope
{
    public:
        test_camp_scope( overmap &om, const tripoint_abs_omt &camp_pos, const tripoint &board_pos ) :
            om_( om ), old_camps_( std::move( om.camps ) ),
            old_camp_index_( get_avatar().camps ), camp_pos_( camp_pos ) {
            om_.camps.clear();
            basecamp camp( "test follower camp", camp_pos_ );
            camp.set_owner( faction_your_followers );
            camp.set_bb_pos( board_pos );
            camp.add_expansion( "faction_base_camp_0", camp_pos_ );
            overmap_buffer.add_camp( camp );
            get_avatar().camps.insert( camp_pos_ );
        }

        ~test_camp_scope() {
            om_.camps = std::move( old_camps_ );
            get_avatar().camps = old_camp_index_;
        }

        test_camp_scope( const test_camp_scope & ) = delete;
        test_camp_scope &operator=( const test_camp_scope & ) = delete;

        basecamp &camp() const {
            return **overmap_buffer.find_camp( camp_pos_.xy() );
        }

    private:
        overmap &om_;
        std::vector<basecamp> old_camps_;
        std::set<tripoint_abs_omt> old_camp_index_;
        tripoint_abs_omt camp_pos_;
};

std::string without_camp_duty_member( const npc &worker )
{
    std::ostringstream serialized;
    JsonOut json( serialized );
    worker.serialize( json );

    std::string result = serialized.str();
    const size_t start = result.find( "\"camp_duty\":" );
    REQUIRE( start != std::string::npos );
    const size_t end = result.find( ',', start );
    REQUIRE( end != std::string::npos );
    result.erase( start, end - start + 1 );
    return result;
}

bool start_urgent_healing( npc &worker )
{
    for( int attempt = 0; attempt < 100 && worker.activity.id() != ACT_FIRSTAID; ++attempt ) {
        const npc_action action = worker.address_needs( 0.0f, true );
        if( static_cast<int>( action ) != 0 ) {
            worker.execute_action( action );
        }
        worker.moves = 100;
    }
    return worker.activity.id() == ACT_FIRSTAID;
}

} // namespace

TEST_CASE( "Legacy NPC priorities protect work from ordinary needs",
           "[npc][camp][priority]" )
{
    npc &worker = setup_camp_worker();
    worker.set_attitude( NPCATT_ACTIVITY );
    worker.assign_activity( ACT_WAIT_NPC, 5000 );
    worker.apply_damage( nullptr, bodypart_id( "arm_r" ), 20 );
    worker.i_add( item( itype_bandages ) );
    worker.set_hunger( 100 );
    worker.set_thirst( 50 );
    worker.set_pain( 10 );
    REQUIRE( worker.activity.id() == ACT_WAIT_NPC );
    REQUIRE( worker.get_hunger() == 100 );
    REQUIRE( worker.get_thirst() == 50 );

    for( int attempt = 0; attempt < 20; ++attempt ) {
        CHECK( static_cast<int>( worker.address_needs( 0.0f, true ) ) == 0 );
    }
    CHECK( worker.activity.id() == ACT_WAIT_NPC );
}

TEST_CASE( "Critical injury interrupts and resumes camp work",
           "[npc][camp][priority][activity]" )
{
    npc &worker = setup_camp_worker();
    const tripoint_abs_omt camp_pos = worker.global_omt_location();
    worker.assigned_camp = camp_pos;
    worker.camp_duty = true;
    worker.set_skill_level( skill_firstaid, 4 );
    worker.set_attitude( NPCATT_ACTIVITY );
    worker.apply_damage( nullptr, bodypart_id( "arm_r" ),
                         worker.get_part_hp_max( bodypart_id( "arm_r" ) ) / 2 + 1 );
    worker.i_add( item( itype_bandages ) );
    worker.assign_activity( ACT_WAIT_NPC, 5000 );
    REQUIRE( worker.activity.id() == ACT_WAIT_NPC );

    REQUIRE( start_urgent_healing( worker ) );
    process_activity( worker );
    CHECK( worker.activity.id() == ACT_WAIT_NPC );
    REQUIRE( worker.assigned_camp );
    CHECK( *worker.assigned_camp == camp_pos );
    CHECK( worker.camp_duty );
}

TEST_CASE( "Camp assignment survives temporary follow and guard orders",
           "[npc][camp][lifecycle]" )
{
    npc &worker = setup_camp_worker();
    const tripoint_abs_omt camp_pos = worker.global_omt_location();
    overmap *const om = overmap_buffer.get_existing( project_to<coords::om>( camp_pos.xy() ) );
    REQUIRE( om != nullptr );
    test_camp_scope scope( *om, camp_pos, get_map().getglobal( worker.pos() ).raw() );
    scope.camp().add_assignee( worker.getID() );
    REQUIRE( worker.assigned_camp );
    REQUIRE( *worker.assigned_camp == camp_pos );
    REQUIRE( worker.camp_duty );

    SECTION( "follow order keeps the assignment" ) {
        talk_function::stop_guard( worker );
        REQUIRE( worker.assigned_camp );
        CHECK( *worker.assigned_camp == camp_pos );
        CHECK_FALSE( worker.camp_duty );

        talk_function::return_to_camp( worker );
        REQUIRE( worker.assigned_camp );
        CHECK( *worker.assigned_camp == camp_pos );
        CHECK( worker.camp_duty );
        CHECK( worker.mission == NPC_MISSION_GUARD_ALLY );
        CHECK( worker.goal == camp_pos );
    }

    SECTION( "guard order keeps the assignment" ) {
        talk_function::assign_guard( worker );
        REQUIRE( worker.assigned_camp );
        CHECK( *worker.assigned_camp == camp_pos );
        CHECK_FALSE( worker.camp_duty );
    }

    SECTION( "return command does not interrupt active camp work" ) {
        worker.set_attitude( NPCATT_ACTIVITY );
        worker.assign_activity( ACT_WAIT_NPC, 5000 );
        talk_function::return_to_camp( worker );
        CHECK( worker.activity.id() == ACT_WAIT_NPC );
        CHECK( worker.get_attitude() == NPCATT_ACTIVITY );
        CHECK( worker.camp_duty );
    }
}

TEST_CASE( "Displaced camp worker targets the assigned camp board",
           "[npc][camp][lifecycle][travel]" )
{
    npc &worker = setup_camp_worker();
    const tripoint_abs_omt camp_pos = worker.global_omt_location();
    overmap *const om = overmap_buffer.get_existing( project_to<coords::om>( camp_pos.xy() ) );
    REQUIRE( om != nullptr );
    test_camp_scope scope( *om, camp_pos, get_map().getglobal( worker.pos() ).raw() );
    scope.camp().add_assignee( worker.getID() );

    worker.spawn_at_omt( camp_pos + point( 1, 0 ) );
    REQUIRE( worker.global_omt_location() != camp_pos );
    worker.camp_duty = false;
    worker.return_to_assigned_camp();

    REQUIRE( worker.assigned_camp );
    CHECK( *worker.assigned_camp == camp_pos );
    CHECK( worker.camp_duty );
    CHECK( worker.goal == camp_pos );
    CHECK( worker.mission == NPC_MISSION_TRAVELLING );
}

TEST_CASE( "Camp worker finishes travel on arrival",
           "[npc][camp][lifecycle][travel]" )
{
    npc &worker = setup_camp_worker();
    const tripoint_abs_omt camp_pos = worker.global_omt_location();
    overmap *const om = overmap_buffer.get_existing( project_to<coords::om>( camp_pos.xy() ) );
    REQUIRE( om != nullptr );
    test_camp_scope scope( *om, camp_pos, get_map().getglobal( worker.pos() ).raw() );
    scope.camp().add_assignee( worker.getID() );
    worker.set_mission( NPC_MISSION_TRAVELLING );
    worker.omt_path.push_back( camp_pos );

    worker.move();

    CHECK( worker.mission == NPC_MISSION_GUARD_ALLY );
    CHECK( worker.omt_path.empty() );
    CHECK( worker.camp_duty );
}

TEST_CASE( "Urgent needs preserve stashed camp work",
           "[npc][camp][priority][activity]" )
{
    npc &worker = setup_camp_worker();
    worker.set_skill_level( skill_firstaid, 4 );
    worker.set_attitude( NPCATT_ACTIVITY );
    worker.apply_damage( nullptr, bodypart_id( "arm_r" ),
                         worker.get_part_hp_max( bodypart_id( "arm_r" ) ) / 2 + 1 );
    worker.i_add( item( itype_bandages ) );
    worker.set_stashed_activity( player_activity( ACT_WAIT_NPC ) );

    worker.move();

    CHECK( worker.activity.id() == ACT_FIRSTAID );
    REQUIRE( worker.has_stashed_activity() );
    CHECK( worker.get_stashed_activity().id() == ACT_WAIT_NPC );

    while( worker.activity.id() == ACT_FIRSTAID ) {
        worker.moves += worker.get_speed();
        worker.activity.do_turn( worker );
    }
    worker.moves = 100;
    worker.move();
    CHECK( worker.activity.id() == ACT_WAIT_NPC );
    CHECK_FALSE( worker.has_stashed_activity() );
}

TEST_CASE( "Camp worker free time remains inside camp",
           "[npc][camp][lifecycle][downtime]" )
{
    npc &worker = setup_camp_worker();
    map &here = get_map();
    const tripoint_abs_omt camp_pos = worker.global_omt_location();
    overmap *const om = overmap_buffer.get_existing( project_to<coords::om>( camp_pos.xy() ) );
    REQUIRE( om != nullptr );
    test_camp_scope scope( *om, camp_pos, get_map().getglobal( worker.pos() ).raw() );
    scope.camp().add_assignee( worker.getID() );

    for( const tripoint &p : here.points_in_radius( worker.pos(), 10 ) ) {
        here.ter_set( p, ter_t_floor );
    }
    worker.chair_pos = cata::nullopt;
    worker.wander_pos = cata::nullopt;
    worker.worker_downtime();

    REQUIRE( worker.wander_pos );
    CHECK( project_to<coords::omt>( *worker.wander_pos ) == camp_pos );
    CHECK( scope.camp().point_within_camp( project_to<coords::omt>( *worker.wander_pos ) ) );
}

TEST_CASE( "Camp duty field preserves old save behavior",
           "[npc][camp][lifecycle][save]" )
{
    npc &worker = setup_camp_worker();
    const tripoint_abs_omt camp_pos = worker.global_omt_location();

    SECTION( "old assigned worker resumes camp duty" ) {
        worker.assigned_camp = camp_pos;
        worker.camp_duty = false;
        standard_npc loaded( "loaded assigned worker" );
        loaded.deserialize( json_loader::from_string( without_camp_duty_member( worker ) ).get_object() );
        REQUIRE( loaded.assigned_camp );
        CHECK( *loaded.assigned_camp == camp_pos );
        CHECK( loaded.camp_duty );
    }

    SECTION( "old unassigned follower remains off duty" ) {
        worker.assigned_camp = cata::nullopt;
        worker.camp_duty = true;
        standard_npc loaded( "loaded unassigned worker" );
        loaded.deserialize( json_loader::from_string( without_camp_duty_member( worker ) ).get_object() );
        CHECK_FALSE( loaded.assigned_camp );
        CHECK_FALSE( loaded.camp_duty );
    }
}

TEST_CASE( "Camp recipes include physical books and powered e-books",
           "[npc][camp][crafting][books]" )
{
    npc &worker = setup_camp_worker();
    worker.set_knowledge_level( skill_electronics, 1 );
    const tripoint_abs_omt camp_pos = worker.global_omt_location();
    overmap *const om = overmap_buffer.get_existing( project_to<coords::om>( camp_pos.xy() ) );
    REQUIRE( om != nullptr );
    test_camp_scope scope( *om, camp_pos, get_map().getglobal( worker.pos() ).raw() );
    scope.camp().add_assignee( worker.getID() );

    item manual( itype_manual_electronics );
    worker.identify( manual );

    SECTION( "physical book in camp supplies" ) {
        inventory supplies;
        supplies.add_item( manual );
        CHECK( scope.camp().recipe_deck_all( &supplies ).count( recipe_test_soldering_iron ) == 1 );
    }

    SECTION( "powered e-reader in camp supplies" ) {
        item reader( itype_test_ebook_reader );
        item battery( itype_test_battery_disposable );
        battery.ammo_set( battery.ammo_default(), 300 );
        REQUIRE( reader.put_in( battery, item_pocket::pocket_type::MAGAZINE_WELL ).success() );
        REQUIRE( reader.put_in( manual, item_pocket::pocket_type::EBOOK ).success() );
        inventory supplies;
        supplies.add_item( reader );
        CHECK( scope.camp().recipe_deck_all( &supplies ).count( recipe_test_soldering_iron ) == 1 );
    }
}

TEST_CASE( "Camp crafting worker availability is explicit",
           "[npc][camp][crafting][workers]" )
{
    npc &worker = setup_camp_worker();
    const tripoint_abs_omt camp_pos = worker.global_omt_location();
    overmap *const om = overmap_buffer.get_existing( project_to<coords::om>( camp_pos.xy() ) );
    REQUIRE( om != nullptr );
    test_camp_scope scope( *om, camp_pos, get_map().getglobal( worker.pos() ).raw() );

    CHECK( scope.camp().available_crafting_workers().empty() );
    scope.camp().add_assignee( worker.getID() );
    const std::vector<npc_ptr> workers = scope.camp().available_crafting_workers();
    REQUIRE( workers.size() == 1 );
    CHECK( workers.front()->getID() == worker.getID() );

    worker.camp_duty = false;
    CHECK( scope.camp().available_crafting_workers().empty() );

    worker.camp_duty = true;
    worker.spawn_at_omt( camp_pos + point( 1, 0 ) );
    CHECK( scope.camp().available_crafting_workers().empty() );
}

TEST_CASE( "Liquid camp craft requires an empty storage fixture",
           "[npc][camp][crafting][liquid]" )
{
    npc &worker = setup_camp_worker();
    map &here = get_map();
    const tripoint target = worker.pos() + tripoint_east;
    const tripoint_abs_ms absolute_target = here.getglobal( target );
    basecamp camp( "liquid test camp", worker.global_omt_location() );
    camp.set_bb_pos( here.getglobal( worker.pos() ).raw() );
    here.furn_set( target, furn_f_bathtub );
    zone_manager::get_manager().add( "Camp storage", zone_type_CAMP_STORAGE,
                                     faction_your_followers, false, true,
                                     absolute_target.raw(), absolute_target.raw() );

    CHECK( camp.has_storage_for_craft( recipe_water_clean.obj(), here,
                                       here.getglobal( worker.pos() ) ) );

    here.add_item_or_charges( target, item( itype_rock ) );
    CHECK_FALSE( camp.has_storage_for_craft( recipe_water_clean.obj(), here,
                 here.getglobal( worker.pos() ) ) );
    CHECK( camp.has_storage_for_craft( recipe_test_soldering_iron.obj(), here,
                                       here.getglobal( worker.pos() ) ) );
}

TEST_CASE( "Remote camp liquid storage uses the camp map",
           "[npc][camp][crafting][liquid][remote]" )
{
    npc &worker = setup_camp_worker();
    const tripoint_abs_ms remote_target = worker.get_location() + tripoint( 1000, 1000, 0 );
    tinymap remote_map;
    remote_map.load( project_to<coords::sm>( remote_target ), false );
    const tripoint remote_local = remote_map.getlocal( remote_target );
    const furn_id old_furniture = remote_map.furn( remote_local );
    remote_map.furn_set( remote_local, furn_f_bathtub );
    zone_manager::get_manager().add( "Remote camp storage", zone_type_CAMP_STORAGE,
                                     faction_your_followers, false, true,
                                     remote_target.raw(), remote_target.raw() );
    basecamp camp( "remote liquid camp", project_to<coords::omt>( remote_target ) );

    CHECK( camp.has_storage_for_craft( recipe_water_clean.obj(), remote_map, remote_target ) );

    remote_map.furn_set( remote_local, old_furniture );
    remote_map.save();
}

TEST_CASE( "Legacy camp sorter reports assigned work",
           "[npc][camp][sorting][activity]" )
{
    npc &worker = setup_camp_worker();
    worker.job.clear_all_priorities();
    REQUIRE( worker.job.set_task_priority( ACT_MOVE_LOOT, 10 ) );

    CHECK( worker.find_job_to_perform() );
    CHECK( worker.activity.id() == ACT_MOVE_LOOT );
}
