import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class WindowsAudioRecoveryContractTest(unittest.TestCase):
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
        self.assertIn("initialize_directsound_with_retry()", source)
        self.assertIn("SDL_getenv( audio_driver_environment )", source)
        self.assertIn("SDL_GetCurrentAudioDriver()", source)
        self.assertIn("SDL_GetAudioDeviceName( i, 0 )", source)
        self.assertIn('current_audio_driver() != "directsound"', source)

        fallback = source[source.index("bool initialize_directsound_with_retry()") :
                          source.index("void configure_audio_channels()")]
        self.assertLess(fallback.index("SDL_setenv"),
                        fallback.index("initialize_audio_subsystem_with_retry"))

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
