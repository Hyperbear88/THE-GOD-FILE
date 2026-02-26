import os
import json
import random
import math
import time
import pygame
import copy
import sys
import traceback
import re
import webbrowser
from urllib.parse import urlparse
from datetime import datetime

# ----------------------------
# 1. LOGGING & EXE PATHS
# ----------------------------
LOG_FILE = "session_log.txt"

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

IMAGES_DIR = resource_path("images")
CARDS_JSON = resource_path("cards.json")
DECK_BACK_IMAGE = "21-Tarot_Back.png"
VANISHED_CARD_IMAGE = "Vanished.png"
SHUFFLE_SOUND = resource_path("shuffle.wav")
VIDEOS_DIR = resource_path("videos")
MENU_BG_IMAGE = "Teller_Room.png"
NORMAL_BG_IMAGE = "BG_3.png"

GOLD, RED_FIRE, ORANGE_FIRE, YELLOW_FIRE, PURPLE_TAP = (235, 190, 60), (220, 30, 30), (255, 120, 0), (255, 200, 0), (180, 50, 255)
PINK_D20 = (255, 100, 220)
PURPLE_FIRE = (180, 50, 255)
MAJOR_FORTUNE_IDS = [13, 16, 20]

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
    pygame.init()
    try: pygame.mixer.init()
    except: pass
    info = pygame.display.Info()
    w, h = info.current_w, info.current_h
    if w == 0 or h == 0: w, h = 1920, 1080
    surf = pygame.display.set_mode((w, h), pygame.FULLSCREEN | pygame.DOUBLEBUF)
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
    """Lightweight vanish animation for Draw of Fate tokens — no replacement image."""
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
    def __init__(self, rect, text, primary=False, danger=False, warning=False, gold=False, disabled=False, fire=False, green=False, image=None, image_height_mult=1.0):
        self.rect, self.text, self.primary, self.danger, self.warning, self.gold, self.disabled, self.fire, self.green = pygame.Rect(rect), text, primary, danger, warning, gold, disabled, fire, green; self.hover, self.particles = False, [FireParticle((self.rect.left, self.rect.right), self.rect.top) for _ in range(15)] if fire else []; self.image = image; self.image_height_mult = image_height_mult
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
            return
        if self.disabled: bg = (40, 40, 40)
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
        bc = GOLD if (self.gold and not self.disabled) else (RED_FIRE if (self.fire and not self.disabled) else ((80,80,80) if self.disabled else (255,255,255,40)))
        pygame.draw.rect(surf, bc, self.rect, 2, 12)
        surf.blit(font.render(self.text, True, (100,100,100) if self.disabled else (245,245,255)), font.render(self.text, True, (0,0,0)).get_rect(center=self.rect.center))
    def handle_event(self, e):
        if self.disabled: return False
        if e.type == pygame.MOUSEMOTION: self.hover = self.rect.collidepoint(e.pos)
        return e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.rect.collidepoint(e.pos)

class Dropdown:
    def __init__(self, rect, items, max_visible=8):
        self.rect, self.items, self.selected_index, self.is_open = pygame.Rect(rect), items, 0, False; self.scroll_offset, self.max_visible, self.item_h = 0, max_visible, 35
    def handle_event(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if self.rect.collidepoint(e.pos): self.is_open = not self.is_open; return True
            if self.is_open:
                menu_rect = pygame.Rect(self.rect.x, self.rect.bottom, self.rect.w, min(len(self.items), self.max_visible) * self.item_h)
                if menu_rect.collidepoint(e.pos): 
                    relative_y = e.pos[1] - self.rect.bottom
                    self.selected_index = (relative_y // self.item_h) + self.scroll_offset
                    self.is_open = False; return True
                    
                self.is_open = False
        if self.is_open and e.type == pygame.MOUSEWHEEL:
            menu_rect = pygame.Rect(self.rect.x, self.rect.bottom, self.rect.w, min(len(self.items), self.max_visible) * self.item_h)
            if menu_rect.collidepoint(pygame.mouse.get_pos()): 
                self.scroll_offset = clamp(self.scroll_offset - e.y, 0, max(0, len(self.items) - self.max_visible)); return True
        return False
    def draw_base(self, surf, font, is_cooldown=False):
        draw_round_rect(surf, self.rect, (10, 15, 25), 8); pygame.draw.rect(surf, (255, 255, 255, 30), self.rect, 1, 8)
        if is_cooldown: surf.blit(font.render("On Cooldown", True, (200, 100, 100)), (self.rect.x + 10, self.rect.y + 7))
        elif self.items: idx = clamp(self.selected_index, 0, len(self.items)-1); surf.blit(font.render(str(self.items[idx][1]), True, (200, 200, 200)), (self.rect.x + 10, self.rect.y + 7))
        else: surf.blit(font.render("Spent / Empty", True, (100, 100, 110)), (self.rect.x + 10, self.rect.y + 7))
    def draw_menu(self, surf, font):
        if not self.is_open: return
        visible_count = min(len(self.items), self.max_visible); menu_rect = pygame.Rect(self.rect.x, self.rect.bottom, self.rect.w, visible_count * self.item_h); pygame.draw.rect(surf, (20, 25, 40), menu_rect); pygame.draw.rect(surf, (255, 255, 255, 50), menu_rect, 1)
        
        for i in range(visible_count):
            idx = i + self.scroll_offset
            if idx >= len(self.items): break
            r = pygame.Rect(self.rect.x, self.rect.bottom + i * self.item_h, self.rect.w, self.item_h)
            if r.collidepoint(pygame.mouse.get_pos()): pygame.draw.rect(surf, (40, 60, 100), r)
            if idx == self.selected_index: pygame.draw.rect(surf, (60, 80, 150), r, 2)
            txt = font.render(str(self.items[idx][1]), True, (255, 255, 255)); surf.blit(txt, (r.x + 15, r.y + (self.item_h // 2 - txt.get_height() // 2)))
        if len(self.items) > self.max_visible:
            bw, bh = 4, visible_count * self.item_h; pygame.draw.rect(surf, (255, 255, 255, 20), (menu_rect.right - bw - 2, menu_rect.y, bw, bh)); pygame.draw.rect(surf, (100, 160, 255, 200), (menu_rect.right - bw - 2, menu_rect.y + int(bh * (self.scroll_offset / len(self.items))), bw, int(bh * (self.max_visible / len(self.items)))))
    def get_selected(self): return self.items[clamp(self.selected_index, 0, len(self.items)-1)][0] if self.items else 1

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

# ----------------------------
# 7. GAME CONTROLLER
# ----------------------------
class Game:
    def __init__(self, cards_data):
        self.cards = {c['id']: c for c in cards_data}; self.ids = [c['id'] for c in cards_data]
        self.deck, self.hand, self.fortune_zone, self.major_zone, self.vanished, self.history = [], [], [], [], [], []
        self.stacked, self.first_three_ids, self.seer_dice_table = None, [], []
        self.days_until_major, self.days_passed, self.shuffle_time, self.history_log, self.fizzles = 0, 0, 0.0, [], []
        self.toast_msg, self.toast_timer, self.level, self.used_major_ids = "", 0.0, 1, []
        self.hand_limit, self.ppf_charges, self.draw_queue, self.draw_timer, self.is_drawing = 1, 3, [], 0.0, False
        self.major_fortune_used_this_week, self.shuffle_anim_timer = False, 0.0
        self.seer_slots_filled_today = 0
        self.draw_of_fate_uses = 0
        self.draw_of_fate_current = 0
        self.rebuild_deck(); self.shuffle_deck(play_sound=False)
        self.draw_of_fate_uses = self.get_draw_of_fate_uses_by_level()
        self.draw_of_fate_current = self.draw_of_fate_uses

    def get_base_limit(self): return 3 if self.level >= 12 else (2 if self.level >= 6 else 1)
    def get_draw_of_fate_uses_by_level(self):
        if self.level >= 18:
            return 3
        if self.level >= 6:
            return 2
        if self.level >= 2:
            return 1
        return 0
    
    def add_history(self, text, card_ids=None): 
        self.history_log.append({"text": f"[{datetime.now().strftime('%H:%M')}] {text}", "card_ids": card_ids or []})
        if len(self.history_log) > 100: self.history_log.pop(0)
        self.toast_msg, self.toast_timer = text, TOAST_DURATION
        
    def save_state(self): 
        self.history.append({"deck": list(self.deck), "hand": [copy.deepcopy(h) for h in self.hand], "fortune_zone": [copy.deepcopy(f) for f in self.fortune_zone], "major_zone": [copy.deepcopy(f) for f in self.major_zone], "vanished": list(self.vanished), "stacked": self.stacked, "f3": list(self.first_three_ids), "cd": self.days_until_major, "days": self.days_passed, "limit": self.hand_limit, "table": list(self.seer_dice_table), "history": [copy.copy(e) for e in self.history_log], "level": self.level, "ppf": self.ppf_charges, "used_major": list(self.used_major_ids), "major_cooldown": self.major_fortune_used_this_week, "seer_filled": self.seer_slots_filled_today, "draw_of_fate": self.draw_of_fate_uses, "draw_of_fate_cur": self.draw_of_fate_current})
        if len(self.history) > 50: self.history.pop(0)
        
    def undo(self):
        if not self.history: return
        s = self.history.pop(); self.deck, self.hand, self.fortune_zone, self.major_zone, self.vanished, self.stacked, self.first_three_ids, self.days_until_major, self.days_passed, self.hand_limit, self.seer_dice_table, self.history_log, self.level, self.ppf_charges, self.used_major_ids, self.major_fortune_used_this_week, self.seer_slots_filled_today, self.draw_of_fate_uses, self.draw_of_fate_current = s["deck"], s["hand"], s.get("fortune_zone", []), s.get("major_zone", []), s["vanished"], s["stacked"], s["f3"], s["cd"], s["days"], s["limit"], s["table"], s.get("history", []), s.get("level", 1), s.get("ppf", 3), s.get("used_major", []), s.get("major_cooldown", False), s.get("seer_filled", 0), s.get("draw_of_fate", 0), s.get("draw_of_fate_cur", 0)
        self.add_history("Undo: Reverted to previous state.")

    def rebuild_deck(self):
        possessed_ids = [h['id'] for h in (self.hand + self.fortune_zone + self.major_zone)]
        self.deck = [cid for cid in self.ids if cid not in possessed_ids and cid not in self.vanished]

    def shuffle_deck(self, play_sound=True, trigger_anim=True):
        random.shuffle(self.deck)
        self.stacked = None 
        if trigger_anim: self.shuffle_anim_timer = SHUFFLE_ANIM_DURATION
        if play_sound: 
            try: pygame.mixer.Sound(SHUFFLE_SOUND).play()
            except: pass

    def long_rest(self, skip_draw=False):
        self.save_state()
        returned_ids = [h['id'] for h in (self.hand + self.fortune_zone + self.major_zone)]
        for h in (self.hand + self.fortune_zone + self.major_zone):
            if h['id'] not in self.vanished:
                if h['id'] not in self.deck: self.deck.append(h['id'])
        self.hand, self.fortune_zone, self.major_zone, self.stacked, self.first_three_ids, self.seer_dice_table, self.ppf_charges, self.days_passed = [], [], [], None, [], [], 3, self.days_passed + 1
        self.seer_slots_filled_today = 0
        self.hand_limit = self.get_base_limit()
        self.draw_of_fate_uses = self.get_draw_of_fate_uses_by_level()
        self.draw_of_fate_current = self.draw_of_fate_uses
        self.vanished = []
        self.rebuild_deck()
        if self.days_passed >= 7:
            self.days_passed = 0
            self.major_fortune_used_this_week = False
        self.shuffle_deck()
        self.add_history(f"Long Rest (Day {self.days_passed}): Hand returned to deck. Deck shuffled.")
        if not skip_draw: self.initiate_bulk_draw(self.hand_limit)
        return self.hand_limit

    def short_rest(self):
        self.save_state()
        self.draw_of_fate_uses = self.get_draw_of_fate_uses_by_level()
        self.draw_of_fate_current = self.draw_of_fate_uses
        self.add_history(f"Short Rest: Channel Divinity restored to {self.draw_of_fate_uses} use(s).")
    
    def mulligan_card(self, card_obj):
        if card_obj in self.fortune_zone or card_obj in self.major_zone:
            self.add_history("Cannot mulligan cards in Fortune or Major Fortune zones.")
            return
        target_list = None
        for lst in [self.hand]:
            if card_obj in lst:
                target_list = lst
                break
        if not target_list:
            return
        self.save_state()
        cid = card_obj['id']
        target_list.remove(card_obj)
        is_tapped = card_obj.get('tapped', False)
        if is_tapped:
            if cid not in self.vanished:
                self.vanished.append(cid)
            self.add_history(f"Mulligan: {self.cards[cid]['name']} (Tapped) -> Vanished.", [cid])
        else:
            self.deck.append(cid)
            self.add_history(f"Mulligan: {self.cards[cid]['name']} -> Shuffled.", [cid])
        self.shuffle_deck()
        self.initiate_bulk_draw(1 if is_tapped else 2)
        
    def stack_on_top(self, cid):
        if cid in self.deck: 
            self.save_state(); self.deck.remove(cid); self.deck.insert(0, cid); self.stacked = cid; self.add_history(f"Fate: {self.cards[cid]['name']} stacked on top.", [cid])

    def force_draw(self, count):
        added = False
        for _ in range(count):
            if not self.deck: break
            self.draw_queue.append(self.deck.pop(0))
            added = True
        if added:
            self.is_drawing = True
            if self.draw_timer <= 0:
                self.draw_timer = DRAW_DELAY_TIME

    def initiate_bulk_draw(self, count):
        if self.is_drawing: return
        cur_h = len([c for c in self.hand if not c['is_vanishing']])
        can_draw = self.hand_limit - cur_h
        if can_draw <= 0 or not self.deck: return
        self.draw_queue = []
        for _ in range(min(count, can_draw)):
            if not self.deck: break
            self.draw_queue.append(self.deck.pop(0))
        if self.draw_queue: self.is_drawing = True; self.draw_timer = DRAW_DELAY_TIME
    
    def process_draw_queue(self):
        drawn_ids = []
        for cid in self.draw_queue:
            if self.stacked == cid: self.stacked = None 
            self.hand.append({"id": cid, "mode": "normal", "orientation": "upright", "flip": 0.0, "scroll_up": 0, "scroll_inv": 0, "max_sc_up": 0, "max_sc_inv": 0, "is_vanishing": False, "tapped": False})
            if len(self.first_three_ids) < 3: self.first_three_ids.append(cid)
            if self.seer_slots_filled_today < 3: 
                self.seer_dice_table.append(cid); self.seer_slots_filled_today += 1
            drawn_ids.append(cid)
        names = ", ".join(self.cards[cid]['name'] for cid in drawn_ids)
        self.add_history(f"Drew {len(drawn_ids)} card(s): {names}", drawn_ids)
        self.draw_queue, self.is_drawing = [], False; self.shuffle_deck(play_sound=False, trigger_anim=False)

    def check_has_tapped_effect(self, card_dict):
        """Helper to cleanly evaluate if a given card dictionary possesses a tapped effect based on its mode and orientation."""
        cd = self.cards[card_dict['id']]
        mode = card_dict['mode']
        ori = card_dict['orientation']
        if mode == 'normal': return cd.get(f'tapped_{ori}', False)
        if mode == 'fortune': return cd.get(f'tapped_fortune_{ori}', False)
        if mode == 'major': return cd.get(f'tapped_major_{ori}', False)
        return False

# ----------------------------
# 8. MAIN STARTUP
# ----------------------------
def safe_main():
    try:
        screen, W, H = safe_init(); clock = pygame.time.Clock(); f_title, f_small, f_tiny, f_seer_bold, f_seer_dice_sim, f_seer_massive, f_preview_title, f_preview_body, f_labels, f_hand_header, f_hand_body = pygame.font.SysFont("Segoe UI", 26, True), pygame.font.SysFont("Segoe UI", 18, True), pygame.font.SysFont("Segoe UI", 18), pygame.font.SysFont("Segoe UI", 20, True), pygame.font.SysFont("Segoe UI", 24, True), pygame.font.SysFont("timesnewroman", 72, True), pygame.font.SysFont("timesnewroman", 44, bold=True), pygame.font.SysFont("georgia", 26), pygame.font.SysFont("timesnewroman", 32, bold=True), pygame.font.SysFont("timesnewroman", 22, bold=True), pygame.font.SysFont("georgia", 18)

        _loading_log = []       # list of (status_text, thumb_surface_or_None)
        _loading_display_pct = 0.0
        _loading_font_log = pygame.font.SysFont("Georgia", 18, True)
        _loading_font_status = pygame.font.SysFont("Georgia", 20, True)
        _loading_font_title = pygame.font.SysFont("Times New Roman", 38, True)
        _loading_font_pct = pygame.font.SysFont("Times New Roman", 24, True)
        _loading_particles = []   # list of [x, y, vx, vy, life, max_life, size, color]
        # Loading screen background video
        _loading_bg_video = {"cap": None, "fps": 30.0, "frame_interval": 1.0/30.0, "accum": 0.0, "frame_surface": None}
        try:
            import cv2 as _cv2_load
            _lbg_path = os.path.join(VIDEOS_DIR, "Fortune_Card_Menu.mp4")
            if os.path.isfile(_lbg_path):
                _lbg_cap = _cv2_load.VideoCapture(_lbg_path)
                if _lbg_cap.isOpened():
                    _lbg_fps = _lbg_cap.get(_cv2_load.CAP_PROP_FPS)
                    if not _lbg_fps or _lbg_fps <= 1: _lbg_fps = 30.0
                    _loading_bg_video["cap"] = _lbg_cap
                    _loading_bg_video["fps"] = _lbg_fps
                    _loading_bg_video["frame_interval"] = 1.0 / _lbg_fps
        except Exception:
            pass
        _loading_last_time = [pygame.time.get_ticks() / 1000.0]

        def draw_loading_screen(pct, status, thumb=None):
            nonlocal _loading_display_pct
            _loading_log.append((status, thumb))
            # Smooth interpolation toward target percentage
            anim_steps = 6
            step_sleep = 0.008
            target = pct
            for _ai in range(anim_steps):
                _loading_display_pct += (target - _loading_display_pct) * 0.35
                if _ai == anim_steps - 1:
                    _loading_display_pct = target
                _render_loading_frame(_loading_display_pct, status, thumb)
                time.sleep(step_sleep)

        def _render_loading_frame(pct, status, thumb):
            screen.fill((8, 6, 18))
            t = pygame.time.get_ticks() / 1000.0
            # --- Video background ---
            _dt_load = t - _loading_last_time[0]
            _loading_last_time[0] = t
            if _loading_bg_video["cap"] is not None:
                _loading_bg_video["accum"] += _dt_load
                while _loading_bg_video["accum"] >= _loading_bg_video["frame_interval"]:
                    _loading_bg_video["accum"] -= _loading_bg_video["frame_interval"]
                    try:
                        import cv2
                        ret, frame = _loading_bg_video["cap"].read()
                    except Exception:
                        ret, frame = False, None
                    if not ret:
                        try:
                            import cv2
                            _loading_bg_video["cap"].set(cv2.CAP_PROP_POS_FRAMES, 0)
                            ret, frame = _loading_bg_video["cap"].read()
                        except Exception:
                            ret, frame = False, None
                        if not ret:
                            break
                    try:
                        import cv2
                        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        fh_v, fw_v = frame.shape[:2]
                        surface = pygame.image.frombuffer(frame.tobytes(), (fw_v, fh_v), "RGB")
                        _loading_bg_video["frame_surface"] = pygame.transform.smoothscale(surface.convert(), (W, H))
                    except Exception:
                        pass
            if _loading_bg_video["frame_surface"] is not None:
                screen.blit(_loading_bg_video["frame_surface"], (0, 0))
                # Dark overlay so UI remains readable
                _dark_ov = pygame.Surface((W, H), pygame.SRCALPHA)
                _dark_ov.fill((0, 0, 0, 180))
                screen.blit(_dark_ov, (0, 0))
            else:
                # Fallback mystical background ambience
                for _si in range(3):
                    _sx = W // 2 + int(math.sin(t * 0.3 + _si * 2.1) * W * 0.35)
                    _sy = H // 3 + int(math.cos(t * 0.25 + _si * 1.7) * H * 0.15)
                    _sr = 120 + int(math.sin(t * 0.5 + _si) * 40)
                    _glow = pygame.Surface((_sr * 2, _sr * 2), pygame.SRCALPHA)
                    _gc = [(40, 20, 80, 18), (80, 40, 20, 12), (20, 40, 80, 15)][_si]
                    pygame.draw.circle(_glow, _gc, (_sr, _sr), _sr)
                    screen.blit(_glow, (_sx - _sr, _sy - _sr))

            bw, bh = 640, 36
            bx, by = (W - bw) // 2, 160
            # --- Title with golden glow ---
            dot_count = int(t * 1.5) % 4
            dots = " ." * dot_count
            title_text = f"Channeling the Arcana{dots}"
            # Title shadow
            _ts = _loading_font_title.render(title_text, True, (60, 30, 10))
            screen.blit(_ts, _ts.get_rect(center=(W // 2 + 2, by - 72)))
            title = _loading_font_title.render(title_text, True, (255, 215, 80))
            screen.blit(title, title.get_rect(center=(W // 2, by - 74)))

            # --- Percentage with mystical styling ---
            pct_str = f"~ {int(pct * 100)}% ~"
            pct_txt = _loading_font_pct.render(pct_str, True, (200, 180, 255))
            screen.blit(pct_txt, pct_txt.get_rect(center=(W // 2, by - 34)))

            # --- Ornate bar frame ---
            # Outer ornate border
            frame_r = pygame.Rect(bx - 6, by - 6, bw + 12, bh + 12)
            pygame.draw.rect(screen, (50, 35, 15), frame_r, border_radius=18)
            pygame.draw.rect(screen, (160, 120, 40), frame_r, 2, border_radius=18)
            # Inner ornate border
            inner_frame = pygame.Rect(bx - 2, by - 2, bw + 4, bh + 4)
            pygame.draw.rect(screen, (30, 20, 45), inner_frame, border_radius=14)
            pygame.draw.rect(screen, (120, 90, 30), inner_frame, 1, border_radius=14)
            # Bar dark interior
            pygame.draw.rect(screen, (15, 10, 30), (bx, by, bw, bh), border_radius=12)

            # --- Filled portion with magical gradient ---
            fill_w = max(0, int((bw - 8) * pct))
            if fill_w > 0:
                bar_surf = pygame.Surface((fill_w, bh - 8), pygame.SRCALPHA)
                for _col_x in range(fill_w):
                    ratio = _col_x / max(fill_w, 1)
                    # Purple-to-gold magical gradient
                    r = int(100 + 155 * ratio)
                    g = int(50 + 150 * ratio)
                    b = int(180 - 140 * ratio)
                    # Mystical shimmer wave
                    shimmer = math.sin(t * 5.0 + _col_x * 0.05) * 0.2 + 0.8
                    pulse = math.sin(t * 2.0 + _col_x * 0.02) * 0.1 + 0.9
                    r = min(255, int(r * shimmer * pulse))
                    g = min(255, int(g * shimmer * pulse))
                    b = min(255, int(b * shimmer * pulse))
                    pygame.draw.line(bar_surf, (r, g, b), (_col_x, 0), (_col_x, bh - 9))
                # Round the fill
                mask_surf = pygame.Surface((fill_w, bh - 8), pygame.SRCALPHA)
                pygame.draw.rect(mask_surf, (255, 255, 255), (0, 0, fill_w, bh - 8), border_radius=10)
                bar_surf.blit(mask_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
                screen.blit(bar_surf, (bx + 4, by + 4))
                # Leading edge glow (mystical purple-gold)
                glow_x = bx + 4 + fill_w
                for _gr, _gc in [(24, (255, 200, 60, 35)), (16, (180, 100, 255, 50)), (10, (255, 255, 200, 60))]:
                    glow_s = pygame.Surface((_gr * 2, bh + 20), pygame.SRCALPHA)
                    pygame.draw.circle(glow_s, _gc, (_gr, (bh + 20) // 2), _gr)
                    screen.blit(glow_s, (glow_x - _gr, by - 10))
                # Spawn sparkle particles at leading edge
                if random.random() < 0.6:
                    _loading_particles.append([
                        glow_x, by + bh // 2,
                        random.uniform(-1.5, 1.5), random.uniform(-3, -0.5),
                        0, random.uniform(0.4, 1.0),
                        random.uniform(1.5, 3.5),
                        random.choice([(255, 220, 80), (200, 150, 255), (255, 180, 255), (255, 255, 200)])
                    ])

            # Corner diamond decorations (drawn, not unicode)
            for _ri, (_rx, _ry) in enumerate([(bx - 18, by + bh // 2), (bx + bw + 18, by + bh // 2)]):
                _rune_pulse = int(180 + 60 * math.sin(t * 3 + _ri * 1.5))
                _dcol = (_rune_pulse, int(_rune_pulse * 0.7), 40)
                _dsz = 7
                pygame.draw.polygon(screen, _dcol, [(_rx, _ry - _dsz), (_rx + _dsz, _ry), (_rx, _ry + _dsz), (_rx - _dsz, _ry)])
                pygame.draw.polygon(screen, (min(255, _rune_pulse + 40), int(_rune_pulse * 0.5), 20), [(_rx, _ry - _dsz), (_rx + _dsz, _ry), (_rx, _ry + _dsz), (_rx - _dsz, _ry)], 1)

            # --- Update and draw particles ---
            for _p in _loading_particles[:]:
                _p[0] += _p[2]; _p[1] += _p[3]; _p[4] += 0.016
                if _p[4] >= _p[5]:
                    _loading_particles.remove(_p); continue
                _alpha = int(255 * (1 - _p[4] / _p[5]))
                _ps = pygame.Surface((int(_p[6] * 2), int(_p[6] * 2)), pygame.SRCALPHA)
                pygame.draw.circle(_ps, (*_p[7], _alpha), (int(_p[6]), int(_p[6])), int(_p[6]))
                screen.blit(_ps, (int(_p[0] - _p[6]), int(_p[1] - _p[6])))

            # --- Current status ---
            sub = _loading_font_status.render(status, True, (200, 190, 230))
            screen.blit(sub, sub.get_rect(center=(W // 2, by + bh + 26)))

            # --- Feature log with thumbnails ---
            log_left = bx - 40
            log_top = by + bh + 60
            row_h = 50
            max_visible = min(len(_loading_log), 10)
            visible = list(reversed(_loading_log[-max_visible:]))
            for _li, (_entry_text, _entry_thumb) in enumerate(visible):
                _ly = log_top + _li * row_h
                if _ly + row_h > H - 10:
                    break
                # Fade: newest (top) is brightest, older entries fade
                fade = max(0.1, ((max_visible - _li) / max_visible) ** 2) if max_visible > 1 else 1.0
                # Row background
                _row_bg = pygame.Surface((bw + 80, row_h - 4), pygame.SRCALPHA)
                pygame.draw.rect(_row_bg, (20, 15, 40, int(210 * fade)), (0, 0, bw + 80, row_h - 4), border_radius=8)
                screen.blit(_row_bg, (log_left, _ly))
                # Gold left border accent
                pygame.draw.rect(screen, (int(235 * fade), int(190 * fade), int(60 * fade)), (log_left, _ly + 4, 3, row_h - 12), border_radius=2)
                # Thumbnail
                _text_x = log_left + 14
                if _entry_thumb is not None:
                    _th_h = row_h - 8
                    _th_w = int(_th_h * (HAND_CARD_W / HAND_CARD_H))
                    _th_img = pygame.transform.smoothscale(_entry_thumb, (_th_w, _th_h))
                    # Subtle border around thumb
                    _tb_r = pygame.Rect(log_left + 10, _ly + 3, _th_w + 4, _th_h + 2)
                    pygame.draw.rect(screen, (int(120 * fade), int(100 * fade), int(50 * fade)), _tb_r, 1, border_radius=3)
                    screen.blit(_th_img, (log_left + 12, _ly + 4))
                    _text_x = log_left + 12 + _th_w + 10
                # Drawn checkmark (no unicode)
                _check_col = (int(80 * fade + 60), int(200 * fade), int(80 * fade + 40))
                _ck_cy = _ly + row_h // 2
                pygame.draw.lines(screen, _check_col, False, [(_text_x, _ck_cy), (_text_x + 5, _ck_cy + 6), (_text_x + 14, _ck_cy - 6)], 2)
                _text_x += 20
                # Entry text — color by type
                if "Hand" in _entry_text:
                    col = (int(130 * fade + 60), int(220 * fade), int(120 * fade))
                elif "Grid" in _entry_text:
                    col = (int(100 * fade + 40), int(170 * fade + 40), int(240 * fade))
                elif "HD" in _entry_text:
                    col = (int(240 * fade), int(200 * fade), int(100 * fade))
                else:
                    col = (int(200 * fade), int(130 * fade + 40), int(240 * fade))
                line = _loading_font_log.render(_entry_text, True, col)
                screen.blit(line, (_text_x, _ly + (row_h - line.get_height()) // 2))

            pygame.display.flip()

        with open(CARDS_JSON, 'r') as f: cards_raw = json.load(f)['cards']
        results = find_bold_markdown(cards_raw)
        log_event(f"Scanning JSON... Found {len(results)} bolded fields.")
        
        hand_tex, view_tex, preview_tex_hd, preview_bgs, thumb_tex, total_steps, cur_step = {}, {}, {}, {}, {}, len(cards_raw) * 4 + 2, 0
        THUMB_H, THUMB_W = 185, 132
        for c in cards_raw:
            cid, cname, img_path = c['id'], c['name'], os.path.join(IMAGES_DIR, c['image'])
            hand_tex[cid] = load_image_safe(img_path, (HAND_CARD_W, HAND_CARD_H), cname); cur_step += 1; draw_loading_screen(cur_step/total_steps, f"Hand Texture: {cname}", hand_tex[cid])
            view_tex[cid] = load_image_safe(img_path, (VIEW_CARD_W, VIEW_CARD_H), cname); cur_step += 1; draw_loading_screen(cur_step/total_steps, f"Grid Texture: {cname}", hand_tex[cid])
            thumb_tex[cid] = pygame.transform.smoothscale(hand_tex[cid], (THUMB_W, THUMB_H))
            prev_h, prev_w = int(H * 0.80), int(int(H * 0.80) * (HAND_CARD_W / HAND_CARD_H))
            preview_tex_hd[cid] = load_image_safe(img_path, (prev_w, prev_h), cname); cur_step += 1; draw_loading_screen(cur_step/total_steps, f"HD View: {cname}", hand_tex[cid])
            found = next((f for f in os.listdir(IMAGES_DIR) if f.lower().startswith(f"{cid}-") and f.lower().endswith("_bg.png")), None); preview_bgs[cid] = pygame.transform.smoothscale(pygame.image.load(os.path.join(IMAGES_DIR, found)).convert(), (W, H)) if found else pygame.Surface((W,H)); cur_step += 1; draw_loading_screen(cur_step/total_steps, f"Backdrop: {cname}", hand_tex[cid])
        
        menu_bg, normal_bg, deck_back_sm, v_face_hand = load_image_safe(os.path.join(IMAGES_DIR, MENU_BG_IMAGE), (W, H)), load_image_safe(os.path.join(IMAGES_DIR, NORMAL_BG_IMAGE), (W, H)), load_image_safe(os.path.join(IMAGES_DIR, DECK_BACK_IMAGE), (160, 224)), load_image_safe(os.path.join(IMAGES_DIR, VANISHED_CARD_IMAGE), (HAND_CARD_W, HAND_CARD_H))
        # Release loading bg video so the file can be reopened later
        if _loading_bg_video["cap"] is not None:
            _loading_bg_video["cap"].release()
            _loading_bg_video["cap"] = None
        v_face_view, v_face_deck = pygame.transform.smoothscale(v_face_hand, (VIEW_CARD_W, VIEW_CARD_H)), pygame.transform.smoothscale(v_face_hand, (160, 224))
        
        glow_gold, glow_purple, game = make_glow(HAND_CARD_W, HAND_CARD_H, GOLD), make_glow(HAND_CARD_W, HAND_CARD_H, PURPLE_TAP), Game(cards_raw)
        
        # RENDERING TOOLS
        f_rich_reg = pygame.font.SysFont("georgia", 18)
        f_rich_bold = pygame.font.SysFont("georgia", 18, bold=True)
        rich_renderer = RichTextRenderer(f_rich_reg, f_rich_bold)
        
        f_p_reg = pygame.font.SysFont("georgia", 26)
        f_p_bold = pygame.font.SysFont("georgia", 26, bold=True)
        p_rich_renderer = RichTextRenderer(f_p_reg, f_p_bold)

        # BUTTON IMAGES
        def _load_btn_img(fname):
            p = os.path.join(IMAGES_DIR, fname)
            if os.path.exists(p):
                return pygame.image.load(p).convert_alpha()
            return None
        _img_draw = _load_btn_img("Draw_Button_Image.png")
        _img_stack = _load_btn_img("Stack_Button_Image.png")
        _img_history = _load_btn_img("History_Button.png")
        _img_turn_undead = _load_btn_img("Turn_Undead_Button.png")
        _img_destroy_undead = _load_btn_img("Destroy_Undead_Button.png")
        _img_settings = _load_btn_img("Settings_Menu_Image.png")
        _img_dof_token = _load_btn_img("Draw_of_Fate_Token.png")
        _img_side_panel = _load_btn_img("Side_Panel_Image.png")

        # UI BUTTONS
        ui_x, ui_w = PADDING+PANEL_INNER_PAD, PANEL_W-PANEL_INNER_PAD*2
        lvl_change_dd = Dropdown((ui_x + 15, PADDING + 45, ui_w - 30, 35), [(i, f"Level {i}") for i in range(1, 21)])
        ppf_btn = Button((ui_x, 115, ui_w, 45), f"PP&F (3/3)", gold=True)
        undo_btn = Button((ui_x, 165, ui_w, 45), "Undo Action", warning=True)
        major_btn = Button((ui_x, 235, ui_w, 45), "Use Major Fortune", danger=True, fire=True)
        reset_major_btn = Button((ui_x, 285, ui_w, 35), "Reset Major Cooldown", warning=True)
        btn_half_w = (ui_w - 10) // 2
        btn_d1 = Button((ui_x, 480, btn_half_w, 45), "Draw 1", True, image=_img_draw)
        stack_btn = Button((ui_x + btn_half_w + 10, 480, btn_half_w, 45), "Stack Top", primary=True, image=_img_stack)
        short_rest_btn = Button((W-750, PADDING, 135, 35), "Short Rest", warning=True)
        rest_btn = Button((W-610, PADDING, 140, 35), "Long Rest", gold=True)
        draw_of_fate_slider = IntSlider((ui_x + 35, H - 200, ui_w - 70, 34), 0, 6, game.draw_of_fate_uses)
        turn_undead_btn = Button((ui_x, H - 160, (ui_w - 10) // 2, 42), "Turn Undead", green=True, image=_img_turn_undead)
        destroy_undead_btn = Button((ui_x + (ui_w - 10) // 2 + 10, H - 160, (ui_w - 10) // 2, 42), "Destroy Undead", danger=True, image=_img_destroy_undead)
        quit_btn = Button((W-160, PADDING + 45, 140, 35), "Exit game", danger=True)
        menu_btn = Button((W-160, PADDING + 85, 140, 35), "Main Menu", warning=True)
        history_btn = Button((W-240, H-810, 210, 270), "View History", primary=True, image=_img_history)
        hamburger_btn = Button((W-50, PADDING, 35, 35), "\u2630", image=_img_settings)
        top_menu_open = False
        exit_view_btn = Button((PADDING, PADDING, 160, 45), "Exit View", primary=True)
        
        menu_box_rect = pygame.Rect(W//2 - 200, H//2 - 50, 400, 350)
        menu_lvl_dd = Dropdown((menu_box_rect.x+50, menu_box_rect.y+100, 300, 45), [(i, i) for i in range(1, 21)])
        start_game_btn = Button((menu_box_rect.x+50, menu_box_rect.y+170, 300, 50), "START GAME", primary=True)
        menu_quit_btn = Button((menu_box_rect.x+50, menu_box_rect.y+240, 300, 50), "Exit game", danger=True)
        
        screen_mode, running, scroll_y, preview_cid, card_fire_particles = "menu", True, 0, None, []
        preview_state = {'mode': 'normal', 'orientation': 'upright'}
        preview_scrolls = {"current": 0, "max": 0}
        prophet_remaining_draws, current_roll_anim = 0, None
        previous_viewer_mode = None
        history_overlay_open, history_scroll = False, 0
        dof_token_fizzles = []
        _prev_dof_uses = game.draw_of_fate_uses
        history_sb_dragging = False
        grid_sb_dragging = False
        preview_sb_dragging = False  
        fool_video_state = {
            "cap": None,
            "fps": 30.0,
            "frame_interval": 1.0 / 30.0,
            "accum": 0.0,
            "frame_surface": None,
            "post_action": None
        }
        card_video_paths = {}
        if os.path.isdir(VIDEOS_DIR):
            for fname in os.listdir(VIDEOS_DIR):
                lower = fname.lower()
                if not lower.endswith(".mp4"):
                    continue
                prefix = fname.split("-", 1)[0]
                if prefix.isdigit():
                    card_video_paths[int(prefix)] = os.path.join(VIDEOS_DIR, fname)

        # Looping background video state for prophet_selection and deck screens
        def _open_loop_video(filename):
            path = os.path.join(VIDEOS_DIR, filename)
            state = {"cap": None, "fps": 30.0, "frame_interval": 1.0/30.0, "accum": 0.0, "frame_surface": None, "path": path}
            try:
                import cv2
                cap = cv2.VideoCapture(path)
                if cap.isOpened():
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    if not fps or fps <= 1: fps = 30.0
                    state["cap"] = cap
                    state["fps"] = fps
                    state["frame_interval"] = 1.0 / fps
            except Exception:
                pass
            return state

        prophet_bg_video = _open_loop_video("Fortune_Card_Menu.mp4")
        deck_bg_video = _open_loop_video("Loopable_Deck.mp4")

        def execute_card_use_action(h, hx, hy):
            game.save_state()
            has_tapped_effect = game.check_has_tapped_effect(h)
            if has_tapped_effect and not h.get('tapped'):
                h['tapped'] = True
                game.add_history(f"{game.cards[h['id']]['name']} was Tapped.", [h['id']])
                return
            h['is_vanishing'] = True
            if h['mode'] == 'major':
                game.major_fortune_used_this_week = True
            cf = v_face_hand if h['id'] in game.vanished else hand_tex[h['id']]
            cf = pygame.transform.rotate(cf, 180) if h['orientation']=="inverted" else cf
            game.fizzles.append(VanishFizzle(h['id'], cf, v_face_hand, (hx, hy), h['mode'], h['orientation'], game))
            game.add_history(f"{game.cards[h['id']]['name']} was Used and Vanished.", [h['id']])

        def start_fool_video(card_id, post_action):
            video_path = card_video_paths.get(card_id)
            if not video_path or not os.path.exists(video_path):
                post_action()
                return False
            try:
                import cv2
            except Exception as ex:
                log_event(f"OpenCV unavailable for card video playback: {ex}", is_error=True)
                post_action()
                return False
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                log_event(f"Could not open card video: {video_path}", is_error=True)
                post_action()
                return False
            fps = cap.get(cv2.CAP_PROP_FPS)
            if not fps or fps <= 1:
                fps = 30.0
            fool_video_state["cap"] = cap
            fool_video_state["fps"] = fps
            fool_video_state["frame_interval"] = 1.0 / fps
            fool_video_state["accum"] = fool_video_state["frame_interval"]
            fool_video_state["frame_surface"] = None
            fool_video_state["post_action"] = post_action
            return True

        def stop_card_video(play_action=True):
            nonlocal screen_mode
            pending = fool_video_state["post_action"]
            cap = fool_video_state["cap"]
            if cap is not None:
                try:
                    cap.release()
                except:
                    pass
            fool_video_state["cap"] = None
            fool_video_state["frame_surface"] = None
            fool_video_state["accum"] = 0.0
            fool_video_state["post_action"] = None
            screen_mode = "normal"
            if play_action and pending:
                pending()

        def apply_level_reset(new_level):
            game.level = new_level
            game.hand_limit = game.get_base_limit()
            if game.level >= 17:
                total = game.long_rest(skip_draw=True)
                return "prophet_selection", total - 1
            game.long_rest()
            return "normal", 0

        def get_draw_of_fate_rect():
            dt_box_w, dt_box_h = PANEL_W - 120, 90
            dt_box_x = PADDING + (PANEL_W - dt_box_w) // 2
            dt_box_y = H - dt_box_h - 35
            return pygame.Rect(dt_box_x, dt_box_y - 275, dt_box_w, 34)

        while running:
            dt = clock.tick(FPS)/1000.0; m_pos = pygame.mouse.get_pos(); 
            game.toast_timer = max(0.0, game.toast_timer - dt)
            game.shuffle_anim_timer = max(0.0, game.shuffle_anim_timer - dt)
            draw_of_fate_slider.rect = get_draw_of_fate_rect()
            fate_r = get_draw_of_fate_rect()
            half_w = (fate_r.w - 10) // 2
            turn_undead_btn.rect = pygame.Rect(fate_r.x, fate_r.bottom + 8, half_w, half_w)
            destroy_undead_btn.rect = pygame.Rect(fate_r.x + half_w + 10, fate_r.bottom + 8, half_w, half_w)
            # Position Draw 1 / Stack Top just above the Draw of Fate title
            _div_top = fate_r.y - 105  # divider_box top
            _title_y = _div_top - 38   # Draw of Fate label y
            _d1_half = (ui_w - 10) // 2
            btn_d1.rect = pygame.Rect(ui_x, _title_y - 108, _d1_half, 90)
            stack_btn.rect = pygame.Rect(ui_x + _d1_half + 10, _title_y - 108, _d1_half, 90)

            if screen_mode == "fool_video" and fool_video_state["cap"] is not None:
                fool_video_state["accum"] += dt
                while fool_video_state["accum"] >= fool_video_state["frame_interval"]:
                    fool_video_state["accum"] -= fool_video_state["frame_interval"]
                    try:
                        import cv2
                        ret, frame = fool_video_state["cap"].read()
                    except Exception:
                        ret, frame = False, None
                    if not ret:
                        stop_card_video(play_action=True)
                        break
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    fh, fw = frame.shape[:2]
                    surface = pygame.image.frombuffer(frame.tobytes(), (fw, fh), "RGB")
                    fool_video_state["frame_surface"] = surface.convert()
            
            # Update looping background videos for prophet_selection and deck screens
            for _bgv in (prophet_bg_video, deck_bg_video):
                if _bgv["cap"] is not None:
                    _bgv["accum"] += dt
                    while _bgv["accum"] >= _bgv["frame_interval"]:
                        _bgv["accum"] -= _bgv["frame_interval"]
                        try:
                            import cv2
                            ret, frame = _bgv["cap"].read()
                        except Exception:
                            ret, frame = False, None
                        if not ret:
                            _bgv["cap"].set(cv2.CAP_PROP_POS_FRAMES, 0)
                            ret, frame = _bgv["cap"].read()
                            if not ret:
                                break
                        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        fh, fw = frame.shape[:2]
                        surface = pygame.image.frombuffer(frame.tobytes(), (fw, fh), "RGB")
                        _bgv["frame_surface"] = surface.convert()

            if current_roll_anim:
                current_roll_anim.update(dt)
                if current_roll_anim.done:
                    game.save_state(); idx_to_pop = -1
                    for i, cid in enumerate(game.seer_dice_table):
                        if cid == current_roll_anim.target_value: idx_to_pop = i; break
                    if idx_to_pop != -1: game.seer_dice_table.pop(idx_to_pop)
                    current_roll_anim = None

            if game.is_drawing:
                game.draw_timer -= dt
                if game.draw_timer <= 0: game.process_draw_queue()

            for f in game.fizzles[:]:
                f.update(dt)
                if f.done:
                    if f.card_id == 20:
                        if f.mode == 'normal' and f.orientation == 'upright': game.force_draw(2)
                        elif f.mode == 'normal' and f.orientation == 'inverted': screen_mode, scroll_y = 'world_restore_view', 0
                    if f.card_id not in game.vanished: game.vanished.append(f.card_id)
                    game.hand = [h for h in game.hand if not (h['id']==f.card_id and h['is_vanishing'])]
                    game.fortune_zone = [h for h in game.fortune_zone if not (h['id']==f.card_id and h['is_vanishing'])]
                    game.major_zone = [h for h in game.major_zone if not (h['id']==f.card_id and h['is_vanishing'])]
                    game.fizzles.remove(f); game.rebuild_deck()
            
            cur_h_count = len([c for c in game.hand if not c['is_vanishing']])
            btn_d1.disabled = (cur_h_count >= game.get_base_limit()) or (game.level >= 2 and game.draw_of_fate_current < 1)
            stack_btn.disabled = (game.level >= 2 and game.draw_of_fate_current < 1)
            turn_undead_btn.disabled = (game.draw_of_fate_current < 1)
            destroy_undead_btn.disabled = (game.draw_of_fate_current < 2)
            ppf_btn.text = f"PP&F ({game.ppf_charges}/3)"
            ppf_btn.disabled = (game.ppf_charges <= 0 or game.level < 6 or len(game.fortune_zone) >= 1)
            major_btn.disabled = (game.major_fortune_used_this_week or len(game.major_zone) > 0 or game.level < 17)
            
            for e in pygame.event.get():
                if current_roll_anim: continue 
                if e.type == pygame.QUIT: running = False
                if screen_mode == "fool_video":
                    if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                        stop_card_video(play_action=True)
                    continue
                
                if screen_mode == "menu":
                    if menu_lvl_dd.handle_event(e):
                        selected_level = menu_lvl_dd.get_selected()
                        game.level = selected_level
                        game.draw_of_fate_uses = game.get_draw_of_fate_uses_by_level()
                        game.draw_of_fate_current = game.draw_of_fate_uses
                        draw_of_fate_slider.set_value(game.draw_of_fate_uses)
                        lvl_change_dd.selected_index = game.level - 1
                    if start_game_btn.handle_event(e):
                        game = Game(cards_raw); game.level = menu_lvl_dd.get_selected(); lvl_change_dd.selected_index = game.level - 1; game.hand_limit = game.get_base_limit(); game.draw_of_fate_uses = game.get_draw_of_fate_uses_by_level(); game.draw_of_fate_current = game.draw_of_fate_uses; draw_of_fate_slider.set_value(game.draw_of_fate_uses)
                        if game.level >= 17: total = game.long_rest(skip_draw=True); prophet_remaining_draws = total - 1; screen_mode, scroll_y = "prophet_selection", 0
                        else: game.long_rest(); screen_mode = "normal"
                    if menu_quit_btn.handle_event(e): running = False
                
                elif screen_mode == "preview_view":
                    if exit_view_btn.handle_event(e): 
                        preview_sb_dragging = False
                        if previous_viewer_mode:
                            screen_mode = previous_viewer_mode
                            previous_viewer_mode = None
                        else:
                            screen_mode = "normal"
                    # Preview scrollbar drag
                    if e.type == pygame.MOUSEBUTTONUP and e.button == 1:
                        preview_sb_dragging = False
                    if e.type == pygame.MOUSEMOTION and preview_sb_dragging:
                        cd = game.cards[preview_cid]; mk = (preview_state['mode'] if preview_state['mode'] != 'normal' else 'effect')
                        links = get_unique_preview_links(cd, mk)
                        gap, spell_w = 120, prev_w // 2
                        total_w = (prev_w * 2 + gap) if not links else (prev_w * 2 + spell_w + gap * 2)
                        start_x = (W - total_w) // 2; start_y = (H - prev_h) // 2
                        _p_panel_x = start_x + prev_w + gap
                        _p_bb = pygame.Rect(25, prev_h//2+40, prev_w-50, prev_h//2-100)
                        _p_track_y = start_y + _p_bb.y + 12
                        _p_track_h = _p_bb.h - 24
                        if preview_scrolls['max'] > 0 and _p_track_h > 30:
                            _rel = clamp(e.pos[1] - _p_track_y - 15, 0, _p_track_h - 30)
                            preview_scrolls['current'] = int(_rel / (_p_track_h - 30) * preview_scrolls['max'])
                    if e.type == pygame.MOUSEBUTTONDOWN:
                        if e.button == 1:
                            cd = game.cards[preview_cid]; mk = (preview_state['mode'] if preview_state['mode'] != 'normal' else 'effect')
                            links = get_unique_preview_links(cd, mk)
                            gap, spell_w = 120, prev_w // 2
                            total_w = (prev_w * 2 + gap) if not links else (prev_w * 2 + spell_w + gap * 2)
                            start_x = (W - total_w) // 2; start_y = (H - prev_h) // 2
                            _p_panel_x = start_x + prev_w + gap
                            _p_bb = pygame.Rect(25, prev_h//2+40, prev_w-50, prev_h//2-100)
                            # Scrollbar track in screen coords
                            _p_sb_x = _p_panel_x + _p_bb.right - 10
                            _p_sb_y = start_y + _p_bb.y + 12
                            _p_sb_h = _p_bb.h - 24
                            _p_sb_rect = pygame.Rect(_p_sb_x, _p_sb_y, 6, _p_sb_h)
                            if _p_sb_rect.collidepoint(e.pos) and preview_scrolls['max'] > 0:
                                preview_sb_dragging = True
                                if _p_sb_h > 30:
                                    _rel = clamp(e.pos[1] - _p_sb_y - 15, 0, _p_sb_h - 30)
                                    preview_scrolls['current'] = int(_rel / (_p_sb_h - 30) * preview_scrolls['max'])
                            else:
                                spell_box_x = start_x + (prev_w + gap) * 2
                                for i, (label, url) in enumerate(links):
                                    if pygame.Rect(spell_box_x + 10, start_y + 85 + i * 65, spell_w - 20, 50).collidepoint(e.pos): webbrowser.open(url)
                        elif e.button == 2: preview_state['orientation'] = "inverted" if preview_state['orientation'] == "upright" else "upright"
                        elif e.button == 3: preview_state['mode'] = ("major" if preview_cid in MAJOR_FORTUNE_IDS else "fortune") if preview_state['mode'] == "normal" else "normal"
                    if e.type == pygame.MOUSEWHEEL:
                        cd = game.cards[preview_cid]
                        mk = (preview_state['mode'] if preview_state['mode'] != 'normal' else 'effect')
                        links = get_unique_preview_links(cd, mk)
                        gap, spell_w = 120, prev_w // 2
                        total_w = (prev_w * 2 + gap) if not links else (prev_w * 2 + spell_w + gap * 2)
                        start_x = (W - total_w) // 2
                        start_y = (H - prev_h) // 2
                        text_panel_x = start_x + prev_w + gap
                        bottom_box_rect = pygame.Rect(text_panel_x + 25, start_y + prev_h//2 + 40, prev_w - 50, prev_h//2 - 100)
                        if bottom_box_rect.collidepoint(m_pos):
                            preview_scrolls['current'] = clamp(preview_scrolls['current'] - e.y*30, 0, preview_scrolls['max'])
                
                elif screen_mode == "normal":
                    # History overlay intercepts scroll and click-outside-to-close
                    if history_overlay_open:
                        _ho_w = (W - PADDING*4) // 4
                        _ho_h = (H - 200) // 2
                        _ho_btn_y = history_btn.rect.y
                        _ho_rect = pygame.Rect(W - _ho_w - PADDING*2, _ho_btn_y - _ho_h - 5, _ho_w, _ho_h)
                        _sb_w_ev = 14; _sb_pad_ev = 6
                        _clip_w_ev = _ho_rect.w - 20 - _sb_w_ev - _sb_pad_ev
                        _clip_h_ev = _ho_h - 60
                        _track_x_ev = _ho_rect.x + 10 + _clip_w_ev + _sb_pad_ev
                        _track_y_ev = _ho_rect.y + 50
                        _track_h_ev = _clip_h_ev
                        _track_rect_ev = pygame.Rect(_track_x_ev, _track_y_ev, _sb_w_ev, _track_h_ev)

                        # Compute total content height for scrollbar math
                        def _ho_total_content_h():
                            _base_rh = 38; _thumb_rh = max(_base_rh, THUMB_H + 8); _lh = f_tiny.get_linesize()
                            _th = 0
                            for ent in game.history_log:
                                if isinstance(ent, dict):
                                    _et = ent["text"]; _ec = ent.get("card_ids", [])
                                else:
                                    _et = ent; _ec = []
                                _ht = any(ci in thumb_tex for ci in _ec)
                                _tw = sum((THUMB_W + 4) for ci in _ec if ci in thumb_tex)
                                _tmw = _clip_w_ev - 20 - _tw
                                _wds = _et.split(' '); _cl = ''; _nl = 0
                                for _wd in _wds:
                                    _tst = (_cl + ' ' + _wd).strip()
                                    if _tmw > 0 and f_tiny.size(_tst)[0] > _tmw:
                                        if _cl: _nl += 1
                                        _cl = _wd
                                    else:
                                        _cl = _tst
                                if _cl: _nl += 1
                                _tbh = max(1, _nl) * _lh
                                _mrh = _thumb_rh if _ht else _base_rh
                                _th += max(_mrh, _tbh + 8)
                            return _th

                        if e.type == pygame.MOUSEBUTTONUP and e.button == 1:
                            history_sb_dragging = False

                        if e.type == pygame.MOUSEMOTION and history_sb_dragging:
                            _tch = _ho_total_content_h()
                            _max_scroll = max(0, _tch - _clip_h_ev)
                            if _max_scroll > 0 and _track_h_ev > _sb_w_ev:
                                _rel_y = clamp(e.pos[1] - _track_y_ev - _sb_w_ev // 2, 0, _track_h_ev - _sb_w_ev)
                                history_scroll = int(_rel_y / (_track_h_ev - _sb_w_ev) * _max_scroll)
                            continue

                        if e.type == pygame.MOUSEWHEEL:
                            if _ho_rect.collidepoint(m_pos):
                                _tch = _ho_total_content_h()
                                _max_scroll = max(0, _tch - (_ho_h - 70))
                                history_scroll = clamp(history_scroll - e.y*60, 0, _max_scroll)
                                continue

                        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                            if _track_rect_ev.collidepoint(e.pos):
                                # Click on scrollbar track — jump to position and start drag
                                history_sb_dragging = True
                                _tch = _ho_total_content_h()
                                _max_scroll = max(0, _tch - _clip_h_ev)
                                if _max_scroll > 0 and _track_h_ev > _sb_w_ev:
                                    _rel_y = clamp(e.pos[1] - _track_y_ev - _sb_w_ev // 2, 0, _track_h_ev - _sb_w_ev)
                                    history_scroll = int(_rel_y / (_track_h_ev - _sb_w_ev) * _max_scroll)
                                continue
                            elif not _ho_rect.collidepoint(e.pos):
                                # Check if they clicked history_btn (toggle handles it below)
                                if not history_btn.rect.collidepoint(e.pos):
                                    history_overlay_open = False
                                    continue
                    mz_rect, vz_rect = pygame.Rect(W-240, H-340, 210, 310), pygame.Rect(W-460, H-340, 210, 310)
                    draw_of_fate_slider.set_value(game.draw_of_fate_uses)
                    prev_lvl_idx = lvl_change_dd.selected_index
                    if lvl_change_dd.handle_event(e):
                        if lvl_change_dd.selected_index != prev_lvl_idx:
                            selected_level = lvl_change_dd.get_selected()
                            next_mode, remaining_draws = apply_level_reset(selected_level)
                            screen_mode = next_mode
                            prophet_remaining_draws = remaining_draws
                            scroll_y = 0
                            draw_of_fate_slider.set_value(game.draw_of_fate_uses)
                            menu_lvl_dd.selected_index = game.level - 1
                    if game.level >= 2 and draw_of_fate_slider.handle_event(e):
                        game.draw_of_fate_uses = draw_of_fate_slider.value
                        game.draw_of_fate_current = min(game.draw_of_fate_current, game.draw_of_fate_uses)
                    if btn_d1.handle_event(e): game.save_state(); game.draw_of_fate_current = max(0, game.draw_of_fate_current - 1); game.initiate_bulk_draw(1)
                    if stack_btn.handle_event(e): game.save_state(); game.draw_of_fate_current = max(0, game.draw_of_fate_current - 1); screen_mode, scroll_y = "stack_selection", 0
                    if game.level >= 6 and ppf_btn.handle_event(e) and not ppf_btn.disabled: screen_mode, scroll_y = "ppf_selection", 0
                    if game.level >= 2 and short_rest_btn.handle_event(e): game.short_rest(); draw_of_fate_slider.set_value(game.draw_of_fate_uses)
                    if game.level >= 2 and turn_undead_btn.handle_event(e): game.save_state(); game.draw_of_fate_current = max(0, game.draw_of_fate_current - 1); game.add_history("Used Turn Undead.")
                    if game.level >= 2 and destroy_undead_btn.handle_event(e): game.save_state(); game.draw_of_fate_current = max(0, game.draw_of_fate_current - 2); game.add_history("Used Destroy Undead.")
                    if rest_btn.handle_event(e):
                        if game.level >= 17: total = game.long_rest(skip_draw=True); prophet_remaining_draws = total - 1; screen_mode, scroll_y = "prophet_selection", 0
                        else: game.long_rest()
                        draw_of_fate_slider.set_value(game.draw_of_fate_uses)
                    if undo_btn.handle_event(e): game.undo()
                    draw_of_fate_slider.set_value(game.draw_of_fate_uses)
                    if history_btn.handle_event(e): history_overlay_open = not history_overlay_open; history_scroll = 0
                    if hamburger_btn.handle_event(e): top_menu_open = not top_menu_open
                    elif top_menu_open:
                        if quit_btn.handle_event(e): running = False
                        elif menu_btn.handle_event(e): screen_mode = "menu"; top_menu_open = False
                        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                            _menu_area = pygame.Rect(W - 170, PADDING, 170, 135)
                            if not _menu_area.collidepoint(e.pos): top_menu_open = False
                    if game.level >= 17:
                        if reset_major_btn.handle_event(e): game.major_fortune_used_this_week = False
                        if not major_btn.disabled and major_btn.handle_event(e): screen_mode, scroll_y = "major_selection", 0
                    
                    if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                        if mz_rect.collidepoint(e.pos): screen_mode, scroll_y = "deck", 0
                        elif vz_rect.collidepoint(e.pos): screen_mode, scroll_y = "vanish_view", 0
                    
                    if game.level >= 6 and e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                        dt_box_w, dt_box_h = PANEL_W - 120, 90
                        dt_box_x = PADDING + (PANEL_W - dt_box_w) // 2
                        dt_box_y = H - dt_box_h - 35
                        dt_box = pygame.Rect(dt_box_x, dt_box_y, dt_box_w, dt_box_h)
                        if dt_box.collidepoint(e.pos):
                            dice_count = len(game.seer_dice_table)
                            if dice_count > 0:
                                spacing = dt_box.w / (dice_count + 1)
                                dc_y = dt_box.centery
                                for i, cid in enumerate(game.seer_dice_table):
                                    dc_x = int(dt_box.x + spacing * (i + 1))
                                    if math.hypot(e.pos[0] - dc_x, e.pos[1] - dc_y) < 22:
                                        current_roll_anim = D20RollAnimation(cid, W, H)
                                        break
                    
                    if e.type == pygame.MOUSEWHEEL:
                        for zone, sy, sx in [(game.hand, 80, PANEL_W+60), (game.fortune_zone, 80+HAND_GRID_SPACING_Y, PANEL_W+60), (game.major_zone, 80+HAND_GRID_SPACING_Y, PANEL_W+60+HAND_GRID_SPACING_X)]:
                            for i, h in enumerate(zone):
                                x, y = sx+(i%4)*HAND_GRID_SPACING_X, sy+(i//4)*HAND_GRID_SPACING_Y
                                if pygame.Rect(x, y, HAND_CARD_W, HAND_CARD_H).collidepoint(m_pos) and h['flip'] >= 0.5:
                                    if m_pos[1] < y + HAND_CARD_H // 2: h['scroll_inv'] = clamp(h['scroll_inv'] - e.y*25, 0, h['max_sc_inv'])
                                    else: h['scroll_up'] = clamp(h['scroll_up'] - e.y*25, 0, h['max_sc_up'])
                    
                    if e.type == pygame.MOUSEBUTTONDOWN:
                        for h, zone, sy, sx in (
                            [(h, game.hand, 80, PANEL_W+60) for h in game.hand] +
                            [(f, game.fortune_zone, 80+HAND_GRID_SPACING_Y, PANEL_W+60) for f in game.fortune_zone] +
                            [(m, game.major_zone, 80+HAND_GRID_SPACING_Y, PANEL_W+60+HAND_GRID_SPACING_X) for m in game.major_zone]
                        ):
                            if h['is_vanishing']: continue
                            idx = zone.index(h)
                            hx, hy = sx+(idx%4)*HAND_GRID_SPACING_X, sy+(idx//4)*HAND_GRID_SPACING_Y
                            card_rect = pygame.Rect(hx, hy, HAND_CARD_W, HAND_CARD_H)
                            
                            mbr, vbr = None, None
                            if zone == game.hand:
                                mbr = pygame.Rect(hx + 15, hy + HAND_CARD_H + 8, 110, 30)
                                vbr = pygame.Rect(hx + 135, hy + HAND_CARD_H + 8, 110, 30)
                            else:
                                vbr = pygame.Rect(hx + 50, hy + HAND_CARD_H + 8, 160, 30)

                            # 1. Left Click Logic
                            if e.button == 1:
                                if mbr and mbr.collidepoint(e.pos):
                                    if game.level >= 2 and game.draw_of_fate_current < 1:
                                        break
                                    game.mulligan_card(h)
                                    if game.level >= 2: game.draw_of_fate_current = max(0, game.draw_of_fate_current - 1)
                                    break
                                elif vbr and vbr.collidepoint(e.pos):
                                    if ((zone == game.fortune_zone and h['mode'] == 'fortune') or (zone == game.major_zone and h['mode'] == 'major')) and not h.get('tapped'):
                                        started = start_fool_video(h['id'], lambda hh=h, x=hx, y=hy: execute_card_use_action(hh, x, y))
                                        if started:
                                            screen_mode = "fool_video"
                                    else:
                                        execute_card_use_action(h, hx, hy)
                                    break
                                # If they click the card itself (not a button) to preview it
                                elif card_rect.collidepoint(e.pos) and not h.get('tapped'):
                                    preview_cid, screen_mode = h['id'], "preview_view"
                                    preview_scrolls = {"current":0,"max":0}
                                    break
                                    
                            # 2. Middle Click Logic (Flip Orientation)
                            elif e.button == 2 and card_rect.collidepoint(e.pos) and not h.get('tapped'):
                                game.save_state()
                                h['orientation'] = 'inverted' if h['orientation'] == 'upright' else 'upright'
                                h['scroll_up'] = 0
                                h['scroll_inv'] = 0
                                break
                                
                            # 3. Right Click Logic (Move between zones)
                            elif e.button == 3 and card_rect.collidepoint(e.pos) and not h.get('tapped'):
                                game.save_state()
                                if zone == game.hand:
                                    if h['id'] in MAJOR_FORTUNE_IDS and game.level >= 17 and len(game.major_zone) < 1:
                                        game.hand.remove(h); h['mode'] = 'major'; game.major_zone.append(h)
                                        game.add_history(f"{game.cards[h['id']]['name']} moved to Major Zone.", [h['id']])
                                    elif game.level >= 6 and len(game.fortune_zone) < 1 and h['id'] not in MAJOR_FORTUNE_IDS:
                                        game.hand.remove(h); h['mode'] = 'fortune'; game.fortune_zone.append(h)
                                        game.add_history(f"{game.cards[h['id']]['name']} moved to Fortune Zone.", [h['id']])
                                else:
                                    if h in game.fortune_zone: game.fortune_zone.remove(h)
                                    elif h in game.major_zone: game.major_zone.remove(h)
                                    h['mode'] = 'normal'; game.hand.append(h)
                                    game.add_history(f"{game.cards[h['id']]['name']} returned to Hand.", [h['id']])
                                break

                elif screen_mode in ["deck", "vanish_view", "world_restore_view", "prophet_selection", "ppf_selection", "stack_selection", "major_selection"]:
                    if exit_view_btn.handle_event(e): screen_mode = "normal"; grid_sb_dragging = False
                    # Grid scrollbar drag support
                    if e.type == pygame.MOUSEBUTTONUP and e.button == 1:
                        grid_sb_dragging = False
                    # Compute scrollbar track geometry for grid views
                    hi_ev, fi_ev = [h['id'] for h in game.hand], [f['id'] for f in (game.fortune_zone+game.major_zone)]
                    _g_cur_list = []
                    if screen_mode == "ppf_selection": _g_cur_list = [c for c in game.ids if c not in MAJOR_FORTUNE_IDS and c not in game.vanished and c not in hi_ev and c not in fi_ev]
                    elif screen_mode == "world_restore_view": _g_cur_list = [vid for vid in game.vanished if vid != 20]
                    elif screen_mode == "deck": _g_cur_list = game.deck
                    elif screen_mode == "vanish_view": _g_cur_list = game.vanished
                    elif screen_mode == "prophet_selection": _g_cur_list = [c for c in game.ids if c != 20 and c not in hi_ev and c not in fi_ev]
                    elif screen_mode == "stack_selection": _g_cur_list = [c for c in game.deck if c != 20]
                    elif screen_mode == "major_selection": _g_cur_list = [c for c in MAJOR_FORTUNE_IDS if c not in game.vanished and c not in hi_ev and c not in fi_ev]
                    _g_max_scroll = get_card_grid_max_scroll(len(_g_cur_list), H)
                    _g_sb_w = 14
                    _g_track_x = W - 30
                    _g_track_y = VIEW_START_Y + 160
                    _g_track_h = H - _g_track_y - 40
                    _g_handle_h = max(_g_sb_w, int(_g_track_h * min(1, _g_track_h / max(1, _g_track_h + _g_max_scroll))))
                    _g_track_rect = pygame.Rect(_g_track_x, _g_track_y, _g_sb_w, _g_track_h)
                    if e.type == pygame.MOUSEMOTION and grid_sb_dragging and _g_max_scroll > 0:
                        _g_rel = clamp(e.pos[1] - _g_track_y - _g_handle_h // 2, 0, _g_track_h - _g_handle_h)
                        scroll_y = int(_g_rel / max(1, _g_track_h - _g_handle_h) * _g_max_scroll)
                    if screen_mode in ["deck", "vanish_view"]:
                        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                            hi, fi = [h['id'] for h in game.hand], [f['id'] for f in (game.fortune_zone+game.major_zone)]; cur_list = []
                            if screen_mode == "deck": cur_list = game.deck
                            elif screen_mode == "vanish_view": cur_list = game.vanished
                            for i, cid in enumerate(cur_list):
                                gx, gy = VIEW_START_X+(i%6)*CELL_W, VIEW_START_Y+(i//6)*CELL_H-scroll_y+160
                                if pygame.Rect(gx, gy, VIEW_CARD_W, VIEW_CARD_H).collidepoint(e.pos):
                                    previous_viewer_mode = screen_mode
                                    preview_cid, screen_mode = cid, "preview_view"; preview_scrolls = {"current":0,"max":0}
                                    break
                    if e.type == pygame.MOUSEWHEEL:
                        hi, fi = [h['id'] for h in game.hand], [f['id'] for f in (game.fortune_zone+game.major_zone)]
                        cur_list = []
                        if screen_mode == "ppf_selection": cur_list = [c for c in game.ids if c not in MAJOR_FORTUNE_IDS and c not in game.vanished and c not in hi and c not in fi]
                        elif screen_mode == "world_restore_view": cur_list = [vid for vid in game.vanished if vid != 20]
                        elif screen_mode == "deck": cur_list = game.deck
                        elif screen_mode == "vanish_view": cur_list = game.vanished
                        elif screen_mode == "prophet_selection": cur_list = [c for c in game.ids if c != 20 and c not in hi and c not in fi]
                        elif screen_mode == "stack_selection": cur_list = [c for c in game.deck if c != 20]
                        elif screen_mode == "major_selection": cur_list = [c for c in MAJOR_FORTUNE_IDS if c not in game.vanished and c not in hi and c not in fi]
                        max_scroll = get_card_grid_max_scroll(len(cur_list), H)
                        scroll_y = clamp(scroll_y - e.y*60, 0, max_scroll)
                    if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                        # Check scrollbar click first
                        if _g_max_scroll > 0 and _g_track_rect.collidepoint(e.pos):
                            grid_sb_dragging = True
                            _g_rel = clamp(e.pos[1] - _g_track_y - _g_handle_h // 2, 0, _g_track_h - _g_handle_h)
                            scroll_y = int(_g_rel / max(1, _g_track_h - _g_handle_h) * _g_max_scroll)
                        else:
                            hi, fi = [h['id'] for h in game.hand], [f['id'] for f in (game.fortune_zone+game.major_zone)]; cur_list = []
                            if screen_mode == "ppf_selection": cur_list = [c for c in game.ids if c not in MAJOR_FORTUNE_IDS and c not in game.vanished and c not in hi and c not in fi]
                            elif screen_mode == "world_restore_view": cur_list = [vid for vid in game.vanished if vid != 20]
                            elif screen_mode == "deck": cur_list = game.deck
                            elif screen_mode == "vanish_view": cur_list = game.vanished
                            elif screen_mode == "prophet_selection": cur_list = [c for c in game.ids if c != 20 and c not in hi and c not in fi]
                            elif screen_mode == "stack_selection": cur_list = [c for c in game.deck if c != 20]
                            elif screen_mode == "major_selection": cur_list = [c for c in MAJOR_FORTUNE_IDS if c not in game.vanished and c not in hi and c not in fi]
                            for i, cid in enumerate(cur_list):
                                gx, gy = VIEW_START_X+(i%6)*CELL_W, VIEW_START_Y+(i//6)*CELL_H-scroll_y+160
                                if pygame.Rect(gx, gy, VIEW_CARD_W, VIEW_CARD_H).collidepoint(e.pos):
                                    if screen_mode == "ppf_selection": game.save_state(); game.fortune_zone.append({"id": cid, "mode": "fortune", "orientation": "upright", "flip": 0.0, "scroll_up": 0, "scroll_inv": 0, "max_sc_up": 0, "max_sc_inv": 0, "is_vanishing": False, "tapped": False}); game.ppf_charges -= 1; game.add_history(f"PP&F: {game.cards[cid]['name']} added to Fortune Zone.", [cid]); game.rebuild_deck(); screen_mode = "normal"
                                    elif screen_mode == "major_selection": game.save_state(); game.major_zone.append({"id": cid, "mode": "major", "orientation": "upright", "flip": 0.0, "scroll_up": 0, "scroll_inv": 0, "max_sc_up": 0, "max_sc_inv": 0, "is_vanishing": False, "tapped": False}); game.major_fortune_used_this_week = True; game.add_history(f"Major Fortune: {game.cards[cid]['name']} activated.", [cid]); game.rebuild_deck(); screen_mode = "normal"
                                    elif screen_mode == "prophet_selection": 
                                        if cid in game.vanished: game.vanished.remove(cid)
                                        if cid in game.deck: game.deck.remove(cid)
                                        game.deck.insert(0, cid)
                                        game.stacked = cid
                                        game.add_history(f"Prophet of Fortune: {game.cards[cid]['name']} selected.", [cid])
                                        game.initiate_bulk_draw(prophet_remaining_draws + 1)
                                        screen_mode = "normal"
                                    elif screen_mode == "world_restore_view": game.vanished.remove(cid); game.hand.append({"id":cid,"mode":"normal","orientation":"upright","flip":0.0,"scroll_up":0,"scroll_inv":0,"max_sc_up":0,"max_sc_inv":0,"is_vanishing":False, "tapped": False}); game.add_history(f"World Restored: {game.cards[cid]['name']} returned to hand.", [cid]); game.rebuild_deck(); screen_mode = "normal"
                                    elif screen_mode == "stack_selection": game.stack_on_top(cid); screen_mode = "normal"
                                    else: preview_cid, screen_mode = cid, "preview_view"; preview_scrolls = {"current":0,"max":0}
                                    break

            # --- DRAWING ---
            screen.fill((10, 12, 18))
            
            if screen_mode == "menu":
                screen.blit(menu_bg, (0, 0))
                draw_round_rect(screen, (menu_box_rect.x, menu_box_rect.y, 400, 350), (15, 20, 30, 200), 20)
                screen.blit(f_preview_title.render("DIVINE SEER DOMAIN", True, GOLD), (W//2 - 220, menu_box_rect.y - 120))
                
                f_choose_level = pygame.font.SysFont("georgia", 32, bold=True)
                choose_lvl_surf = f_choose_level.render("Choose player level", True, (220, 210, 160))
                choose_lvl_x = menu_box_rect.x + 200 - choose_lvl_surf.get_width()//2
                choose_lvl_y = menu_box_rect.y + 38
                screen.blit(choose_lvl_surf, (choose_lvl_x, choose_lvl_y))
                menu_lvl_dd.draw_base(screen, f_small)
                start_game_btn.draw(screen, f_small, dt)
                menu_quit_btn.draw(screen, f_small, dt)
                menu_lvl_dd.draw_menu(screen, f_small)
            
            elif screen_mode == "normal":
                screen.blit(normal_bg, (0, 0))
                
                # 1. SIDEBAR
                _side_r = pygame.Rect(PADDING, PADDING, PANEL_W, H - PADDING * 2)
                if _img_side_panel:
                    _sp_img = pygame.transform.smoothscale(_img_side_panel, (_side_r.w, _side_r.h))
                    # Grey-out tint
                    _grey_ov = pygame.Surface((_side_r.w, _side_r.h), pygame.SRCALPHA)
                    _grey_ov.fill((25, 25, 35, 120))
                    _sp_img.blit(_grey_ov, (0, 0))
                    # Clip to rounded rect
                    _sp_mask = pygame.Surface((_side_r.w, _side_r.h), pygame.SRCALPHA)
                    draw_round_rect(_sp_mask, (0, 0, _side_r.w, _side_r.h), (255, 255, 255, 255), 15)
                    _sp_img.blit(_sp_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
                    screen.blit(_sp_img, (_side_r.x, _side_r.y))
                else:
                    draw_round_rect(screen, _side_r, (18, 24, 38, 240), 15)
                pygame.draw.rect(screen, (255, 255, 255, 40), _side_r, 2, 15)
                
                screen.blit(f_small.render("Select player level", True, (200, 255, 220)), (ui_x + 15, PADDING + 15))
                lvl_change_dd.draw_base(screen, f_small)
                (game.level >= 6 and ppf_btn.draw(screen, f_tiny, dt))
                undo_btn.draw(screen, f_small, dt)
                
                if game.level >= 17:
                    major_btn.draw(screen, f_small, dt)
                    reset_major_btn.draw(screen, f_tiny, dt)

                # 2. TOP RIGHT BUTTONS
                (game.level >= 2 and short_rest_btn.draw(screen, f_tiny, dt))
                rest_btn.draw(screen, f_tiny, dt)
                hamburger_btn.draw(screen, f_tiny, dt)
                if top_menu_open:
                    _menu_bg = pygame.Rect(W - 170, PADDING + 40, 160, 90)
                    draw_round_rect(screen, _menu_bg, (18, 24, 38, 230), 10)
                    pygame.draw.rect(screen, (255, 255, 255, 40), _menu_bg, 1, 10)
                    menu_btn.draw(screen, f_tiny, dt)
                    quit_btn.draw(screen, f_tiny, dt)
                
                # 3. SEER DICE TABLE
                if game.level >= 2:
                    fate_rect = get_draw_of_fate_rect()
                    divider_box = pygame.Rect(fate_rect.x + 2, fate_rect.y - 105, fate_rect.w - 4, 60)
                    draw_round_rect(screen, divider_box, (20, 25, 40, 220), 12)
                    pygame.draw.rect(screen, GOLD, divider_box, 1, 12)
                    # Draw of Fate tokens inside the box
                    _tok_pad = 4
                    _tok_gap = 4
                    _tok_h = divider_box.h - _tok_pad * 2
                    _tok_w = (divider_box.w - _tok_pad * 2 - 5 * _tok_gap) // 6
                    _tok_y = divider_box.y + _tok_pad
                    # Detect charge decrease and spawn fizzle
                    if game.draw_of_fate_current < _prev_dof_uses and _img_dof_token:
                        _tok_img_fz = pygame.transform.smoothscale(_img_dof_token, (_tok_w, _tok_h))
                        for _fi in range(_prev_dof_uses - 1, game.draw_of_fate_current - 1, -1):
                            _fx = divider_box.x + _tok_pad + _fi * (_tok_w + _tok_gap)
                            dof_token_fizzles.append(TokenFizzle(_tok_img_fz, (_fx, _tok_y), _tok_w, _tok_h))
                    _prev_dof_uses = game.draw_of_fate_current
                    # Draw remaining tokens
                    if _img_dof_token and game.draw_of_fate_current > 0:
                        _tok_img = pygame.transform.smoothscale(_img_dof_token, (_tok_w, _tok_h))
                        for _ti in range(game.draw_of_fate_current):
                            screen.blit(_tok_img, (divider_box.x + _tok_pad + _ti * (_tok_w + _tok_gap), _tok_y))
                    # Update and draw token fizzles
                    for _tf in dof_token_fizzles[:]: 
                        _tf.update(dt)
                        _tf.draw(screen)
                        if _tf.done: dof_token_fizzles.remove(_tf)
                    label = f_small.render("Draw of Fate", True, GOLD)
                    _dof_lbl_x = fate_rect.centerx - label.get_width() // 2
                    _dof_lbl_y = divider_box.y - 32
                    _dof_lbl_bg = pygame.Rect(_dof_lbl_x - 6, _dof_lbl_y - 2, label.get_width() + 12, label.get_height() + 4)
                    draw_round_rect(screen, _dof_lbl_bg, (0, 0, 0, 180), 6)
                    screen.blit(label, (_dof_lbl_x, _dof_lbl_y))
                    uses_label = f_small.render("Channel Divinity Uses:", True, GOLD)
                    _cd_lbl_x = fate_rect.centerx - uses_label.get_width() // 2
                    _cd_lbl_y = fate_rect.y - 32
                    _cd_lbl_bg = pygame.Rect(_cd_lbl_x - 6, _cd_lbl_y - 2, uses_label.get_width() + 12, uses_label.get_height() + 4)
                    draw_round_rect(screen, _cd_lbl_bg, (0, 0, 0, 180), 6)
                    screen.blit(uses_label, (_cd_lbl_x, _cd_lbl_y))
                    draw_of_fate_slider.draw(screen, f_small)
                    turn_undead_btn.draw(screen, f_tiny, dt)
                    destroy_undead_btn.draw(screen, f_tiny, dt)
                    # Labels under Turn/Destroy Undead
                    _tu_lbl = f_small.render("Turn Undead", True, GOLD)
                    _tu_lbl_x = turn_undead_btn.rect.centerx - _tu_lbl.get_width() // 2
                    _tu_lbl_y = turn_undead_btn.rect.bottom + 4
                    _tu_lbl_bg = pygame.Rect(_tu_lbl_x - 6, _tu_lbl_y - 2, _tu_lbl.get_width() + 12, _tu_lbl.get_height() + 4)
                    draw_round_rect(screen, _tu_lbl_bg, (0, 0, 0, 180), 6)
                    screen.blit(_tu_lbl, (_tu_lbl_x, _tu_lbl_y))
                    _du_lbl = f_small.render("Destroy Undead", True, GOLD)
                    _du_lbl_x = destroy_undead_btn.rect.centerx - _du_lbl.get_width() // 2
                    _du_lbl_y = destroy_undead_btn.rect.bottom + 4
                    _du_lbl_bg = pygame.Rect(_du_lbl_x - 6, _du_lbl_y - 2, _du_lbl.get_width() + 12, _du_lbl.get_height() + 4)
                    draw_round_rect(screen, _du_lbl_bg, (0, 0, 0, 180), 6)
                    screen.blit(_du_lbl, (_du_lbl_x, _du_lbl_y))
                    btn_d1.draw(screen, f_tiny, dt)
                    stack_btn.draw(screen, f_tiny, dt)
                if game.level >= 6:
                    dt_box_w, dt_box_h = PANEL_W - 120, 90
                    dt_box_x = PADDING + (PANEL_W - dt_box_w) // 2
                    dt_box_y = H - dt_box_h - 35
                    dt_box = pygame.Rect(dt_box_x, dt_box_y, dt_box_w, dt_box_h)
                    title_surf = f_small.render("SEER DICE TABLE", True, PINK_D20)
                    title_x = dt_box.centerx - title_surf.get_width() // 2
                    _seer_lbl_y = dt_box.y - 32
                    _seer_lbl_bg = pygame.Rect(title_x - 6, _seer_lbl_y - 2, title_surf.get_width() + 12, title_surf.get_height() + 4)
                    draw_round_rect(screen, _seer_lbl_bg, (0, 0, 0, 180), 6)
                    screen.blit(title_surf, (title_x, _seer_lbl_y))
                    draw_round_rect(screen, dt_box, (10, 15, 25, 240), 15)
                    pygame.draw.rect(screen, PINK_D20, dt_box, 1, 15)
                    dice_count = len(game.seer_dice_table)
                    if dice_count > 0:
                        spacing = dt_box.w / (dice_count + 1)
                        dc_y = dt_box.centery + 8
                        for i, cid in enumerate(game.seer_dice_table):
                            dc_x = int(dt_box.x + spacing * (i + 1))
                            draw_d20_static(screen, (dc_x, dc_y), 22, cid, f_seer_bold)

                # 4. HORIZONTAL DIVIDER LINE
                line_y = 80 + HAND_CARD_H + 95
                pygame.draw.line(screen, (255, 255, 255, 180), (PANEL_W + 60, line_y), (W - 60, line_y), 3)

                # 5. ZONE LABELS
                zone_x = PANEL_W + 60
                screen.blit(f_hand_header.render("Hand Zone", True, (230,240,255)), (zone_x + 15, 38))
                if game.level >= 6:
                    draw_round_rect(screen, (zone_x, 38+HAND_GRID_SPACING_Y-5, 200, 32), (20,25,40,200), 8)
                    pygame.draw.rect(screen, GOLD, (zone_x, 38+HAND_GRID_SPACING_Y-5, 200, 32), 1, 8)
                    screen.blit(f_small.render("Fortune Card Zone", True, GOLD), (zone_x + 10, 38+HAND_GRID_SPACING_Y))
                if game.level >= 17:
                    mx = zone_x + HAND_GRID_SPACING_X
                    draw_round_rect(screen, (mx, 38+HAND_GRID_SPACING_Y-5, 180, 32), (20,25,40,200), 8)
                    pygame.draw.rect(screen, (255,100,100), (mx, 38+HAND_GRID_SPACING_Y-5, 180, 32), 1, 8)
                    screen.blit(f_small.render("Major Card Zone", True, (255,120,120)), (mx + 10, 38+HAND_GRID_SPACING_Y))

                # 6. DRAW CARDS
                for p in card_fire_particles[:]: p.update(); (p.life <= 0 and card_fire_particles.remove(p))
                for zone, sy, sx in [(game.hand, 80, PANEL_W+60), (game.fortune_zone, 80+HAND_GRID_SPACING_Y, PANEL_W+60), (game.major_zone, 80+HAND_GRID_SPACING_Y, PANEL_W+60+HAND_GRID_SPACING_X)]:
                    if (zone == game.fortune_zone and game.level < 6) or (zone == game.major_zone and game.level < 17): continue
                    for i, h in enumerate(zone):
                        if h['is_vanishing']: continue
                        x, y = sx+(i%4)*HAND_GRID_SPACING_X, sy+(i//4)*HAND_GRID_SPACING_Y
                        h['flip'] = clamp(h['flip'] + (12*dt if pygame.Rect(x,y,HAND_CARD_W,HAND_CARD_H).collidepoint(m_pos) else -12*dt), 0, 1)
                        
                        if h.get('tapped'): screen.blit(glow_purple, (x-15, y-15))
                        elif h['mode'] == "fortune": screen.blit(glow_gold, (x-15, y-15))
                        elif h['mode'] == "major": 
                            p_p = (math.sin(pygame.time.get_ticks()*0.01)+1)/2
                            draw_round_rect(screen, pygame.Rect(x,y,HAND_CARD_W,HAND_CARD_H).inflate(12,12), (200,50,20,int(60+p_p*40)), CARD_RADIUS+5)

                        sw = max(1, int(HAND_CARD_W * abs(math.cos(h['flip'] * math.pi))))
                        if h['flip'] >= 0.5:
                            cs = pygame.Surface((HAND_CARD_W, HAND_CARD_H), pygame.SRCALPHA)
                            draw_round_rect(cs, (0,0,HAND_CARD_W,HAND_CARD_H), (20, 25, 40, 255), CARD_RADIUS)
                            pygame.draw.rect(cs, (180, 160, 100), (0,0,HAND_CARD_W,HAND_CARD_H), 4, CARD_RADIUS)
                            cd, mt = game.cards[h['id']], (h['mode'] if h['mode'] not in ['normal','major'] else 'effect')
                            if h['orientation'] == 'upright':
                                top_box = pygame.Surface((HAND_CARD_W-40, HAND_CARD_H//2-70), pygame.SRCALPHA)
                                rich_renderer.draw_rich_box(top_box, top_box.get_rect(), cd.get(f'{mt}_inverted', "..."), h['scroll_inv'])
                                top_box = pygame.transform.rotate(top_box, 180)
                                cs.blit(top_box, (20, 30))
                                h['max_sc_up'] = rich_renderer.draw_rich_box(cs, pygame.Rect(20, HAND_CARD_H//2+40, HAND_CARD_W-40, HAND_CARD_H//2-70), cd.get(f'{mt}_upright', "..."), h['scroll_up'])
                                h['max_sc_inv'] = top_box.get_height()
                            else:
                                top_box = pygame.Surface((HAND_CARD_W-40, HAND_CARD_H//2-70), pygame.SRCALPHA)
                                rich_renderer.draw_rich_box(top_box, top_box.get_rect(), cd.get(f'{mt}_upright', "..."), h['scroll_up'])
                                top_box = pygame.transform.rotate(top_box, 180)
                                cs.blit(top_box, (20, 30))
                                h['max_sc_inv'] = rich_renderer.draw_rich_box(cs, pygame.Rect(20, HAND_CARD_H//2+40, HAND_CARD_W-40, HAND_CARD_H//2-70), cd.get(f'{mt}_inverted', "..."), h['scroll_inv'])
                                h['max_sc_up'] = top_box.get_height()
                            content = cs
                        else:
                            content = pygame.transform.rotate(hand_tex[h['id']], 180) if h['orientation']=="inverted" else hand_tex[h['id']]
                        
                        card_x = x + (HAND_CARD_W - sw) // 2
                        screen.blit(pygame.transform.smoothscale(content, (sw, HAND_CARD_H)), (card_x, y))
                        if zone == game.fortune_zone:
                            draw_card_glitter(screen, pygame.Rect(card_x, y, sw, HAND_CARD_H), pygame.time.get_ticks() / 1000.0, "gold")
                        elif zone == game.major_zone:
                            draw_card_glitter(screen, pygame.Rect(card_x, y, sw, HAND_CARD_H), pygame.time.get_ticks() / 1000.0, "red")
                        
                        # Card Buttons
                        if zone == game.hand:
                            mbr, vbr = pygame.Rect(x+15, y+HAND_CARD_H+8, 110, 30), pygame.Rect(x+135, y+HAND_CARD_H+8, 110, 30)
                            _mull_disabled = (game.level >= 2 and game.draw_of_fate_current < 1)
                            if _mull_disabled:
                                draw_round_rect(screen, mbr, (20, 20, 20, 160), 15)
                                pygame.draw.rect(screen, (60, 60, 60, 100), mbr, 1, 15)
                                screen.blit(f_tiny.render("MULL", True, (100, 100, 100)), f_tiny.render("MULL", True, (0,0,0)).get_rect(center=mbr.center))
                            else:
                                draw_round_rect(screen, mbr, (50, 70, 40, 100) if mbr.collidepoint(m_pos) else (30, 40, 25, 160), 15)
                                pygame.draw.rect(screen, (100, 200, 100, 100), mbr, 1, 15)
                                screen.blit(f_tiny.render("MULL", True, (200, 255, 200)), f_tiny.render("MULL", True, (0,0,0)).get_rect(center=mbr.center))
                            
                            draw_round_rect(screen, vbr, (100, 40, 40, 100) if vbr.collidepoint(m_pos) else (45, 25, 25, 160), 15)
                            pygame.draw.rect(screen, (200, 100, 100, 100), vbr, 1, 15)
                            btn_label = "VANISH" if h.get('tapped') else "USE"
                            screen.blit(f_tiny.render(btn_label, True, (240, 240, 240)), f_tiny.render(btn_label, True, (0,0,0)).get_rect(center=vbr.center))
                        else:
                            vbr = pygame.Rect(x+50, y+HAND_CARD_H+8, 160, 30)
                            draw_round_rect(screen, vbr, (60, 60, 70, 100) if vbr.collidepoint(m_pos) else (40, 40, 50, 160), 15)
                            pygame.draw.rect(screen, (200, 200, 255, 60), vbr, 1, 15)
                            btn_label = "VANISH" if h.get('tapped') else "USE"
                            btn_color = (220, 230, 255) if h.get('tapped') else (240, 240, 240)
                            screen.blit(f_tiny.render(btn_label, True, btn_color), f_tiny.render(btn_label, True, (0,0,0)).get_rect(center=vbr.center))

                # 7. DECK & VANISHED PILE
                vz_rect = pygame.Rect(W-460, H-340, 210, 310)
                mz_rect = pygame.Rect(W-240, H-340, 210, 310)
                _hist_h = 135
                history_btn.rect = pygame.Rect(mz_rect.x, mz_rect.y - _hist_h - 10, mz_rect.w, _hist_h)
                history_btn.draw(screen, f_tiny, dt)
                
                for r, lbl in [(vz_rect, "Vanished Pile"), (mz_rect, "Main Deck")]:
                    draw_round_rect(screen, r, (5,8,15,220), 20)
                    pygame.draw.rect(screen, (255,255,255,255), r, 2, 20)
                    txt = f_small.render(lbl, True, (255, 255, 255))
                    screen.blit(txt, (r.centerx - txt.get_width()//2, r.y + 12))

                deck_x, deck_y = mz_rect.x+25, mz_rect.y+48
                deck_w, deck_h = 160, 224
                
                if game.shuffle_anim_timer > 0:
                    anim_t = 1.0 - (game.shuffle_anim_timer / SHUFFLE_ANIM_DURATION)
                    num_cards = 7
                    spread = 38
                    for i in range(num_cards):
                        frac = (i - (num_cards-1)/2) / ((num_cards-1)/2)
                        offset = math.sin(anim_t * math.pi) * frac * spread
                        angle = math.sin(anim_t * math.pi) * frac * 18
                        card_img = pygame.transform.rotozoom(deck_back_sm, angle, 1.0)
                        cx = deck_x + offset
                        cy = deck_y - abs(frac)*12
                        screen.blit(card_img, (cx, cy))
                else:
                    if game.stacked:
                        screen.blit(pygame.transform.smoothscale(view_tex[game.stacked], (deck_w, deck_h)), (deck_x, deck_y))
                    else:
                        screen.blit(deck_back_sm, (deck_x, deck_y))
                
                if game.vanished:
                    screen.blit(v_face_deck, (vz_rect.x+25, vz_rect.y+48))
                
                lvl_change_dd.draw_menu(screen, f_small)
                [f.draw(screen) for f in game.fizzles]

                # History overlay (drawn on top of normal view)
                if history_overlay_open:
                    _ho_w = (W - PADDING*4) // 4
                    _ho_h = (H - 200) // 2
                    _ho_btn_y = history_btn.rect.y
                    _ho_rect = pygame.Rect(W - _ho_w - PADDING*2, _ho_btn_y - _ho_h - 5, _ho_w, _ho_h)
                    draw_round_rect(screen, _ho_rect, (15, 20, 30, 200), 15)
                    pygame.draw.rect(screen, GOLD, _ho_rect, 2, 15)
                    _ho_title = f_hand_header.render("ACTION HISTORY", True, GOLD)
                    screen.blit(_ho_title, (_ho_rect.centerx - _ho_title.get_width()//2, _ho_rect.y + 12))
                    # Scrollbar constants
                    _sb_w = 14
                    _sb_pad = 6
                    # Clip rendering to the panel area (leave room for scrollbar)
                    _clip_rect = pygame.Rect(_ho_rect.x + 10, _ho_rect.y + 50, _ho_rect.w - 20 - _sb_w - _sb_pad, _ho_rect.h - 60)
                    _ho_surf = pygame.Surface((_clip_rect.w, _clip_rect.h), pygame.SRCALPHA)
                    _base_row_h = 38
                    _thumb_row_h = max(_base_row_h, THUMB_H + 8)
                    _line_h = f_tiny.get_linesize()

                    # Pre-compute row heights with word wrap
                    def _wrap_text(_font, _text, _max_w):
                        """Return list of lines that fit within _max_w."""
                        if _max_w <= 0:
                            return [_text]
                        words = _text.split(' ')
                        lines, cur = [], ''
                        for w in words:
                            test = (cur + ' ' + w).strip()
                            if _font.size(test)[0] <= _max_w:
                                cur = test
                            else:
                                if cur:
                                    lines.append(cur)
                                cur = w
                        if cur:
                            lines.append(cur)
                        return lines if lines else ['']

                    _y_cursor = 0
                    for _i, _entry in enumerate(reversed(game.history_log)):
                        if isinstance(_entry, dict):
                            _txt = _entry["text"]
                            _cids = _entry.get("card_ids", [])
                        else:
                            _txt = _entry
                            _cids = []
                        _has_thumbs = any(_ci in thumb_tex for _ci in _cids)
                        # Calculate thumb width offset
                        _thumb_total_w = sum((THUMB_W + 4) for _ci in _cids if _ci in thumb_tex)
                        _text_max_w = _clip_rect.w - 20 - _thumb_total_w
                        _lines = _wrap_text(f_tiny, _txt, _text_max_w)
                        _text_block_h = len(_lines) * _line_h
                        _min_h = _thumb_row_h if _has_thumbs else _base_row_h
                        _row_h = max(_min_h, _text_block_h + 8)
                        _y_pos = _y_cursor - history_scroll
                        _y_cursor += _row_h
                        if -_row_h < _y_pos < _clip_rect.h:
                            _tx = 20
                            for _ci in _cids:
                                if _ci in thumb_tex:
                                    _ho_surf.blit(thumb_tex[_ci], (_tx, _y_pos + (_row_h - THUMB_H) // 2))
                                    _tx += THUMB_W + 4
                            # Draw wrapped text lines, vertically centered
                            _text_y = _y_pos + (_row_h - _text_block_h) // 2
                            for _line in _lines:
                                _line_surf = f_tiny.render(_line, True, (200, 210, 230))
                                _ho_surf.blit(_line_surf, (_tx, _text_y))
                                _text_y += _line_h
                    screen.blit(_ho_surf, (_clip_rect.x, _clip_rect.y))
                    # Thick scrollbar with square scroller
                    _total_content_h = _y_cursor
                    _visible_h = _clip_rect.h
                    if _total_content_h > _visible_h:
                        _track_x = _clip_rect.right + _sb_pad
                        _track_y = _clip_rect.y
                        _track_h = _clip_rect.h
                        # Track background
                        pygame.draw.rect(screen, (30, 35, 50), (_track_x, _track_y, _sb_w, _track_h))
                        pygame.draw.rect(screen, GOLD, (_track_x, _track_y, _sb_w, _track_h), 1)
                        # Square scroller handle
                        _scroll_ratio = history_scroll / max(1, _total_content_h - _visible_h)
                        _handle_h = _sb_w  # square
                        _handle_y = _track_y + int((_track_h - _handle_h) * _scroll_ratio)
                        pygame.draw.rect(screen, GOLD, (_track_x, _handle_y, _sb_w, _handle_h))

            elif screen_mode == "preview_view":
                screen.blit(preview_bgs[preview_cid], (0,0))
                overlay = pygame.Surface((W,H), pygame.SRCALPHA); overlay.fill((0,0,0,160)); screen.blit(overlay, (0,0))
                
                cd, mk = game.cards[preview_cid], (preview_state['mode'] if preview_state['mode'] != 'normal' else 'effect')
                links = get_unique_preview_links(cd, mk)
                
                gap, spell_w = 120, prev_w // 2
                num_cols = 3 if links else 2
                total_w = (prev_w * 2 + gap) if not links else (prev_w * 2 + spell_w + gap * 2)
                start_x = (W - total_w) // 2
                start_y = (H - prev_h) // 2

                if preview_state['mode'] == 'fortune':
                    screen.blit(pygame.transform.smoothscale(glow_gold, (prev_w+60, prev_h+60)), (start_x-30, start_y-30))
                    screen.blit(pygame.transform.smoothscale(glow_gold, (prev_w+60, prev_h+60)), (start_x + prev_w + gap - 30, start_y-30))
                elif preview_state['mode'] == 'major':
                    pulse = (math.sin(pygame.time.get_ticks()*0.01)+1)/2
                    for card_x in [start_x, start_x + prev_w + gap]:
                        for glow in range(18, 0, -3):
                            alpha = max(30, 120 - glow*6) + int(60*pulse)
                            glow_surf = pygame.Surface((prev_w+glow*2, prev_h+glow*2), pygame.SRCALPHA)
                            pygame.draw.rect(glow_surf, (255, 40, 40, alpha), (0, 0, prev_w+glow*2, prev_h+glow*2), border_radius=CARD_RADIUS+10, width=glow)
                            screen.blit(glow_surf, (card_x-glow, start_y-glow))

                art = preview_tex_hd[preview_cid]
                if preview_state['orientation'] == 'inverted': 
                    art = pygame.transform.rotate(art, 180)
                screen.blit(art, (start_x, start_y))
                
                if preview_state['mode'] == 'fortune':
                    draw_card_glitter(screen, pygame.Rect(start_x, start_y, prev_w, prev_h), pygame.time.get_ticks() / 1000.0, "gold")
                elif preview_state['mode'] == 'major':
                    draw_card_glitter(screen, pygame.Rect(start_x, start_y, prev_w, prev_h), pygame.time.get_ticks() / 1000.0, "red")

                t_bg = pygame.Surface((prev_w, prev_h), pygame.SRCALPHA)
                draw_round_rect(t_bg, (0,0,prev_w,prev_h), (20, 25, 40, 255), CARD_RADIUS)
                pygame.draw.rect(t_bg, (180, 160, 100), (0,0,prev_w,prev_h), 4, CARD_RADIUS)

                if preview_state['orientation'] == 'upright':
                    top_box_rect = pygame.Rect(25, 60, prev_w-50, prev_h//2-100)
                    top_box = pygame.Surface((top_box_rect.w, top_box_rect.h), pygame.SRCALPHA)
                    p_rich_renderer.draw_rich_box(top_box, top_box.get_rect(), cd.get(f'{mk}_inverted', "..."), 0, show_scrollbar=False)
                    top_box = pygame.transform.rotate(top_box, 180)
                    t_bg.blit(top_box, (top_box_rect.x, top_box_rect.y))
                    
                    bottom_box_rect = pygame.Rect(25, prev_h//2+40, prev_w-50, prev_h//2-100)
                    preview_scrolls['current'] = clamp(preview_scrolls['current'], 0, preview_scrolls['max'])
                    preview_scrolls['max'] = p_rich_renderer.draw_rich_box(t_bg, bottom_box_rect, cd.get(f'{mk}_upright', "..."), preview_scrolls['current'])
                else:
                    top_box_rect = pygame.Rect(25, 60, prev_w-50, prev_h//2-100)
                    top_box = pygame.Surface((top_box_rect.w, top_box_rect.h), pygame.SRCALPHA)
                    p_rich_renderer.draw_rich_box(top_box, top_box.get_rect(), cd.get(f'{mk}_upright', "..."), 0, show_scrollbar=False)
                    top_box = pygame.transform.rotate(top_box, 180)
                    t_bg.blit(top_box, (top_box_rect.x, top_box_rect.y))
                    
                    bottom_box_rect = pygame.Rect(25, prev_h//2+40, prev_w-50, prev_h//2-100)
                    preview_scrolls['current'] = clamp(preview_scrolls['current'], 0, preview_scrolls['max'])
                    preview_scrolls['max'] = p_rich_renderer.draw_rich_box(t_bg, bottom_box_rect, cd.get(f'{mk}_inverted', "..."), preview_scrolls['current'])

                screen.blit(t_bg, (start_x + prev_w + gap, start_y))

                divider_y = start_y + prev_h // 2 - 18
                upright_label = f_labels.render("UPRIGHT", True, GOLD)
                reverse_label = f_labels.render("REVERSE", True, GOLD)
                upright_x = start_x + prev_w + gap + 20
                reverse_x = start_x + prev_w + gap + prev_w - reverse_label.get_width() - 20
                if preview_state['orientation'] == 'upright':
                    screen.blit(upright_label, (upright_x, divider_y))
                    reverse_label_rot = pygame.transform.rotate(reverse_label, 180)
                    screen.blit(reverse_label_rot, (reverse_x, divider_y))
                else:
                    upright_label_rot = pygame.transform.rotate(upright_label, 180)
                    screen.blit(reverse_label, (upright_x, divider_y))
                    screen.blit(upright_label_rot, (reverse_x, divider_y))

                effect_label = f_labels.render("EFFECT", True, GOLD)
                effect_bottom_y = start_y + prev_h - effect_label.get_height() - 10
                screen.blit(effect_label, (start_x + prev_w + gap + (prev_w - effect_label.get_width()) // 2, effect_bottom_y))
                effect_label_rot = pygame.transform.rotate(effect_label, 180)
                effect_top_y = start_y + 10
                screen.blit(effect_label_rot, (start_x + prev_w + gap + (prev_w - effect_label.get_width()) // 2, effect_top_y))

                name_s = f_preview_title.render(f"{cd['id']} - {cd['name']} ({preview_state['mode'].upper()} MODE)", True, GOLD)
                screen.blit(name_s, (W//2-name_s.get_width()//2, H-80))

                if links:
                    spell_box = pygame.Rect(start_x + (prev_w + gap) * 2, start_y, spell_w, prev_h)
                    draw_round_rect(screen, spell_box, (15, 20, 30, 240), 15); pygame.draw.rect(screen, GOLD, spell_box, 2, 15)
                    title_s = f_labels.render("SPELLS", True, GOLD); screen.blit(title_s, (spell_box.centerx - title_s.get_width()//2, spell_box.y + 15))
                    for i, (label, url) in enumerate(links):
                        lbr = pygame.Rect(spell_box.x+10, spell_box.y+85+i*65, spell_box.w-20, 50)
                        draw_round_rect(screen, lbr, (40, 60, 90) if lbr.collidepoint(m_pos) else (20, 30, 50), 10); pygame.draw.rect(screen, GOLD, lbr, 2, 10)
                        screen.blit(f_hand_header.render(label, True, (240, 240, 255)), f_hand_header.render(label, True, (240, 240, 255)).get_rect(center=lbr.center))
                
                exit_view_btn.draw(screen, f_small, dt)

            elif screen_mode == "fool_video":
                screen.fill((0, 0, 0))
                frame_surface = fool_video_state["frame_surface"]
                if frame_surface is not None:
                    fw, fh = frame_surface.get_size()
                    scale = min(W / fw, H / fh)
                    dw, dh = max(1, int(fw * scale)), max(1, int(fh * scale))
                    video_frame = pygame.transform.smoothscale(frame_surface, (dw, dh))
                    screen.blit(video_frame, ((W - dw) // 2, (H - dh) // 2))

            elif screen_mode in ["deck", "vanish_view", "world_restore_view", "prophet_selection", "ppf_selection", "stack_selection", "major_selection"]:
                # Render looping video background for prophet_selection and deck
                _active_bg = None
                if screen_mode == "prophet_selection": _active_bg = prophet_bg_video
                elif screen_mode == "deck": _active_bg = deck_bg_video
                if _active_bg and _active_bg["frame_surface"] is not None:
                    _fs = _active_bg["frame_surface"]
                    _fw, _fh = _fs.get_size()
                    _scale = max(W / _fw, H / _fh)
                    _dw, _dh = max(1, int(_fw * _scale)), max(1, int(_fh * _scale))
                    _vf = pygame.transform.smoothscale(_fs, (_dw, _dh))
                    screen.blit(_vf, ((W - _dw) // 2, (H - _dh) // 2))
                    # Dim overlay so cards remain readable
                    _dim = pygame.Surface((W, H), pygame.SRCALPHA)
                    _dim.fill((10, 12, 18, 140))
                    screen.blit(_dim, (0, 0))

                hi, fi, cur_list = [h['id'] for h in game.hand], [f['id'] for f in (game.fortune_zone+game.major_zone)], []
                if screen_mode == "ppf_selection": cur_list = [c for c in game.ids if c not in MAJOR_FORTUNE_IDS and c not in game.vanished and c not in hi and c not in fi]
                elif screen_mode == "world_restore_view": cur_list = [vid for vid in game.vanished if vid != 20]
                elif screen_mode == "deck": cur_list = game.deck
                elif screen_mode == "vanish_view": cur_list = game.vanished
                elif screen_mode == "prophet_selection": cur_list = [c for c in game.ids if c != 20 and c not in hi and c not in fi]
                elif screen_mode == "stack_selection": cur_list = [c for c in game.deck if c != 20]
                elif screen_mode == "major_selection": cur_list = [c for c in MAJOR_FORTUNE_IDS if c not in game.vanished and c not in hi and c not in fi]
                
                if screen_mode == "deck":
                    title_text = "MAIN DECK"
                    title_color = GOLD
                elif screen_mode == "vanish_view":
                    title_text = "VANISHED PILE"
                    title_color = (200, 50, 20)
                else:
                    title_text = None
                
                if title_text:
                    title_font = pygame.font.SysFont("timesnewroman", 64, bold=True)
                    title_surf = title_font.render(title_text, True, title_color)
                    title_y = VIEW_START_Y + 20 - scroll_y
                    title_rect = title_surf.get_rect(center=(W//2, title_y))
                    glow_surf = pygame.Surface((title_rect.w + 20, title_rect.h + 20), pygame.SRCALPHA)
                    pygame.draw.rect(glow_surf, (*title_color, 50), glow_surf.get_rect(), border_radius=10)
                    screen.blit(glow_surf, (title_rect.x - 10, title_rect.y - 10))
                    screen.blit(title_surf, title_rect)
                
                for i, cid in enumerate(cur_list):
                    gx, gy = VIEW_START_X+(i%6)*CELL_W, VIEW_START_Y+(i//6)*CELL_H-scroll_y+160
                    if -VIEW_CARD_H < gy < H: screen.blit(v_face_view if screen_mode=="vanish_view" else view_tex[cid], (gx, gy))
                # Grid scrollbar
                _g_max_scroll_draw = get_card_grid_max_scroll(len(cur_list), H)
                if _g_max_scroll_draw > 0:
                    _g_sb_w_d = 14
                    _g_track_x_d = W - 30
                    _g_track_y_d = VIEW_START_Y + 160
                    _g_track_h_d = H - _g_track_y_d - 40
                    _g_handle_h_d = max(_g_sb_w_d, int(_g_track_h_d * min(1, _g_track_h_d / max(1, _g_track_h_d + _g_max_scroll_draw))))
                    pygame.draw.rect(screen, (30, 35, 50), (_g_track_x_d, _g_track_y_d, _g_sb_w_d, _g_track_h_d))
                    pygame.draw.rect(screen, GOLD, (_g_track_x_d, _g_track_y_d, _g_sb_w_d, _g_track_h_d), 1)
                    _g_scroll_ratio = scroll_y / max(1, _g_max_scroll_draw)
                    _g_handle_y_d = _g_track_y_d + int((_g_track_h_d - _g_handle_h_d) * _g_scroll_ratio)
                    pygame.draw.rect(screen, GOLD, (_g_track_x_d, _g_handle_y_d, _g_sb_w_d, _g_handle_h_d))
                exit_view_btn.draw(screen, f_small, dt)

            if current_roll_anim: current_roll_anim.draw(screen, f_seer_dice_sim, f_seer_massive)
            
            if game.toast_timer > 0:
                t_surf = f_small.render(game.toast_msg, True, (255,255,255))
                pygame.draw.rect(screen, (0,0,0,180), (W//2-200, 20, 400, 40), border_radius=10)
                screen.blit(t_surf, t_surf.get_rect(center=(W//2, 40)))
            
            pygame.display.flip()

    except Exception: log_event(traceback.format_exc(), True); pygame.quit(); sys.exit()

if __name__ == "__main__": safe_main()
