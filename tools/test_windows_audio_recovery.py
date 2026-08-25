import pathlib
import re
import shutil
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class WindowsAudioRecoveryContractTest(unittest.TestCase):
    def test_retry_policy_executes_bounded_sequences(self) -> None:
        compiler = shutil.which("c++") or shutil.which("g++") or shutil.which("clang++")
        self.assertIsNotNone(compiler, "a C++ compiler is required for the audio policy test")

        harness = r'''
#include "src/audio_retry_policy.h"
#include <cassert>
#include <vector>

int main() {
    std::vector<int> calls;
    bool result = audio_retry_policy::try_twice(
        [&]( int attempt ) { calls.push_back( attempt ); return attempt == 2; },
        [&]() { calls.push_back( 99 ); } );
    assert( result );
    assert( ( calls == std::vector<int>{ 1, 99, 2 } ) );

    calls.clear();
    result = audio_retry_policy::try_twice(
        [&]( int attempt ) { calls.push_back( attempt ); return true; },
        [&]() { calls.push_back( 99 ); } );
    assert( result );
    assert( ( calls == std::vector<int>{ 1 } ) );

    calls.clear();
    result = audio_retry_policy::initialize_temporary_backend(
        [&]() { calls.push_back( 1 ); return true; },
        [&]() { calls.push_back( 2 ); return false; },
        [&]() { calls.push_back( 3 ); } );
    assert( !result );
    assert( ( calls == std::vector<int>{ 1, 2, 3 } ) );

    calls.clear();
    result = audio_retry_policy::initialize_temporary_backend(
        [&]() { calls.push_back( 1 ); return false; },
        [&]() { calls.push_back( 2 ); return true; },
        [&]() { calls.push_back( 3 ); } );
    assert( !result );
    assert( ( calls == std::vector<int>{ 1, 2 } ) );

    calls.clear();
    result = audio_retry_policy::initialize_temporary_backend(
        [&]() { calls.push_back( 1 ); return true; },
        [&]() { calls.push_back( 2 ); return true; },
        [&]() { calls.push_back( 3 ); } );
    assert( result );
    assert( ( calls == std::vector<int>{ 1, 2 } ) );
}
'''
        with tempfile.TemporaryDirectory() as temp_dir:
            source = pathlib.Path(temp_dir) / "audio_retry_policy_test.cpp"
            binary = pathlib.Path(temp_dir) / "audio_retry_policy_test"
            source.write_text(harness, encoding="utf-8")
            subprocess.run(
                [compiler, "-std=c++17", "-I", str(ROOT), str(source), "-o", str(binary)],
                check=True,
            )
            subprocess.run([str(binary)], check=True)

    def test_audio_init_has_bounded_retry_and_windows_fallback(self) -> None:
        source = (ROOT / "src" / "sdlsound.cpp").read_text(encoding="utf-8")

        self.assertIn("open_audio_mixer_with_retry", source)
        self.assertIn("initialize_audio_subsystem_with_retry", source)
        self.assertIn("SDL_Delay( audio_retry_delay_ms )", source)
        self.assertIn("SDL_InitSubSystem( SDL_INIT_AUDIO )", source)
        self.assertIn("SDL_QuitSubSystem( SDL_INIT_AUDIO )", source)
        self.assertIn('constexpr const char *audio_driver_environment = "SDL_AUDIODRIVER"', source)
        self.assertIn('SDL_setenv( audio_driver_environment, "directsound", 1 )', source)
        self.assertIn('had_previous_driver ? previous_driver.c_str() : ""', source)
        self.assertIn("restored_driver == nullptr", source)
        self.assertIn("!environment_restored", source)
        self.assertIn("audio_retry_policy::initialize_temporary_backend", source)
        self.assertIn("disabling sound for this session", source)
        self.assertIn("initialize_directsound_with_retry()", source)
        self.assertIn("SDL_getenv( audio_driver_environment )", source)
        self.assertIn("SDL_GetCurrentAudioDriver()", source)
        self.assertIn("SDL_GetAudioDeviceName( i, 0 )", source)
        self.assertIn('current_audio_driver() != "directsound"', source)

        fallback = source[source.index("bool initialize_directsound_with_retry()") :
                          source.index("void configure_audio_channels()")]
        self.assertLess(fallback.index("SDL_setenv"),
                        fallback.index("initialize_audio_subsystem_with_retry"))
        self.assertLess(fallback.index("initialize_audio_subsystem_with_retry"),
                        fallback.index("environment_restored"))

        shutdown = source[source.index("void shutdown_sound()") : source.index("static void musicFinished()")]
        self.assertIn("quit_audio_subsystem();", shutdown)

    def test_soundpack_load_requires_initialized_mixer(self) -> None:
        source = (ROOT / "src" / "sdltiles.cpp").read_text(encoding="utf-8")

        self.assertRegex(
            source,
            re.compile(
                r"if\( is_sound_initialized\(\) \)\s*\{\s*load_soundset\(\);\s*\}",
                re.MULTILINE,
            ),
        )

    def test_sdl_startup_does_not_make_audio_fatal(self) -> None:
        source = (ROOT / "src" / "sdltiles.cpp").read_text(encoding="utf-8")

        init_sdl = source[source.index("static void InitSDL()") : source.index("static bool SetupRenderTarget()")]
        self.assertIn("SDL_INIT_VIDEO | SDL_INIT_TIMER", init_sdl)
        self.assertNotIn("SDL_INIT_AUDIO", init_sdl)


if __name__ == "__main__":
    unittest.main()
