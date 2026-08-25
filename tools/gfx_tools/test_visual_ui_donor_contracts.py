#!/usr/bin/env python3

"""Regression contracts for every upstream PR bundled by the visual/UI backport.

Most renderer behavior in CDDA 0.G cannot be instantiated in its headless Catch2
runner because it has no off-screen SDL fixture.  These tests therefore combine
parsed data assertions with call-path/source contracts.  Pure calculations and
save-facing behavior are additionally covered by tests/visual_ui_backport_test.cpp.
"""

import json
import unittest
from pathlib import Path
from typing import Any


REPO_ROOT = Path( __file__ ).resolve().parents[2]


def text( relative_path: str ) -> str:
    return ( REPO_ROOT / relative_path ).read_text( encoding="utf-8" )


def json_data( relative_path: str ) -> Any:
    return json.loads( text( relative_path ) )


def function_body( relative_path: str, marker: str ) -> str:
    """Return a C++ function body, including nested blocks, from a unique marker."""
    source = text( relative_path )
    start = source.find( marker )
    if start < 0:
        raise AssertionError( f"Missing function marker {marker!r} in {relative_path}" )
    opening = source.find( "{", start )
    if opening < 0:
        raise AssertionError( f"Missing body after {marker!r} in {relative_path}" )

    depth = 0
    for index in range( opening, len( source ) ):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[opening:index + 1]
    raise AssertionError( f"Unterminated body after {marker!r} in {relative_path}" )


def keybinding( binding_id: str ) -> dict[str, Any]:
    matches = [
        entry for entry in json_data( "data/raw/keybindings.json" )
        if entry.get( "type" ) == "keybinding" and entry.get( "id" ) == binding_id
    ]
    if len( matches ) != 1:
        raise AssertionError( f"Expected one keybinding {binding_id}, found {len( matches )}" )
    return matches[0]


def tile_entry( tileset: str, tile_id: str ) -> dict[str, Any]:
    config = json_data( f"gfx/{tileset}/tile_config.json" )
    for sheet in config.get( "tiles-new", [] ):
        for entry in sheet.get( "tiles", [] ):
            ids = entry.get( "id", [] )
            ids = [ids] if isinstance( ids, str ) else ids
            if tile_id in ids:
                return entry
    raise AssertionError( f"Missing tile {tile_id} in {tileset}" )


class PR63089TallSpriteOcclusionTest( unittest.TestCase ):
    def test_occlusion_controls_reach_the_renderer( self ) -> None:
        self.assertEqual( keybinding( "toggle_prevent_occlusion" )["category"], "DEFAULTMODE" )
        options = text( "src/options.cpp" )
        for option_id in (
            "PREVENT_OCCLUSION", "PREVENT_OCCLUSION_RETRACT", "PREVENT_OCCLUSION_TRANSP",
            "PREVENT_OCCLUSION_MIN_DIST", "PREVENT_OCCLUSION_MAX_DIST",
        ):
            self.assertIn( f'"{option_id}"', options )

        renderer = function_body(
            "src/cata_tiles.cpp",
            "bool cata_tiles::draw_from_id_string_internal( const std::string &id, TILE_CATEGORY category",
        )
        self.assertIn( "calculate_occlusion_retract", renderer )
        self.assertIn( 'id + "_transparent"', renderer )
        self.assertIn( "prevent_occlusion_retract", renderer )


class PR65622RunningSmashingAnimationTest( unittest.TestCase ):
    def test_run_directions_and_smash_results_emit_animation_ids( self ) -> None:
        movement = function_body( "src/game.cpp", "bool game::walk_move(" )
        for direction in ( "n", "ne", "e", "se", "s", "sw", "w", "nw" ):
            self.assertIn( f'"run_{direction}"', movement )

        smashing = function_body( "src/handle_action.cpp", "static void smash()" )
        for result in ( "bash_complete", "bash_effective", "bash_ineffective" ):
            self.assertIn( f'"{result}"', smashing )


class PR66087AsynchronousAnimationTest( unittest.TestCase ):
    def test_async_layers_persist_until_timeout_or_input_cleanup( self ) -> None:
        draw_api = function_body( "src/animation.cpp", "void game::draw_async_anim(" )
        self.assertIn( "tilecontext->init_draw_async_anim", draw_api )
        self.assertIn( "invalidate_main_ui_adaptor", draw_api )

        tile_draw = function_body( "src/cata_tiles.cpp", "void cata_tiles::draw_async_anim()" )
        self.assertIn( "async_anim_layer", tile_draw )
        self.assertIn( "draw_from_id_string", tile_draw )

        action_loop = text( "src/handle_action.cpp" )
        self.assertGreaterEqual( action_loop.count( "void_async_anim_curses" ), 2 )
        self.assertGreaterEqual( action_loop.count( "tilecontext->void_async_anim" ), 2 )
        self.assertIn( "async_anim_timeout", action_loop )


class PR65738LowerZVisionTest( unittest.TestCase ):
    def test_vertical_range_controls_bottom_up_non_isometric_draw( self ) -> None:
        options = text( "src/options.cpp" )
        self.assertIn( '"FOV_3D_Z_RANGE"', options )
        self.assertIn( 'setPrerequisite( "FOV_3D" )', options )

        renderer = function_body( "src/cata_tiles.cpp", "void cata_tiles::draw(" )
        self.assertIn( "effective_3d_draw_depth", renderer )
        self.assertIn( "draw_points_3d", renderer )
        self.assertIn( "min_draw_z", renderer )
        self.assertIn( "drawing_layers_legacy", renderer )


class PR66383IsometricMultiZTest( unittest.TestCase ):
    def test_bundled_isometric_tilesets_define_positive_height( self ) -> None:
        self.assertEqual(
            json_data( "gfx/SmashButton_iso/tile_config.json" )["tile_info"][0]["zlevel_height"],
            10,
        )
        self.assertEqual(
            json_data( "gfx/Ultica_iso/tile_config.json" )["tile_info"][0]["zlevel_height"],
            96,
        )

    def test_sprite_and_fog_paths_share_the_final_screen_transform( self ) -> None:
        sprite = function_body( "src/cata_tiles.cpp", "bool cata_tiles::draw_sprite_at(" )
        fog = function_body( "src/cata_tiles.cpp", "void cata_tiles::draw_zlevel_overlay(" )
        self.assertIn( "destination.y = zlevel_screen_y", sprite )
        self.assertIn( "draw_rect.y = zlevel_screen_y", fog )

class PR66730UpperCreatureShadowTest( unittest.TestCase ):
    def test_shadow_is_drawn_only_when_upper_creature_is_not_directly_drawn( self ) -> None:
        renderer = function_body( "src/cata_tiles.cpp", "void cata_tiles::draw(" )
        self.assertIn( 'find_tile_looks_like( "shadow"', renderer )
        self.assertIn( "!( this->*f )( draw_loc", renderer )
        self.assertIn( "draw_critter_above", renderer )

        shadow = function_body( "src/cata_tiles.cpp", "bool cata_tiles::draw_critter_above(" )
        self.assertIn( "scan_p.z - you.pos().z <= fov_3d_z_range", shadow )
        self.assertIn( 'draw_from_id_string( "shadow"', shadow )
        self.assertIn( "you.sees( critter )", shadow )
        self.assertIn( "shadow", tile_entry( "UltimateCataclysm", "shadow" )["id"] )


class PR66931ArmorSpriteOverrideTest( unittest.TestCase ):
    def test_override_is_bound_to_ui_save_vars_and_worn_overlay( self ) -> None:
        self.assertTrue( keybinding( "CHANGE_ARMOR_SPRITE" )["bindings"] )
        attire = function_body( "src/character_attire.cpp", "void outfit::get_overlay_ids(" )
        self.assertIn( 'has_var( "sprite_override" )', attire )
        self.assertIn( 'get_var( "sprite_override_variant"', attire )

        player_ui = text( "src/player_display.cpp" )
        self.assertIn( 'set_var( "sprite_override"', player_ui )
        self.assertIn( 'erase_var( "sprite_override"', player_ui )
        self.assertIn( 'register_action( "CHANGE_ARMOR_SPRITE"', player_ui )


class PR67997VisibilityCacheCorrectnessTest( unittest.TestCase ):
    def test_each_lower_tile_uses_its_own_visibility_and_cache_is_invalidated( self ) -> None:
        renderer = function_body( "src/cata_tiles.cpp", "void cata_tiles::draw(" )
        self.assertIn( "calc_ll_invis( draw_loc )", renderer )
        self.assertIn( "ll_invis_cache.emplace( draw_loc", renderer )

        calculation = function_body( "src/cata_tiles.cpp", "cata_tiles::calc_ll_invis(" )
        self.assertIn( "access_cache( draw_loc.z )", calculation )
        self.assertIn( "visibility_cache[draw_loc.x][draw_loc.y]", calculation )

        cache_update = function_body( "src/map.cpp", "void map::update_visibility_cache(" )
        self.assertIn( "tilecontext->clear_draw_caches()", cache_update )


class PR67434LedgeSightCoverageTest( unittest.TestCase ):
    def test_ledges_adjust_player_seen_cache_without_creature_stealth_changes( self ) -> None:
        coverage = function_body(
            "src/map.cpp",
            "int map::ledge_coverage( const tripoint &viewer_p, const tripoint &target_p",
        )
        self.assertIn( "dont_draw_lower_floor( p )", coverage )
        self.assertIn( "if( coverage < 0.0f )", coverage )
        self.assertIn( "if( const furn_id target_furn", coverage )

        seen_cache = function_body( "src/lightmap.cpp", "void map::seen_cache_process_ledges(" )
        self.assertIn( "coverage > 100", seen_cache )
        self.assertIn( "floor_caches", seen_cache )

        cache_builder = function_body( "src/lightmap.cpp", "void map::build_seen_cache(" )
        self.assertIn( "if( !camera )", cache_builder )
        self.assertIn( "seen_cache_process_ledges", cache_builder )

        lower_floor = function_body( "src/map.cpp", "bool map::dont_draw_lower_floor(" )
        self.assertIn( "!inbounds( p )", lower_floor )
        self.assertIn( "TFLAG_Z_TRANSPARENT", lower_floor )


class PR68660VerticalLookTest( unittest.TestCase ):
    def test_look_vertical_actions_are_not_gated_by_3d_vision( self ) -> None:
        look = function_body( "src/game.cpp", "look_around_result game::look_around(" )
        self.assertNotIn( "allow_zlev_move", look )
        self.assertIn( 'action == "LEVEL_UP" || action == "LEVEL_DOWN"', look )
        self.assertIn( "m.build_map_cache( center.z )", look )

        cache_build = function_body( "src/map.cpp", "void map::build_map_cache(" )
        self.assertIn( "const bool affects_seen_cache = z == zlev || fov_3d", cache_build )
        self.assertIn( "floor_cache_was_dirty && affects_seen_cache", cache_build )


class PR68153ColorThemesTest( unittest.TestCase ):
    def test_all_eight_themes_define_the_full_base_palette( self ) -> None:
        expected = {
            "abyss", "blood_moon", "empyrium", "oxygen",
            "shogun", "spark", "sun", "vector",
        }
        base_colors = {
            "BLACK", "RED", "GREEN", "BROWN", "BLUE", "MAGENTA", "CYAN", "GRAY",
            "DGRAY", "LRED", "LGREEN", "YELLOW", "LBLUE", "LMAGENTA", "LCYAN", "WHITE",
        }
        for theme in expected:
            with self.subTest( theme=theme ):
                payload = json_data( f"data/raw/color_themes/base_colors-{theme}.json" )
                self.assertEqual( len( payload ), 1 )
                self.assertTrue( base_colors.issubset( payload[0] ) )


class PR75636WeightedFieldSpritesTest( unittest.TestCase ):
    def test_field_layering_uses_shared_weighted_selector_for_both_contexts( self ) -> None:
        drawing = function_body( "src/cata_tiles.cpp", "bool cata_tiles::draw_field_or_item(" )
        self.assertGreaterEqual( drawing.count( "pick_layer_variant_sprite" ), 4 )
        self.assertGreaterEqual( drawing.count( "simple_point_hash( p )" ), 2 )
        self.assertIn( "Multiple sprites can be provided with specific weights",
                       text( "doc/TILESET.md" ) )


class PR80980AnimatedRainVariantsTest( unittest.TestCase ):
    def test_weather_uses_nondeterministic_seed_and_ultica_has_varied_rain( self ) -> None:
        renderer = function_body(
            "src/cata_tiles.cpp",
            "bool cata_tiles::draw_from_id_string_internal( const std::string &id, TILE_CATEGORY category",
        )
        weather_case = renderer[renderer.index( "case TILE_CATEGORY::WEATHER:" ):]
        self.assertIn( "seed = rng_bits()", weather_case )

        rain = tile_entry( "UltimateCataclysm", "weather_rain_drop" )
        self.assertIsInstance( rain["fg"], list )
        self.assertGreaterEqual( len( rain["fg"] ), 2 )
        self.assertTrue( all( entry.get( "weight", 0 ) > 0 for entry in rain["fg"] ) )


class PR85166VisibleMeleeHitTest( unittest.TestCase ):
    def test_visible_monster_melee_attack_reuses_hit_animation( self ) -> None:
        attack = function_body( "src/monmove.cpp", "bool monster::attack_at(" )
        self.assertIn( "const bool attacked = melee_attack( mon )", attack )
        self.assertIn( "attacked && get_player_view().sees( p )", attack )
        self.assertIn( "g->draw_hit_mon( p, mon, mon.is_dead() )", attack )

        animation = function_body( "src/animation.cpp", "void game::draw_hit_mon(" )
        self.assertIn( "tilecontext->init_draw_hit", animation )
        self.assertIn( "bullet_animation().progress()", animation )


class PR86002SpecificWeaponSoundTest( unittest.TestCase ):
    def test_exact_sound_selection_and_array_variants_are_wired_end_to_end( self ) -> None:
        gun = function_body( "src/sounds.cpp", "void sfx::generate_gun_sound(" )
        self.assertIn( "gun_sound_candidates", gun )
        self.assertIn( "has_exact_variant_sound", gun )
        self.assertIn( "candidates.back()", gun )

        melee = function_body( "src/sounds.cpp", "void sfx::sound_thread::operator()() const" )
        self.assertIn( "melee_sound_fallback_variant", melee )
        self.assertIn( "melee_hit_sound_id", melee )
        self.assertIn( "has_exact_variant_sound", melee )

        loader = text( "src/sdlsound.cpp" )
        effects = function_body( "src/sdlsound.cpp", "void sfx::load_sound_effects(" )
        preload = function_body( "src/sdlsound.cpp", "void sfx::load_sound_effect_preload(" )
        self.assertIn( 'has_array( "variant" )', effects )
        self.assertIn( 'get_string_array( "variant" )', effects )
        self.assertIn( 'has_array( "variant" )', preload )
        self.assertIn( 'find_no_fallback', loader )


class PR86249NpcFootstepTest( unittest.TestCase ):
    def test_step_owner_position_terrain_and_angle_drive_audio( self ) -> None:
        movement = function_body( "src/character.cpp", "void Character::make_footstep_noise() const" )
        self.assertIn( "sfx::do_footstep( *this )", movement )

        footstep = function_body( "src/sounds.cpp", "void sfx::do_footstep( const Character &ch )" )
        self.assertIn( "get_heard_volume( ch.pos() )", footstep )
        self.assertIn( "ch.is_npc() ? sfx::get_heard_angle( ch.pos() )", footstep )
        self.assertIn( "here.ter( ch.pos() )", footstep )
        self.assertIn( "here.veh_at( ch.pos() )", footstep )
        self.assertIn( "ch.is_barefoot()", footstep )


if __name__ == "__main__":
    unittest.main()
