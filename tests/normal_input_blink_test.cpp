#include "cata_catch.h"

#include <chrono>

#include "normal_input_blink.h"

TEST_CASE( "normal_input_shadow_blink_uses_legacy_timeout", "[action][tiles][shadow_blink]" )
{
    CHECK_FALSE( normal_input_blink_timeout_elapsed( std::chrono::milliseconds( 0 ) ) );
    CHECK_FALSE( normal_input_blink_timeout_elapsed( std::chrono::milliseconds( BLINK_SPEED ) ) );
    CHECK( normal_input_blink_timeout_elapsed( std::chrono::milliseconds( BLINK_SPEED + 1 ) ) );
}
