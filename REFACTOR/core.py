import os
import json
import random
import math
import time
import pygame
import copy
import sys
import random
import traceback
import re
import webbrowser
import shutil
from urllib.parse import urlparse
from datetime import datetime

# ----------------------------
# 1. LOGGING & EXE PATHS
# ----------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(SCRIPT_DIR, "Docs")
LEGACY_DOCS_DIR = os.path.join(os.path.expanduser("~"), "Documents", "THE GOD FILE")
APP_DATA_DIR = DOCS_DIR
LOCAL_SETTINGS_FILE = os.path.join(SCRIPT_DIR, "user_settings.json")
LOCAL_SAVE_DIR = os.path.join(SCRIPT_DIR, "saves")

try:
    os.makedirs(APP_DATA_DIR, exist_ok=True)
except Exception:
    APP_DATA_DIR = SCRIPT_DIR

LOG_FILE = os.path.join(APP_DATA_DIR, "session_log.txt")
SETTINGS_FILE = os.path.join(APP_DATA_DIR, "user_settings.json")
SAVE_DIR = os.path.join(APP_DATA_DIR, "saves")

def _migrate_legacy_user_files():
    try:
        if not os.path.exists(SETTINGS_FILE):
            legacy_settings_file = os.path.join(LEGACY_DOCS_DIR, "user_settings.json")
            if os.path.exists(legacy_settings_file):
                shutil.copy2(legacy_settings_file, SETTINGS_FILE)
    except Exception:
        pass
    try:
        if not os.path.exists(SETTINGS_FILE) and os.path.exists(LOCAL_SETTINGS_FILE):
            shutil.copy2(LOCAL_SETTINGS_FILE, SETTINGS_FILE)
    except Exception:
        pass
    try:
        legacy_save_dir = os.path.join(LEGACY_DOCS_DIR, "saves")
        if os.path.isdir(legacy_save_dir):
            os.makedirs(SAVE_DIR, exist_ok=True)
            for filename in os.listdir(legacy_save_dir):
                if filename.lower().endswith(".json"):
                    old_path = os.path.join(legacy_save_dir, filename)
                    new_path = os.path.join(SAVE_DIR, filename)
                    if os.path.isfile(old_path) and not os.path.exists(new_path):
                        shutil.copy2(old_path, new_path)
    except Exception:
        pass
    try:
        if os.path.isdir(LOCAL_SAVE_DIR):
            os.makedirs(SAVE_DIR, exist_ok=True)
            for filename in os.listdir(LOCAL_SAVE_DIR):
                if filename.lower().endswith(".json"):
                    old_path = os.path.join(LOCAL_SAVE_DIR, filename)
                    new_path = os.path.join(SAVE_DIR, filename)
                    if os.path.isfile(old_path) and not os.path.exists(new_path):
                        shutil.copy2(old_path, new_path)
    except Exception:
        pass

_migrate_legacy_user_files()

def log_event(message, is_error=False):
    timestamp = datetime.now().strftime("%H:%M:%S")
    prefix = "[ERROR] " if is_error else "[INFO]  "
    log_entry = f"{timestamp} {prefix}{message}"
    print(log_entry)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")
            f.flush()
    except: pass

def load_user_settings():
    defaults = {
        "menu_music_enabled": True,
        "menu_music_volume": 70,
        "audio_enabled": True,
        "sfx_enabled": True,
        "menu_videos_enabled": True,
        "card_videos_enabled": True,
        "autosave_enabled": False,
        "autosave_interval_min": 5,
    }
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                defaults.update(raw)
    except Exception as ex:
        log_event(f"Could not load settings: {ex}", is_error=True)
    defaults["menu_music_volume"] = int(clamp(defaults.get("menu_music_volume", 70), 0, 100))
    defaults["menu_music_enabled"] = bool(defaults.get("menu_music_enabled", True))
    defaults["audio_enabled"] = bool(defaults.get("audio_enabled", True))
    defaults["sfx_enabled"] = bool(defaults.get("sfx_enabled", True))
    defaults["menu_videos_enabled"] = bool(defaults.get("menu_videos_enabled", True))
    defaults["card_videos_enabled"] = bool(defaults.get("card_videos_enabled", True))
    defaults["autosave_enabled"] = bool(defaults.get("autosave_enabled", False))
    _autosave_raw = defaults.get("autosave_interval_min", 5)
    try:
        _autosave_raw = int(_autosave_raw)
    except Exception:
        _autosave_raw = 5
    defaults["autosave_interval_min"] = int(clamp(round(_autosave_raw / 5) * 5, 5, 30))
    return defaults

def save_user_settings(settings):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    except Exception as ex:
        log_event(f"Could not save settings: {ex}", is_error=True)

def resource_path(relative_path):
    candidates = []
    meipass_path = getattr(sys, '_MEIPASS', None)
    if meipass_path:
        candidates.append(meipass_path)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates.append(script_dir)
    candidates.append(os.path.abspath("."))

    for base_path in candidates:
        full_path = os.path.join(base_path, relative_path)
        if os.path.exists(full_path):
            return full_path

    return os.path.join(script_dir, relative_path)

def docs_or_resource_path(filename):
    candidates = [
        os.path.join(DOCS_DIR, filename),
        resource_path(os.path.join("Docs", filename)),
        resource_path(filename),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return os.path.join(DOCS_DIR, filename)

# ----------------------------
# 2. GLOBAL CONSTANTS
# ----------------------------
FPS = 60
PANEL_W, PADDING, PANEL_INNER_PAD = 420, 20, 30 
HAND_CARD_W, HAND_CARD_H = 260, 370 
VIEW_CARD_W, VIEW_CARD_H = 210, 300 
CARD_RADIUS = 20
TOAST_DURATION = 3.0
DRAW_DELAY_TIME = 0.4 
SHUFFLE_ANIM_DURATION = 0.8

CELL_SPACING_X, CELL_SPACING_Y = 50, 160 
CELL_W, CELL_H = VIEW_CARD_W + CELL_SPACING_X, VIEW_CARD_H + CELL_SPACING_Y
VIEW_START_X, VIEW_START_Y = 80, 120

HAND_GRID_SPACING_X = 290
HAND_GRID_SPACING_Y = 515 
MAIN_MENU_MUSIC = resource_path(os.path.join("audio", "main menu.mp3"))
LIBRARY_MUSIC = resource_path(os.path.join("audio", "Library.mp3"))
SPELL_LIBRARY_MUSIC = resource_path(os.path.join("audio", "Spell Library.mp3"))
GLOSSARY_MUSIC = resource_path(os.path.join("audio", "Glossary.mp3"))
PPF_BG_MUSIC = resource_path(os.path.join("audio", "PP&F_BG.mp3"))
BUTTON_PRESS_SOUND = resource_path(os.path.join("audio", "button-press.mp3"))
TURNPAGE_SOUND = resource_path(os.path.join("audio", "turnpage.mp3"))
MAJOR_PROMOTION_SOUND = resource_path(os.path.join("audio", "MFortune_promotion.mp3"))
FORTUNE_PROMOTION_SOUND = resource_path(os.path.join("audio", "fortune_promotion.mp3"))
POT_OF_GREED_SOUND = resource_path(os.path.join("audio", "I SUMMON POT OF GREED.wav"))
VANISH_FX_SOUND = resource_path(os.path.join("audio", "Vanish_FX.wav"))

AUDIO_DIR = resource_path("audio")
IMAGES_DIR = resource_path("images")
CARDS_JSON = docs_or_resource_path("cards.json")
DECK_BACK_IMAGE = "21-Tarot_Back.png"
VANISHED_CARD_IMAGE = "Vanished.png"
DECK_PILE_IMAGE = "Deck_Pile.png"
VANISH_PILE_IMAGE = "Vanish_Pile.png"
SHUFFLE_SOUND = resource_path(os.path.join("audio", "shuffle.wav"))
VIDEOS_DIR = resource_path("videos")
DECK_VIEW_MUSIC = resource_path(os.path.join("audio", "Deck_View.mp3"))
VANISHED_PILE_MUSIC = resource_path(os.path.join("audio", "Vanished_Pile.mp3"))
VANISHED_PILE_ALT_MUSIC = resource_path(os.path.join("audio", "Vanished_2.mp3"))
MENU_BG_IMAGE = "Teller_Room.png"
NORMAL_BG_IMAGE = "BG_3.png"
MAX_SAVE_SLOTS = 3
MAX_AUTOSAVE_SLOTS = 10

GOLD, RED_FIRE, ORANGE_FIRE, YELLOW_FIRE, PURPLE_TAP = (235, 190, 60), (220, 30, 30), (255, 120, 0), (255, 200, 0), (180, 50, 255)
PINK_D20 = (255, 100, 220)
PURPLE_FIRE = (180, 50, 255)
MAJOR_FORTUNE_IDS = [13, 16, 20]
FORTUNE_UNLOCKS = {
    6: [2, 3, 5, 6, 7, 10, 11],
    9: [1, 4, 8, 9, 12, 14, 15, 17],
    13: [18, 19],
}
MAJOR_UNLOCKS_17 = [13, 16, 20]

# ----------------------------
# 3. HELPER FUNCTIONS
# ----------------------------
def find_bold_markdown(data, path=""):
    found_items = []
    bold_pattern = r'\*\*(.*?)\*\*'
    if isinstance(data, dict):
        for key, value in data.items():
            new_path = f"{path}.{key}" if path else key
            found_items.extend(find_bold_markdown(value, new_path))
    elif isinstance(data, list):
        for index, value in enumerate(data):
            new_path = f"{path}[{index}]"
            found_items.extend(find_bold_markdown(value, new_path))
    elif isinstance(data, str):
        matches = re.findall(bold_pattern, data)
        if matches:
            found_items.append(f"{path}: {', '.join(matches)}")
    return found_items

def clamp(x, a, b): return max(a, min(b, x))

def draw_round_rect(surf, rect, color, radius=12, width=0): 
    pygame.draw.rect(surf, color, rect, border_radius=radius, width=width)

def extract_links(text):
    return re.findall(r'\[([^\]]+)\]\(([^\)]+)\)', str(text))

def normalize_aidedd_spell_url(url, label=""):
    raw_url = str(url).strip()
    if raw_url and not re.match(r'^https?://', raw_url, re.IGNORECASE):
        raw_url = f"https://{raw_url.lstrip('/')}"

    parsed = urlparse(raw_url) if raw_url else None
    if parsed and parsed.scheme in ("http", "https") and parsed.netloc.lower().endswith("aidedd.org"):
        return raw_url

    slug = re.sub(r'[^a-z0-9]+', '-', str(label).lower()).strip('-')
    if slug:
        return f"https://www.aidedd.org/dnd/sorts.php?vo={slug}"
    return "https://www.aidedd.org/dnd/sorts.php"

def get_unique_preview_links(card_data, mode_key):
    raw_links = extract_links(card_data.get(f'{mode_key}_inverted', "")) + extract_links(card_data.get(f'{mode_key}_upright', ""))
    unique_links = []
    seen_urls = set()
    for label, url in raw_links:
        safe_url = normalize_aidedd_spell_url(url, label)
        key = safe_url.lower()
        if key in seen_urls:
            continue
        seen_urls.add(key)
        unique_links.append((label, safe_url))
    return unique_links

def draw_card_glitter(surf, rect, t, style="gold"):
    if rect.w <= 0 or rect.h <= 0:
        return
    metallic_overlay = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    speed_factor = 0.16
    num_particles = int(rect.w * rect.h * 0.012)
    if style == "red":
        base_shades = [(170, 45, 45, 70), (210, 60, 60, 80), (150, 35, 35, 60), (230, 90, 90, 90), (130, 30, 30, 50)]
        pulse_color = (255, 145, 145, 190)
    else:
        base_shades = [(195, 155, 50, 70), (215, 175, 70, 80), (185, 135, 40, 60), (225, 195, 95, 90), (175, 125, 30, 50)]
        pulse_color = (255, 240, 145, 190)
    pulse_period = 2.2
    for i in range(num_particles):
        seed = i * 9973
        base_x = seed % rect.w
        base_y = (seed // rect.w) % rect.h
        drift_x = int(math.sin(t * speed_factor + seed) * 8)
        drift_y = int(math.cos(t * speed_factor + seed * 1.3) * 8)
        x = (base_x + drift_x) % rect.w
        y = (base_y + drift_y) % rect.h
        pulse = 0.5 * (1 + math.sin(t * (2 * math.pi / pulse_period) + seed))
        color = pulse_color if pulse > 0.85 else base_shades[seed % len(base_shades)]
        radius = 1 if (seed % 5) else 2
        pygame.draw.circle(metallic_overlay, color, (x, y), radius)
    surf.blit(metallic_overlay, rect.topleft)

def get_card_grid_max_scroll(item_count, screen_h):
    if item_count <= 0:
        return 0
    rows = (item_count + 5) // 6
    content_top = VIEW_START_Y + 160
    content_bottom = content_top + (rows - 1) * CELL_H + VIEW_CARD_H
    visible_bottom = screen_h - 40
    return max(0, content_bottom - visible_bottom)

# ----------------------------
# 4. RICH TEXT ENGINE
# ----------------------------
def get_token_color(text, is_bold, is_link):
    if is_link: return (80, 180, 255)   # BLUE: Spells
    if is_bold:
        t = text.lower()
        # RED: Actions/Disadvantage
        if any(w in t for w in ["action", "reaction", "bonus action", "disadvantage", "fail", "failure", "attack"]):
            return (255, 80, 80)
        # GREEN: Conditions/Advantage/Range/Time
        if any(w in t for w in ["advantage", "feet", "ft", "minute", "hour", "day", "round", "stunned", "charmed", "frightened", "exhaustion", "invisible", "resistance", "immunity", "rest"]):
            return (80, 255, 120)
        return GOLD # Default Bold
    return (230, 240, 255) # Normal Text

def tokenize_markdown(text):
    pattern = r'(\[.*?\]\(.*?\))|(\*\*.*?\*\*)|([^\*\[]+|[\*\[])'
    tokens = []
    for match in re.finditer(pattern, str(text)):
        raw = match.group(0)
        if raw.startswith('[') and '](' in raw:
            name = raw[1:raw.find(']')]
            tokens.append({'text': name, 'bold': True, 'link': True})
        elif raw.startswith('**') and raw.endswith('**'):
            tokens.append({'text': raw[2:-2], 'bold': True, 'link': False})
        else:
            tokens.append({'text': raw, 'bold': False, 'link': False})
    return tokens

class RichTextRenderer:
    def __init__(self, font_reg, font_bold):
        self.font_reg = font_reg
        self.font_bold = font_bold

    def draw_rich_box(self, surf, rect, text, scroll_offset, bar_on_left=False, show_scrollbar=True):
        draw_round_rect(surf, rect, (15, 18, 25), 14)
        pygame.draw.rect(surf, (180, 160, 100), rect, 2, 14)
        
        tokens = tokenize_markdown(text)
        margin, line_h = 15, self.font_reg.get_height() + 6
        max_w = rect.width - (margin * 2)
        lines, cur_line, cur_x = [], [], 0
        
        for tok in tokens:
            paragraphs = tok['text'].split('\n')
            for p_idx, p_text in enumerate(paragraphs):
                if p_idx > 0:
                    lines.append(cur_line)
                    cur_line, cur_x = [], 0

                words = p_text.split(' ')
                for i, word in enumerate(words):
                    if not word and i > 0: continue 
                    space = " " if i < len(words)-1 else ""
                    w_str = word + space
                    f = self.font_bold if tok['bold'] else self.font_reg
                    word_w = f.size(w_str)[0]
                    
                    if cur_x + word_w > max_w:
                        lines.append(cur_line)
                        cur_line, cur_x = [], 0
                    
                    color = get_token_color(w_str, tok['bold'], tok['link'])
                    cur_line.append({'img': f.render(w_str, True, color), 'w': word_w})
                    cur_x += word_w
        if cur_line: lines.append(cur_line)

        text_surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        total_h = len(lines) * line_h + margin * 2
        max_scroll = max(0, total_h - rect.h)
        for i, line in enumerate(lines):
            dx, dy = margin, margin + (i * line_h) - scroll_offset
            if -line_h < dy < rect.h:
                for segment in line:
                    text_surf.blit(segment['img'], (dx, dy))
                    dx += segment['w']
        
        surf.blit(text_surf, rect.topleft)

        if show_scrollbar and total_h > rect.h:
            bx = rect.x + 4 if bar_on_left else rect.right - 10
            pygame.draw.rect(surf, (40, 45, 55), (bx, rect.y + 12, 6, rect.h - 24), border_radius=3)
            pygame.draw.rect(surf, (100, 180, 255), (bx, rect.y + 12 + int((rect.h - 24 - 30)*(scroll_offset/max_scroll)), 6, 30), border_radius=3)
        
        return max_scroll

def make_glow(w, h, color):
    s = pygame.Surface((w+24, h+24), pygame.SRCALPHA)
    for i in range(12, 0, -1):
        pygame.draw.rect(s, (*color, int(140*(1-i/12))), (12-i, 12-i, w+i*2, h+i*2), CARD_RADIUS+i)
    return s

def safe_init():
    try: pygame.mixer.pre_init(44100, -16, 2, 128)
    except: pass
    pygame.init()
    try: pygame.mixer.init()
    except: pass
    try: pygame.mixer.set_num_channels(32)
    except: pass
    info = pygame.display.Info()
    w, h = info.current_w, info.current_h
    if w == 0 or h == 0: w, h = 1920, 1080
    surf = pygame.display.set_mode((w, h), pygame.FULLSCREEN | pygame.DOUBLEBUF)
    try: pygame.event.set_grab(True)
    except: pass
    pygame.display.set_caption("Divine Seer Domain")
    return surf, w, h

def load_image_safe(path, size, name="Unknown"):
    try:
        if os.path.exists(path):
            img = pygame.image.load(path).convert_alpha()
            return pygame.transform.smoothscale(img, size)
    except: pass
    surf = pygame.Surface(size, pygame.SRCALPHA)
    surf.fill((30, 35, 45))
    pygame.draw.rect(surf, (255, 255, 255, 40), surf.get_rect(), 2, border_radius=18)
    return surf

def fade_edges_to_alpha(surf, feather=26):
    """Return a copy with alpha faded near the edges."""
    out = surf.copy().convert_alpha()
    w, h = out.get_size()
    feather = max(1, int(feather))
    for x in range(w):
        dx = min(x, w - 1 - x)
        fx = clamp(dx / feather, 0.0, 1.0)
        for y in range(h):
            dy = min(y, h - 1 - y)
            fy = clamp(dy / feather, 0.0, 1.0)
            edge_factor = min(fx, fy)
            if edge_factor < 1.0:
                r, g, b, a = out.get_at((x, y))
                out.set_at((x, y), (r, g, b, int(a * edge_factor)))
    return out

def draw_d20_static(surf, center, radius, value, font, is_reveal=False):
    pts = []
    for i in range(6):
        angle = math.radians(i * 60 - 30)
        pts.append((center[0] + radius * math.cos(angle), center[1] + radius * math.sin(angle)))
    if is_reveal:
        pulse = (math.sin(pygame.time.get_ticks() * 0.01) + 1) / 2
        g_s = pygame.Surface((radius*4, radius*4), pygame.SRCALPHA)
        pygame.draw.circle(g_s, (*PINK_D20, int(60 + 40*pulse)), (radius*2, radius*2), radius*1.5)
        surf.blit(g_s, (center[0]-radius*2, center[1]-radius*2))
    pygame.draw.polygon(surf, (40, 20, 50), pts)
    pygame.draw.polygon(surf, PINK_D20, pts, 3 if is_reveal else 2)
    pygame.draw.line(surf, PINK_D20, pts[0], pts[3], 1)
    pygame.draw.line(surf, PINK_D20, pts[1], pts[4], 1)
    pygame.draw.line(surf, PINK_D20, pts[2], pts[5], 1)
    txt = font.render(str(value), True, (255, 255, 255))
    surf.blit(txt, txt.get_rect(center=center))

def draw_d100_static(surf, center, radius, value, font, is_reveal=False):
    if is_reveal:
        pulse = (math.sin(pygame.time.get_ticks() * 0.01) + 1) / 2
        glow = pygame.Surface((radius * 5, radius * 5), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*GOLD, int(50 + 45 * pulse)), (radius * 2, radius * 2), int(radius * 1.7))
        surf.blit(glow, (center[0] - radius * 2, center[1] - radius * 2))
    pygame.draw.circle(surf, (55, 36, 10), center, radius)
    pygame.draw.circle(surf, GOLD, center, radius, 4 if is_reveal else 3)
    pygame.draw.circle(surf, (255, 235, 170), center, max(6, radius - 16), 2)
    txt = font.render(str(value), True, (255, 250, 220))
    surf.blit(txt, txt.get_rect(center=center))

# ----------------------------
# 5. FX CLASSES
# ----------------------------
class D20RollAnimation:
    def __init__(self, target_value, screen_w, screen_h):
        self.target_value, self.sw, self.sh = target_value, screen_w, screen_h
        self.pos, self.target_pos = [0, screen_h // 2], [screen_w // 2, screen_h // 2]
        self.timer, self.duration, self.phase, self.particles, self.done = 0.0, 2.0, "rolling", [], False
        self.angle_x, self.angle_y, self.angle_z = random.uniform(0, 5), random.uniform(0, 5), random.uniform(0, 5)
        self.rot_speed = [random.uniform(4, 8), random.uniform(4, 8), random.uniform(4, 8)]
        phi = (1 + math.sqrt(5)) / 2
        self.verts = [(-1, phi, 0), (1, phi, 0), (-1, -phi, 0), (1, -phi, 0), (0, -1, phi), (0, 1, phi), (0, -1, -phi), (0, 1, -phi), (phi, 0, -1), (phi, 0, 1), (-phi, 0, -1), (-phi, 0, 1)]
        self.faces = [(0,11,5),(0,5,1),(0,1,7),(0,7,10),(0,10,11),(1,5,9),(5,11,4),(11,10,2),(10,7,6),(7,1,8),(3,9,4),(3,4,2),(3,2,6),(3,6,8),(3,8,9),(4,9,5),(2,4,11),(6,2,10),(8,6,7),(9,8,1)]

    def rotate_point(self, p):
        x, y, z = p
        c, s = math.cos(self.angle_x), math.sin(self.angle_x); ny, nz = y*c - z*s, y*s + z*c; y, z = ny, nz
        c, s = math.cos(self.angle_y), math.sin(self.angle_y); nx, nz = x*c + z*s, -x*s + z*c; x, z = nx, nz
        c, s = math.cos(self.angle_z), math.sin(self.angle_z); nx, ny = x*c - y*s, x*s + y*c; x, y = nx, ny
        return (x, y, z)

    def update(self, dt):
        self.timer += dt
        if self.phase == "rolling":
            p = min(1.0, self.timer / self.duration)
            ease = 1 - (1 - p)**3; self.pos[0] = -300 + (self.target_pos[0] + 300) * ease; self.pos[1] = (self.sh // 2) - abs(math.sin(p * math.pi * 3.5) * 80 * (1-p)); decay = (1.0 - p)
            self.angle_x += self.rot_speed[0] * dt * (0.5 + decay); self.angle_y += self.rot_speed[1] * dt * (0.5 + decay); self.angle_z += self.rot_speed[2] * dt * (0.5 + decay)
            if p >= 1.0: self.phase = "reveal"; self.timer = 0
        elif self.phase == "reveal":
            if self.timer > 0.8:
                self.phase = "fire"; self.timer = 0
                for _ in range(80):
                    part = FireParticle((int(self.pos[0]-10), int(self.pos[0]+10)), self.pos[1]); part.color = random.choice([PINK_D20, PURPLE_FIRE]); part.vel_x, part.vel_y = random.uniform(-18, 18), random.uniform(-18, 18); self.particles.append(part)
        elif self.phase == "fire":
            if self.timer > 1.2: self.done = True
        for p in self.particles[:]:
            p.update()
            if p.life <= 0: self.particles.remove(p)

    def draw(self, surf, font_dice, font_res):
        overlay = pygame.Surface((self.sw, self.sh), pygame.SRCALPHA); overlay.fill((0, 0, 0, 180)); surf.blit(overlay, (0, 0))
        if self.phase == "rolling":
            scale = 100; projected = []
            for v in self.verts:
                rx, ry, rz = self.rotate_point(v)
                projected.append((self.pos[0] + rx * scale, self.pos[1] + ry * scale, rz))
            for i, f_idx in enumerate(self.faces):
                p1, p2, p3 = projected[f_idx[0]], projected[f_idx[1]], projected[f_idx[2]]; val = (p2[0]-p1[0])*(p3[1]-p1[1]) - (p2[1]-p1[1])*(p3[0]-p1[0])
                if val > 0:
                    shade = 30 if i % 2 == 0 else 50
                    pygame.draw.polygon(surf, (shade, 20, shade+20), [p1[:2], p2[:2], p3[:2]]); pygame.draw.polygon(surf, PINK_D20, [p1[:2], p2[:2], p3[:2]], 2)
                    cx, cy = (p1[0]+p2[0]+p3[0])/3, (p1[1]+p2[1]+p3[1])/3
                    num_txt = font_dice.render(str(random.randint(1,20)), True, (160, 80, 140)); surf.blit(num_txt, num_txt.get_rect(center=(cx, cy)))
        elif self.phase in ["reveal", "fire"]:
            draw_d20_static(surf, self.pos, 110, self.target_value, font_res, is_reveal=True)
        for p in self.particles: p.draw(surf)

class D100RollAnimation:
    def __init__(self, target_value, screen_w, screen_h):
        self.target_value, self.sw, self.sh = target_value, screen_w, screen_h
        self.pos = [-180.0, max(180.0, screen_h * 0.72)]
        self.target_pos = [screen_w // 2, max(180.0, screen_h * 0.52)]
        self.timer, self.duration, self.phase, self.particles, self.done = 0.0, 1.8, "rolling", [], False
        self.rotation = 0.0
        self.spin_speed = random.uniform(12.0, 18.0)
        self.bounce_height = random.uniform(80.0, 120.0)

    def update(self, dt):
        self.timer += dt
        if self.phase == "rolling":
            p = min(1.0, self.timer / self.duration)
            ease = 1 - (1 - p) ** 3
            self.pos[0] = -180 + (self.target_pos[0] + 180) * ease
            self.pos[1] = self.target_pos[1] - abs(math.sin(p * math.pi * 2.8) * self.bounce_height * (1 - p * 0.45))
            self.rotation += self.spin_speed * dt * (1.2 - 0.7 * p)
            if p >= 1.0:
                self.phase = "reveal"
                self.timer = 0.0
                for _ in range(70):
                    part = FireParticle((int(self.pos[0] - 14), int(self.pos[0] + 14)), self.pos[1], color=GOLD)
                    part.vel_x = random.uniform(-16, 16)
                    part.vel_y = random.uniform(-18, 12)
                    self.particles.append(part)
        elif self.phase == "reveal":
            if self.timer > 1.1:
                self.done = True
        for p in self.particles[:]:
            p.update()
            if p.life <= 0:
                self.particles.remove(p)

    def draw(self, surf, font_roll, font_result):
        overlay = pygame.Surface((self.sw, self.sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surf.blit(overlay, (0, 0))
        if self.phase == "rolling":
            size = 120
            die_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            draw_d100_static(
                die_surf,
                (size, size),
                size - 10,
                random.randint(1, 100),
                font_roll,
                is_reveal=False,
            )
            die_surf = pygame.transform.rotate(die_surf, math.degrees(self.rotation))
            surf.blit(die_surf, die_surf.get_rect(center=(int(self.pos[0]), int(self.pos[1]))))
        else:
            draw_d100_static(surf, (int(self.pos[0]), int(self.pos[1])), 115, self.target_value, font_result, is_reveal=True)
        for p in self.particles:
            p.draw(surf)

class FireParticle:
    def __init__(self, x_range, y, color=None): self.reset(x_range, y, color)
    def reset(self, x_range, y, color=None):
        self.x, self.y = random.randint(x_range[0], x_range[1]), y + random.randint(-2, 2); self.vel_y, self.vel_x, self.life = -random.uniform(1.0, 4.0), random.uniform(-1.0, 1.0), 1.0; self.decay = random.uniform(0.015, 0.035); self.color = color if color else random.choice([GOLD, RED_FIRE, ORANGE_FIRE, YELLOW_FIRE]); self.size = random.randint(2, 5)
    def update(self): self.x += self.vel_x; self.y += self.vel_y; self.life -= self.decay
    def draw(self, surf):
        if self.life > 0:
            alpha = int(clamp(self.life * 255, 0, 255))
            p_s = pygame.Surface((self.size*2, self.size*2), pygame.SRCALPHA); pygame.draw.circle(p_s, (*self.color, alpha), (self.size, self.size), self.size)
            surf.blit(p_s, (self.x - self.size, self.y - self.size))

class TokenFizzle:
    """Lightweight vanish animation for Draw of Fate tokens â€” no replacement image."""
    def __init__(self, surf, pos, w, h):
        self.surf, self.pos, self.w, self.h = surf, pos, w, h
        self.progress, self.done, self.particles = 0.0, False, []
    def update(self, dt):
        if self.progress < 1.0:
            self.progress += dt * 1.2
            if self.progress > 1.0: self.progress = 1.0
            by = self.pos[1] + int((1.0 - self.progress) * self.h)
            for _ in range(3): self.particles.append(FireParticle((self.pos[0], self.pos[0] + self.w), by, random.choice([(20,20,20), (255,100,20), (200,50,10)])))
        else:
            self.done = True
        for p in self.particles[:]:
            p.update()
            if p.life <= 0: self.particles.remove(p)
    def draw(self, surf):
        bh = int((1.0 - self.progress) * self.h)
        if bh > 0:
            surf.blit(self.surf, self.pos, (0, 0, self.w, bh))
            er = pygame.Rect(self.pos[0] - 2, self.pos[1] + bh - 3, self.w + 4, 6)
            draw_round_rect(surf, er.inflate(2, 2), (180, 40, 10, 100), 3)
            pygame.draw.rect(surf, (255, 140, 20), er, border_radius=2)
        for p in self.particles: p.draw(surf)

class VanishFizzle:
    def __init__(self, card_id, start_surf, end_surf, pos, mode, orientation, game_ref):
        self.card_id, self.start_surf, self.end_surf, self.pos, self.mode, self.orientation, self.game = card_id, start_surf, end_surf, pos, mode, orientation, game_ref; self.progress, self.delay_timer, self.done, self.particles = 0.0, 0.5, False, []
    def update(self, dt):
        if self.progress < 1.0:
            self.progress += dt * 0.666
            if self.progress > 1.0: self.progress = 1.0
            by = self.pos[1] + int((1.0 - self.progress) * HAND_CARD_H)
            for _ in range(4): self.particles.append(FireParticle((self.pos[0], self.pos[0] + HAND_CARD_W), by, random.choice([(20,20,20), (255,100,20), (200,50,10)])))
        else:
            self.delay_timer -= dt
            if self.delay_timer <= 0: 
                self.done = True
                self.game.shuffle_deck() 
        for p in self.particles[:]:
            p.update()
            if p.life <= 0: self.particles.remove(p)
    def draw(self, surf):
        surf.blit(self.end_surf, self.pos); bh = int((1.0 - self.progress) * HAND_CARD_H)
        if bh > 0:
            surf.blit(self.start_surf, self.pos, (0, 0, HAND_CARD_W, bh)); ey, er = self.pos[1] + bh, pygame.Rect(self.pos[0]-5, self.pos[1]+bh-4, HAND_CARD_W+10, 8)
            draw_round_rect(surf, er.inflate(4, 4), (180, 40, 10, 100), 5); pygame.draw.rect(surf, (255, 140, 20), er, border_radius=3)
        for p in self.particles: p.draw(surf)

# ----------------------------
# 6. UI CLASSES
# ----------------------------
class Button:
    click_sound = None
    click_channel = None
    sfx_enabled = True

    def __init__(self, rect, text, primary=False, danger=False, warning=False, gold=False, disabled=False, fire=False, green=False, cyan=False, pink=False, image=None, image_height_mult=1.0, fantasy=False, pulse_frame=False):
        self.rect, self.text, self.primary, self.danger, self.warning, self.gold, self.disabled, self.fire, self.green, self.cyan, self.pink = pygame.Rect(rect), text, primary, danger, warning, gold, disabled, fire, green, cyan, pink; self.hover, self.particles = False, [FireParticle((self.rect.left, self.rect.right), self.rect.top) for _ in range(15)] if fire else []; self.image = image; self.image_height_mult = image_height_mult; self.fantasy = fantasy; self.pulse_frame = pulse_frame
    def draw(self, surf, font, dt):
        if self.image:
            img_h = int(self.rect.h * self.image_height_mult)
            img = pygame.transform.smoothscale(self.image, (self.rect.w, img_h))
            if self.disabled:
                dark = img.copy()
                dark.fill((150, 150, 150), special_flags=pygame.BLEND_RGB_SUB)
                surf.blit(dark, self.rect.topleft)
            elif self.hover:
                bright = img.copy()
                bright.fill((30, 30, 30), special_flags=pygame.BLEND_RGB_ADD)
                surf.blit(bright, self.rect.topleft)
            else:
                surf.blit(img, self.rect.topleft)
            if self.pulse_frame:
                pulse = (math.sin(pygame.time.get_ticks() * 0.006) + 1) / 2
                frame_surf = pygame.Surface((self.rect.w, self.rect.h), pygame.SRCALPHA)
                inner_margin = max(6, min(self.rect.w, self.rect.h) // 18)
                if self.pink:
                    base_col = (236, 126, 194)
                    hover_col = (255, 176, 224)
                elif self.cyan:
                    base_col = (120, 232, 255)
                    hover_col = (190, 246, 255)
                else:
                    base_col = (235, 190, 60)
                    hover_col = (255, 228, 140)
                edge_col = hover_col if self.hover and not self.disabled else base_col
                edge_alpha = 150 if self.disabled else int(165 + pulse * 55)
                glow_alpha = 35 if self.disabled else int(32 + pulse * 38)
                inner_rect = pygame.Rect(inner_margin, inner_margin, max(8, self.rect.w - inner_margin * 2), max(8, self.rect.h - inner_margin * 2))
                for inset, alpha_scale in ((0, 1.0), (4, 0.7), (8, 0.45)):
                    glow_rect = inner_rect.inflate(-inset * 2, -inset * 2)
                    if glow_rect.w <= 0 or glow_rect.h <= 0:
                        continue
                    pygame.draw.rect(frame_surf, (*edge_col, int(glow_alpha * alpha_scale)), glow_rect, border_radius=12)
                pygame.draw.rect(frame_surf, (*edge_col, edge_alpha), inner_rect, 3, 12)
                surf.blit(frame_surf, self.rect.topleft)
            return
        if self.disabled: bg = (40, 40, 40)
        elif self.fantasy and self.green: bg = (34, 102, 56)
        elif self.fantasy and self.pink: bg = (112, 44, 102)
        elif self.fantasy and self.cyan: bg = (32, 92, 112)
        elif self.fantasy and self.danger: bg = (110, 42, 36)
        elif self.fantasy and self.warning: bg = (128, 94, 38)
        elif self.fantasy and self.primary: bg = (88, 60, 34)
        elif self.fantasy and self.gold: bg = (108, 82, 30)
        elif self.fantasy: bg = (72, 50, 30)
        elif self.pink: bg = (118, 50, 110)
        elif self.cyan: bg = (35, 100, 120)
        elif self.green: bg = (30, 90, 45)
        elif self.primary: bg = (35, 65, 110)
        elif self.danger: bg = (110, 45, 60)
        elif self.warning: bg = (140, 90, 30)
        elif self.gold: bg = (100, 80, 20)
        else: bg = (25, 35, 55)
        if self.hover and not self.disabled: bg = tuple(min(c+20, 255) for c in bg)
        if self.gold and not self.disabled:
            pulse = (math.sin(pygame.time.get_ticks() * 0.008) + 1) / 2
            draw_round_rect(surf, self.rect.inflate(int(4+pulse*6), int(4+pulse*6)), (235, 190, 60, 80), 14)
        if self.fire and not self.disabled:
            pulse = (math.sin(pygame.time.get_ticks() * 0.01) + 1) / 2
            draw_round_rect(surf, self.rect.inflate(int(4+pulse*6), int(4+pulse*6)), (200, 50, 20, 80), 14)
            for p in self.particles:
                p.update()
                if p.life <= 0: p.reset((self.rect.left, self.rect.right), self.rect.top + 5)
                p.draw(surf)
        draw_round_rect(surf, self.rect, bg, 12)
        bc = (
            (236, 126, 194) if (self.pink and not self.disabled) else
            ((120, 232, 255) if (self.cyan and not self.disabled) else
             ((120, 240, 150) if (self.green and not self.disabled) else
              ((255, 126, 126) if (self.danger and not self.disabled) else
             (GOLD if (self.gold and not self.disabled) else
              (RED_FIRE if (self.fire and not self.disabled) else
               ((80,80,80) if self.disabled else ((212, 168, 96) if self.fantasy else (255,255,255,40))))))))
        )
        pygame.draw.rect(surf, bc, self.rect, 2, 12)
        txt_col = (100,100,100) if self.disabled else ((248, 231, 199) if self.fantasy else (245,245,255))
        surf.blit(font.render(self.text, True, txt_col), font.render(self.text, True, (0,0,0)).get_rect(center=self.rect.center))
    def handle_event(self, e):
        if self.disabled: return False
        if e.type == pygame.MOUSEMOTION: self.hover = self.rect.collidepoint(e.pos)
        clicked = e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.rect.collidepoint(e.pos)
        if clicked and Button.sfx_enabled and Button.click_sound is not None:
            try:
                if Button.click_channel is not None:
                    if not Button.click_channel.get_busy():
                        Button.click_channel.play(Button.click_sound)
                else:
                    Button.click_sound.play()
            except: pass
        return clicked

class Dropdown:
    def __init__(self, rect, items, max_visible=8, fantasy=False):
        self.rect, self.items, self.selected_index, self.is_open = pygame.Rect(rect), items, 0, False; self.scroll_offset, self.max_visible, self.item_h = 0, max_visible, 35; self.fantasy = fantasy; self.open_up = False
    def _menu_rect(self):
        _menu_h = min(len(self.items), self.max_visible) * self.item_h
        _menu_y = self.rect.y - _menu_h if self.open_up else self.rect.bottom
        return pygame.Rect(self.rect.x, _menu_y, self.rect.w, _menu_h)
    def handle_event(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if self.rect.collidepoint(e.pos): self.is_open = not self.is_open; return True
            if self.is_open:
                menu_rect = self._menu_rect()
                if menu_rect.collidepoint(e.pos): 
                    relative_y = e.pos[1] - menu_rect.y
                    self.selected_index = (relative_y // self.item_h) + self.scroll_offset
                    self.is_open = False; return True
                    
                self.is_open = False
        if self.is_open and e.type == pygame.MOUSEWHEEL:
            menu_rect = self._menu_rect()
            if menu_rect.collidepoint(pygame.mouse.get_pos()): 
                self.scroll_offset = clamp(self.scroll_offset - e.y, 0, max(0, len(self.items) - self.max_visible)); return True
        return False
    def draw_base(self, surf, font, is_cooldown=False):
        _bg = (56, 40, 25) if self.fantasy else (10, 15, 25)
        _bc = (212, 168, 96) if self.fantasy else (255, 255, 255, 30)
        draw_round_rect(surf, self.rect, _bg, 8); pygame.draw.rect(surf, _bc, self.rect, 1, 8)
        if is_cooldown: surf.blit(font.render("On Cooldown", True, (210, 120, 110) if self.fantasy else (200, 100, 100)), (self.rect.x + 10, self.rect.y + 7))
        elif self.items: idx = clamp(self.selected_index, 0, len(self.items)-1); surf.blit(font.render(str(self.items[idx][1]), True, (238, 220, 182) if self.fantasy else (200, 200, 200)), (self.rect.x + 10, self.rect.y + 7))
        else: surf.blit(font.render("Spent / Empty", True, (130, 116, 96) if self.fantasy else (100, 100, 110)), (self.rect.x + 10, self.rect.y + 7))
    def draw_menu(self, surf, font):
        if not self.is_open: return
        visible_count = min(len(self.items), self.max_visible); menu_rect = self._menu_rect(); pygame.draw.rect(surf, (48, 34, 21) if self.fantasy else (20, 25, 40), menu_rect); pygame.draw.rect(surf, (212, 168, 96, 170) if self.fantasy else (255, 255, 255, 50), menu_rect, 1)
        
        for i in range(visible_count):
            idx = i + self.scroll_offset
            if idx >= len(self.items): break
            r = pygame.Rect(self.rect.x, menu_rect.y + i * self.item_h, self.rect.w, self.item_h)
            if r.collidepoint(pygame.mouse.get_pos()): pygame.draw.rect(surf, (90, 67, 40) if self.fantasy else (40, 60, 100), r)
            if idx == self.selected_index: pygame.draw.rect(surf, (204, 156, 82) if self.fantasy else (60, 80, 150), r, 2)
            txt = font.render(str(self.items[idx][1]), True, (246, 230, 196) if self.fantasy else (255, 255, 255)); surf.blit(txt, (r.x + 15, r.y + (self.item_h // 2 - txt.get_height() // 2)))
        if len(self.items) > self.max_visible:
            bw, bh = 4, visible_count * self.item_h; pygame.draw.rect(surf, (220, 185, 120, 40) if self.fantasy else (255, 255, 255, 20), (menu_rect.right - bw - 2, menu_rect.y, bw, bh)); pygame.draw.rect(surf, (214, 172, 98, 220) if self.fantasy else (100, 160, 255, 200), (menu_rect.right - bw - 2, menu_rect.y + int(bh * (self.scroll_offset / len(self.items))), bw, int(bh * (self.max_visible / len(self.items)))))
    def get_selected(self): return self.items[clamp(self.selected_index, 0, len(self.items)-1)][0] if self.items else 1

class FantasyLevelStepper:
    def __init__(self, rect, min_value=1, max_value=20, value=1):
        self.rect = pygame.Rect(rect)
        self.min_value = int(min_value)
        self.max_value = int(max_value)
        self.value = int(clamp(value, self.min_value, self.max_value))
        self.selected_index = self.value - self.min_value
        self.left_rect = pygame.Rect(0, 0, 0, 0)
        self.right_rect = pygame.Rect(0, 0, 0, 0)
        self.center_rect = pygame.Rect(0, 0, 0, 0)
        self.editing = False
        self.input_buffer = str(self.value)
        self._sync_layout()

    def _sync_layout(self):
        h = self.rect.h
        btn_w = max(42, int(h * 0.95))
        self.left_rect = pygame.Rect(self.rect.x + 6, self.rect.y + (h - (h - 8)) // 2, btn_w, h - 8)
        self.right_rect = pygame.Rect(self.rect.right - btn_w - 6, self.rect.y + (h - (h - 8)) // 2, btn_w, h - 8)
        self.center_rect = pygame.Rect(self.left_rect.right + 8, self.rect.y + 4, self.right_rect.left - self.left_rect.right - 16, h - 8)

    def set_value(self, value):
        self.value = int(clamp(value, self.min_value, self.max_value))
        self.selected_index = self.value - self.min_value
        if not self.editing:
            self.input_buffer = str(self.value)

    def get_selected(self):
        return self.value

    def _play_click(self):
        if Button.sfx_enabled and Button.click_sound is not None:
            try:
                if Button.click_channel is not None:
                    if not Button.click_channel.get_busy():
                        Button.click_channel.play(Button.click_sound)
                else:
                    Button.click_sound.play()
            except Exception:
                pass

    def handle_event(self, e):
        self._sync_layout()
        changed = False
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if self.left_rect.collidepoint(e.pos):
                old = self.value
                self.set_value(self.value - 1)
                changed = (self.value != old)
                self.editing = False
            elif self.right_rect.collidepoint(e.pos):
                old = self.value
                self.set_value(self.value + 1)
                changed = (self.value != old)
                self.editing = False
            elif self.center_rect.collidepoint(e.pos):
                self.editing = True
                self.input_buffer = str(self.value)
            else:
                if self.editing:
                    try:
                        old = self.value
                        self.set_value(int(self.input_buffer))
                        changed = (self.value != old)
                    except Exception:
                        self.input_buffer = str(self.value)
                self.editing = False
        elif e.type == pygame.MOUSEWHEEL and self.rect.collidepoint(pygame.mouse.get_pos()):
            old = self.value
            self.set_value(self.value + e.y)
            changed = (self.value != old)
            self.editing = False
        elif e.type == pygame.KEYDOWN and self.editing:
            if e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                try:
                    old = self.value
                    self.set_value(int(self.input_buffer))
                    changed = (self.value != old)
                except Exception:
                    self.input_buffer = str(self.value)
                self.editing = False
            elif e.key == pygame.K_ESCAPE:
                self.editing = False
                self.input_buffer = str(self.value)
            elif e.key == pygame.K_BACKSPACE:
                self.input_buffer = self.input_buffer[:-1]
                if self.input_buffer == "":
                    self.input_buffer = ""
            else:
                if e.unicode.isdigit():
                    if len(self.input_buffer) < 2:
                        self.input_buffer += e.unicode
                    else:
                        self.input_buffer = self.input_buffer[1:] + e.unicode
        if changed:
            self._play_click()
        return changed

    def draw_base(self, surf, font):
        self._sync_layout()
        draw_round_rect(surf, self.rect, (43, 28, 18, 225), 14)
        pygame.draw.rect(surf, (120, 86, 42, 230), self.rect, 3, 14)
        inner = self.rect.inflate(-8, -8)
        draw_round_rect(surf, inner, (18, 14, 24, 225), 12)
        pygame.draw.rect(surf, (212, 168, 96, 190), inner, 1, 12)

        for r, direction in [(self.left_rect, "left"), (self.right_rect, "right")]:
            hov = r.collidepoint(pygame.mouse.get_pos())
            draw_round_rect(surf, r, (85, 60, 34, 235) if hov else (66, 46, 28, 235), 10)
            pygame.draw.rect(surf, (230, 190, 112), r, 2, 10)
            cx, cy = r.center
            if direction == "left":
                pts = [(cx + 7, cy - 10), (cx - 7, cy), (cx + 7, cy + 10)]
            else:
                pts = [(cx - 7, cy - 10), (cx + 7, cy), (cx - 7, cy + 10)]
            pygame.draw.polygon(surf, (255, 230, 170), pts)
            pygame.draw.polygon(surf, (140, 95, 45), pts, 1)

        draw_round_rect(surf, self.center_rect, (26, 20, 30, 210), 10)
        pygame.draw.rect(surf, (190, 155, 92), self.center_rect, 1, 10)
        _show_txt = self.input_buffer if self.editing else str(self.value)
        if self.editing and (pygame.time.get_ticks() // 450) % 2 == 0:
            _show_txt += "|"
        _num = font.render(_show_txt, True, (247, 228, 188))
        _num_shadow = font.render(_show_txt, True, (30, 18, 10))
        cx, cy = self.center_rect.center
        surf.blit(_num_shadow, (_num_shadow.get_rect(center=(cx + 1, cy + 1))))
        surf.blit(_num, (_num.get_rect(center=(cx, cy))))

    def draw_menu(self, surf, font):
        return

class IntSlider:
    def __init__(self, rect, min_value, max_value, value=None):
        self.rect = pygame.Rect(rect)
        self.min_value = int(min_value)
        self.max_value = int(max_value)
        self.value = int(clamp(value if value is not None else min_value, self.min_value, self.max_value))
        self.dragging = False

    def set_value(self, value):
        self.value = int(clamp(value, self.min_value, self.max_value))

    def _track_rect(self):
        return pygame.Rect(self.rect.x + 18, self.rect.centery - 3, self.rect.w - 36, 6)

    def _value_to_x(self):
        track = self._track_rect()
        span = max(1, self.max_value - self.min_value)
        t = (self.value - self.min_value) / span
        return int(track.x + t * track.w)

    def _set_from_x(self, x):
        track = self._track_rect()
        clamped_x = clamp(x, track.x, track.right)
        ratio = (clamped_x - track.x) / max(1, track.w)
        self.value = int(round(self.min_value + ratio * (self.max_value - self.min_value)))
        self.value = int(clamp(self.value, self.min_value, self.max_value))

    def handle_event(self, e):
        changed = False
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.rect.collidepoint(e.pos):
            old = self.value
            self.dragging = True
            self._set_from_x(e.pos[0])
            changed = self.value != old
        elif e.type == pygame.MOUSEMOTION and self.dragging:
            old = self.value
            self._set_from_x(e.pos[0])
            changed = self.value != old
        elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
            self.dragging = False
        return changed

    def draw(self, surf, font):
        draw_round_rect(surf, self.rect, (10, 15, 25), 8)
        pygame.draw.rect(surf, GOLD, self.rect, 1, 8)

        track = self._track_rect()
        pygame.draw.rect(surf, (40, 45, 55), track, border_radius=3)
        knob_x = self._value_to_x()
        fill_w = max(2, knob_x - track.x)
        pygame.draw.rect(surf, GOLD, (track.x, track.y, fill_w, track.h), border_radius=3)
        # Draw knob as a rounded pill with value text
        _knob_r = 12
        pygame.draw.circle(surf, (255, 245, 185), (knob_x, track.centery), _knob_r)
        pygame.draw.circle(surf, GOLD, (knob_x, track.centery), _knob_r, 2)
        _val_surf = font.render(str(self.value), True, (20, 15, 5))
        surf.blit(_val_surf, (knob_x - _val_surf.get_width() // 2, track.centery - _val_surf.get_height() // 2))
