#include "cata_catch.h"

#include "action.h"

TEST_CASE( "legacy_iso_wall_action_aliases_occlusion_toggle", "[action][tiles]" )
{
    CHECK( look_up_action( "toggle_iso_walls" ) == ACTION_TOGGLE_PREVENT_OCCLUSION );
    CHECK( look_up_action( "toggle_prevent_occlusion" ) == ACTION_TOGGLE_PREVENT_OCCLUSION );
}
