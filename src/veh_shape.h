#pragma once
#ifndef CATA_SRC_VEH_SHAPE_H
#define CATA_SRC_VEH_SHAPE_H

#include <functional>
#include <set>
#include <string>
#include <vector>

#include "input.h"
#include "optional.h"
#include "ret_val.h"
#include "vehicle.h"

class player_activity;

class veh_shape
{
    public:
        explicit veh_shape( vehicle &vehicle );

        /** Start the visual vehicle shape editor at the given map position. */
        player_activity start( const tripoint &pos );

    private:
        input_context ctxt;
        vehicle &veh;

        std::set<tripoint> cursor_allowed;
        tripoint cursor_pos;

        tripoint get_cursor_pos() const;
        bool set_cursor_pos( const tripoint &new_pos );
        bool handle_cursor_movement( const std::string &action );
        std::vector<vpart_reference> parts_under_cursor() const;
        void init_input();

        cata::optional<vpart_reference> select_part_at_cursor(
            const std::string &title, const std::string &extra_description,
            const std::function<ret_val<void>( const vpart_reference & )> &predicate,
            const cata::optional<vpart_reference> &preselect ) const;

        void change_part_shape( vpart_reference vpr ) const;
};

#endif // CATA_SRC_VEH_SHAPE_H
