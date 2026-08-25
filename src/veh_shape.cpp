#include "veh_shape.h"

#include <algorithm>
#include <map>
#include <utility>

#include "avatar.h"
#include "cata_scope_helpers.h"
#include "debug.h"
#include "game.h"
#include "map.h"
#include "memory_fast.h"
#include "options.h"
#include "output.h"
#include "player_activity.h"
#include "translations.h"
#include "ui.h"
#include "ui_manager.h"
#include "veh_type.h"
#include "veh_utils.h"
#include "vpart_range.h"

veh_shape::veh_shape( vehicle &vehicle ) : veh( vehicle )
{
}

player_activity veh_shape::start( const tripoint &pos )
{
    avatar &you = get_avatar();
    on_out_of_scope cleanup( []() {
        map &here = get_map();
        here.invalidate_map_cache( here.get_abs_sub().z() );
    } );
    restore_on_out_of_scope<tripoint> view_offset_prev( you.view_offset );

    cursor_allowed.clear();
    for( const vpart_reference &part : veh.get_all_parts() ) {
        cursor_allowed.insert( part.pos() );
    }

    if( !set_cursor_pos( pos ) ) {
        debugmsg( "Failed to set vehicle shape cursor at the selected part" );
        set_cursor_pos( veh.global_part_pos3( 0 ) );
    }

    const shared_ptr_fast<game::draw_callback_t> target_ui_cb =
    make_shared_fast<game::draw_callback_t>( [this]() {
        g->draw_cursor_unobscuring( cursor_pos );
    } );
    g->add_draw_callback( target_ui_cb );

    ui_adaptor ui;
    ui.mark_resize();
    init_input();

    std::string action = "CONFIRM";
    while( true ) {
        g->invalidate_main_ui_adaptor();
        ui_manager::redraw();

        if( action.empty() ) {
            action = ctxt.handle_input( get_option<int>( "EDGE_SCROLL" ) );
        }

        if( handle_cursor_movement( action ) || action == "HELP_KEYBINDINGS" ) {
            action.clear();
            continue;
        }
        if( action == "CONFIRM" ) {
            cata::optional<vpart_reference> part;
            do {
                part = select_part_at_cursor( _( "Choose part to change shape" ),
                                              _( "Confirm to select or quit to select another tile." ),
                []( const vpart_reference & vp ) {
                    if( vp.info().symbols.empty() ) {
                        return ret_val<void>::make_failure( _( "Only one shape" ) );
                    }
                    const cata::optional<vpart_reference> displayed = vp.part_displayed();
                    if( displayed && displayed->part_index() != vp.part_index() ) {
                        return ret_val<void>::make_success( _( "Part is obscured" ) );
                    }
                    return ret_val<void>::make_success();
                }, part );
                if( part ) {
                    change_part_shape( part.value() );
                }
            } while( part );
            action.clear();
            continue;
        }
        if( action == "QUIT" ) {
            return player_activity();
        }

        debugmsg( "Unexpected vehicle shape editor action: %s", action );
        return player_activity();
    }
}

std::vector<vpart_reference> veh_shape::parts_under_cursor() const
{
    std::vector<vpart_reference> result;
    for( const vpart_reference &part : veh.get_all_parts() ) {
        if( part.pos() == cursor_pos && !part.part().is_fake ) {
            result.push_back( part );
        }
    }
    return result;
}

cata::optional<vpart_reference> veh_shape::select_part_at_cursor(
    const std::string &title, const std::string &extra_description,
    const std::function<ret_val<void>( const vpart_reference & )> &predicate,
    const cata::optional<vpart_reference> &preselect ) const
{
    const std::vector<vpart_reference> parts = parts_under_cursor();
    if( parts.empty() ) {
        return cata::nullopt;
    }

    uilist menu;
    menu.desc_enabled = !extra_description.empty();
    menu.desc_lines_hint = 1;
    menu.hilight_disabled = true;
    menu.w_x_setup = TERMX / 8;

    for( const vpart_reference &part : parts ) {
        const ret_val<void> predicate_result = predicate( part );
        uilist_entry entry( -1, true, MENU_AUTOASSIGN, part.part().name(), "",
                            predicate_result.str() );
        entry.desc = extra_description;
        entry.enabled = predicate_result.success();
        entry.retval = predicate_result.success() ? static_cast<int>( menu.entries.size() ) : -2;
        if( preselect && preselect->part_index() == part.part_index() ) {
            menu.selected = static_cast<int>( menu.entries.size() );
        }
        menu.entries.push_back( entry );
    }
    menu.text = title;
    menu.query();

    return menu.ret >= 0 ? cata::optional<vpart_reference>( parts[menu.ret] ) : cata::nullopt;
}

static std::string variant_label( const std::string &variant )
{
    for( const std::pair<std::string, translation> &known : vpart_variants ) {
        if( known.first == variant ) {
            return known.second.translated();
        }
    }
    return variant;
}

void veh_shape::change_part_shape( vpart_reference vpr ) const
{
    vehicle_part &part = vpr.part();
    const vpart_info &vpi = part.info();
    veh_menu menu( veh, _( "Choose cosmetic variant:" ) );
    std::string chosen_variant = part.variant;

    struct shape_choice {
        std::string id;
        std::string label;
        int symbol;
    };
    std::vector<shape_choice> choices;
    choices.push_back( { std::string(), _( "Default" ), special_symbol( vpi.sym ) } );
    for( const std::pair<const std::string, int> &variant : vpi.symbols ) {
        choices.push_back( { variant.first, variant_label( variant.first ),
                             special_symbol( variant.second ) } );
    }

    do {
        menu.reset( false );
        for( const shape_choice &choice : choices ) {
            menu.add( choice.label )
            .text_color( part.variant == choice.id ? c_light_green : c_light_gray )
            .keep_menu_open()
            .skip_locked_check()
            .skip_theft_check()
            .location( veh.global_part_pos3( part ) )
            .select( part.variant == choice.id )
            .desc( _( "Confirm to save or exit to revert" ) )
            .symbol( choice.symbol )
            .symbol_color( vpi.color )
            .on_select( [&part, variant = choice.id]() {
                part.variant = variant;
            } )
            .on_submit( [&chosen_variant, variant = choice.id]() {
                chosen_variant = variant;
            } );
        }

        menu.sort( []( const veh_menu_item &a, const veh_menu_item &b ) {
            const static std::map<int, int> symbol_order = {
                { LINE_XOXO, 0 }, { LINE_OXOX, 1 }, { LINE_XOOX, 2 }, { LINE_XXOO, 3 },
                { LINE_XXXX, 4 }, { LINE_OXXO, 5 }, { LINE_OOXX, 6 }
            };
            const auto a_iter = symbol_order.find( a._symbol );
            const auto b_iter = symbol_order.find( b._symbol );
            if( a_iter != symbol_order.end() ) {
                return b_iter == symbol_order.end() || a_iter->second < b_iter->second;
            }
            return b_iter == symbol_order.end() && a._symbol < b._symbol;
        } );
    } while( menu.query() );

    part.variant = chosen_variant;
}

tripoint veh_shape::get_cursor_pos() const
{
    return cursor_pos;
}

bool veh_shape::set_cursor_pos( const tripoint &new_pos )
{
    if( cursor_allowed.count( new_pos ) == 0 ) {
        return false;
    }
    cursor_pos = new_pos;
    avatar &you = get_avatar();
    you.view_offset = cursor_pos - you.pos();
    return true;
}

bool veh_shape::handle_cursor_movement( const std::string &action )
{
    if( action == "MOUSE_MOVE" || action == "TIMEOUT" ) {
        set_cursor_pos( cursor_pos + g->mouse_edge_scrolling_terrain( ctxt ) );
    } else if( const cata::optional<tripoint> delta = ctxt.get_direction( action ) ) {
        set_cursor_pos( cursor_pos + delta.value() );
    } else if( action == "zoom_in" ) {
        g->zoom_in();
    } else if( action == "zoom_out" ) {
        g->zoom_out();
    } else if( action == "SELECT" ) {
        const cata::optional<tripoint> mouse_pos = ctxt.get_coordinates( g->w_terrain );
        if( !mouse_pos ) {
            return false;
        }
        set_cursor_pos( mouse_pos.value() );
    } else if( action == "LEVEL_UP" ) {
        set_cursor_pos( cursor_pos + tripoint_above );
    } else if( action == "LEVEL_DOWN" ) {
        set_cursor_pos( cursor_pos + tripoint_below );
    } else {
        return false;
    }
    return true;
}

void veh_shape::init_input()
{
    ctxt = input_context( "VEH_SHAPES", keyboard_mode::keycode );
    ctxt.set_iso( true );
    ctxt.register_directions();
    ctxt.register_action( "CONFIRM" );
    ctxt.register_action( "SELECT" );
    ctxt.register_action( "QUIT" );
    ctxt.register_action( "HELP_KEYBINDINGS" );
    ctxt.register_action( "MOUSE_MOVE" );
    ctxt.register_action( "LEVEL_UP" );
    ctxt.register_action( "LEVEL_DOWN" );
    ctxt.register_action( "zoom_out" );
    ctxt.register_action( "zoom_in" );
}
