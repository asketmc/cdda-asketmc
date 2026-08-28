#if defined(TILES)

#include <cmath>

#include "cata_catch.h"
#include "sdltiles.h"

TEST_CASE( "native DPI scaling preserves a complete minimum terminal", "[sdl][dpi]" )
{
    const point base_font( 12, 26 );
    const point usable_client( 1904, 1000 );
    const point minimum_cells( 80, 24 );

    const float scale = fit_dpi_scale_to_client( 2.0f, base_font, usable_client, 1,
                        minimum_cells );
    const point scaled_font( static_cast<int>( std::lround( base_font.x * scale ) ),
                             static_cast<int>( std::lround( base_font.y * scale ) ) );

    CHECK( scale > 1.0f );
    CHECK( scale < 2.0f );
    CHECK( scaled_font.x * minimum_cells.x <= usable_client.x );
    CHECK( scaled_font.y * minimum_cells.y <= usable_client.y );
}

TEST_CASE( "native DPI scaling is recalculated for each display", "[sdl][dpi]" )
{
    const point base_font( 8, 16 );
    const point usable_client( 2560, 1400 );
    const point minimum_cells( 80, 24 );

    CHECK( fit_dpi_scale_to_client( 1.0f, base_font, usable_client, 1,
                                    minimum_cells ) == Approx( 1.0f ) );
    CHECK( fit_dpi_scale_to_client( 1.5f, base_font, usable_client, 1,
                                    minimum_cells ) == Approx( 1.5f ) );
}

TEST_CASE( "window fitting never returns less than a complete minimum terminal", "[sdl][dpi]" )
{
    const point cell_size( 17, 41 );
    const point minimum_cells( 80, 24 );
    const point minimum_client( cell_size.x * minimum_cells.x,
                                cell_size.y * minimum_cells.y );

    CHECK( fit_windowed_client_size( point( 2000, 1500 ), point( 1904, 1000 ),
                                    cell_size, minimum_cells ) == point( 1904, 984 ) );
    CHECK( fit_windowed_client_size( point( 200, 200 ), point( 1904, 1000 ),
                                    cell_size, minimum_cells ) == minimum_client );
}

TEST_CASE( "oversized base fonts are fitted without cropping the minimum terminal", "[sdl][dpi]" )
{
    const point base_font( 40, 80 );
    const point usable_client( 1000, 700 );
    const point minimum_cells( 80, 24 );

    const float scale = fit_dpi_scale_to_client( 1.0f, base_font, usable_client, 1,
                        minimum_cells );
    const point scaled_font( static_cast<int>( std::lround( base_font.x * scale ) ),
                             static_cast<int>( std::lround( base_font.y * scale ) ) );

    CHECK( scale < 1.0f );
    CHECK( scaled_font.x * minimum_cells.x <= usable_client.x );
    CHECK( scaled_font.y * minimum_cells.y <= usable_client.y );
}

TEST_CASE( "maximized fonts fit the usable work area", "[sdl][dpi]" )
{
    const point base_font( 8, 16 );
    const point maximized_client( 1366, 728 );
    const point minimum_cells( 80, 24 );

    const float scale = fit_dpi_scale_to_client( 2.0f, base_font, maximized_client, 1,
                        minimum_cells );
    const point scaled_font( static_cast<int>( std::lround( base_font.x * scale ) ),
                             static_cast<int>( std::lround( base_font.y * scale ) ) );

    CHECK( scaled_font.x * minimum_cells.x <= maximized_client.x );
    CHECK( scaled_font.y * minimum_cells.y <= maximized_client.y );
}

TEST_CASE( "window borders remain inside the usable display", "[sdl][dpi]" )
{
    const point usable_position( 0, 0 );
    const point usable_size( 1920, 1040 );
    const point client_size( 1904, 1000 );
    const point border_top_left( 8, 31 );
    const point border_bottom_right( 8, 8 );

    CHECK( fit_windowed_client_position( point( 500, 300 ), client_size, usable_position,
                                        usable_size, border_top_left,
                                        border_bottom_right ) == point( 8, 32 ) );
    CHECK( fit_windowed_client_position( point( -2200, -100 ), point( 1200, 700 ),
                                        point( -1920, 0 ), usable_size, border_top_left,
                                        border_bottom_right ) == point( -1912, 31 ) );
}

#endif
