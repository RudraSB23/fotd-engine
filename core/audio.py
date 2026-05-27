# core/audio.py

import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

import pygame.mixer as _mixer

__all__ = [
    "init_audio",
    "quit_audio",
    "play_bgm",
    "stop_bgm",
    "pause_bgm",
    "resume_bgm",
    "set_bgm_volume",
    "is_bgm_playing",
    "play_sfx",
    "stop_sfx",
    "stop_all_sfx",
    "preload_sfx",
    "async_play_bgm",
    "async_play_sfx",
]

_ROOT = Path(__file__).parent.parent
AUDIO_DIR = _ROOT / "assets" / "audio"

SFX_CHANNELS = 8

_initialized = False
_sfx_cache: dict[str, _mixer.Sound] = {}
_cache_lock = threading.Lock()

_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="audio-io")


def init_audio(frequency: int = 44100, channels: int = 2, buffer: int = 512) -> None:
    """Initialize the pygame mixer. Safe to call multiple times."""
    global _initialized
    if _initialized:
        return
    _mixer.pre_init(frequency=frequency, channels=channels, buffer=buffer)
    _mixer.init()
    _mixer.set_num_channels(SFX_CHANNELS)
    _initialized = True


def quit_audio() -> None:
    """Cleanly shut down the mixer. Call on app exit."""
    global _initialized
    if _initialized:
        _mixer.quit()
        _initialized = False


# ---------------------------------------------------------------------------
# BGM — streaming music (one track at a time)
# ---------------------------------------------------------------------------


def play_bgm(
    filename: str, loops: int = -1, volume: float = 0.7, fade_ms: int = 0
) -> None:
    """
    Load and play a BGM track from assets/audio/.
    loops=-1 loops forever. Fails silently if file is missing.
    """
    path = AUDIO_DIR / filename
    try:
        _mixer.music.load(str(path))
        _mixer.music.set_volume(max(0.0, min(1.0, volume)))
        _mixer.music.play(loops=loops, fade_ms=fade_ms)
    except Exception as e:
        print(f"[audio] play_bgm failed for '{filename}': {e}")


def stop_bgm(fade_ms: int = 0) -> None:
    if fade_ms > 0:
        _mixer.music.fadeout(fade_ms)
    else:
        _mixer.music.stop()


def pause_bgm() -> None:
    _mixer.music.pause()


def resume_bgm() -> None:
    _mixer.music.unpause()


def set_bgm_volume(volume: float) -> None:
    _mixer.music.set_volume(max(0.0, min(1.0, volume)))


def is_bgm_playing() -> int:
    return _mixer.music.get_busy()  # fix #8: already int-truthy, no bool() needed


# ---------------------------------------------------------------------------
# SFX — short sound effects (multiple simultaneous channels)
# ---------------------------------------------------------------------------


def _load_sfx(filename: str) -> Optional[_mixer.Sound]:
    """Load and cache a Sound object. Thread-safe. Returns None on failure."""
    with _cache_lock:  # fix #4
        if filename in _sfx_cache:
            return _sfx_cache[filename]
        path = AUDIO_DIR / filename
        try:
            sound = _mixer.Sound(str(path))
            _sfx_cache[filename] = sound
            return sound
        except Exception as e:
            print(f"[audio] _load_sfx failed for '{filename}': {e}")
            return None


def play_sfx(filename: str, volume: float = 1.0, channel: Optional[int] = None) -> None:
    """
    Play a sound effect. Cached after first load.
    Note: pygame.mixer.Sound.play() is non-blocking at the C level — no thread needed.
    Optionally pin to a specific channel index (0 to SFX_CHANNELS-1).
    """
    sound = _load_sfx(filename)
    if sound is None:
        return
    sound.set_volume(max(0.0, min(1.0, volume)))
    if channel is not None:
        _mixer.Channel(channel).play(sound)  # fix #5: play() is already non-blocking
    else:
        sound.play()


def stop_sfx(filename: str) -> None:
    """
    Stop all channels currently playing this specific sound.
    Note: stops every simultaneous instance of this sound, not just one.
    See stop_all_sfx() to stop everything at once.
    """  # fix #6: clarified docstring
    with _cache_lock:
        sound = _sfx_cache.get(filename)
    if sound is not None:
        sound.stop()


def stop_all_sfx() -> None:
    """Stop every SFX channel immediately."""  # fix #6: new function
    for i in range(SFX_CHANNELS):
        _mixer.Channel(i).stop()


def preload_sfx(*filenames: str) -> None:
    """Pre-load SFX files into cache at startup to avoid first-play latency."""
    for f in filenames:
        _load_sfx(f)


# ---------------------------------------------------------------------------
# Async helpers — executor only wraps disk I/O (load), not play()
# ---------------------------------------------------------------------------


async def async_play_bgm(filename: str, **kwargs) -> None:
    """Non-blocking BGM for Textual async contexts. Executor wraps only the load I/O."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(_executor, lambda: play_bgm(filename, **kwargs))


async def async_play_sfx(filename: str, **kwargs) -> None:
    """Non-blocking SFX for Textual async contexts. Loads on executor, plays on main thread."""
    loop = asyncio.get_event_loop()
    sound = await loop.run_in_executor(_executor, lambda: _load_sfx(filename))
    if sound is None:
        return
    volume = kwargs.get("volume", 1.0)
    channel = kwargs.get("channel")
    sound.set_volume(max(0.0, min(1.0, volume)))
    if channel is not None:
        _mixer.Channel(channel).play(sound)
    else:
        sound.play()
