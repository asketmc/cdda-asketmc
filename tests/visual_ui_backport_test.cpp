#include <algorithm>
#include <list>
#include <string>
#include <utility>
#include <vector>

#include "avatar.h"
#include "cata_catch.h"
#include "item.h"
#include "optional.h"
#include "player_helpers.h"
#include "sounds.h"

#if defined(TILES)
#include "cata_tiles.h"
#endif

#if defined(TILES)
TEST_CASE( "tall_sprite_occlusion_retraction_modes", "[tiles][visual_backport][pr63089]" )
{
    CHECK( calculate_occlusion_retract( 0, 1.0f, 1.0f, 5.0f ) == 0 );
    CHECK( calculate_occlusion_retract( 1, 99.0f, 1.0f, 5.0f ) == 100 );

    CHECK( calculate_occlusion_retract( 2, 1.0f, 1.0f, 5.0f ) == 100 );
    CHECK( calculate_occlusion_retract( 2, 3.0f, 1.0f, 5.0f ) == 50 );
    CHECK( calculate_occlusion_retract( 2, 5.0f, 1.0f, 5.0f ) == 0 );
    CHECK( calculate_occlusion_retract( 2, 10.0f, 5.0f, 5.0f ) == 0 );
}

TEST_CASE( "isometric_multi_z_uses_scaled_height_and_legacy_fallback",
           "[tiles][visual_backport][pr66383][pr82240]" )
{
    // SmashButton_iso: source width 16, pixelscale 2 at default zoom.
    CHECK( scaled_zlevel_height( 10, 32, 16 ) == 20 );
    CHECK( scaled_zlevel_height( 10, 16, 16 ) == 10 );
    // Ultica_iso: source width 48 at default and 1.5x zoom.
    CHECK( scaled_zlevel_height( 96, 48, 48 ) == 96 );
    CHECK( scaled_zlevel_height( 96, 72, 48 ) == 144 );

    // Sprite and geometry-fog paths use this same final screen transform,
    // including height accumulated from tile height_3d layers.
    CHECK( zlevel_screen_y( 200, 10, 32, 16 ) == 180 );
    CHECK( zlevel_screen_y( 200, -10, 32, 16 ) == 220 );
    CHECK( zlevel_screen_y( 200, 14, 32, 16 ) == 172 );
    CHECK( zlevel_screen_y( 200, 96, 72, 48 ) == 56 );

    CHECK( effective_3d_draw_depth( false, 4, 0 ) == 4 );
    CHECK( effective_3d_draw_depth( true, 4, 20 ) == 4 );
    CHECK( effective_3d_draw_depth( true, 4, 0 ) == 0 );
    CHECK( effective_3d_draw_depth( true, 4, -1 ) == 0 );

    CHECK( zlevel_fog_alpha( false, 96 ) == 100 );
    CHECK( zlevel_fog_alpha( true, 0 ) == 100 );
    CHECK( zlevel_fog_alpha( true, 96 ) > zlevel_fog_alpha( true, 48 ) );
}

TEST_CASE( "weighted_field_sprite_selection_respects_weights",
           "[tiles][visual_backport][pr75636]" )
{
    layer_variant variant;
    variant.sprite = { { "first", 1 }, { "second", 2 } };
    variant.total_weight = 3;

    CHECK( pick_layer_variant_sprite( variant, 0 ) == "first" );
    CHECK( pick_layer_variant_sprite( variant, 1 ) == "second" );
    CHECK( pick_layer_variant_sprite( variant, 2 ) == "second" );
    CHECK( pick_layer_variant_sprite( variant, 3 ) == "first" );

    variant.total_weight = 0;
    CHECK( pick_layer_variant_sprite( variant, 0 ).empty() );
}

TEST_CASE( "modern_ultica_layer_suffixes_preserve_normal_item_variants",
           "[tiles][visual_backport][ultica_layering]" )
{
    layer_variant layer;
    layer.append_suffix = "_hoisted";

    CHECK( layered_item_variant( layer, "" ) == "_hoisted" );
    CHECK( layered_item_variant( layer, "folded" ) == "folded_hoisted" );
    CHECK( tile_id_with_variant( "american_flag", "_hoisted", true ) ==
           "american_flag_hoisted" );
    CHECK( tile_id_with_variant( "american_flag", "folded", true ) ==
           "american_flag_var_folded" );
    CHECK( tile_id_with_variant( "vp_door", "_open", false ) ==
           "vp_door_var__open" );
    CHECK( tile_id_with_variant( "american_flag", "", true ) == "american_flag" );
}
#endif

TEST_CASE( "armor_sprite_override_replaces_the_worn_overlay",
           "[armor][visual_backport][pr66931]" )
{
    avatar &dummy = get_avatar();
    clear_character( dummy );

    const cata::optional<std::list<item>::iterator> worn_result =
        dummy.wear_item( item( "backpack" ), false, false );
    REQUIRE( worn_result );
    item &worn = **worn_result;
    const auto has_overlay = [&dummy]( const std::pair<std::string, std::string> &expected ) {
        const std::vector<std::pair<std::string, std::string>> overlays = dummy.get_overlay_ids();
        return std::find( overlays.begin(), overlays.end(), expected ) != overlays.end();
    };

    CHECK( has_overlay( { "worn_backpack", "" } ) );

    worn.set_var( "sprite_override", "helmet_ballistic" );
    worn.set_var( "sprite_override_variant", "test_variant" );
    CHECK_FALSE( has_overlay( { "worn_backpack", "" } ) );
    CHECK( has_overlay( { "worn_helmet_ballistic", "test_variant" } ) );
}

TEST_CASE( "specific_gun_sound_candidates_keep_legacy_fallback_order",
           "[sound][visual_backport][pr86002]" )
{
    const std::vector<sfx::sound_effect_choice> choices = sfx::gun_sound_candidates(
                "rifle_m4", "223", "_suppressed", "weapon_fire_suppressed" );
    REQUIRE( choices.size() == 5 );
    CHECK( choices[0].id == "fire_gun_suppressed" );
    CHECK( choices[0].variant == "rifle_m4" );
    CHECK( choices[1].id == "fire_ammo_suppressed" );
    CHECK( choices[1].variant == "223" );
    CHECK( choices[2].id == "fire_gun" );
    CHECK( choices[2].variant == "weapon_fire_suppressed" );
    CHECK( choices[3].id == "fire_gun_suppressed" );
    CHECK( choices[3].variant == "default" );
    CHECK( choices[4].id == "fire_gun" );
    CHECK( choices[4].variant == "default" );
}

TEST_CASE( "specific_melee_sound_fallbacks_use_skill_size_and_material",
           "[sound][visual_backport][pr86002]" )
{
    CHECK( sfx::melee_sound_fallback_variant( "bashing", 8 ) == "small_bash" );
    CHECK( sfx::melee_sound_fallback_variant( "bashing", 9 ) == "big_bash" );
    CHECK( sfx::melee_sound_fallback_variant( "cutting", 6 ) == "small_cutting" );
    CHECK( sfx::melee_sound_fallback_variant( "cutting", 7 ) == "big_cutting" );
    CHECK( sfx::melee_sound_fallback_variant( "stabbing", 4 ) == "small_stabbing" );
    CHECK( sfx::melee_sound_fallback_variant( "stabbing", 5 ) == "big_stabbing" );
    CHECK( sfx::melee_sound_fallback_variant( "unarmed", 0 ) == "unarmed" );
    CHECK( sfx::melee_sound_fallback_variant( "launcher", 20 ) == "default" );

    CHECK( sfx::melee_hit_sound_id( true, "steel" ) == "melee_hit_metal" );
    CHECK( sfx::melee_hit_sound_id( true, "flesh" ) == "melee_hit_flesh" );
    CHECK( sfx::melee_hit_sound_id( false, "steel" ) == "melee_hit_flesh" );
}
