#include <ostream>
#include <string>

#include "avatar.h"
#include "cata_catch.h"
#include "cata_path.h"
#include "cata_utility.h"
#include "filesystem.h"
#include "player_helpers.h"

TEST_CASE( "failed avatar export restores the live character", "[avatar][export]" )
{
    clear_avatar();
    avatar &you = get_avatar();
    you.name = "export restoration test";
    you.str_max = 14;

    const std::string original_name = you.name;
    const int original_strength = you.str_max;
    const character_id original_id = you.getID();

    const cata_path blocker{ cata_path::root_path::user, "avatar_export_failure_blocker" };
    remove_file( blocker.get_unrelative_path() );
    write_to_file( blocker, []( std::ostream &out ) {
        out << "not a directory";
    } );
    REQUIRE( file_exist( blocker ) );

    CHECK_THROWS( you.export_as_npc( blocker / "avatar.npc" ) );
    CHECK( you.name == original_name );
    CHECK( you.str_max == original_strength );
    CHECK( you.getID() == original_id );

    CHECK( remove_file( blocker.get_unrelative_path() ) );
}
