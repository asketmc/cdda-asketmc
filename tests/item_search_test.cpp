#include "cata_catch.h"

#include "item.h"
#include "item_search.h"
#include "type_id.h"

static const itype_id itype_glasses_eye( "glasses_eye" );
static const itype_id itype_gloves_liner( "gloves_liner" );

TEST_CASE( "item_filter_by_covered_body_part", "[item][inventory][filter]" )
{
    const item eyeglasses( itype_glasses_eye );
    const item glove_liners( itype_gloves_liner );

    const auto covers_eyes = basic_item_filter( "v:eyes" );
    CHECK( covers_eyes( eyeglasses ) );
    CHECK_FALSE( covers_eyes( glove_liners ) );

    const auto covers_hands = basic_item_filter( "v:hands" );
    CHECK( covers_hands( glove_liners ) );
    CHECK_FALSE( covers_hands( eyeglasses ) );
}
