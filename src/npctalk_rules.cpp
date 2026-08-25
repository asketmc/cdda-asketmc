#include "npctalk_rules.h"

#include <array>
#include <cstddef>
#include <string>
#include <utility>
#include <vector>

#include "game.h"
#include "messages.h"
#include "npc.h"
#include "output.h"
#include "string_formatter.h"
#include "translations.h"
#include "ui.h"

namespace
{

struct boolean_rule_entry {
    ally_rule rule;
    const char *name;
    const char *enabled_description;
    const char *disabled_description;
};

const std::array<boolean_rule_entry, 18> boolean_rules = { {
        {
            ally_rule::use_guns, "Ranged weapons",
            "May use ranged weapons.", "Will not use ranged weapons."
        },
        {
            ally_rule::use_grenades, "Grenades",
            "May use grenades.", "Will not use grenades."
        },
        {
            ally_rule::use_silent, "Silent weapons only",
            "Will use only silent ranged weapons.", "May use noisy ranged weapons."
        },
        {
            ally_rule::avoid_friendly_fire, "Avoid friendly fire",
            "Will avoid shots that might hit an ally.", "May take shots that risk hitting an ally."
        },
        {
            ally_rule::allow_pick_up, "Pick up items",
            "May pick up items allowed by the pickup list.", "Will not pick up items."
        },
        {
            ally_rule::allow_bash, "Bash obstacles",
            "May bash obstacles while moving.", "Will not bash obstacles while moving."
        },
        {
            ally_rule::allow_sleep, "Sleep when tired",
            "May sleep when tired.", "Will stay awake."
        },
        {
            ally_rule::allow_complain, "Report needs",
            "Will tell you when something is needed.", "Will stay quiet about unmet needs."
        },
        {
            ally_rule::allow_pulp, "Pulp corpses",
            "May pulp zombie corpses.", "Will leave corpses alone."
        },
        {
            ally_rule::close_doors, "Close doors",
            "Will close doors after passing through.", "Will leave doors open."
        },
        {
            ally_rule::lock_doors, "Lock doors",
            "Will lock doors that are closed.", "Will leave doors unlocked."
        },
        {
            ally_rule::follow_close, "Stay close",
            "Will stay close even when repositioning would help.", "May move freely as needed."
        },
        {
            ally_rule::follow_distance_2, "Follow at two tiles",
            "Will normally follow at a distance of two tiles.",
            "Will normally follow at a distance of four tiles."
        },
        {
            ally_rule::avoid_doors, "Avoid opening doors",
            "Will avoid opening doors when possible.", "May open doors when needed."
        },
        {
            ally_rule::avoid_locks, "Avoid unlocking doors",
            "Will avoid unlocking doors.", "May unlock doors when needed."
        },
        {
            ally_rule::hold_the_line, "Hold the line",
            "Will avoid moving onto obstacles adjacent to you.",
            "May move onto nearby obstacles to fight."
        },
        {
            ally_rule::ignore_noise, "Ignore noises",
            "Will ignore noises that would otherwise be investigated.",
            "May investigate noises."
        },
        {
            ally_rule::forbid_engage, "Forbid autonomous engagement",
            "Will not autonomously engage enemies.",
            "May engage enemies according to the engagement rule."
        }
    }
};

template<typename T>
struct rule_choice {
    T value;
    const char *label;
    const char *description;
};

template<typename T>
bool choose_rule( const std::string &title, const std::string &prompt, T &current,
                  const std::vector<rule_choice<T>> &choices )
{
    uilist menu;
    menu.title = title;
    menu.text = prompt;
    menu.desc_enabled = true;
    menu.desc_lines_hint = 3;
    for( size_t i = 0; i < choices.size(); ++i ) {
        const rule_choice<T> &choice = choices[i];
        std::string label = _( choice.label );
        if( current == choice.value ) {
            label += _( " (current)" );
        }
        menu.addentry_desc( static_cast<int>( i ), true, MENU_AUTOASSIGN, label,
                            _( choice.description ) );
    }
    menu.query();
    if( menu.ret < 0 || static_cast<size_t>( menu.ret ) >= choices.size() ) {
        return false;
    }
    current = choices[menu.ret].value;
    return true;
}

bool choose_engagement_rule( npc &follower )
{
    const std::vector<rule_choice<combat_engagement>> choices = {
        {
            combat_engagement::NONE, "Do not engage",
            "Fight only when personal survival depends on it."
        },
        {
            combat_engagement::CLOSE, "Engage nearby enemies",
            "Attack enemies that get close."
        },
        {
            combat_engagement::WEAK, "Engage weak enemies",
            "Attack enemies that should be easy to defeat."
        },
        {
            combat_engagement::HIT, "Engage enemies I attack",
            "Attack enemies only after you attack them first."
        },
        {
            combat_engagement::ALL, "Engage all enemies",
            "Attack any enemy without waiting for permission."
        },
        {
            combat_engagement::FREE_FIRE, "Free fire without moving",
            "Attack enemies in ranged-weapon reach, but do not move to engage."
        },
        {
            combat_engagement::NO_MOVE, "Engage without moving",
            "Attack enemies that can be reached without moving."
        }
    };
    return choose_rule( _( "Follower engagement" ),
                        string_format( _( "Set engagement rules for %s." ), follower.disp_name() ),
                        follower.rules.engagement, choices );
}

bool choose_aim_rule( npc &follower )
{
    const std::vector<rule_choice<aim_rule>> choices = {
        {
            aim_rule::WHEN_CONVENIENT, "Aim when convenient",
            "Aim when circumstances allow it."
        },
        {
            aim_rule::SPRAY, "Fire quickly",
            "Prioritize firing quickly over careful aim."
        },
        {
            aim_rule::PRECISE, "Aim carefully",
            "Take time to aim carefully when possible."
        },
        {
            aim_rule::STRICTLY_PRECISE, "Require precise aim",
            "Do not shoot without taking a long time to aim."
        }
    };
    return choose_rule( _( "Follower aiming" ),
                        string_format( _( "Set aiming rules for %s." ), follower.disp_name() ),
                        follower.rules.aim, choices );
}

bool choose_cbm_recharge_rule( npc &follower )
{
    const std::vector<rule_choice<cbm_recharge_rule>> choices = {
        {
            cbm_recharge_rule::CBM_RECHARGE_ALL, "Recharge to 90%",
            "Consume supplies to recharge power CBMs up to 90%."
        },
        {
            cbm_recharge_rule::CBM_RECHARGE_MOST, "Recharge to 75%",
            "Consume supplies to recharge power CBMs up to 75%."
        },
        {
            cbm_recharge_rule::CBM_RECHARGE_SOME, "Recharge to 50%",
            "Consume supplies to recharge power CBMs up to 50%."
        },
        {
            cbm_recharge_rule::CBM_RECHARGE_LITTLE, "Recharge to 25%",
            "Consume supplies to recharge power CBMs up to 25%."
        },
        {
            cbm_recharge_rule::CBM_RECHARGE_NONE, "Recharge to 10%",
            "Consume supplies to recharge power CBMs only up to 10%."
        }
    };
    return choose_rule( _( "Follower CBM recharging" ),
                        string_format( _( "Set CBM recharging rules for %s." ), follower.disp_name() ),
                        follower.rules.cbm_recharge, choices );
}

bool choose_cbm_reserve_rule( npc &follower )
{
    const std::vector<rule_choice<cbm_reserve_rule>> choices = {
        {
            cbm_reserve_rule::CBM_RESERVE_ALL, "Reserve 100%",
            "Reserve all CBM power for defense and utility."
        },
        {
            cbm_reserve_rule::CBM_RESERVE_MOST, "Reserve 75%",
            "Reserve 75% of CBM power for defense and utility."
        },
        {
            cbm_reserve_rule::CBM_RESERVE_SOME, "Reserve 50%",
            "Reserve 50% of CBM power for defense and utility."
        },
        {
            cbm_reserve_rule::CBM_RESERVE_LITTLE, "Reserve 25%",
            "Reserve 25% of CBM power for defense and utility."
        },
        {
            cbm_reserve_rule::CBM_RESERVE_NONE, "Reserve 0%",
            "Do not reserve CBM power for defense and utility."
        }
    };
    return choose_rule( _( "Follower CBM power reserve" ),
                        string_format( _( "Set CBM reserve rules for %s." ), follower.disp_name() ),
                        follower.rules.cbm_reserve, choices );
}

npc *choose_other_follower( const npc &follower, const std::string &prompt )
{
    std::vector<npc *> followers;
    for( npc &candidate : g->all_npcs() ) {
        if( candidate.is_player_ally() && &candidate != &follower ) {
            followers.push_back( &candidate );
        }
    }
    if( followers.empty() ) {
        popup( _( "%s is your only available follower." ), follower.disp_name() );
        return nullptr;
    }

    uilist menu;
    menu.title = _( "Transfer follower rules" );
    menu.text = prompt;
    for( size_t i = 0; i < followers.size(); ++i ) {
        menu.addentry( static_cast<int>( i ), true, MENU_AUTOASSIGN, followers[i]->disp_name() );
    }
    menu.query();
    if( menu.ret < 0 || static_cast<size_t>( menu.ret ) >= followers.size() ) {
        return nullptr;
    }
    return followers[menu.ret];
}

enum class transfer_part : int {
    behaviors,
    aiming,
    engagement,
    cbm_recharge,
    cbm_reserve,
    pickup_list,
    all
};

bool choose_transfer_part( transfer_part &part )
{
    uilist menu;
    menu.title = _( "Transfer follower rules" );
    menu.text = _( "Which settings should be transferred?" );
    menu.desc_enabled = true;
    menu.desc_lines_hint = 2;
    menu.addentry_desc( static_cast<int>( transfer_part::behaviors ), true, MENU_AUTOASSIGN,
                        _( "Behavior rules" ), _( "Boolean behavior rules and their overrides." ) );
    menu.addentry_desc( static_cast<int>( transfer_part::aiming ), true, MENU_AUTOASSIGN,
                        _( "Aiming rule" ), _( "The selected aiming behavior." ) );
    menu.addentry_desc( static_cast<int>( transfer_part::engagement ), true, MENU_AUTOASSIGN,
                        _( "Engagement rule" ), _( "The selected enemy engagement behavior." ) );
    menu.addentry_desc( static_cast<int>( transfer_part::cbm_recharge ), true, MENU_AUTOASSIGN,
                        _( "CBM recharge rule" ), _( "The CBM automatic recharge threshold." ) );
    menu.addentry_desc( static_cast<int>( transfer_part::cbm_reserve ), true, MENU_AUTOASSIGN,
                        _( "CBM reserve rule" ), _( "The CBM power reserve threshold." ) );
    menu.addentry_desc( static_cast<int>( transfer_part::pickup_list ), true, MENU_AUTOASSIGN,
                        _( "Pickup list" ), _( "The follower-specific item pickup list." ) );
    menu.addentry_desc( static_cast<int>( transfer_part::all ), true, MENU_AUTOASSIGN,
                        _( "All settings" ), _( "Every rule and the pickup list." ) );
    menu.query();
    if( menu.ret < static_cast<int>( transfer_part::behaviors ) ||
        menu.ret > static_cast<int>( transfer_part::all ) ) {
        return false;
    }
    part = static_cast<transfer_part>( menu.ret );
    return true;
}

void copy_rule_part( const npc &source, npc &destination, transfer_part part )
{
    if( part == transfer_part::behaviors || part == transfer_part::all ) {
        destination.rules.flags = source.rules.flags;
        destination.rules.overrides = source.rules.overrides;
        destination.rules.override_enable = source.rules.override_enable;
    }
    if( part == transfer_part::aiming || part == transfer_part::all ) {
        destination.rules.aim = source.rules.aim;
    }
    if( part == transfer_part::engagement || part == transfer_part::all ) {
        destination.rules.engagement = source.rules.engagement;
    }
    if( part == transfer_part::cbm_recharge || part == transfer_part::all ) {
        destination.rules.cbm_recharge = source.rules.cbm_recharge;
    }
    if( part == transfer_part::cbm_reserve || part == transfer_part::all ) {
        destination.rules.cbm_reserve = source.rules.cbm_reserve;
    }
    if( part == transfer_part::pickup_list || part == transfer_part::all ) {
        destination.rules.pickup_whitelist = source.rules.pickup_whitelist;
    }
    destination.invalidate_range_cache();
    destination.wield_better_weapon();
}

void transfer_rules( npc &follower, bool exporting )
{
    const std::string prompt = exporting ?
                               string_format( _( "Export settings from %s to which follower?" ),
                                   follower.disp_name() ) :
                               string_format( _( "Import settings to %s from which follower?" ),
                                   follower.disp_name() );
    npc *other = choose_other_follower( follower, prompt );
    if( other == nullptr ) {
        return;
    }
    transfer_part part = transfer_part::all;
    if( !choose_transfer_part( part ) ) {
        return;
    }
    npc &source = exporting ? follower : *other;
    npc &destination = exporting ? *other : follower;
    copy_rule_part( source, destination, part );
    add_msg( m_info, _( "Follower rules copied from %1$s to %2$s." ), source.disp_name(),
             destination.disp_name() );
}

std::string boolean_state( const npc_follower_rules &rules, const boolean_rule_entry &entry )
{
    std::string state = rules.has_flag( entry.rule ) ? _( "Enabled" ) : _( "Disabled" );
    if( rules.has_override_enable( entry.rule ) ) {
        state += _( " (override)" );
    }
    return state;
}

std::string percent_state( int value )
{
    return string_format( _( "%d%%" ), value );
}

std::string engagement_state( combat_engagement rule )
{
    switch( rule ) {
        case combat_engagement::NONE:
            return _( "Do not engage" );
        case combat_engagement::CLOSE:
            return _( "Nearby enemies" );
        case combat_engagement::WEAK:
            return _( "Weak enemies" );
        case combat_engagement::HIT:
            return _( "Enemies you attack" );
        case combat_engagement::ALL:
            return _( "All enemies" );
        case combat_engagement::FREE_FIRE:
            return _( "Free fire, no movement" );
        case combat_engagement::NO_MOVE:
            return _( "No movement" );
    }
    return _( "Unknown" );
}

std::string aiming_state( aim_rule rule )
{
    switch( rule ) {
        case aim_rule::WHEN_CONVENIENT:
            return _( "When convenient" );
        case aim_rule::SPRAY:
            return _( "Fire quickly" );
        case aim_rule::PRECISE:
            return _( "Careful" );
        case aim_rule::STRICTLY_PRECISE:
            return _( "Strictly precise" );
    }
    return _( "Unknown" );
}

} // namespace

void show_follower_rules_ui( npc &follower )
{
    enum menu_action : int {
        reset_all = 1000,
        import_rules,
        export_rules,
        engagement,
        aiming,
        cbm_recharge,
        cbm_reserve,
        pickup_list
    };

    int selected = 0;
    bool done = false;
    while( !done ) {
        uilist menu;
        menu.title = string_format( _( "Rules for your follower, %s" ), follower.disp_name() );
        menu.text = _( "Select a behavior to change it.  Existing dialogue rule menus remain available." );
        menu.footer_text = _( "Enabled behavior rules are marked [x]." );
        menu.desc_enabled = true;
        menu.desc_lines_hint = 3;
        menu.selected = selected;

        menu.addentry_desc( reset_all, true, 'D', _( "Restore all defaults" ),
                            _( "Restore every behavior, combat, CBM, and pickup setting to its default." ) );
        menu.addentry_desc( import_rules, true, 'I', _( "Import settings from follower" ),
                            _( "Copy all or part of another follower's settings to this follower." ) );
        menu.addentry_desc( export_rules, true, 'E', _( "Export settings to follower" ),
                            _( "Copy all or part of this follower's settings to another follower." ) );

        for( size_t i = 0; i < boolean_rules.size(); ++i ) {
            const boolean_rule_entry &entry = boolean_rules[i];
            const bool enabled = follower.rules.has_flag( entry.rule );
            const std::string label = string_format( "%s %s", enabled ? "[x]" : "[ ]", _( entry.name ) );
            const std::string description = enabled ? _( entry.enabled_description ) :
                                            _( entry.disabled_description );
            menu.addentry_col( static_cast<int>( i ), true, MENU_AUTOASSIGN, label,
                               boolean_state( follower.rules, entry ), description );
        }

        menu.addentry_col( engagement, true, 'G', _( "Engagement rule" ),
                           engagement_state( follower.rules.engagement ),
                           _( "Choose when this follower may engage enemies." ) );
        menu.addentry_col( aiming, true, 'A', _( "Aiming rule" ),
                           aiming_state( follower.rules.aim ),
                           _( "Choose how carefully this follower aims ranged weapons." ) );
        if( !follower.get_bionics().empty() ) {
            menu.addentry_col( cbm_recharge, true, 'R', _( "CBM recharge threshold" ),
                               percent_state( static_cast<int>( follower.rules.cbm_recharge ) ),
                               _( "Choose when this follower consumes supplies to recharge CBM power." ) );
            menu.addentry_col( cbm_reserve, true, 'V', _( "CBM power reserve" ),
                               percent_state( static_cast<int>( follower.rules.cbm_reserve ) ),
                               _( "Choose how much CBM power is reserved for defense and utility." ) );
        }
        menu.addentry_desc( pickup_list, true, 'P', _( "Edit pickup list" ),
                            _( "Edit the item pickup list used when picking up items is enabled." ) );

        menu.query();
        selected = menu.selected;
        if( menu.ret < 0 ) {
            done = true;
        } else if( menu.ret >= 0 && static_cast<size_t>( menu.ret ) < boolean_rules.size() ) {
            const boolean_rule_entry &entry = boolean_rules[menu.ret];
            const bool was_enabled = follower.rules.has_flag( entry.rule );
            follower.rules.toggle_flag( entry.rule );
            follower.rules.toggle_specific_override_state( entry.rule, !was_enabled );
            follower.invalidate_range_cache();
            follower.wield_better_weapon();
        } else {
            switch( menu.ret ) {
                case reset_all:
                    if( query_yn( _( "Restore all follower rules for %s to their defaults?" ),
                                  follower.disp_name() ) ) {
                        follower.rules = npc_follower_rules();
                        follower.invalidate_range_cache();
                        follower.wield_better_weapon();
                    }
                    break;
                case import_rules:
                    transfer_rules( follower, false );
                    break;
                case export_rules:
                    transfer_rules( follower, true );
                    break;
                case engagement:
                    if( choose_engagement_rule( follower ) ) {
                        follower.invalidate_range_cache();
                        follower.wield_better_weapon();
                    }
                    break;
                case aiming:
                    if( choose_aim_rule( follower ) ) {
                        follower.invalidate_range_cache();
                    }
                    break;
                case cbm_recharge:
                    choose_cbm_recharge_rule( follower );
                    break;
                case cbm_reserve:
                    choose_cbm_reserve_rule( follower );
                    break;
                case pickup_list:
                    follower.rules.pickup_whitelist->show( follower.name );
                    break;
            }
        }
    }
}
