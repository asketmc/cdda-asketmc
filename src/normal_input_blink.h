#pragma once
#ifndef CATA_SRC_NORMAL_INPUT_BLINK_H
#define CATA_SRC_NORMAL_INPUT_BLINK_H

#include <chrono>

#include "game_constants.h"

// BLINK_SPEED is a compile-time 0.G constant, not a configurable option.
inline bool normal_input_blink_timeout_elapsed( const std::chrono::milliseconds elapsed )
{
    return elapsed.count() > BLINK_SPEED;
}

#endif // CATA_SRC_NORMAL_INPUT_BLINK_H
