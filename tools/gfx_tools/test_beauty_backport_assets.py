#!/usr/bin/env python3

import hashlib
import json
import struct
import unittest
from pathlib import Path
from typing import Any


REPO_ROOT = Path( __file__ ).resolve().parents[2]


def load_json( path: Path ) -> Any:
    return json.loads( path.read_text( encoding="utf-8" ) )


def tile_ids( config: dict[str, Any] ) -> set[str]:
    result: set[str] = set()
    for sheet in config.get( "tiles-new", [] ):
        for tile in sheet.get( "tiles", [] ):
            value = tile.get( "id", [] )
            if isinstance( value, str ):
                result.add( value )
            else:
                result.update( entry for entry in value if isinstance( entry, str ) )
    return result


def sprite_value_indices( value: Any ) -> list[int]:
    if isinstance( value, bool ):
        return []
    if isinstance( value, int ):
        return [ value ]
    if isinstance( value, list ):
        return [ index for entry in value for index in sprite_value_indices( entry ) ]
    if isinstance( value, dict ) and "sprite" in value:
        return sprite_value_indices( value["sprite"] )
    return []


def tile_sprite_indices( value: Any ) -> list[int]:
    if isinstance( value, list ):
        return [ index for entry in value for index in tile_sprite_indices( entry ) ]
    if not isinstance( value, dict ):
        return []
    result: list[int] = []
    for key, member in value.items():
        if key in { "fg", "bg" }:
            result.extend( sprite_value_indices( member ) )
        elif key == "additional_tiles":
            result.extend( tile_sprite_indices( member ) )
    return result


def sprite_location( index: int, ranges: list[tuple[str, int, int]] ) -> str:
    for name, start, end in ranges:
        if start <= index < end:
            return f"{name}:{index - start}"
    raise AssertionError( f"Sprite {index} is outside the configured sheets" )


def normalized_sprite_value(
    value: Any, ranges: list[tuple[str, int, int]]
) -> Any:
    if isinstance( value, bool ):
        return value
    if isinstance( value, int ):
        return sprite_location( value, ranges )
    if isinstance( value, list ):
        return [ normalized_sprite_value( entry, ranges ) for entry in value ]
    if isinstance( value, dict ):
        result = dict( value )
        if "sprite" in result:
            result["sprite"] = normalized_sprite_value( result["sprite"], ranges )
        return result
    return value


def normalized_tile_mapping(
    tile: dict[str, Any], ranges: list[tuple[str, int, int]]
) -> dict[str, Any]:
    result: dict[str, Any] = { "id": tile.get( "id" ) }
    for key in ( "fg", "bg" ):
        if key in tile:
            result[key] = normalized_sprite_value( tile[key], ranges )
    if "additional_tiles" in tile:
        result["additional_tiles"] = [
            normalized_tile_mapping( entry, ranges )
            for entry in tile["additional_tiles"]
        ]
    return result


def sheet_sprite_count( tileset_dir: Path, config: dict[str, Any], sheet: dict[str, Any] ) -> int:
    header = ( tileset_dir / sheet["file"] ).read_bytes()[:24]
    width, height = struct.unpack( ">II", header[16:24] )
    tile_info = config["tile_info"][0]
    sprite_width = sheet.get( "sprite_width", tile_info["width"] )
    sprite_height = sheet.get( "sprite_height", tile_info["height"] )
    return ( width // sprite_width ) * ( height // sprite_height )


def widget_references( value: Any ) -> set[str]:
    result: set[str] = set()
    if isinstance( value, dict ):
        widgets = value.get( "widgets", [] )
        if isinstance( widgets, list ):
            for widget in widgets:
                if isinstance( widget, str ):
                    result.add( widget )
                else:
                    result.update( widget_references( widget ) )
        for member in value.values():
            if isinstance( member, ( dict, list ) ):
                result.update( widget_references( member ) )
    elif isinstance( value, list ):
        for member in value:
            result.update( widget_references( member ) )
    return result


class BeautyBackportAssetsTest( unittest.TestCase ):
    def test_tileset_manifests_match_installed_configs_and_images( self ) -> None:
        for tileset_name in ( "UltimateCataclysm", "SurveyorsMap" ):
            with self.subTest( tileset=tileset_name ):
                tileset_dir = REPO_ROOT / "gfx" / tileset_name
                manifest = load_json( tileset_dir / "BACKPORT_MANIFEST.json" )
                config = load_json( tileset_dir / "tile_config.json" )

                self.assertEqual( manifest["release_tag"], "2026-08-23" )
                self.assertEqual(
                    manifest["release_commit"],
                    "1f1988c5e144473f894fcb1e2914af51fd08b7af",
                )
                self.assertEqual(
                    len( tile_ids( config ) ),
                    manifest["upstream_ids"] + manifest["legacy_ids_retained"],
                )
                referenced_images = { sheet["file"] for sheet in config["tiles-new"] }
                missing_images = sorted(
                    name for name in referenced_images if not ( tileset_dir / name ).is_file()
                )
                self.assertEqual( missing_images, [] )
                self.assertTrue(
                    set( manifest["legacy_images"] ).issubset( referenced_images )
                )

    def test_latest_ultica_layering_schema_is_supported_by_the_backport( self ) -> None:
        layering = load_json( REPO_ROOT / "gfx/UltimateCataclysm/layering.json" )
        variants = layering["variants"]
        self.assertTrue( any( isinstance( entry["context"], list ) for entry in variants ) )
        suffix_entries = [ entry for entry in variants if "append_variants" in entry ]
        self.assertGreaterEqual( len( suffix_entries ), 3 )
        self.assertTrue(
            any(
                "sprite" not in item
                for entry in suffix_entries
                for item in entry.get( "item_variants", [] )
            )
        )

        loader = ( REPO_ROOT / "src/cata_tiles.cpp" ).read_text( encoding="utf-8" )
        self.assertIn( 'item.has_array( "context" )', loader )
        self.assertIn( 'item.has_string( "append_variants" )', loader )
        self.assertIn( 'v.sprite.emplace( v.id, 1 )', loader )

    def test_ultica_legacy_tiles_reference_rebased_compatibility_sprites( self ) -> None:
        tileset_dir = REPO_ROOT / "gfx/UltimateCataclysm"
        config = load_json( tileset_dir / "tile_config.json" )
        ranges: list[tuple[str, int, int]] = []
        next_index = 0
        for sheet in config["tiles-new"]:
            count = sheet_sprite_count( tileset_dir, config, sheet )
            ranges.append( ( sheet["file"], next_index, next_index + count ) )
            next_index += count

        compat_ranges = [
            ( start, end ) for name, start, end in ranges if name.startswith( "compat_0g_" )
        ]
        self.assertTrue( compat_ranges )
        bad_references: list[tuple[str, int]] = []
        for sheet in config["tiles-new"]:
            if not sheet["file"].startswith( "compat_0g_" ):
                continue
            for tile in sheet.get( "tiles", [] ):
                for index in tile_sprite_indices( tile ):
                    if not any( start <= index < end for start, end in compat_ranges ):
                        bad_references.append( ( str( tile.get( "id" ) ), index ) )
        self.assertEqual( bad_references, [] )

    def test_ultica_follower_overlays_keep_exact_legacy_sheet_offsets( self ) -> None:
        tileset_dir = REPO_ROOT / "gfx/UltimateCataclysm"
        config = load_json( tileset_dir / "tile_config.json" )
        sheet_ranges: dict[str, tuple[int, int]] = {}
        tiles: dict[str, tuple[str, dict[str, Any]]] = {}
        next_index = 0
        for sheet in config["tiles-new"]:
            count = sheet_sprite_count( tileset_dir, config, sheet )
            sheet_ranges[sheet["file"]] = ( next_index, next_index + count )
            for tile in sheet.get( "tiles", [] ):
                value = tile.get( "id", [] )
                ids = [ value ] if isinstance( value, str ) else value
                for tile_id in ids:
                    if isinstance( tile_id, str ):
                        tiles[tile_id] = ( sheet["file"], tile )
            next_index += count

        expected_offsets = {
            # Base follower plus representative legacy hair, armor, and weapon overlays.
            "npc_male": ( "human_body_plus.png", 266 ),
            "overlay_male_mutation_hair_black_short": ( "compat_0g_human_body.png", 182 ),
            "overlay_female_mutation_hair_red_long": ( "compat_0g_human_body.png", 223 ),
            "overlay_wielded_deagle_44": ( "compat_0g_human_body.png", 480 ),
            "overlay_female_worn_chainmail_vest": ( "compat_0g_human_body.png", 1134 ),
            "overlay_male_worn_armor_lightplate": ( "compat_0g_human_body.png", 1159 ),
            "overlay_male_worn_gloves_xlsurvivor": ( "compat_0g_human_body.png", 1798 ),
        }
        for tile_id, ( expected_sheet, expected_offset ) in expected_offsets.items():
            with self.subTest( tile_id=tile_id ):
                actual_sheet, tile = tiles[tile_id]
                self.assertEqual( actual_sheet, expected_sheet )
                sheet_start, sheet_end = sheet_ranges[actual_sheet]
                self.assertEqual( tile["fg"], sheet_start + expected_offset )
                self.assertLess( tile["fg"], sheet_end )

        human_body_hash = hashlib.sha256(
            ( tileset_dir / "compat_0g_human_body.png" ).read_bytes()
        ).hexdigest()
        self.assertEqual(
            human_body_hash,
            "de83cd372ef2729b5ea05554a00178c20144b639c4edbb9d81a395850a0bfbaf",
        )

    def test_normal_input_shadow_blink_calls_compiled_legacy_helper( self ) -> None:
        source = ( REPO_ROOT / "src/handle_action.cpp" ).read_text( encoding="utf-8" )
        self.assertIn( "normal_input_blink_timeout_elapsed( elapsed_ms )", source )
        self.assertNotIn( 'get_option<int>( "BLINK_SPEED" )', source )

    def test_eight_backported_color_themes_are_complete( self ) -> None:
        theme_dir = REPO_ROOT / "data" / "raw" / "color_themes"
        expected = {
            "abyss", "blood_moon", "empyrium", "oxygen",
            "shogun", "spark", "sun", "vector",
        }
        color_names = {
            "BLACK", "RED", "GREEN", "BROWN", "BLUE", "MAGENTA", "CYAN", "GRAY",
            "DGRAY", "LRED", "LGREEN", "YELLOW", "LBLUE", "LMAGENTA", "LCYAN", "WHITE",
        }

        for theme_name in expected:
            with self.subTest( theme=theme_name ):
                objects = load_json( theme_dir / f"base_colors-{theme_name}.json" )
                self.assertEqual( len( objects ), 1 )
                color_def = objects[0]
                self.assertEqual( color_def["type"], "colordef" )
                self.assertTrue( color_names.issubset( color_def ) )
                self.assertTrue(
                    all(
                        len( color_def[name] ) == 3
                        and all( isinstance( channel, int ) and 0 <= channel <= 255
                                 for channel in color_def[name] )
                        for name in color_names
                    )
                )

    def test_font_defaults_and_license_are_packaged( self ) -> None:
        font_data = load_json( REPO_ROOT / "data" / "fontdata.json" )
        expected_font = "data/font/JetBrainsMono-Regular.ttf"
        for key in ( "typeface", "map_typeface", "overmap_typeface" ):
            self.assertEqual( font_data[key][0], expected_font )
        self.assertTrue( ( REPO_ROOT / expected_font ).is_file() )
        self.assertTrue( ( REPO_ROOT / "data/font/JetBrainsMono-OFL.txt" ).is_file() )

    def test_structured_sidebar_widget_references_resolve( self ) -> None:
        ui_root = REPO_ROOT / "data" / "json" / "ui"
        all_objects: list[dict[str, Any]] = []
        for path in ui_root.rglob( "*.json" ):
            payload = load_json( path )
            if isinstance( payload, list ):
                all_objects.extend( entry for entry in payload if isinstance( entry, dict ) )

        widget_ids = {
            entry["id"] for entry in all_objects
            if entry.get( "type" ) == "widget" and isinstance( entry.get( "id" ), str )
        }
        structured_objects = [
            entry for entry in all_objects
            if isinstance( entry.get( "id" ), str )
            and entry["id"].startswith( "structured_" )
        ]
        self.assertIn( "structured_sidebar", widget_ids )
        missing = set().union(
            *( widget_references( entry ) for entry in structured_objects )
        ) - widget_ids
        self.assertEqual( missing, set() )


if __name__ == "__main__":
    unittest.main()
