###############################################
##               Jumping Cube                ##
##  Data-driven expedition runner in Python  ##
##   with missions, van hub, and upgrades    ##
##                                           ##
## angeldev0                                 ##
###############################################

import importlib.util
import json
import math
import os
import random
import struct
import sys
import wave
from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List, Optional, Sequence, Tuple

import pygame


APP_NAME = "JumpingCube"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DATA_DIR = os.path.join(os.path.expanduser("~"), "Documents", APP_NAME)
SAVE_DIRECTORY = os.path.join(APP_DATA_DIR, "saves")
SETTINGS_PATH = os.path.join(APP_DATA_DIR, "settings.json")
USER_LEVELS_DIR = os.path.join(APP_DATA_DIR, "levels")
AUDIO_DIRECTORY = os.path.join(APP_DATA_DIR, "audio")
BUNDLED_GAME_ASSET_DIR = os.path.join("assets", "game")
BUNDLED_AUDIO_ASSET_DIR = os.path.join("assets", "audio")

DEFAULT_RESOLUTIONS = [
    (800, 600),
    (1024, 768),
    (1280, 720),
    (1366, 768),
    (1600, 900),
    (1920, 1080),
]

KEY_CODE_TO_NAME = {
    value: name
    for name, value in pygame.__dict__.items()
    if name.startswith("K_") and isinstance(value, int)
}

COLORS = [
    (255, 0, 0),
    (0, 255, 0),
    (0, 0, 255),
    (255, 255, 0),
    (0, 255, 255),
    (255, 0, 255),
]
COIN_COLOR = (255, 223, 0)
MENU_BACKGROUND_COLOR = (42, 56, 82)
MENU_TEXT_COLOR = (255, 255, 255)
MENU_HIGHLIGHT_COLOR = (60, 158, 250)
TITLE_COLOR = (255, 255, 0)


def ensure_directories() -> None:
    os.makedirs(APP_DATA_DIR, exist_ok=True)
    os.makedirs(SAVE_DIRECTORY, exist_ok=True)
    os.makedirs(USER_LEVELS_DIR, exist_ok=True)
    os.makedirs(AUDIO_DIRECTORY, exist_ok=True)


def get_asset_path(relative_path: str) -> str:
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(SCRIPT_DIR, relative_path)


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


def default_settings() -> Dict:
    return {
        "version": 1,
        "display": {
            "resolution": [800, 600],
            "fullscreen": False,
        },
        "audio": {
            "master": 0.85,
            "music": 0.7,
            "sfx": 0.9,
        },
        "controls": {
            "move_left": "K_a",
            "move_right": "K_d",
            "jump": "K_SPACE",
            "pause": "K_ESCAPE",
            "menu_up": "K_UP",
            "menu_down": "K_DOWN",
            "menu_select": "K_RETURN",
            "menu_back": "K_BACKSPACE",
        },
    }


def merge_settings(default_value, loaded_value):
    if isinstance(default_value, dict):
        source = loaded_value if isinstance(loaded_value, dict) else {}
        merged = {}
        for key, value in default_value.items():
            merged[key] = merge_settings(value, source.get(key))
        return merged
    return default_value if loaded_value is None else loaded_value


def normalize_settings(settings: Dict) -> Dict:
    if not isinstance(settings.get("display", {}).get("resolution"), list):
        settings["display"]["resolution"] = [800, 600]

    resolution = settings["display"]["resolution"]
    if len(resolution) != 2:
        resolution = [800, 600]
    width = int(clamp(int(resolution[0]), 640, 3840))
    height = int(clamp(int(resolution[1]), 480, 2160))
    settings["display"]["resolution"] = [width, height]
    settings["display"]["fullscreen"] = bool(settings["display"].get("fullscreen", False))

    settings["audio"]["master"] = float(clamp(float(settings["audio"].get("master", 0.85)), 0.0, 1.0))
    settings["audio"]["music"] = float(clamp(float(settings["audio"].get("music", 0.7)), 0.0, 1.0))
    settings["audio"]["sfx"] = float(clamp(float(settings["audio"].get("sfx", 0.9)), 0.0, 1.0))

    controls = settings.get("controls", {})
    for action, key_name in default_settings()["controls"].items():
        candidate = controls.get(action, key_name)
        if not isinstance(candidate, str) or key_code_from_name(candidate) == pygame.K_UNKNOWN:
            controls[action] = key_name
        else:
            controls[action] = candidate
    settings["controls"] = controls
    return settings


def load_settings() -> Dict:
    defaults = default_settings()
    if not os.path.exists(SETTINGS_PATH):
        settings = defaults
        save_settings(settings)
        return settings

    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as file:
            loaded = json.load(file)
    except (OSError, json.JSONDecodeError):
        settings = defaults
        save_settings(settings)
        return settings

    settings = merge_settings(defaults, loaded)
    settings = normalize_settings(settings)
    save_settings(settings)
    return settings


def save_settings(settings: Dict) -> None:
    with open(SETTINGS_PATH, "w", encoding="utf-8") as file:
        json.dump(settings, file, indent=2)


def key_code_from_name(key_name: str) -> int:
    key_code = getattr(pygame, key_name, pygame.K_UNKNOWN)
    return key_code if isinstance(key_code, int) else pygame.K_UNKNOWN


def key_name_from_code(key_code: int) -> str:
    return KEY_CODE_TO_NAME.get(key_code, "K_UNKNOWN")


def find_audio_asset(base_name: str) -> Optional[str]:
    bundled_extensions = [".ogg", ".mp3", ".wav"]
    user_extensions = [".ogg", ".mp3"]

    search_directories = [
        (AUDIO_DIRECTORY, user_extensions),
        (get_asset_path(BUNDLED_AUDIO_ASSET_DIR), bundled_extensions),
    ]

    for directory, extensions in search_directories:
        for extension in extensions:
            candidate = os.path.join(directory, f"{base_name}{extension}")
            if os.path.exists(candidate):
                return candidate
    return None


def generate_tone_wave(path: str, frequency: float, duration: float, volume: float) -> None:
    sample_rate = 44100
    total_samples = int(sample_rate * duration)

    with wave.open(path, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)

        for sample_index in range(total_samples):
            t = sample_index / sample_rate
            value = math.sin(2.0 * math.pi * frequency * t)
            packed_value = struct.pack("<h", int(32767 * volume * value))
            wav_file.writeframesraw(packed_value)
        wav_file.writeframes(b"")


def generate_melody_wave(path: str, melody: List[Tuple[float, float]], volume: float) -> None:
    sample_rate = 44100
    with wave.open(path, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)

        for frequency, duration in melody:
            total_samples = int(sample_rate * duration)
            for sample_index in range(total_samples):
                t = sample_index / sample_rate
                base = math.sin(2.0 * math.pi * frequency * t)
                harmonic = 0.35 * math.sin(2.0 * math.pi * (frequency * 2.0) * t)
                value = (base + harmonic) / 1.35
                packed_value = struct.pack("<h", int(32767 * volume * value))
                wav_file.writeframesraw(packed_value)
        wav_file.writeframes(b"")


def ensure_audio_assets() -> Dict[str, str]:
    os.makedirs(AUDIO_DIRECTORY, exist_ok=True)
    sound_keys = [
        "menu_music",
        "mission_music",
        "hub_music",
        "shoot",
        "pickup",
        "hit",
        "win",
        "lose",
        "menu_move",
        "menu_select",
        "upgrade",
    ]

    legacy_aliases = {
        "mission_music": "game_music",
        "pickup": "coin",
    }

    files: Dict[str, str] = {}
    for key in sound_keys:
        existing_file = find_audio_asset(key)
        if existing_file is None and key in legacy_aliases:
            existing_file = find_audio_asset(legacy_aliases[key])
        if existing_file:
            files[key] = existing_file
        else:
            files[key] = os.path.join(AUDIO_DIRECTORY, f"{key}.wav")

    if not os.path.exists(files["menu_music"]):
        generate_melody_wave(
            files["menu_music"],
            [
                (293.66, 0.3),
                (349.23, 0.3),
                (440.00, 0.3),
                (349.23, 0.3),
                (261.63, 0.3),
                (329.63, 0.3),
                (392.00, 0.3),
                (329.63, 0.3),
            ]
            * 3,
            0.18,
        )

    if not os.path.exists(files["mission_music"]):
        generate_melody_wave(
            files["mission_music"],
            [
                (164.81, 0.14),
                (196.00, 0.14),
                (220.00, 0.14),
                (246.94, 0.14),
                (196.00, 0.14),
                (164.81, 0.14),
                (220.00, 0.14),
                (261.63, 0.14),
            ]
            * 5,
            0.2,
        )

    if not os.path.exists(files["hub_music"]):
        generate_melody_wave(
            files["hub_music"],
            [
                (220.00, 0.35),
                (277.18, 0.35),
                (329.63, 0.35),
                (277.18, 0.35),
                (246.94, 0.35),
                (293.66, 0.35),
                (349.23, 0.35),
                (293.66, 0.35),
            ]
            * 2,
            0.16,
        )

    if not os.path.exists(files["shoot"]):
        generate_tone_wave(files["shoot"], 760.0, 0.05, 0.28)
    if not os.path.exists(files["pickup"]):
        generate_tone_wave(files["pickup"], 920.0, 0.08, 0.32)
    if not os.path.exists(files["hit"]):
        generate_tone_wave(files["hit"], 180.0, 0.09, 0.35)
    if not os.path.exists(files["win"]):
        generate_melody_wave(files["win"], [(523.25, 0.1), (659.25, 0.1), (783.99, 0.2), (1046.5, 0.24)], 0.35)
    if not os.path.exists(files["lose"]):
        generate_melody_wave(files["lose"], [(220.0, 0.14), (196.0, 0.16), (174.61, 0.18), (164.81, 0.22)], 0.32)
    if not os.path.exists(files["menu_move"]):
        generate_tone_wave(files["menu_move"], 620.0, 0.05, 0.18)
    if not os.path.exists(files["menu_select"]):
        generate_tone_wave(files["menu_select"], 860.0, 0.07, 0.22)
    if not os.path.exists(files["upgrade"]):
        generate_melody_wave(files["upgrade"], [(440.0, 0.08), (554.37, 0.08), (659.25, 0.13)], 0.3)

    return files


class AudioManager:
    def __init__(self):
        self.enabled = False
        self.current_track: Optional[str] = None
        self.files: Dict[str, str] = {}
        self.sounds: Dict[str, pygame.mixer.Sound] = {}
        self.master_volume = 1.0
        self.music_volume = 0.7
        self.sfx_volume = 0.9

        try:
            pygame.mixer.init()
            self.enabled = True
        except pygame.error:
            self.enabled = False
            return

        self.files = ensure_audio_assets()
        for sound_name in ["shoot", "pickup", "hit", "win", "lose", "menu_move", "menu_select", "upgrade"]:
            self.sounds[sound_name] = pygame.mixer.Sound(self.files[sound_name])

    def apply_settings(self, audio_settings: Dict) -> None:
        self.master_volume = float(audio_settings.get("master", 1.0))
        self.music_volume = float(audio_settings.get("music", 0.7))
        self.sfx_volume = float(audio_settings.get("sfx", 0.9))
        if not self.enabled:
            return
        pygame.mixer.music.set_volume(self.master_volume * self.music_volume)
        for sound in self.sounds.values():
            sound.set_volume(self.master_volume * self.sfx_volume)

    def play_music(self, track_key: str) -> None:
        if not self.enabled:
            return
        if self.current_track == track_key:
            return
        if track_key == "menu":
            music_key = "menu_music"
        elif track_key == "hub":
            music_key = "hub_music"
        else:
            music_key = "mission_music"
        path = self.files.get(music_key)
        if not path:
            return
        self.current_track = track_key
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.play(-1)
            pygame.mixer.music.set_volume(self.master_volume * self.music_volume)
        except pygame.error:
            pass

    def stop_music(self) -> None:
        if self.enabled:
            pygame.mixer.music.stop()
        self.current_track = None

    def play_sfx(self, sound_name: str) -> None:
        if not self.enabled:
            return
        sound = self.sounds.get(sound_name)
        if sound:
            sound.play()


@dataclass
class LevelDefinition:
    level_id: str
    name: str
    description: str
    base_size: Tuple[int, int]
    player_start: Tuple[int, int]
    obstacles: List[Tuple[int, int, int, int]]
    enemy_spawns: List[Tuple[int, int]]
    extraction_zone: Tuple[int, int, int, int]
    required_scrap: int
    time_limit_sec: int
    player_speed: float
    enemy_speed: float
    enemy_health: int
    enemy_touch_damage: int


def parse_level_dict(data: Dict, source_path: str) -> LevelDefinition:
    if not isinstance(data, dict):
        raise ValueError("LEVEL must be a dictionary")

    filename = os.path.splitext(os.path.basename(source_path))[0]
    level_id = str(data.get("id", filename)).strip()
    if not level_id:
        raise ValueError("Level id cannot be empty")

    name = str(data.get("name", level_id)).strip() or level_id
    description = str(data.get("description", "")).strip()

    dimensions = data.get("dimensions", (800, 600))
    if not isinstance(dimensions, (list, tuple)) or len(dimensions) != 2:
        raise ValueError("dimensions must be [width, height]")
    base_width = int(dimensions[0])
    base_height = int(dimensions[1])
    if base_width < 300 or base_height < 300:
        raise ValueError("dimensions are too small")

    player_start = data.get("player_start", (base_width // 2, base_height - 60))
    if not isinstance(player_start, (list, tuple)) or len(player_start) != 2:
        raise ValueError("player_start must be [x, y]")
    player_x = int(player_start[0])
    player_y = int(player_start[1])

    raw_obstacles = data.get("obstacles", data.get("platforms", []))
    if not isinstance(raw_obstacles, list):
        raise ValueError("obstacles must be a list")

    obstacles: List[Tuple[int, int, int, int]] = []
    for obstacle in raw_obstacles:
        if not isinstance(obstacle, (list, tuple)) or len(obstacle) != 4:
            raise ValueError("each obstacle must be [x, y, width, height]")
        px, py, pw, ph = (int(obstacle[0]), int(obstacle[1]), int(obstacle[2]), int(obstacle[3]))
        if pw <= 0 or ph <= 0:
            raise ValueError("obstacle dimensions must be positive")
        obstacles.append((px, py, pw, ph))

    raw_enemy_spawns = data.get("enemy_spawns", data.get("coins", []))
    if not isinstance(raw_enemy_spawns, list) or not raw_enemy_spawns:
        raise ValueError("enemy_spawns must be a non-empty list")

    enemy_spawns: List[Tuple[int, int]] = []
    for spawn in raw_enemy_spawns:
        if not isinstance(spawn, (list, tuple)) or len(spawn) < 2:
            raise ValueError("each enemy spawn must be [x, y]")
        enemy_spawns.append((int(spawn[0]), int(spawn[1])))

    extraction_zone = data.get("extraction_zone", (base_width - 120, base_height - 120, 90, 70))
    if not isinstance(extraction_zone, (list, tuple)) or len(extraction_zone) != 4:
        raise ValueError("extraction_zone must be [x, y, width, height]")
    extraction_rect = (
        int(extraction_zone[0]),
        int(extraction_zone[1]),
        max(30, int(extraction_zone[2])),
        max(30, int(extraction_zone[3])),
    )

    required_scrap = int(data.get("required_scrap", data.get("required_coins", max(1, len(enemy_spawns) // 2))))
    required_scrap = max(1, min(required_scrap, len(enemy_spawns)))

    time_limit_sec = int(data.get("time_limit_sec", 90))
    time_limit_sec = max(15, time_limit_sec)

    player_speed = float(data.get("player_speed", data.get("move_speed", 4.3)))
    enemy_speed = float(data.get("enemy_speed", 1.4))
    enemy_health = max(1, int(data.get("enemy_health", 35)))
    enemy_touch_damage = max(1, int(data.get("enemy_touch_damage", 12)))

    return LevelDefinition(
        level_id=level_id,
        name=name,
        description=description,
        base_size=(base_width, base_height),
        player_start=(player_x, player_y),
        obstacles=obstacles,
        enemy_spawns=enemy_spawns,
        extraction_zone=extraction_rect,
        required_scrap=required_scrap,
        time_limit_sec=time_limit_sec,
        player_speed=player_speed,
        enemy_speed=enemy_speed,
        enemy_health=enemy_health,
        enemy_touch_damage=enemy_touch_damage,
    )


class LevelRepository:
    def __init__(self, user_levels_dir: str, bundled_levels_dir: str):
        self.user_levels_dir = user_levels_dir
        self.bundled_levels_dir = bundled_levels_dir

    @staticmethod
    def _level_files(directory: str) -> List[str]:
        if not os.path.isdir(directory):
            return []
        files = []
        for name in os.listdir(directory):
            if not name.endswith(".py"):
                continue
            if name.startswith("_"):
                continue
            files.append(os.path.join(directory, name))
        files.sort()
        return files

    @staticmethod
    def _load_level_file(path: str) -> LevelDefinition:
        module_name = f"jumping_cube_level_{abs(hash(path))}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise ValueError("Could not load module spec")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        if not hasattr(module, "LEVEL"):
            raise ValueError("LEVEL dictionary not found")
        return parse_level_dict(module.LEVEL, path)

    def discover_levels(self) -> Tuple[List[LevelDefinition], List[str]]:
        levels_by_id: Dict[str, LevelDefinition] = {}
        errors: List[str] = []

        for level_file in self._level_files(self.bundled_levels_dir):
            try:
                level = self._load_level_file(level_file)
                levels_by_id[level.level_id] = level
            except Exception as error:
                errors.append(f"Bundled level error in {os.path.basename(level_file)}: {error}")

        for level_file in self._level_files(self.user_levels_dir):
            try:
                level = self._load_level_file(level_file)
                levels_by_id[level.level_id] = level
            except Exception as error:
                errors.append(f"User level error in {os.path.basename(level_file)}: {error}")

        levels = list(levels_by_id.values())
        levels.sort(key=lambda item: item.level_id)
        return levels, errors


class Screen(Enum):
    USERNAME = auto()
    MAIN_MENU = auto()
    LEVEL_SELECT = auto()
    GAMEPLAY = auto()
    SAFE_HUB = auto()
    PAUSE = auto()
    SETTINGS = auto()
    LOAD_GAME = auto()
    WIN = auto()
    GAME_OVER = auto()


class JumpingCubeGame:
    def __init__(self):
        pygame.init()
        ensure_directories()

        self.settings = load_settings()
        self.running = True
        self.clock = pygame.time.Clock()

        self.screen_state = Screen.USERNAME
        self.settings_return_screen = Screen.MAIN_MENU
        self.load_return_screen = Screen.MAIN_MENU

        self.username = ""
        self.status_message = ""
        self.status_until = 0
        self.level_errors: List[str] = []

        self.menu_indices: Dict[Screen, int] = {
            Screen.MAIN_MENU: 0,
            Screen.LEVEL_SELECT: 0,
            Screen.SAFE_HUB: 0,
            Screen.PAUSE: 0,
            Screen.LOAD_GAME: 0,
            Screen.SETTINGS: 0,
            Screen.WIN: 0,
            Screen.GAME_OVER: 0,
        }
        self.current_menu_rects: List[pygame.Rect] = []

        self.rebinding_action: Optional[str] = None
        self.settings_items = [
            ("master", "Master Volume", "slider"),
            ("music", "Music Volume", "slider"),
            ("sfx", "SFX Volume", "slider"),
            ("fullscreen", "Fullscreen", "toggle"),
            ("resolution", "Resolution", "resolution"),
            ("move_left", "Rebind Move Left", "rebind"),
            ("move_right", "Rebind Move Right", "rebind"),
            ("jump", "Rebind Fire / Action", "rebind"),
            ("pause", "Rebind Pause", "rebind"),
            ("menu_up", "Rebind Menu Up", "rebind"),
            ("menu_down", "Rebind Menu Down", "rebind"),
            ("menu_select", "Rebind Menu Select", "rebind"),
            ("menu_back", "Rebind Menu Back", "rebind"),
            ("back", "Back", "action"),
        ]

        self.square_size = 42
        self.border_thickness = 5

        self.current_level: Optional[LevelDefinition] = None
        self.current_level_index = 0
        self.pending_level_index = 0
        self.platforms: List[pygame.Rect] = []
        self.coins: List[pygame.Rect] = []
        self.enemies: List[Dict] = []
        self.bullets: List[Dict] = []
        self.extraction_zone = pygame.Rect(0, 0, 80, 80)
        self.coin_size_default = 18

        self.player_x = 0.0
        self.player_y = 0.0
        self.player_health_max = 100
        self.player_health = 100
        self.player_damage = 20
        self.player_speed_bonus = 0.0
        self.last_shot_ms = 0
        self.last_player_hit_ms = 0

        self.collected_coins = 0
        self.scrap_bank = 0
        self.upgrade_levels = {"armor": 0, "weapon": 0, "engine": 0}
        self.level_start_ticks = 0

        self.save_files: List[str] = []

        self.screen = None
        self.screen_width = 800
        self.screen_height = 600
        self.background_scaled = None
        self.menu_background_scaled = None
        self._apply_display_settings(persist=False)

        pygame.display.set_caption("Jumping Cube")

        self.font = pygame.font.SysFont(None, 36)
        self.small_font = pygame.font.SysFont(None, 24)
        self.large_font = pygame.font.SysFont(None, 56)

        self.background_image = self._load_image(
            [
                os.path.join(BUNDLED_GAME_ASSET_DIR, "background_game.png"),
                "background.jpeg",
            ],
            alpha=False,
        )
        self.menu_background_image = self._load_image(
            [
                os.path.join(BUNDLED_GAME_ASSET_DIR, "background_menu.png"),
                os.path.join(BUNDLED_GAME_ASSET_DIR, "background_game.png"),
                "background.jpeg",
            ],
            alpha=False,
        )
        self.platform_image = self._load_image(
            [
                os.path.join(BUNDLED_GAME_ASSET_DIR, "platform.png"),
                "platforms.png",
            ],
            alpha=True,
            fallback_size=(100, 12),
        )
        self.square_image_original = self._load_image(
            [
                os.path.join(BUNDLED_GAME_ASSET_DIR, "player.png"),
                "square.png",
            ],
            alpha=True,
            fallback_size=(50, 50),
        )
        self.coin_image = self._load_image(
            [os.path.join(BUNDLED_GAME_ASSET_DIR, "coin.png")],
            alpha=True,
            fallback_size=(24, 24),
        )
        self.menu_button_image = self._load_image(
            [os.path.join(BUNDLED_GAME_ASSET_DIR, "menu_button.png")],
            alpha=True,
            fallback_size=(300, 56),
        )
        self.menu_button_selected_image = self._load_image(
            [
                os.path.join(BUNDLED_GAME_ASSET_DIR, "menu_button_selected.png"),
                os.path.join(BUNDLED_GAME_ASSET_DIR, "menu_button.png"),
            ],
            alpha=True,
            fallback_size=(300, 56),
        )
        self.square_image = pygame.transform.scale(self.square_image_original, (self.square_size, self.square_size))
        self._rescale_background()

        self.audio = AudioManager()
        self.audio.apply_settings(self.settings["audio"])

        self.level_repository = LevelRepository(USER_LEVELS_DIR, get_asset_path("levels"))
        self.levels: List[LevelDefinition] = []
        self.refresh_levels()

        self.audio.play_music("menu")

    def _load_image(self, filenames: Sequence[str] | str, alpha: bool, fallback_size: Tuple[int, int] = (100, 100)) -> pygame.Surface:
        candidates = [filenames] if isinstance(filenames, str) else list(filenames)

        for filename in candidates:
            path = get_asset_path(filename)
            try:
                image = pygame.image.load(path)
                return image.convert_alpha() if alpha else image.convert()
            except (pygame.error, FileNotFoundError):
                continue

        if alpha:
            fallback = pygame.Surface(fallback_size, pygame.SRCALPHA)
            fallback.fill((180, 180, 180, 255))
            return fallback

        fallback = pygame.Surface(fallback_size)
        fallback.fill((80, 120, 180))
        return fallback

    def _rescale_background(self) -> None:
        self.background_scaled = pygame.transform.scale(self.background_image, (self.screen_width, self.screen_height))
        self.menu_background_scaled = pygame.transform.scale(self.menu_background_image, (self.screen_width, self.screen_height))

    def _apply_display_settings(self, persist: bool = True) -> None:
        width, height = self.settings["display"]["resolution"]
        flags = pygame.FULLSCREEN if self.settings["display"].get("fullscreen", False) else 0
        self.screen = pygame.display.set_mode((int(width), int(height)), flags)
        self.screen_width, self.screen_height = self.screen.get_size()
        self.settings["display"]["resolution"] = [self.screen_width, self.screen_height]
        if persist:
            save_settings(self.settings)

    def show_status(self, text: str, duration_ms: int = 2000) -> None:
        self.status_message = text
        self.status_until = pygame.time.get_ticks() + duration_ms

    def action_key(self, action: str) -> int:
        key_name = self.settings["controls"].get(action, "K_UNKNOWN")
        return key_code_from_name(key_name)

    def action_matches_event(self, event: pygame.event.Event, action: str) -> bool:
        return event.key == self.action_key(action)

    def action_pressed(self, keys, action: str) -> bool:
        key_code = self.action_key(action)
        if key_code == pygame.K_UNKNOWN:
            return False
        return bool(keys[key_code])

    def transition_to(self, screen: Screen) -> None:
        self.screen_state = screen
        self.current_menu_rects = []
        if screen in [
            Screen.MAIN_MENU,
            Screen.LEVEL_SELECT,
            Screen.SAFE_HUB,
            Screen.SETTINGS,
            Screen.LOAD_GAME,
            Screen.PAUSE,
            Screen.WIN,
            Screen.GAME_OVER,
            Screen.USERNAME,
        ]:
            if screen == Screen.SAFE_HUB:
                self.audio.play_music("hub")
            else:
                self.audio.play_music("menu")
        elif screen == Screen.GAMEPLAY:
            self.audio.play_music("mission")

    def refresh_levels(self) -> None:
        levels, errors = self.level_repository.discover_levels()
        self.level_errors = errors

        if not levels:
            fallback = LevelDefinition(
                level_id="fallback",
                name="Dustline Block",
                description="Auto-generated fallback mission",
                base_size=(800, 600),
                player_start=(70, 500),
                obstacles=[
                    (0, 0, 800, 24),
                    (0, 576, 800, 24),
                    (0, 0, 24, 600),
                    (776, 0, 24, 600),
                    (220, 180, 120, 60),
                    (460, 320, 160, 70),
                ],
                enemy_spawns=[
                    (130, 120),
                    (660, 130),
                    (160, 440),
                    (640, 460),
                    (390, 120),
                    (390, 470),
                ],
                extraction_zone=(655, 495, 100, 70),
                required_scrap=4,
                time_limit_sec=90,
                player_speed=4.2,
                enemy_speed=1.4,
                enemy_health=34,
                enemy_touch_damage=12,
            )
            levels = [fallback]
            self.level_errors.append("No mission files loaded from levels directories; fallback mission used.")

        self.levels = levels
        self.current_level_index = int(clamp(self.current_level_index, 0, len(self.levels) - 1))

    def level_by_id(self, level_id: str) -> Tuple[Optional[LevelDefinition], int]:
        for index, level in enumerate(self.levels):
            if level.level_id == level_id:
                return level, index
        return None, -1

    def _scale_value(self, value: int, source_max: int, target_max: int) -> int:
        if source_max <= 0:
            return value
        return int((value / source_max) * target_max)

    def start_level(self, level_index: int) -> None:
        self.refresh_levels()
        level_index = int(clamp(level_index, 0, len(self.levels) - 1))
        self.current_level_index = level_index
        self.pending_level_index = min(level_index + 1, len(self.levels) - 1)
        self.current_level = self.levels[level_index]

        base_width, base_height = self.current_level.base_size
        sx = self.screen_width / base_width
        sy = self.screen_height / base_height

        self.platforms = []
        for obstacle in self.current_level.obstacles:
            x = int(obstacle[0] * sx)
            y = int(obstacle[1] * sy)
            w = max(20, int(obstacle[2] * sx))
            h = max(20, int(obstacle[3] * sy))
            self.platforms.append(pygame.Rect(x, y, w, h))

        self.coins = []
        self.enemies = []
        for spawn in self.current_level.enemy_spawns:
            x = int(spawn[0] * sx)
            y = int(spawn[1] * sy)
            rect = pygame.Rect(x, y, 32, 32)
            speed = float(self.current_level.enemy_speed * ((sx + sy) * 0.5))
            self.enemies.append(
                {
                    "rect": rect,
                    "fx": float(rect.x),
                    "fy": float(rect.y),
                    "speed": speed,
                    "hp": int(self.current_level.enemy_health),
                }
            )

        ex = self.current_level.extraction_zone
        self.extraction_zone = pygame.Rect(
            int(ex[0] * sx),
            int(ex[1] * sy),
            max(30, int(ex[2] * sx)),
            max(30, int(ex[3] * sy)),
        )

        self.player_x = float(self.current_level.player_start[0] * sx)
        self.player_y = float(self.current_level.player_start[1] * sy)
        self.player_x = clamp(self.player_x, 0, self.screen_width - self.square_size)
        self.player_y = clamp(self.player_y, 0, self.screen_height - self.square_size)

        self.player_health = self.player_health_max
        self.last_player_hit_ms = 0
        self.last_shot_ms = 0
        self.bullets = []
        self.collected_coins = 0
        self.level_start_ticks = pygame.time.get_ticks()

        self.transition_to(Screen.GAMEPLAY)
        self.show_status(f"Deployed to {self.current_level.name}")

    def start_new_run(self) -> None:
        self.scrap_bank = 0
        self.upgrade_levels = {"armor": 0, "weapon": 0, "engine": 0}
        self.player_health_max = 100
        self.player_damage = 20
        self.player_speed_bonus = 0.0
        self.start_level(0)

    def upgrade_cost(self, upgrade_key: str) -> int:
        base = {
            "armor": 6,
            "weapon": 7,
            "engine": 6,
        }.get(upgrade_key, 6)
        return base + (self.upgrade_levels.get(upgrade_key, 0) * 4)

    def buy_upgrade(self, upgrade_key: str) -> None:
        cost = self.upgrade_cost(upgrade_key)
        if self.scrap_bank < cost:
            self.show_status("Not enough scrap")
            return

        self.scrap_bank -= cost
        self.upgrade_levels[upgrade_key] = self.upgrade_levels.get(upgrade_key, 0) + 1

        if upgrade_key == "armor":
            self.player_health_max += 20
        elif upgrade_key == "weapon":
            self.player_damage += 4
        elif upgrade_key == "engine":
            self.player_speed_bonus += 0.3

        self.player_health = self.player_health_max
        self.audio.play_sfx("upgrade")
        self.show_status(f"Upgraded {upgrade_key}")

    def create_save_payload(self) -> Dict:
        elapsed_ms = pygame.time.get_ticks() - self.level_start_ticks
        level_id = self.current_level.level_id if self.current_level else ""
        return {
            "schema_version": 3,
            "username": self.username,
            "screen": self.screen_state.name,
            "level_id": level_id,
            "level_index": self.current_level_index,
            "player": {
                "x": self.player_x,
                "y": self.player_y,
                "health": self.player_health,
            },
            "mission": {
                "scrap_collected": self.collected_coins,
                "elapsed_ms": elapsed_ms,
                "coins": [[coin.x, coin.y, coin.width, coin.height] for coin in self.coins],
                "enemies": [
                    {
                        "x": enemy["rect"].x,
                        "y": enemy["rect"].y,
                        "width": enemy["rect"].width,
                        "height": enemy["rect"].height,
                        "speed": enemy["speed"],
                        "hp": enemy["hp"],
                    }
                    for enemy in self.enemies
                ],
                "extraction_zone": [
                    self.extraction_zone.x,
                    self.extraction_zone.y,
                    self.extraction_zone.width,
                    self.extraction_zone.height,
                ],
            },
            "progression": {
                "scrap_bank": self.scrap_bank,
                "pending_level_index": self.pending_level_index,
                "upgrade_levels": self.upgrade_levels,
                "player_health_max": self.player_health_max,
                "player_damage": self.player_damage,
                "player_speed_bonus": self.player_speed_bonus,
            },
            "elapsed_ms": elapsed_ms,
            "saved_at": pygame.time.get_ticks(),
        }

    def save_game(self) -> None:
        if not self.username:
            self.show_status("Set username before saving")
            return
        if self.current_level is None:
            self.show_status("Start a level before saving")
            return

        timestamp = pygame.time.get_ticks()
        filename = f"save_{self.username}_{self.current_level.level_id}_{timestamp}.json"
        path = os.path.join(SAVE_DIRECTORY, filename)

        with open(path, "w", encoding="utf-8") as save_file:
            json.dump(self.create_save_payload(), save_file, indent=2)

        self.show_status("Game saved")
        self.update_save_files()

    def _restore_new_save_schema(self, save_data: Dict) -> bool:
        progression = save_data.get("progression", {})
        self.scrap_bank = int(progression.get("scrap_bank", 0))
        self.pending_level_index = int(progression.get("pending_level_index", 0))
        self.upgrade_levels = dict(progression.get("upgrade_levels", {"armor": 0, "weapon": 0, "engine": 0}))
        self.player_health_max = int(progression.get("player_health_max", 100))
        self.player_damage = int(progression.get("player_damage", 20))
        self.player_speed_bonus = float(progression.get("player_speed_bonus", 0.0))

        level_id = str(save_data.get("level_id", "")).strip()
        level_index = int(save_data.get("level_index", 0))

        if level_id:
            level, idx = self.level_by_id(level_id)
            if level is not None:
                level_index = idx

        self.start_level(level_index)

        player_data = save_data.get("player", {})
        self.player_x = float(player_data.get("x", self.player_x))
        self.player_y = float(player_data.get("y", self.player_y))
        self.player_health = int(player_data.get("health", self.player_health_max))

        mission = save_data.get("mission", {})
        self.coins = []
        for coin in mission.get("coins", []):
            if not isinstance(coin, list) or len(coin) != 4:
                continue
            self.coins.append(pygame.Rect(int(coin[0]), int(coin[1]), int(coin[2]), int(coin[3])))

        self.enemies = []
        for enemy in mission.get("enemies", []):
            if not isinstance(enemy, dict):
                continue
            rect = pygame.Rect(
                int(enemy.get("x", 0)),
                int(enemy.get("y", 0)),
                int(enemy.get("width", 32)),
                int(enemy.get("height", 32)),
            )
            self.enemies.append(
                {
                    "rect": rect,
                    "fx": float(rect.x),
                    "fy": float(rect.y),
                    "speed": float(enemy.get("speed", self.current_level.enemy_speed if self.current_level else 1.4)),
                    "hp": int(enemy.get("hp", self.current_level.enemy_health if self.current_level else 30)),
                }
            )

        extraction = mission.get("extraction_zone", [])
        if isinstance(extraction, list) and len(extraction) == 4:
            self.extraction_zone = pygame.Rect(
                int(extraction[0]),
                int(extraction[1]),
                int(extraction[2]),
                int(extraction[3]),
            )

        self.collected_coins = int(mission.get("scrap_collected", 0))

        elapsed_ms = int(mission.get("elapsed_ms", save_data.get("elapsed_ms", 0)))
        self.level_start_ticks = pygame.time.get_ticks() - elapsed_ms

        saved_screen = save_data.get("screen", "GAMEPLAY")
        if saved_screen == Screen.SAFE_HUB.name:
            self.transition_to(Screen.SAFE_HUB)
        else:
            self.transition_to(Screen.GAMEPLAY)
        return True

    def _restore_legacy_save_schema(self, save_data: Dict) -> bool:
        self.start_new_run()
        self.scrap_bank = int(save_data.get("collected_coins", 0))
        self.transition_to(Screen.SAFE_HUB)
        return True

    def load_game(self, filename: str) -> bool:
        path = os.path.join(SAVE_DIRECTORY, filename)
        if not os.path.exists(path):
            self.show_status("Save file not found")
            return False

        try:
            with open(path, "r", encoding="utf-8") as save_file:
                save_data = json.load(save_file)
        except (OSError, json.JSONDecodeError):
            self.show_status("Save file could not be loaded")
            return False

        schema_version = int(save_data.get("schema_version", 1))

        if schema_version >= 3:
            restored = self._restore_new_save_schema(save_data)
        else:
            restored = self._restore_legacy_save_schema(save_data)

        if restored:
            self.show_status("Save loaded")
            return True

        self.show_status("Could not restore save")
        return False

    def update_save_files(self) -> None:
        if not self.username:
            self.save_files = []
            return

        prefix = f"save_{self.username}"
        files = [
            name
            for name in os.listdir(SAVE_DIRECTORY)
            if name.startswith(prefix) and name.endswith(".json")
        ]
        files.sort(reverse=True)
        self.save_files = files
        self.menu_indices[Screen.LOAD_GAME] = int(clamp(self.menu_indices[Screen.LOAD_GAME], 0, max(len(files), 1) - 1))

    def open_level_select(self) -> None:
        self.refresh_levels()
        self.menu_indices[Screen.LEVEL_SELECT] = int(clamp(self.current_level_index, 0, len(self.levels) - 1))
        self.transition_to(Screen.LEVEL_SELECT)

    def open_load_menu(self, return_screen: Screen) -> None:
        self.load_return_screen = return_screen
        self.update_save_files()
        self.transition_to(Screen.LOAD_GAME)

    def open_settings(self, return_screen: Screen) -> None:
        self.settings_return_screen = return_screen
        self.menu_indices[Screen.SETTINGS] = 0
        self.rebinding_action = None
        self.transition_to(Screen.SETTINGS)

    def draw_title(self, text: str) -> None:
        title_surface = self.large_font.render(text, True, TITLE_COLOR)
        self.screen.blit(title_surface, (self.screen_width // 2 - title_surface.get_width() // 2, 40))

    def draw_status(self) -> None:
        if not self.status_message:
            return
        if pygame.time.get_ticks() > self.status_until:
            self.status_message = ""
            return

        status_surface = self.small_font.render(self.status_message, True, (255, 255, 255))
        background_rect = pygame.Rect(
            self.screen_width // 2 - status_surface.get_width() // 2 - 12,
            self.screen_height - 44,
            status_surface.get_width() + 24,
            28,
        )
        pygame.draw.rect(self.screen, (20, 20, 20), background_rect, border_radius=6)
        self.screen.blit(status_surface, (background_rect.x + 12, background_rect.y + 6))

    def draw_menu_list(self, title: str, options: List[str], selected_index: int, subtitle: str = "") -> None:
        if self.menu_background_scaled is not None:
            self.screen.blit(self.menu_background_scaled, (0, 0))
        else:
            self.screen.fill(MENU_BACKGROUND_COLOR)
        self.draw_title(title)

        if subtitle:
            subtitle_surface = self.small_font.render(subtitle, True, MENU_TEXT_COLOR)
            self.screen.blit(
                subtitle_surface,
                (self.screen_width // 2 - subtitle_surface.get_width() // 2, 106),
            )

        y_start = 180
        spacing = 54
        button_width = min(560, self.screen_width - 120)
        button_height = 42
        x = self.screen_width // 2 - button_width // 2

        self.current_menu_rects = []
        for index, label in enumerate(options):
            y = y_start + index * spacing
            rect = pygame.Rect(x, y, button_width, button_height)
            self.current_menu_rects.append(rect)

            if index == selected_index:
                button_image = pygame.transform.scale(self.menu_button_selected_image, (rect.width, rect.height))
            else:
                button_image = pygame.transform.scale(self.menu_button_image, (rect.width, rect.height))

            self.screen.blit(button_image, rect.topleft)

            text_surface = self.font.render(label, True, MENU_BACKGROUND_COLOR)
            self.screen.blit(
                text_surface,
                (
                    rect.x + rect.width // 2 - text_surface.get_width() // 2,
                    rect.y + rect.height // 2 - text_surface.get_height() // 2,
                ),
            )

    def main_menu_items(self) -> List[Tuple[str, callable]]:
        return [
            ("Start Expedition", self.start_new_run),
            ("Mission Select", self.open_level_select),
            ("Load Game", lambda: self.open_load_menu(Screen.MAIN_MENU)),
            ("Settings", lambda: self.open_settings(Screen.MAIN_MENU)),
            ("Refresh Missions", self.refresh_levels),
            ("Quit", self.stop_running),
        ]

    def pause_menu_items(self) -> List[Tuple[str, callable]]:
        return [
            ("Resume", lambda: self.transition_to(Screen.GAMEPLAY)),
            ("Save Game", self.save_game),
            ("Load Game", lambda: self.open_load_menu(Screen.PAUSE)),
            ("Settings", lambda: self.open_settings(Screen.PAUSE)),
            ("Retreat to Van", lambda: self.transition_to(Screen.SAFE_HUB)),
            ("Main Menu", lambda: self.transition_to(Screen.MAIN_MENU)),
            ("Quit", self.stop_running),
        ]

    def safe_hub_items(self) -> List[Tuple[str, callable]]:
        items: List[Tuple[str, callable]] = []

        target_level = int(clamp(self.pending_level_index, 0, len(self.levels) - 1))
        mission_name = self.levels[target_level].name
        items.append((f"Deploy: {mission_name}", lambda i=target_level: self.start_level(i)))

        items.append(
            (
                f"Upgrade Armor (+20 HP) - {self.upgrade_cost('armor')} scrap",
                lambda: self.buy_upgrade("armor"),
            )
        )
        items.append(
            (
                f"Upgrade Weapon (+4 DMG) - {self.upgrade_cost('weapon')} scrap",
                lambda: self.buy_upgrade("weapon"),
            )
        )
        items.append(
            (
                f"Upgrade Engine (+0.3 SPD) - {self.upgrade_cost('engine')} scrap",
                lambda: self.buy_upgrade("engine"),
            )
        )
        items.append(("Save Game", self.save_game))
        items.append(("Main Menu", lambda: self.transition_to(Screen.MAIN_MENU)))
        return items

    def win_menu_items(self) -> List[Tuple[str, callable]]:
        items = [
            ("Start New Expedition", self.start_new_run),
            ("Mission Select", self.open_level_select),
        ]
        items.append(("Main Menu", lambda: self.transition_to(Screen.MAIN_MENU)))
        return items

    def game_over_items(self) -> List[Tuple[str, callable]]:
        return [
            ("Retry Mission", lambda: self.start_level(self.current_level_index)),
            ("Retreat to Van", lambda: self.transition_to(Screen.SAFE_HUB)),
            ("Main Menu", lambda: self.transition_to(Screen.MAIN_MENU)),
        ]

    def draw_username_screen(self) -> None:
        if self.menu_background_scaled is not None:
            self.screen.blit(self.menu_background_scaled, (0, 0))
        else:
            self.screen.fill(MENU_BACKGROUND_COLOR)
        self.draw_title("Jumping Cube")
        prompt = self.font.render("Enter your username", True, MENU_TEXT_COLOR)
        self.screen.blit(prompt, (self.screen_width // 2 - prompt.get_width() // 2, self.screen_height // 2 - 80))

        input_rect = pygame.Rect(self.screen_width // 2 - 220, self.screen_height // 2 - 18, 440, 56)
        pygame.draw.rect(self.screen, MENU_TEXT_COLOR, input_rect, border_radius=6)
        username_surface = self.font.render(self.username or "...", True, MENU_BACKGROUND_COLOR)
        self.screen.blit(
            username_surface,
            (input_rect.x + 12, input_rect.y + input_rect.height // 2 - username_surface.get_height() // 2),
        )

        hint = self.small_font.render("Press Enter to continue", True, MENU_TEXT_COLOR)
        self.screen.blit(hint, (self.screen_width // 2 - hint.get_width() // 2, self.screen_height // 2 + 60))

    def draw_main_menu(self) -> None:
        items = self.main_menu_items()
        index = self.menu_indices[Screen.MAIN_MENU]
        subtitle = f"Player: {self.username or 'Unknown'}"
        self.draw_menu_list("Main Menu", [label for label, _ in items], index, subtitle)

        if self.level_errors:
            error_text = self.level_errors[-1]
            display = self.small_font.render(error_text[:90], True, (255, 200, 120))
            self.screen.blit(display, (20, self.screen_height - 75))

    def draw_level_select(self) -> None:
        options = [f"{level.level_id}: {level.name}" for level in self.levels]
        options.append("Back")
        index = self.menu_indices[Screen.LEVEL_SELECT]
        self.draw_menu_list("Mission Select", options, index, "External missions override bundled ones")

    def draw_load_game(self) -> None:
        options = [f for f in self.save_files] if self.save_files else ["No saves found"]
        options.append("Back")
        index = self.menu_indices[Screen.LOAD_GAME]
        self.draw_menu_list("Load Game", options, index, "Select a save file")

    def draw_settings(self) -> None:
        if self.menu_background_scaled is not None:
            self.screen.blit(self.menu_background_scaled, (0, 0))
        else:
            self.screen.fill(MENU_BACKGROUND_COLOR)
        self.draw_title("Settings")

        x = 80
        y_start = 130
        row_height = 34
        width = self.screen_width - 160

        index = self.menu_indices[Screen.SETTINGS]
        self.current_menu_rects = []

        for item_index, (key, label, item_type) in enumerate(self.settings_items):
            y = y_start + item_index * row_height
            rect = pygame.Rect(x, y, width, row_height - 4)
            self.current_menu_rects.append(rect)

            selected = item_index == index
            color = MENU_HIGHLIGHT_COLOR if selected else MENU_TEXT_COLOR
            pygame.draw.rect(self.screen, color, rect, border_radius=5)

            value_text = ""
            if item_type == "slider":
                value = int(self.settings["audio"][key] * 100)
                value_text = f"{value}%"
            elif item_type == "toggle":
                value_text = "ON" if self.settings["display"]["fullscreen"] else "OFF"
            elif item_type == "resolution":
                resolution = self.settings["display"]["resolution"]
                value_text = f"{resolution[0]}x{resolution[1]}"
            elif item_type == "rebind":
                value_text = self.settings["controls"].get(key, "K_UNKNOWN")
            elif key == "back":
                value_text = ""

            text = f"{label}"
            text_surface = self.small_font.render(text, True, MENU_BACKGROUND_COLOR)
            self.screen.blit(text_surface, (rect.x + 10, rect.y + 6))

            if value_text:
                value_surface = self.small_font.render(value_text, True, MENU_BACKGROUND_COLOR)
                self.screen.blit(value_surface, (rect.right - value_surface.get_width() - 10, rect.y + 6))

        hint = "Arrows to navigate | Left/Right to adjust | Enter to select"
        if self.rebinding_action:
            hint = f"Press any key to bind '{self.rebinding_action}' (Esc to cancel)"

        hint_surface = self.small_font.render(hint, True, MENU_TEXT_COLOR)
        self.screen.blit(
            hint_surface,
            (self.screen_width // 2 - hint_surface.get_width() // 2, self.screen_height - 52),
        )

    def draw_pause(self) -> None:
        items = self.pause_menu_items()
        index = self.menu_indices[Screen.PAUSE]
        self.draw_menu_list("Paused", [label for label, _ in items], index)

    def draw_safe_hub(self) -> None:
        items = self.safe_hub_items()
        index = self.menu_indices[Screen.SAFE_HUB]
        subtitle = (
            f"Van Hub  |  Scrap: {self.scrap_bank}  |  HP: {self.player_health_max}  "
            f"DMG: {self.player_damage}  SPD: {self.player_speed_bonus:+.1f}"
        )
        self.draw_menu_list("Safe Van", [label for label, _ in items], index, subtitle)

    def draw_win(self) -> None:
        items = self.win_menu_items()
        index = self.menu_indices[Screen.WIN]
        self.draw_menu_list("Expedition Complete", [label for label, _ in items], index)

    def draw_game_over(self) -> None:
        items = self.game_over_items()
        index = self.menu_indices[Screen.GAME_OVER]
        self.draw_menu_list("Game Over", [label for label, _ in items], index)

    def draw_gameplay(self) -> None:
        self.screen.blit(self.background_scaled, (0, 0))

        extraction_color = (72, 212, 133) if self.current_level and self.collected_coins >= self.current_level.required_scrap else (82, 102, 128)
        pygame.draw.rect(self.screen, extraction_color, self.extraction_zone, border_radius=8)
        van_label = self.small_font.render("VAN", True, (15, 24, 20))
        self.screen.blit(
            van_label,
            (
                self.extraction_zone.x + self.extraction_zone.width // 2 - van_label.get_width() // 2,
                self.extraction_zone.y + self.extraction_zone.height // 2 - van_label.get_height() // 2,
            ),
        )

        for obstacle in self.platforms:
            platform_surface = pygame.transform.scale(self.platform_image, (obstacle.width, obstacle.height))
            self.screen.blit(platform_surface, (obstacle.x, obstacle.y))

        for scrap in self.coins:
            coin_surface = pygame.transform.scale(self.coin_image, (scrap.width, scrap.height))
            self.screen.blit(coin_surface, (scrap.x, scrap.y))

        for enemy in self.enemies:
            rect = enemy["rect"]
            pygame.draw.rect(self.screen, (188, 76, 76), rect, border_radius=6)
            hp_ratio = 0.0
            if self.current_level and self.current_level.enemy_health > 0:
                hp_ratio = clamp(enemy["hp"] / self.current_level.enemy_health, 0.0, 1.0)
            hp_width = max(0, int(rect.width * hp_ratio))
            hp_rect = pygame.Rect(rect.x, rect.y - 8, hp_width, 4)
            pygame.draw.rect(self.screen, (236, 104, 104), hp_rect)

        for bullet in self.bullets:
            pygame.draw.circle(self.screen, (255, 236, 146), (int(bullet["x"]), int(bullet["y"])), int(bullet["radius"]))

        self.screen.blit(self.square_image, (int(self.player_x), int(self.player_y)))

        if self.current_level:
            level_name = self.small_font.render(f"Mission: {self.current_level.name}", True, (255, 255, 255))
            self.screen.blit(level_name, (10, 10))

            scrap_text = self.small_font.render(
                f"Scrap: {self.collected_coins}/{self.current_level.required_scrap}  |  Bank: {self.scrap_bank}",
                True,
                (255, 255, 255),
            )
            self.screen.blit(scrap_text, (10, 36))

            health_text = self.small_font.render(
                f"HP: {self.player_health}/{self.player_health_max}  |  Damage: {self.player_damage}",
                True,
                (255, 255, 255),
            )
            self.screen.blit(health_text, (10, 62))

            elapsed_sec = max(0, (pygame.time.get_ticks() - self.level_start_ticks) // 1000)
            remaining = max(0, self.current_level.time_limit_sec - elapsed_sec)
            time_text = self.small_font.render(f"Time: {remaining}s", True, (255, 255, 255))
            self.screen.blit(time_text, (10, 88))

            objective_text = self.small_font.render(
                "Objective: clear enemies for scrap, then reach the VAN",
                True,
                (255, 255, 255),
            )
            self.screen.blit(objective_text, (10, self.screen_height - 30))

        border_color = (255, 255, 255)
        if self.player_health < max(25, self.player_health_max * 0.35):
            border_color = random.choice(COLORS)

        pygame.draw.rect(self.screen, border_color, (0, 0, self.screen_width, self.border_thickness))
        pygame.draw.rect(self.screen, border_color, (0, 0, self.border_thickness, self.screen_height))
        pygame.draw.rect(
            self.screen,
            border_color,
            (0, self.screen_height - self.border_thickness, self.screen_width, self.border_thickness),
        )
        pygame.draw.rect(
            self.screen,
            border_color,
            (self.screen_width - self.border_thickness, 0, self.border_thickness, self.screen_height),
        )

    def draw(self) -> None:
        if self.screen_state == Screen.USERNAME:
            self.draw_username_screen()
        elif self.screen_state == Screen.MAIN_MENU:
            self.draw_main_menu()
        elif self.screen_state == Screen.LEVEL_SELECT:
            self.draw_level_select()
        elif self.screen_state == Screen.GAMEPLAY:
            self.draw_gameplay()
        elif self.screen_state == Screen.SAFE_HUB:
            self.draw_safe_hub()
        elif self.screen_state == Screen.PAUSE:
            self.draw_pause()
        elif self.screen_state == Screen.SETTINGS:
            self.draw_settings()
        elif self.screen_state == Screen.LOAD_GAME:
            self.draw_load_game()
        elif self.screen_state == Screen.WIN:
            self.draw_win()
        elif self.screen_state == Screen.GAME_OVER:
            self.draw_game_over()

        self.draw_status()
        pygame.display.flip()

    def stop_running(self) -> None:
        self.running = False

    def handle_list_menu_event(
        self,
        event: pygame.event.Event,
        screen: Screen,
        items: List[Tuple[str, callable]],
        back_action=None,
    ) -> None:
        if not items:
            return

        index = self.menu_indices.get(screen, 0)
        index = int(clamp(index, 0, len(items) - 1))

        if event.type == pygame.KEYDOWN:
            if self.action_matches_event(event, "menu_up"):
                index = (index - 1) % len(items)
                self.audio.play_sfx("menu_move")
            elif self.action_matches_event(event, "menu_down"):
                index = (index + 1) % len(items)
                self.audio.play_sfx("menu_move")
            elif self.action_matches_event(event, "menu_select"):
                self.audio.play_sfx("menu_select")
                items[index][1]()
            elif self.action_matches_event(event, "menu_back") and back_action:
                self.audio.play_sfx("menu_select")
                back_action()

        elif event.type == pygame.MOUSEMOTION:
            for i, rect in enumerate(self.current_menu_rects):
                if rect.collidepoint(event.pos):
                    index = i
                    break

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, rect in enumerate(self.current_menu_rects):
                if rect.collidepoint(event.pos):
                    index = i
                    self.audio.play_sfx("menu_select")
                    items[index][1]()
                    break

        self.menu_indices[screen] = index

    def resolve_resolution_index(self) -> int:
        current = tuple(self.settings["display"]["resolution"])
        if current in DEFAULT_RESOLUTIONS:
            return DEFAULT_RESOLUTIONS.index(current)
        return 0

    def update_settings_item(self, direction: int) -> None:
        index = self.menu_indices[Screen.SETTINGS]
        key, _, item_type = self.settings_items[index]

        if item_type == "slider":
            current = self.settings["audio"][key]
            self.settings["audio"][key] = float(clamp(current + (0.05 * direction), 0.0, 1.0))
            self.audio.apply_settings(self.settings["audio"])
            self.audio.play_sfx("menu_move")
            save_settings(self.settings)

        elif item_type == "toggle" and key == "fullscreen":
            self.settings["display"]["fullscreen"] = not self.settings["display"]["fullscreen"]
            self._apply_display_settings(persist=True)
            self._rescale_background()
            self.audio.play_sfx("menu_select")

        elif item_type == "resolution":
            resolution_index = self.resolve_resolution_index()
            resolution_index = (resolution_index + direction) % len(DEFAULT_RESOLUTIONS)
            new_resolution = DEFAULT_RESOLUTIONS[resolution_index]
            self.settings["display"]["resolution"] = [new_resolution[0], new_resolution[1]]
            self._apply_display_settings(persist=True)
            self._rescale_background()
            self.audio.play_sfx("menu_move")

    def start_rebind(self, action: str) -> None:
        self.rebinding_action = action
        self.show_status(f"Press a key for {action}", 3000)

    def finish_rebind(self, key_code: int) -> None:
        if self.rebinding_action is None:
            return
        key_name = key_name_from_code(key_code)
        if key_name == "K_UNKNOWN":
            self.show_status("Unsupported key")
            return

        for action_name, assigned_key in self.settings["controls"].items():
            if action_name != self.rebinding_action and assigned_key == key_name:
                self.show_status(f"{key_name} already assigned to {action_name}")
                return

        self.settings["controls"][self.rebinding_action] = key_name
        save_settings(self.settings)
        self.rebinding_action = None
        self.audio.play_sfx("menu_select")
        self.show_status("Control updated")

    def handle_settings_event(self, event: pygame.event.Event) -> None:
        if self.rebinding_action:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.rebinding_action = None
                    self.show_status("Rebind cancelled")
                else:
                    self.finish_rebind(event.key)
            return

        index = self.menu_indices[Screen.SETTINGS]
        index = int(clamp(index, 0, len(self.settings_items) - 1))

        if event.type == pygame.KEYDOWN:
            if self.action_matches_event(event, "menu_up"):
                index = (index - 1) % len(self.settings_items)
                self.audio.play_sfx("menu_move")
            elif self.action_matches_event(event, "menu_down"):
                index = (index + 1) % len(self.settings_items)
                self.audio.play_sfx("menu_move")
            elif event.key == pygame.K_LEFT:
                self.update_settings_item(-1)
            elif event.key == pygame.K_RIGHT:
                self.update_settings_item(1)
            elif self.action_matches_event(event, "menu_back"):
                self.transition_to(self.settings_return_screen)
            elif self.action_matches_event(event, "menu_select"):
                key, _, item_type = self.settings_items[index]
                if item_type == "rebind":
                    self.start_rebind(key)
                elif item_type == "toggle":
                    self.update_settings_item(1)
                elif item_type == "resolution":
                    self.update_settings_item(1)
                elif key == "back":
                    self.transition_to(self.settings_return_screen)

        elif event.type == pygame.MOUSEMOTION:
            for i, rect in enumerate(self.current_menu_rects):
                if rect.collidepoint(event.pos):
                    index = i
                    break

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, rect in enumerate(self.current_menu_rects):
                if rect.collidepoint(event.pos):
                    index = i
                    key, _, item_type = self.settings_items[index]
                    if item_type == "rebind":
                        self.start_rebind(key)
                    elif item_type == "slider":
                        local_x = event.pos[0] - rect.x
                        ratio = clamp(local_x / rect.width, 0.0, 1.0)
                        self.settings["audio"][key] = float(ratio)
                        self.audio.apply_settings(self.settings["audio"])
                        save_settings(self.settings)
                        self.audio.play_sfx("menu_move")
                    elif item_type == "toggle":
                        self.update_settings_item(1)
                    elif item_type == "resolution":
                        self.update_settings_item(1)
                    elif key == "back":
                        self.transition_to(self.settings_return_screen)
                    break

        self.menu_indices[Screen.SETTINGS] = index

    def _move_player_axis(self, delta_x: float, delta_y: float) -> None:
        if delta_x != 0.0:
            self.player_x += delta_x
            player_rect = pygame.Rect(int(self.player_x), int(self.player_y), self.square_size, self.square_size)
            for obstacle in self.platforms:
                if not player_rect.colliderect(obstacle):
                    continue
                if delta_x > 0:
                    self.player_x = obstacle.left - self.square_size
                elif delta_x < 0:
                    self.player_x = obstacle.right
                player_rect.x = int(self.player_x)

        if delta_y != 0.0:
            self.player_y += delta_y
            player_rect = pygame.Rect(int(self.player_x), int(self.player_y), self.square_size, self.square_size)
            for obstacle in self.platforms:
                if not player_rect.colliderect(obstacle):
                    continue
                if delta_y > 0:
                    self.player_y = obstacle.top - self.square_size
                elif delta_y < 0:
                    self.player_y = obstacle.bottom
                player_rect.y = int(self.player_y)

    def try_jump(self) -> None:
        if self.current_level is None:
            return

        now = pygame.time.get_ticks()
        cooldown_ms = max(90, 190 - (self.upgrade_levels.get("weapon", 0) * 10))
        if now - self.last_shot_ms < cooldown_ms:
            return
        self.last_shot_ms = now

        center_x = self.player_x + (self.square_size * 0.5)
        center_y = self.player_y + (self.square_size * 0.5)

        target_x = center_x
        target_y = center_y - 1
        nearest_distance = float("inf")

        for enemy in self.enemies:
            rect = enemy["rect"]
            enemy_x = rect.centerx
            enemy_y = rect.centery
            distance = math.hypot(enemy_x - center_x, enemy_y - center_y)
            if distance < nearest_distance:
                nearest_distance = distance
                target_x = enemy_x
                target_y = enemy_y

        dx = target_x - center_x
        dy = target_y - center_y
        distance = max(1.0, math.hypot(dx, dy))

        bullet_speed = 10.5
        self.bullets.append(
            {
                "x": center_x,
                "y": center_y,
                "vx": (dx / distance) * bullet_speed,
                "vy": (dy / distance) * bullet_speed,
                "born_ms": now,
                "life_ms": 900,
                "radius": 4,
            }
        )
        self.audio.play_sfx("shoot")

    def handle_username_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_RETURN and self.username.strip():
            self.username = self.username.strip()
            self.update_save_files()
            self.transition_to(Screen.MAIN_MENU)
            self.show_status(f"Welcome {self.username}")
        elif event.key == pygame.K_BACKSPACE:
            self.username = self.username[:-1]
        elif event.key == pygame.K_ESCAPE:
            self.stop_running()
        else:
            if event.unicode and event.unicode.isprintable() and len(self.username) < 18:
                self.username += event.unicode

    def handle_main_menu_event(self, event: pygame.event.Event) -> None:
        self.handle_list_menu_event(
            event,
            Screen.MAIN_MENU,
            self.main_menu_items(),
            back_action=self.stop_running,
        )

    def handle_level_select_event(self, event: pygame.event.Event) -> None:
        items: List[Tuple[str, callable]] = []
        for index, _level in enumerate(self.levels):
            items.append(("", lambda i=index: self.start_level(i)))
        items.append(("Back", lambda: self.transition_to(Screen.MAIN_MENU)))

        self.handle_list_menu_event(
            event,
            Screen.LEVEL_SELECT,
            items,
            back_action=lambda: self.transition_to(Screen.MAIN_MENU),
        )

    def handle_pause_event(self, event: pygame.event.Event) -> None:
        self.handle_list_menu_event(
            event,
            Screen.PAUSE,
            self.pause_menu_items(),
            back_action=lambda: self.transition_to(Screen.GAMEPLAY),
        )

    def handle_safe_hub_event(self, event: pygame.event.Event) -> None:
        self.handle_list_menu_event(
            event,
            Screen.SAFE_HUB,
            self.safe_hub_items(),
            back_action=lambda: self.transition_to(Screen.MAIN_MENU),
        )

    def handle_win_event(self, event: pygame.event.Event) -> None:
        self.handle_list_menu_event(
            event,
            Screen.WIN,
            self.win_menu_items(),
            back_action=lambda: self.transition_to(Screen.MAIN_MENU),
        )

    def handle_game_over_event(self, event: pygame.event.Event) -> None:
        self.handle_list_menu_event(
            event,
            Screen.GAME_OVER,
            self.game_over_items(),
            back_action=lambda: self.transition_to(Screen.MAIN_MENU),
        )

    def handle_load_game_event(self, event: pygame.event.Event) -> None:
        items: List[Tuple[str, callable]] = []

        if self.save_files:
            for save_name in self.save_files:
                items.append((save_name, lambda name=save_name: self.load_game(name)))
        else:
            items.append(("No saves found", lambda: None))

        items.append(("Back", lambda: self.transition_to(self.load_return_screen)))

        self.handle_list_menu_event(
            event,
            Screen.LOAD_GAME,
            items,
            back_action=lambda: self.transition_to(self.load_return_screen),
        )

    def handle_gameplay_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if self.action_matches_event(event, "pause"):
                self.transition_to(Screen.PAUSE)
                return
            if self.action_matches_event(event, "jump"):
                self.try_jump()
                return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.try_jump()
            return

        if event.type == pygame.ACTIVEEVENT and event.state == 2 and not event.gain:
            self.transition_to(Screen.PAUSE)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self.stop_running()
            return

        if self.screen_state == Screen.USERNAME:
            self.handle_username_event(event)
        elif self.screen_state == Screen.MAIN_MENU:
            self.handle_main_menu_event(event)
        elif self.screen_state == Screen.LEVEL_SELECT:
            self.handle_level_select_event(event)
        elif self.screen_state == Screen.GAMEPLAY:
            self.handle_gameplay_event(event)
        elif self.screen_state == Screen.SAFE_HUB:
            self.handle_safe_hub_event(event)
        elif self.screen_state == Screen.PAUSE:
            self.handle_pause_event(event)
        elif self.screen_state == Screen.SETTINGS:
            self.handle_settings_event(event)
        elif self.screen_state == Screen.LOAD_GAME:
            self.handle_load_game_event(event)
        elif self.screen_state == Screen.WIN:
            self.handle_win_event(event)
        elif self.screen_state == Screen.GAME_OVER:
            self.handle_game_over_event(event)

    def update_gameplay(self) -> None:
        if self.current_level is None:
            return

        keys = pygame.key.get_pressed()
        move_x = 0.0
        move_y = 0.0
        if self.action_pressed(keys, "move_left"):
            move_x -= 1.0
        if self.action_pressed(keys, "move_right"):
            move_x += 1.0
        if self.action_pressed(keys, "menu_up"):
            move_y -= 1.0
        if self.action_pressed(keys, "menu_down"):
            move_y += 1.0

        movement_length = math.hypot(move_x, move_y)
        if movement_length > 0:
            move_x /= movement_length
            move_y /= movement_length

        player_speed = max(1.0, self.current_level.player_speed + self.player_speed_bonus)
        self._move_player_axis(move_x * player_speed, 0.0)
        self._move_player_axis(0.0, move_y * player_speed)

        self.player_x = clamp(self.player_x, 0, self.screen_width - self.square_size)
        self.player_y = clamp(self.player_y, 0, self.screen_height - self.square_size)

        now = pygame.time.get_ticks()

        for bullet in self.bullets[:]:
            bullet["x"] += bullet["vx"]
            bullet["y"] += bullet["vy"]

            bullet_rect = pygame.Rect(
                int(bullet["x"] - bullet["radius"]),
                int(bullet["y"] - bullet["radius"]),
                int(bullet["radius"] * 2),
                int(bullet["radius"] * 2),
            )

            expired = now - bullet["born_ms"] > bullet["life_ms"]
            out_of_bounds = (
                bullet["x"] < -20
                or bullet["x"] > self.screen_width + 20
                or bullet["y"] < -20
                or bullet["y"] > self.screen_height + 20
            )
            hit_wall = any(bullet_rect.colliderect(obstacle) for obstacle in self.platforms)
            if expired or out_of_bounds or hit_wall:
                self.bullets.remove(bullet)
                continue

            hit_enemy = None
            for enemy in self.enemies:
                if bullet_rect.colliderect(enemy["rect"]):
                    hit_enemy = enemy
                    break

            if hit_enemy is not None:
                hit_enemy["hp"] -= self.player_damage
                self.audio.play_sfx("hit")
                if bullet in self.bullets:
                    self.bullets.remove(bullet)
                if hit_enemy["hp"] <= 0:
                    drop_size = self.coin_size_default
                    drop_x = hit_enemy["rect"].centerx - drop_size // 2
                    drop_y = hit_enemy["rect"].centery - drop_size // 2
                    self.coins.append(pygame.Rect(drop_x, drop_y, drop_size, drop_size))
                    self.enemies.remove(hit_enemy)

        player_rect = pygame.Rect(int(self.player_x), int(self.player_y), self.square_size, self.square_size)

        for enemy in self.enemies:
            enemy.setdefault("fx", float(enemy["rect"].x))
            enemy.setdefault("fy", float(enemy["rect"].y))

            dx = player_rect.centerx - enemy["rect"].centerx
            dy = player_rect.centery - enemy["rect"].centery
            distance = max(1.0, math.hypot(dx, dy))
            step_x = (dx / distance) * enemy["speed"]
            step_y = (dy / distance) * enemy["speed"]

            enemy["fx"] += step_x
            enemy["rect"].x = int(enemy["fx"])
            for obstacle in self.platforms:
                if enemy["rect"].colliderect(obstacle):
                    enemy["fx"] -= step_x
                    enemy["rect"].x = int(enemy["fx"])
                    break

            enemy["fy"] += step_y
            enemy["rect"].y = int(enemy["fy"])
            for obstacle in self.platforms:
                if enemy["rect"].colliderect(obstacle):
                    enemy["fy"] -= step_y
                    enemy["rect"].y = int(enemy["fy"])
                    break

            if player_rect.colliderect(enemy["rect"]):
                if now - self.last_player_hit_ms > 700:
                    self.last_player_hit_ms = now
                    self.player_health -= self.current_level.enemy_touch_damage
                    self.audio.play_sfx("hit")

        for scrap in self.coins[:]:
            if player_rect.colliderect(scrap):
                self.coins.remove(scrap)
                self.collected_coins += 1
                self.audio.play_sfx("pickup")

        if self.player_health <= 0:
            self.player_health = 0
            self.audio.play_sfx("lose")
            self.transition_to(Screen.GAME_OVER)
            return

        elapsed_sec = (pygame.time.get_ticks() - self.level_start_ticks) // 1000
        if elapsed_sec >= self.current_level.time_limit_sec:
            self.audio.play_sfx("lose")
            self.transition_to(Screen.GAME_OVER)
            return

        objective_met = self.collected_coins >= self.current_level.required_scrap
        if objective_met and player_rect.colliderect(self.extraction_zone):
            self.scrap_bank += self.collected_coins
            self.audio.play_sfx("win")
            if self.current_level_index < len(self.levels) - 1:
                self.pending_level_index = self.current_level_index + 1
                self.transition_to(Screen.SAFE_HUB)
                self.show_status("Mission complete. Back to the van.")
            else:
                self.transition_to(Screen.WIN)
                self.show_status("Final mission complete.")

    def run(self) -> None:
        while self.running:
            for event in pygame.event.get():
                self.handle_event(event)

            if self.screen_state == Screen.GAMEPLAY:
                self.update_gameplay()

            self.draw()
            self.clock.tick(60)

        self.audio.stop_music()
        pygame.quit()


def main() -> None:
    game = JumpingCubeGame()
    game.run()


if __name__ == "__main__":
    main()
