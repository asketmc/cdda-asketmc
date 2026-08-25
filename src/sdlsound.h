#pragma once
#ifndef CATA_SRC_SDLSOUND_H
#define CATA_SRC_SDLSOUND_H

#include <string>
#if defined(SDL_SOUND)

/**
 * Attempt to initialize an audio device.  Returns false if initialization fails.
 */
bool init_sound();
bool is_sound_initialized();
void shutdown_sound();
void play_music( const std::string &playlist );
void stop_music();
void update_music_volume();
void load_soundset();

#else

inline bool init_sound()
{
    return false;
}
inline bool is_sound_initialized()
{
    return false;
}
inline void shutdown_sound() { }
inline void play_music( const std::string &/*playlist*/ )
{
}
inline void update_music_volume() { }
inline void load_soundset() { }

#endif

#endif // CATA_SRC_SDLSOUND_H
