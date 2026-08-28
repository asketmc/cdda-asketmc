#include "cata_catch.h"

#include <algorithm>
#include <array>
#include <sstream>
#include <utility>

#include "activity_handlers.h"
#include "avatar.h"
#include "flag.h"
#include "item.h"
#include "item_location.h"
#include "json.h"
#include "json_loader.h"
#include "map.h"
#include "map_helpers.h"
#include "mtype.h"
#include "player_activity.h"
#include "player_helpers.h"

static const activity_id ACT_BLEED( "ACT_BLEED" );
static const activity_id ACT_BUTCHER( "ACT_BUTCHER" );
static const activity_id ACT_BUTCHER_FULL( "ACT_BUTCHER_FULL" );
static const activity_id ACT_DISMEMBER( "ACT_DISMEMBER" );
static const activity_id ACT_DISSECT( "ACT_DISSECT" );
static const activity_id ACT_FIELD_DRESS( "ACT_FIELD_DRESS" );
static const activity_id ACT_QUARTER( "ACT_QUARTER" );
static const activity_id ACT_SKIN( "ACT_SKIN" );

static const itype_id itype_knife_butcher( "knife_butcher" );
static const itype_id itype_scalpel( "scalpel" );
static const mtype_id mon_test_bovine( "mon_test_bovine" );
static const skill_id skill_survival( "survival" );

static item_location add_test_corpse( const tripoint &pos )
{
    map &here = get_map();
    item &corpse = here.add_item( pos, item::make_corpse( mon_test_bovine ) );
    return item_location( map_cursor( pos ), &corpse );
}

static void prepare_butcher( avatar &you, const itype_id &tool = itype_scalpel )
{
    clear_avatar();
    clear_map();
    you.set_skill_level( skill_survival, 10 );
    item knife( tool );
    REQUIRE( you.wield( knife ) );
}

static player_activity set_up_activity( avatar &you, const activity_id &id,
                                        const item_location &corpse )
{
    player_activity act( id, 0, true );
    act.targets.push_back( corpse );
    activity_handlers::butcher_finish( &act, &you );
    REQUIRE_FALSE( act.is_null() );
    REQUIRE_FALSE( act.index );
    REQUIRE( act.moves_total > 0 );
    return act;
}

TEST_CASE( "corpse processing activities save independent progress",
           "[butchery][progress]" )
{
    avatar &you = get_avatar();
    prepare_butcher( you );
    item_location corpse = add_test_corpse( you.pos() );
    const std::array<std::pair<activity_id, butcher_type>, 8> processing {{
            { ACT_BLEED, butcher_type::BLEED },
            { ACT_BUTCHER, butcher_type::QUICK },
            { ACT_BUTCHER_FULL, butcher_type::FULL },
            { ACT_FIELD_DRESS, butcher_type::FIELD_DRESS },
            { ACT_SKIN, butcher_type::SKIN },
            { ACT_QUARTER, butcher_type::QUARTER },
            { ACT_DISMEMBER, butcher_type::DISMEMBER },
            { ACT_DISSECT, butcher_type::DISSECT }
        }};

    for( size_t i = 0; i < processing.size(); ++i ) {
        player_activity act( processing[i].first, 1000 );
        act.moves_total = 1000;
        act.moves_left = 900 - static_cast<int>( i ) * 100;
        act.targets.push_back( corpse );
        activity_handlers::butcher_do_turn( &act, &you );
    }

    for( size_t i = 0; i < processing.size(); ++i ) {
        CHECK( butcher_get_progress( *corpse, processing[i].second ) ==
               Approx( 0.1 + static_cast<double>( i ) * 0.1 ) );
    }
}

TEST_CASE( "corpse progress survives serialization", "[butchery][progress][serialization]" )
{
    item corpse = item::make_corpse( mon_test_bovine );
    corpse.set_var( "DISSECT_progress", 0.375 );

    std::ostringstream saved;
    JsonOut json( saved );
    corpse.serialize( json );
    item restored;
    restored.deserialize( json_loader::from_string( saved.str() ).get_object() );

    CHECK( butcher_get_progress( restored, butcher_type::DISSECT ) == Approx( 0.375 ) );
    CHECK( butcher_get_progress( restored, butcher_type::QUICK ) == 0.0 );
}

TEST_CASE( "interrupted butchery resumes after moving the corpse and changing tools",
           "[butchery][progress][activity]" )
{
    avatar &you = get_avatar();
    prepare_butcher( you );
    map &here = get_map();
    item_location corpse = add_test_corpse( you.pos() );

    you.activity = set_up_activity( you, ACT_BUTCHER, corpse );
    const int original_total = you.activity.moves_total;
    you.activity.moves_left = original_total * 3 / 5;
    activity_handlers::butcher_do_turn( &you.activity, &you );
    const double saved_progress = butcher_get_progress( *corpse, butcher_type::QUICK );
    REQUIRE( saved_progress == Approx( 0.4 ).margin( 0.001 ) );

    you.cancel_activity();
    you.backlog.clear();
    REQUIRE( butcher_get_progress( *corpse, butcher_type::QUICK ) == Approx( saved_progress ) );

    const tripoint destination = you.pos() + tripoint_east;
    item moved = *corpse;
    corpse.remove_item();
    item &moved_corpse = here.add_item( destination, std::move( moved ) );
    item_location moved_location( map_cursor( destination ), &moved_corpse );

    you.remove_weapon();
    item better_knife( itype_knife_butcher );
    REQUIRE( you.wield( better_knife ) );
    player_activity resumed = set_up_activity( you, ACT_BUTCHER, moved_location );

    CHECK( resumed.moves_total < original_total );
    CHECK( resumed.moves_left == resumed.moves_total -
           static_cast<int>( resumed.moves_total * saved_progress ) );
}

TEST_CASE( "completed corpse processing clears progress and cannot repeat output",
           "[butchery][progress][activity]" )
{
    avatar &you = get_avatar();
    prepare_butcher( you );
    map &here = get_map();
    item_location corpse = add_test_corpse( you.pos() );
    corpse->set_flag( flag_FIELD_DRESS );
    corpse->set_var( "QUARTER_progress", 0.5 );
    player_activity act = set_up_activity( you, ACT_QUARTER, corpse );

    act.moves_left = 0;
    activity_handlers::butcher_finish( &act, &you );
    REQUIRE( corpse );
    CHECK( corpse->has_flag( flag_QUARTERED ) );
    CHECK( butcher_get_progress( *corpse, butcher_type::QUARTER ) == 0.0 );
    const auto corpse_count = [&]() {
        return std::count_if( here.i_at( you.pos() ).begin(), here.i_at( you.pos() ).end(),
        []( const item & it ) {
            return it.is_corpse();
        } );
    };
    REQUIRE( corpse_count() == 4 );

    activity_handlers::butcher_finish( &act, &you );
    CHECK( corpse_count() == 4 );
}

TEST_CASE( "corpse processing stops when its target moves unexpectedly",
           "[butchery][progress][activity]" )
{
    avatar &you = get_avatar();
    prepare_butcher( you );
    map &here = get_map();
    item_location corpse = add_test_corpse( you.pos() );
    player_activity act = set_up_activity( you, ACT_BUTCHER, corpse );
    act.moves_left = act.moves_total / 2;
    activity_handlers::butcher_do_turn( &act, &you );
    const double saved_progress = butcher_get_progress( *corpse, butcher_type::QUICK );

    item moved = *corpse;
    corpse.remove_item();
    item &moved_corpse = here.add_item( you.pos() + tripoint_east, std::move( moved ) );
    activity_handlers::butcher_do_turn( &act, &you );

    CHECK( act.is_null() );
    CHECK( butcher_get_progress( moved_corpse, butcher_type::QUICK ) == Approx( saved_progress ) );
}

TEST_CASE( "butcher everything resumes each partially processed corpse",
           "[butchery][progress][activity]" )
{
    avatar &you = get_avatar();
    prepare_butcher( you );
    item_location first = add_test_corpse( you.pos() );
    item_location second = add_test_corpse( you.pos() );
    first->set_var( "QUICK_progress", 0.25 );
    second->set_var( "QUICK_progress", 0.5 );

    player_activity act( ACT_BUTCHER, 0, true );
    act.targets = { first, second };
    activity_handlers::butcher_finish( &act, &you );
    REQUIRE_FALSE( act.index );
    CHECK( act.moves_left == act.moves_total / 2 );

    act.moves_left = 0;
    activity_handlers::butcher_finish( &act, &you );
    REQUIRE( act.targets.size() == 1 );
    activity_handlers::butcher_finish( &act, &you );
    REQUIRE_FALSE( act.index );
    CHECK( act.moves_left == act.moves_total - act.moves_total / 4 );
}

TEST_CASE( "starting a quick method does not block finer corpse processing",
           "[butchery][progress][compatibility]" )
{
    avatar &you = get_avatar();
    prepare_butcher( you );
    item_location corpse = add_test_corpse( you.pos() );
    corpse->set_var( "QUICK_progress", 0.75 );

    player_activity dissection = set_up_activity( you, ACT_DISSECT, corpse );
    CHECK( dissection.moves_left == dissection.moves_total );
    CHECK( butcher_get_progress( *corpse, butcher_type::QUICK ) == Approx( 0.75 ) );
    CHECK( butcher_get_progress( *corpse, butcher_type::DISSECT ) == 0.0 );
}
