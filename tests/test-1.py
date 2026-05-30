import asyncio
import dataclasses
import json
import os
import sys
import tempfile
import types
import unittest.mock as mock
from pathlib import Path
from typing import ClassVar

import pytest

# ---------------------------------------------------------------------------
# Make the repo root importable regardless of where pytest is called from.
# ---------------------------------------------------------------------------
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# ---------------------------------------------------------------------------
# Stub out pygame.mixer BEFORE any engine import touches it.
# ---------------------------------------------------------------------------
pygame_stub = types.ModuleType("pygame")
mixer_stub = types.ModuleType("pygame.mixer")


class _FakeSound:
    def __init__(self, path):
        self._volume = 1.0

    def set_volume(self, v):
        self._volume = v

    def play(self, *a, **kw):
        pass

    def stop(self):
        pass


class _FakeMusic:
    _volume = 0.7
    _busy = False

    def load(self, path):
        pass

    def play(self, loops=-1, fade_ms=0):
        _FakeMusic._busy = True

    def stop(self):
        _FakeMusic._busy = False

    def fadeout(self, ms):
        _FakeMusic._busy = False

    def pause(self):
        pass

    def unpause(self):
        pass

    def set_volume(self, v):
        _FakeMusic._volume = v

    def get_volume(self):
        return _FakeMusic._volume

    def get_busy(self):
        return int(_FakeMusic._busy)


class _FakeChannel:
    def __init__(self, i):
        pass

    def play(self, sound):
        pass

    def stop(self):
        pass


mixer_stub.Sound = _FakeSound
mixer_stub.music = _FakeMusic()
mixer_stub.Channel = _FakeChannel
mixer_stub.pre_init = mock.MagicMock()
mixer_stub.init = mock.MagicMock()
mixer_stub.quit = mock.MagicMock()
mixer_stub.set_num_channels = mock.MagicMock()

pygame_stub.mixer = mixer_stub
sys.modules["pygame"] = pygame_stub
sys.modules["pygame.mixer"] = mixer_stub

# ---------------------------------------------------------------------------
# Now import engine modules
# ---------------------------------------------------------------------------
from core.ascii import ASCII_SNIPPETS, ASSETS_DIR, load_ascii, load_ascii_snippet
from core.audio import (
    _sfx_cache,
    async_play_bgm,
    async_play_sfx,
    init_audio,
    is_bgm_playing,
    pause_bgm,
    play_bgm,
    play_sfx,
    preload_sfx,
    quit_audio,
    resume_bgm,
    set_bgm_volume,
    stop_all_sfx,
    stop_bgm,
    stop_sfx,
)
from core.gamestate import GameState
from core.input import InputManager, get_input_manager, init_input_manager
from core.scene import Scene, Tick
from core.styles_handler import load_styles
from ui.dialogue import (
    PAUSE_ESCAPE,
    PUNCTUATION_PAUSES,
    ChoiceMenu,
    DialogueBox,
    DialogueLine,
    MessageBox,
)
from ui.messages import (
    ActionTriggered,
    BGMRequested,
    BGMStopped,
    ChoiceCancelled,
    ChoiceSelected,
    DialogueFinished,
    GameOver,
    GameStarted,
    LogoFinished,
    MessageBoxDismissed,
    SceneBack,
    SceneChanged,
    SceneTransition,
    ScreenPopped,
    StateSaved,
)

pytestmark = pytest.mark.asyncio


# ===========================================================================
# 1. GameState
# ===========================================================================


class TestGameStateBasic:
    """GameState — dataclass base, ClassVar save_path."""

    def setup_method(self):
        self.tmp = tempfile.TemporaryDirectory()
        _save_path = Path(self.tmp.name) / "saves" / "test.json"

        @dataclasses.dataclass
        class _State(GameState):
            health: int = 100
            name: str = "hero"
            flags: dict = dataclasses.field(default_factory=dict)

        _State.save_path = _save_path

        self.State = _State

    def teardown_method(self):
        self.tmp.cleanup()

    # --- save / load ---

    def test_save_creates_file(self):
        s = self.State()
        s.save()
        assert self.State.save_path.is_file()

    def test_save_creates_parent_dirs(self):
        s = self.State()
        s.save()
        assert self.State.save_path.parent.is_dir()

    def test_save_json_content(self):
        s = self.State(health=42, name="ryu")
        s.save()
        data = json.loads(self.State.save_path.read_text())
        assert data["health"] == 42
        assert data["name"] == "ryu"

    def test_load_roundtrip(self):
        s = self.State(health=77, name="ken")
        s.save()
        s2 = self.State.load()
        assert s2.health == 77
        assert s2.name == "ken"

    def test_load_missing_returns_default(self):
        s = self.State.load()
        assert s.health == 100
        assert s.name == "hero"

    def test_load_corrupt_json_returns_default(self):
        self.State.save_path.parent.mkdir(parents=True, exist_ok=True)
        self.State.save_path.write_text("NOT_JSON")
        s = self.State.load()
        assert s.health == 100

    def test_load_wrong_keys_returns_default(self):
        self.State.save_path.parent.mkdir(parents=True, exist_ok=True)
        self.State.save_path.write_text(json.dumps({"unknown_key": 999}))
        s = self.State.load()
        assert s.health == 100

    def test_load_partial_keys_uses_defaults(self):
        """Missing keys fall back to dataclass defaults."""
        self.State.save_path.parent.mkdir(parents=True, exist_ok=True)
        self.State.save_path.write_text(json.dumps({"health": 50}))
        s = self.State.load()
        assert s.health == 50
        assert s.name == "hero"
        assert s.flags == {}

    # --- reset ---

    def test_reset_restores_scalar_defaults(self):
        s = self.State(health=1, name="changed")
        s.reset()
        assert s.health == 100
        assert s.name == "hero"

    def test_reset_restores_factory_defaults(self):
        s = self.State(flags={"visited": True})
        s.reset()
        assert s.flags == {}

    def test_reset_returns_none(self):
        s = self.State()
        assert s.reset() is None

    # --- exists ---

    def test_exists_false_before_save(self):
        s = self.State()
        assert s.exists() is False

    def test_exists_true_after_save(self):
        s = self.State()
        s.save()
        assert s.exists() is True

    # --- misc ---

    def test_subclass_save_path_independent(self):
        tmp2 = tempfile.TemporaryDirectory()
        p2 = Path(tmp2.name) / "other.json"

        @dataclasses.dataclass
        class _Other(GameState):
            level: int = 1

        _Other.save_path = p2

        self.State(health=5).save()
        _Other(level=99).save()
        assert self.State.save_path != _Other.save_path
        assert json.loads(_Other.save_path.read_text())["level"] == 99
        tmp2.cleanup()

    def test_json_sorted_keys(self):
        self.State().save()
        raw = self.State.save_path.read_text()
        keys = list(json.loads(raw).keys())
        assert keys == sorted(keys)

    def test_unicode_name_roundtrip(self):
        self.State(name="勇者").save()
        assert self.State.load().name == "勇者"


# ===========================================================================
# 2. InputManager
# ===========================================================================


class TestInputManager:
    """InputManager — bindings CRUD, key map, singleton."""

    def setup_method(self):
        self.im = InputManager()
        self.im.load_defaults()

    # --- defaults ---

    def test_default_confirm(self):
        assert "enter" in self.im.get_keys("confirm")

    def test_default_cancel(self):
        assert "escape" in self.im.get_keys("cancel")

    def test_default_move_up_has_two_keys(self):
        keys = self.im.get_keys("move_up")
        assert "up" in keys and "w" in keys

    def test_default_move_down(self):
        keys = self.im.get_keys("move_down")
        assert "down" in keys and "s" in keys

    def test_default_move_left(self):
        keys = self.im.get_keys("move_left")
        assert "left" in keys and "a" in keys

    def test_default_move_right(self):
        keys = self.im.get_keys("move_right")
        assert "right" in keys and "d" in keys

    # --- bind ---

    def test_bind_replaces_keys(self):
        self.im.bind("confirm", "space", "enter")
        assert self.im.get_keys("confirm") == ["space", "enter"]

    def test_bind_new_action(self):
        self.im.bind("dash", "shift")
        assert self.im.get_keys("dash") == ["shift"]

    def test_bind_updates_key_map(self):
        self.im.bind("confirm", "z")
        assert self.im.get_action("z") == "confirm"
        assert self.im.get_action("enter") != "confirm"

    # --- unbind ---

    def test_unbind_removes_action(self):
        self.im.unbind("confirm")
        assert self.im.get_keys("confirm") == []

    def test_unbind_removes_from_key_map(self):
        self.im.unbind("confirm")
        assert self.im.get_action("enter") is None

    def test_unbind_unknown_action_no_exception(self):
        self.im.unbind("nonexistent_action")  # prints warning, must not raise

    # --- get_action ---

    def test_get_action_known_key(self):
        assert self.im.get_action("enter") == "confirm"

    def test_get_action_unknown_key_returns_none(self):
        assert self.im.get_action("f12") is None

    # --- get_keys ---

    def test_get_keys_unknown_action_returns_empty(self):
        assert self.im.get_keys("fly") == []

    def test_get_keys_returns_copy(self):
        keys = self.im.get_keys("confirm")
        keys.append("MUTATED")
        assert "MUTATED" not in self.im.get_keys("confirm")

    # --- is_bound ---

    def test_is_bound_true_for_defaults(self):
        assert self.im.is_bound("confirm") is True

    def test_is_bound_false_for_unknown(self):
        assert self.im.is_bound("teleport") is False

    def test_is_bound_false_after_unbind(self):
        self.im.unbind("confirm")
        assert self.im.is_bound("confirm") is False

    # --- to_textual_bindings ---

    def test_to_textual_bindings_format(self):
        bindings = self.im.to_textual_bindings("confirm")
        assert len(bindings) == 1
        key, action, description = bindings[0]
        assert key == "enter"
        assert action == "confirm"
        assert description == "Confirm"

    def test_to_textual_bindings_multi_key(self):
        assert len(self.im.to_textual_bindings("move_up")) == 2

    def test_to_textual_bindings_unknown_action_returns_empty(self):
        assert self.im.to_textual_bindings("fly") == []

    def test_to_textual_bindings_underscore_replaced_in_description(self):
        bindings = self.im.to_textual_bindings("move_up")
        assert bindings[0][2] == "Move Up"

    # --- singleton ---

    def test_init_input_manager_returns_instance(self):
        import core.input as _ci

        _ci._manager = None
        assert isinstance(init_input_manager(), InputManager)

    def test_init_input_manager_idempotent(self):
        import core.input as _ci

        _ci._manager = None
        m1 = init_input_manager()
        m2 = init_input_manager()
        assert m1 is m2

    def test_get_input_manager_returns_none_before_init(self):
        import core.input as _ci

        _ci._manager = None
        assert get_input_manager() is None

    def test_get_input_manager_after_init(self):
        import core.input as _ci

        _ci._manager = None
        init_input_manager()
        assert get_input_manager() is not None


# ===========================================================================
# 3. Audio
# ===========================================================================


class TestAudio:
    """Audio — init/quit, BGM, SFX, cache, async helpers."""

    def setup_method(self):
        import core.audio as _ca

        _ca._initialized = False
        _ca._sfx_cache.clear()
        _FakeMusic._busy = False

    def teardown_method(self):
        import core.audio as _ca

        _ca._initialized = False
        _ca._sfx_cache.clear()
        mixer_stub.init.reset_mock()
        mixer_stub.quit.reset_mock()

    # --- init / quit ---

    def test_init_calls_mixer_init(self):
        init_audio()
        mixer_stub.init.assert_called_once()

    def test_init_idempotent(self):
        init_audio()
        init_audio()
        assert mixer_stub.init.call_count == 1

    def test_quit_calls_mixer_quit(self):
        init_audio()
        quit_audio()
        mixer_stub.quit.assert_called_once()

    def test_quit_resets_initialized_flag(self):
        import core.audio as _ca

        init_audio()
        quit_audio()
        assert _ca._initialized is False

    def test_quit_without_init_no_exception(self):
        quit_audio()

    # --- BGM ---

    def test_play_bgm_missing_file_no_exception(self):
        init_audio()
        play_bgm("nonexistent_track.mp3")

    def test_play_bgm_sets_busy(self):
        init_audio()
        play_bgm("track.mp3")
        assert _FakeMusic._busy is True

    def test_stop_bgm_clears_busy(self):
        init_audio()
        play_bgm("track.mp3")
        stop_bgm()
        assert _FakeMusic._busy is False

    def test_pause_resume_no_exception(self):
        init_audio()
        pause_bgm()
        resume_bgm()

    def test_set_bgm_volume_clamped_high(self):
        init_audio()
        set_bgm_volume(5.0)
        assert mixer_stub.music.get_volume() <= 1.0

    def test_set_bgm_volume_clamped_low(self):
        init_audio()
        set_bgm_volume(-1.0)
        assert mixer_stub.music.get_volume() >= 0.0

    def test_is_bgm_playing_returns_int(self):
        init_audio()
        assert isinstance(is_bgm_playing(), int)

    def test_is_bgm_playing_false_initially(self):
        init_audio()
        assert is_bgm_playing() == 0

    def test_stop_bgm_fade_calls_fadeout(self):
        init_audio()
        play_bgm("track.mp3")
        stop_bgm(fade_ms=500)
        assert _FakeMusic._busy is False

    # --- SFX ---

    def test_play_sfx_missing_file_no_exception(self):
        init_audio()
        play_sfx("ghost.mp3")

    def test_play_sfx_routes_through_load(self):
        init_audio()
        with mock.patch("core.audio._load_sfx", return_value=_FakeSound("x")) as m:
            play_sfx("boom.mp3")
            m.assert_called_once_with("boom.mp3")

    def test_preload_sfx_populates_cache(self):
        import core.audio as _ca

        with tempfile.TemporaryDirectory() as td:
            fake_file = Path(td) / "click.mp3"
            fake_file.write_bytes(b"FAKE")
            _ca.AUDIO_DIR = Path(td)
            init_audio()
            with mock.patch("pygame.mixer.Sound", return_value=_FakeSound("x")):
                preload_sfx("click.mp3")
            assert "click.mp3" in _ca._sfx_cache

    def test_stop_sfx_no_exception_if_not_loaded(self):
        init_audio()
        stop_sfx("not_loaded.mp3")

    def test_stop_all_sfx_no_exception(self):
        init_audio()
        stop_all_sfx()

    def test_stop_sfx_calls_stop_on_sound(self):
        import core.audio as _ca

        fake = _FakeSound("x")
        _ca._sfx_cache["hit.mp3"] = fake
        with mock.patch.object(fake, "stop") as m:
            stop_sfx("hit.mp3")
            m.assert_called_once()

    # --- async helpers ---

    async def test_async_play_bgm_no_exception(self):
        init_audio()
        await async_play_bgm("missing.mp3")

    async def test_async_play_sfx_no_exception(self):
        init_audio()
        await async_play_sfx("missing.mp3")

    async def test_async_play_sfx_plays_when_loaded(self):
        fake = _FakeSound("x")
        with mock.patch("core.audio._load_sfx", return_value=fake):
            with mock.patch.object(fake, "play") as m:
                init_audio()
                await async_play_sfx("loaded.mp3")
                m.assert_called_once()


# ===========================================================================
# 4. ASCII loader
# ===========================================================================


class TestAscii:
    def test_load_ascii_missing_returns_empty_string(self):
        assert load_ascii("definitely_not_a_file.txt") == ""

    def test_load_ascii_reads_file(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "art.txt").write_text("hello art", encoding="utf-8")
            import core.ascii as _ca

            orig = _ca.ASSETS_DIR
            _ca.ASSETS_DIR = Path(td)
            result = load_ascii("art.txt")
            _ca.ASSETS_DIR = orig
        assert result == "hello art"

    def test_load_ascii_unicode(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "jp.txt").write_text("日本語アート", encoding="utf-8")
            import core.ascii as _ca

            orig = _ca.ASSETS_DIR
            _ca.ASSETS_DIR = Path(td)
            result = load_ascii("jp.txt")
            _ca.ASSETS_DIR = orig
        assert result == "日本語アート"

    def test_load_ascii_snippet_known(self):
        import core.ascii as _ca

        _ca.ASCII_SNIPPETS["test_key"] = ">>>snippet<<<"
        result = load_ascii_snippet("test_key")
        del _ca.ASCII_SNIPPETS["test_key"]
        assert result == ">>>snippet<<<"

    def test_load_ascii_snippet_unknown_returns_empty(self):
        assert load_ascii_snippet("does_not_exist") == ""


# ===========================================================================
# 5. Styles handler
# ===========================================================================


class TestStylesHandler:
    def test_returns_list(self):
        assert isinstance(load_styles(), list)

    def test_only_tcss_files(self):
        for p in load_styles():
            assert p.endswith(".tcss"), f"Non-.tcss file returned: {p}"

    def test_returns_absolute_paths(self):
        for p in load_styles():
            assert os.path.isabs(p), f"Expected absolute path, got: {p}"

    def test_no_duplicate_paths(self):
        result = load_styles()
        assert len(result) == len(set(result))


# ===========================================================================
# 6. Scene & Tick
# ===========================================================================


class TestSceneAndTick:
    def test_tick_stores_dt(self):
        t = Tick(0.016)
        assert t.dt == pytest.approx(0.016)

    def test_tick_is_message(self):
        from textual.message import Message

        assert isinstance(Tick(0.0), Message)

    def test_tick_dt_zero_allowed(self):
        assert Tick(0.0).dt == 0.0

    def test_scene_is_screen_subclass(self):
        from textual.screen import Screen

        assert issubclass(Scene, Screen)

    def test_scene_instantiable(self):
        assert Scene() is not None


# ===========================================================================
# 7. UI Messages
# ===========================================================================


class TestMessages:
    def test_logo_finished(self):
        from textual.message import Message

        assert isinstance(LogoFinished(), Message)

    def test_bgm_requested_fields(self):
        m = BGMRequested("theme.mp3", fade_ms=500)
        assert m.filename == "theme.mp3" and m.fade_ms == 500

    def test_bgm_requested_default_fade(self):
        assert BGMRequested("theme.mp3").fade_ms == 1000

    def test_bgm_stopped(self):
        assert BGMStopped() is not None

    def test_scene_transition(self):
        assert SceneTransition("battle").scene_id == "battle"

    def test_screen_popped(self):
        assert ScreenPopped() is not None

    def test_game_started(self):
        assert GameStarted() is not None

    def test_game_over_default_reason(self):
        assert GameOver().reason == ""

    def test_game_over_custom_reason(self):
        assert GameOver("fell into void").reason == "fell into void"

    def test_scene_changed(self):
        assert SceneChanged("world_map").scene_id == "world_map"

    def test_scene_back(self):
        assert SceneBack() is not None

    def test_action_triggered(self):
        m = ActionTriggered("confirm", "enter")
        assert m.action == "confirm" and m.key == "enter"

    def test_state_saved(self):
        assert StateSaved(2).slot == 2

    def test_dialogue_finished(self):
        assert DialogueFinished() is not None

    def test_choice_selected(self):
        m = ChoiceSelected(1, "Attack")
        assert m.index == 1 and m.text == "Attack"

    def test_choice_cancelled(self):
        assert ChoiceCancelled() is not None

    def test_message_box_dismissed(self):
        assert MessageBoxDismissed() is not None


# ===========================================================================
# 8. DialogueLine
# ===========================================================================


class TestDialogueLine:
    def test_text_field(self):
        assert DialogueLine(text="Hello.").text == "Hello."

    def test_default_speaker_empty(self):
        assert DialogueLine(text="Hi").speaker == ""

    def test_default_color(self):
        assert DialogueLine(text="Hi").color == "white"

    def test_default_typing_speed(self):
        assert DialogueLine(text="Hi").typing_speed == pytest.approx(0.04)

    def test_default_pause_scale(self):
        assert DialogueLine(text="Hi").pause_scale == pytest.approx(1.0)

    def test_custom_fields(self):
        line = DialogueLine(
            "Ready?",
            speaker="Narrator",
            color="cyan",
            typing_speed=0.02,
            pause_scale=0.5,
        )
        assert line.speaker == "Narrator"
        assert line.color == "cyan"
        assert line.typing_speed == pytest.approx(0.02)
        assert line.pause_scale == pytest.approx(0.5)


# ===========================================================================
# 9. PUNCTUATION_PAUSES & PAUSE_ESCAPE constants
# ===========================================================================


class TestDialogueConstants:
    def test_comma_pause(self):
        assert PUNCTUATION_PAUSES[","] == pytest.approx(0.25)

    def test_period_pause(self):
        assert PUNCTUATION_PAUSES["."] == pytest.approx(0.5)

    def test_ellipsis_pause(self):
        assert PUNCTUATION_PAUSES["…"] == pytest.approx(0.8)

    def test_exclamation(self):
        assert PUNCTUATION_PAUSES["!"] == pytest.approx(0.5)

    def test_question(self):
        assert PUNCTUATION_PAUSES["?"] == pytest.approx(0.5)

    def test_semicolon(self):
        assert PUNCTUATION_PAUSES[";"] == pytest.approx(0.25)

    def test_colon(self):
        assert PUNCTUATION_PAUSES[":"] == pytest.approx(0.25)

    def test_pause_escape_is_backslash(self):
        assert PAUSE_ESCAPE == "\\"


# ===========================================================================
# 10. DialogueBox — async play() logic (no Textual app required)
# ===========================================================================


class TestDialogueBoxPlay:
    """Patches query_one and asyncio.sleep — tests play() logic in isolation."""

    def _make_box(self, lines):
        box = DialogueBox.__new__(DialogueBox)
        box._lines = lines
        box._skip_key = "enter"
        box._skip_requested = False
        box._speaker_updates = []
        box._text_updates = []

        class _FakeStatic:
            def __init__(self, lst):
                self._lst = lst

            def update(self, v):
                self._lst.append(v)

        speaker_w = _FakeStatic(box._speaker_updates)
        text_w = _FakeStatic(box._text_updates)

        def fake_query_one(selector, klass=None):
            return speaker_w if "speaker" in selector else text_w

        box.query_one = fake_query_one
        box._messages = []
        box.post_message = lambda m: box._messages.append(m)
        return box

    async def test_play_posts_dialogue_finished(self):
        box = self._make_box([DialogueLine("Hi")])
        with mock.patch("asyncio.sleep", new=mock.AsyncMock()):
            await box.play()
        assert any(isinstance(m, DialogueFinished) for m in box._messages)

    async def test_play_updates_speaker(self):
        box = self._make_box([DialogueLine("Hello", speaker="Alice")])
        with mock.patch("asyncio.sleep", new=mock.AsyncMock()):
            await box.play()
        assert "Alice" in box._speaker_updates

    async def test_play_reveals_full_text(self):
        box = self._make_box([DialogueLine("Hi!")])
        with mock.patch("asyncio.sleep", new=mock.AsyncMock()):
            await box.play()
        # second-to-last update is the fully revealed line; last is the 0.2s end pause
        assert "Hi!" in box._text_updates

    async def test_play_multiple_lines(self):
        lines = [DialogueLine("Line one"), DialogueLine("Line two")]
        box = self._make_box(lines)
        with mock.patch("asyncio.sleep", new=mock.AsyncMock()):
            await box.play()
        assert "Line one" in box._text_updates
        assert "Line two" in box._text_updates

    async def test_play_skip_reveals_full_line_immediately(self):
        box = self._make_box([DialogueLine("A" * 50)])
        call_count = 0

        async def fake_sleep(t):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                box._skip_requested = True

        with mock.patch("asyncio.sleep", new=fake_sleep):
            await box.play()
        assert "A" * 50 in box._text_updates

    async def test_pause_escape_suppresses_punctuation_pause(self):
        """\\. should render as '.' without triggering the 0.5s period pause."""
        box = self._make_box([DialogueLine(r"hello\. world")])
        sleep_times = []

        async def fake_sleep(t):
            sleep_times.append(t)

        with mock.patch("asyncio.sleep", new=fake_sleep):
            await box.play()
        assert 0.5 not in sleep_times

    async def test_pause_scale_multiplies_pauses(self):
        box = self._make_box([DialogueLine("Hi.", pause_scale=2.0)])
        sleep_times = []

        async def fake_sleep(t):
            sleep_times.append(t)

        with mock.patch("asyncio.sleep", new=fake_sleep):
            await box.play()
        assert 1.0 in sleep_times  # 0.5 * 2.0

    async def test_empty_lines_list_posts_finished(self):
        box = self._make_box([])
        with mock.patch("asyncio.sleep", new=mock.AsyncMock()):
            await box.play()
        assert any(isinstance(m, DialogueFinished) for m in box._messages)


# ===========================================================================
# 11. ChoiceMenu — key navigation logic
# ===========================================================================


class TestChoiceMenu:
    def _make_menu(self, choices):
        m = ChoiceMenu.__new__(ChoiceMenu)
        m._prompt = "Choose:"
        m._choices = choices
        m._selected = 0
        m._messages = []
        m.post_message = lambda msg: m._messages.append(msg)

        class _FW:
            def __init__(self):
                self._classes = set()

            def add_class(self, c):
                self._classes.add(c)

            def remove_class(self, c):
                self._classes.discard(c)

        m._items = [_FW() for _ in choices]
        m.query = lambda sel: m._items
        return m

    def test_initial_selection_zero(self):
        assert self._make_menu(["A", "B", "C"])._selected == 0

    def test_key_down_increments(self):
        m = self._make_menu(["A", "B", "C"])
        m.key_down()
        assert m._selected == 1

    def test_key_up_decrements(self):
        m = self._make_menu(["A", "B", "C"])
        m._selected = 2
        m.key_up()
        assert m._selected == 1

    def test_key_down_clamps_at_last(self):
        m = self._make_menu(["A", "B"])
        m._selected = 1
        m.key_down()
        assert m._selected == 1

    def test_key_up_clamps_at_zero(self):
        m = self._make_menu(["A", "B"])
        m.key_up()
        assert m._selected == 0

    def test_key_j_same_as_down(self):
        m = self._make_menu(["A", "B"])
        m.key_j()
        assert m._selected == 1

    def test_key_k_same_as_up(self):
        m = self._make_menu(["A", "B"])
        m._selected = 1
        m.key_k()
        assert m._selected == 0

    def test_key_enter_posts_choice_selected(self):
        m = self._make_menu(["Attack", "Run"])
        m._selected = 1
        m.key_enter()
        assert len(m._messages) == 1
        msg = m._messages[0]
        assert isinstance(msg, ChoiceSelected)
        assert msg.index == 1 and msg.text == "Run"

    def test_key_escape_posts_choice_cancelled(self):
        m = self._make_menu(["A", "B"])
        m.key_escape()
        assert any(isinstance(msg, ChoiceCancelled) for msg in m._messages)

    def test_update_selection_marks_correct_item(self):
        m = self._make_menu(["A", "B", "C"])
        m._selected = 2
        m._update_selection()
        assert "choice-selected" in m._items[2]._classes
        assert "choice-selected" not in m._items[0]._classes


# ===========================================================================
# 12. MessageBox — no-choice dismissal, with-choice navigation
# ===========================================================================


class TestMessageBox:
    def _make_box(self, lines, choices=None):
        b = MessageBox.__new__(MessageBox)
        b._lines = lines
        b._choices = choices
        b._selected = 0
        b._messages = []
        b.post_message = lambda m: b._messages.append(m)

        class _FW:
            def __init__(self):
                self._classes = set()

            def add_class(self, c):
                self._classes.add(c)

            def remove_class(self, c):
                self._classes.discard(c)

        b._items = [_FW() for _ in (choices or [])]
        b.query = lambda sel: b._items
        return b

    def test_no_choices_any_key_posts_dismissed(self):
        b = self._make_box(["Info line"])
        from textual.events import Key

        b.on_key(Key(key="space", character=" "))
        assert any(isinstance(m, MessageBoxDismissed) for m in b._messages)

    def test_with_choices_key_does_not_dismiss(self):
        b = self._make_box(["Pick one"], choices=["Yes", "No"])
        from textual.events import Key

        b.on_key(Key(key="space", character=" "))
        assert not any(isinstance(m, MessageBoxDismissed) for m in b._messages)

    def test_key_down_moves_selection(self):
        b = self._make_box(["Q"], choices=["Yes", "No"])
        b.key_down()
        assert b._selected == 1

    def test_key_up_moves_selection(self):
        b = self._make_box(["Q"], choices=["Yes", "No"])
        b._selected = 1
        b.key_up()
        assert b._selected == 0

    def test_key_enter_posts_choice_selected(self):
        b = self._make_box(["Q"], choices=["Yes", "No"])
        b.key_enter()
        assert any(
            isinstance(m, ChoiceSelected) and m.text == "Yes" for m in b._messages
        )

    def test_key_escape_with_choices_posts_cancelled(self):
        b = self._make_box(["Q"], choices=["Yes", "No"])
        b.key_escape()
        assert any(isinstance(m, ChoiceCancelled) for m in b._messages)

    def test_key_escape_no_choices_no_cancelled(self):
        b = self._make_box(["Info"])
        b.key_escape()
        assert not any(isinstance(m, ChoiceCancelled) for m in b._messages)

    def test_key_j_k_aliases(self):
        b = self._make_box(["Q"], choices=["A", "B", "C"])
        b.key_j()
        b.key_j()
        assert b._selected == 2
        b.key_k()
        assert b._selected == 1


# ===========================================================================
# 13. Game tick loop — dt calculation (no running Textual app)
# ===========================================================================


class TestGameTickLogic:
    def _make_game(self, target_fps=30):
        from core.game import Game

        g = object.__new__(Game)
        g._target_fps = target_fps
        g._last_time = 0.0
        g._ticked_dts = []
        return g

    def _fake_screen_ctx(self, g):
        from core.game import Game

        fake = mock.MagicMock()
        fake.post_message.side_effect = lambda msg: g._ticked_dts.append(msg.dt)
        return mock.patch.object(
            Game, "screen", new_callable=lambda: property(lambda self: fake)
        )

    async def test_first_frame_dt_equals_target(self):
        from core.game import Game

        g = self._make_game(30)
        with self._fake_screen_ctx(g):
            with mock.patch("time.monotonic", return_value=1.0):
                await Game._tick(g)
        assert g._ticked_dts[0] == pytest.approx(1.0 / 30)

    async def test_subsequent_frame_dt_from_delta(self):
        from core.game import Game

        g = self._make_game(30)
        g._last_time = 1.0
        with self._fake_screen_ctx(g):
            with mock.patch("time.monotonic", return_value=1.016):
                await Game._tick(g)
        assert g._ticked_dts[0] == pytest.approx(0.016, abs=1e-6)

    async def test_dt_clamped_to_max(self):
        from core.game import MAX_DT, Game

        g = self._make_game(30)
        g._last_time = 0.0001
        with self._fake_screen_ctx(g):
            with mock.patch("time.monotonic", return_value=99.0):
                await Game._tick(g)
        assert g._ticked_dts[0] <= MAX_DT

    async def test_last_time_updated_after_tick(self):
        from core.game import Game

        g = self._make_game(30)
        fake = mock.MagicMock()
        with mock.patch.object(
            Game, "screen", new_callable=lambda: property(lambda self: fake)
        ):
            with mock.patch("time.monotonic", return_value=5.0):
                await Game._tick(g)
        assert g._last_time == 5.0

    def test_max_dt_constant(self):
        from core.game import MAX_DT

        assert MAX_DT == pytest.approx(0.1)


# ===========================================================================
# 14. SceneManager — push / pop / replace / current_scene / is_empty
# ===========================================================================


class TestSceneManager:
    def _make_sm(self):
        from core.scene_manager import SceneManager

        class _FakeApp(SceneManager):
            def __init__(self):
                self._stack = []

            def push_screen(self, screen):
                self._stack.append(screen)

            def pop_screen(self):
                self._stack.pop()

            def switch_screen(self, screen):
                if self._stack:
                    self._stack[-1] = screen
                else:
                    self._stack.append(screen)

            @property
            def screen(self):
                return self._stack[-1] if self._stack else None

            @property
            def screen_stack(self):
                return self._stack

        return _FakeApp()

    def test_push_scene_adds_to_stack(self):
        sm = self._make_sm()
        sm.push_scene(Scene())
        assert len(sm._stack) == 1

    def test_current_scene_returns_top(self):
        sm = self._make_sm()
        s = Scene()
        sm.push_scene(s)
        assert sm.current_scene is s

    def test_pop_scene_removes_top(self):
        sm = self._make_sm()
        sm.push_scene(Scene())
        sm.push_scene(Scene())
        sm.pop_scene()
        assert len(sm._stack) == 1

    def test_pop_scene_calls_on_resume_if_present(self):
        sm = self._make_sm()
        resumed = []

        class _RS(Scene):
            def on_resume(self):
                resumed.append(True)

        sm.push_scene(_RS())
        sm.push_scene(Scene())
        sm.pop_scene()
        assert resumed == [True]

    def test_replace_scene_swaps_top(self):
        sm = self._make_sm()
        s1, s2 = Scene(), Scene()
        sm.push_scene(s1)
        sm.replace_scene(s2)
        assert sm.current_scene is s2

    def test_is_empty_true_when_no_scenes(self):
        assert self._make_sm().is_empty is True

    def test_is_empty_false_when_scenes_present(self):
        sm = self._make_sm()
        sm.push_scene(Scene())
        assert sm.is_empty is False

    def test_push_multiple_scenes(self):
        sm = self._make_sm()
        for _ in range(5):
            sm.push_scene(Scene())
        assert len(sm._stack) == 5
