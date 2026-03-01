from .core import *
from .game import Game

# ----------------------------
# 8. MAIN STARTUP
# ----------------------------

def safe_main():
    try:
        random.seed(int.from_bytes(os.urandom(16), "big") ^ time.time_ns())
        screen, W, H = safe_init(); clock = pygame.time.Clock(); f_title, f_small, f_tiny, f_seer_bold, f_seer_dice_sim, f_seer_massive, f_preview_title, f_preview_body, f_labels, f_hand_header, f_hand_body = pygame.font.SysFont("Segoe UI", 26, True), pygame.font.SysFont("Segoe UI", 18, True), pygame.font.SysFont("Segoe UI", 18), pygame.font.SysFont("Segoe UI", 20, True), pygame.font.SysFont("Segoe UI", 24, True), pygame.font.SysFont("timesnewroman", 72, True), pygame.font.SysFont("timesnewroman", 44, bold=True), pygame.font.SysFont("georgia", 26), pygame.font.SysFont("timesnewroman", 32, bold=True), pygame.font.SysFont("timesnewroman", 22, bold=True), pygame.font.SysFont("georgia", 18)

        _loading_log = []       # list of (status_text, thumb_surface_or_None)
        _loading_display_pct = 0.0
        _loading_font_log = pygame.font.SysFont("Georgia", 18, True)
        _loading_font_status = pygame.font.SysFont("Georgia", 20, True)
        _loading_font_title = pygame.font.SysFont("Times New Roman", 38, True)
        _loading_font_pct = pygame.font.SysFont("Times New Roman", 24, True)
        _loading_particles = []   # list of [x, y, vx, vy, life, max_life, size, color]
        # Loading screen background video
        _loading_bg_video = {
            "backend": None,  # "cv2" | "imageio" | None
            "path": os.path.join(VIDEOS_DIR, "Fortune_Card_Menu.mp4"),
            "cap": None,
            "reader": None,
            "fps": 30.0,
            "frame_interval": 1.0 / 30.0,
            "accum": 0.0,
            "frame_surface": None,
        }

        def _open_loading_bg_video():
            if not os.path.isfile(_loading_bg_video["path"]):
                log_event(f"Loading video not found: {_loading_bg_video['path']}", is_error=True)
                return

            try:
                import cv2 as _cv2_load
                _lbg_cap = _cv2_load.VideoCapture(_loading_bg_video["path"])
                if _lbg_cap.isOpened():
                    _lbg_fps = _lbg_cap.get(_cv2_load.CAP_PROP_FPS)
                    if not _lbg_fps or _lbg_fps <= 1:
                        _lbg_fps = 30.0
                    _loading_bg_video["backend"] = "cv2"
                    _loading_bg_video["cap"] = _lbg_cap
                    _loading_bg_video["fps"] = _lbg_fps
                    _loading_bg_video["frame_interval"] = 1.0 / _lbg_fps
                    log_event("Loading video backend: cv2")
                    return
            except Exception as _cv2_ex:
                log_event(f"cv2 unavailable for loading video: {_cv2_ex}", is_error=True)

            try:
                import imageio.v2 as _iio
                _reader = _iio.get_reader(_loading_bg_video["path"], format="ffmpeg")
                _meta = _reader.get_meta_data() or {}
                _lbg_fps = float(_meta.get("fps", 30.0) or 30.0)
                if _lbg_fps <= 1:
                    _lbg_fps = 30.0
                _loading_bg_video["backend"] = "imageio"
                _loading_bg_video["reader"] = _reader
                _loading_bg_video["fps"] = _lbg_fps
                _loading_bg_video["frame_interval"] = 1.0 / _lbg_fps
                log_event("Loading video backend: imageio")
                return
            except Exception as _iio_ex:
                log_event(f"imageio unavailable for loading video: {_iio_ex}", is_error=True)

            log_event("Loading video disabled: no usable backend found.", is_error=True)

        def _close_loading_bg_video():
            if _loading_bg_video["cap"] is not None:
                _loading_bg_video["cap"].release()
                _loading_bg_video["cap"] = None
            if _loading_bg_video["reader"] is not None:
                try:
                    _loading_bg_video["reader"].close()
                except Exception:
                    pass
                _loading_bg_video["reader"] = None

        _open_loading_bg_video()
        # Keep units consistent with render-time timestamps (seconds).
        _loading_last_time = [pygame.time.get_ticks() / 1000.0]

        def draw_loading_screen(pct, status, thumb=None):
            nonlocal _loading_display_pct
            _loading_log.append((status, thumb))
            # Smooth interpolation toward target percentage
            anim_steps = 6
            step_sleep = 0.008
            target = pct
            for _ai in range(anim_steps):
                _loading_display_pct += (target - _loading_display_pct) * 0.22
                if _ai == anim_steps - 1:
                    _loading_display_pct = target
                _render_loading_frame(_loading_display_pct, status, thumb)
                time.sleep(step_sleep)

        def _render_loading_frame(pct, status, thumb):
            screen.fill((8, 6, 18))
            t = pygame.time.get_ticks() / 1000.0
            # --- Video background ---
            _dt_load = t - _loading_last_time[0]
            if _dt_load < 0:
                _dt_load = 0
            _loading_last_time[0] = t
            if _loading_bg_video["backend"] is not None:
                _loading_bg_video["accum"] += _dt_load
                while _loading_bg_video["accum"] >= _loading_bg_video["frame_interval"]:
                    _loading_bg_video["accum"] -= _loading_bg_video["frame_interval"]
                    ret, frame = False, None
                    if _loading_bg_video["backend"] == "cv2" and _loading_bg_video["cap"] is not None:
                        try:
                            import cv2
                            ret, frame = _loading_bg_video["cap"].read()
                            if not ret:
                                _loading_bg_video["cap"].set(cv2.CAP_PROP_POS_FRAMES, 0)
                                ret, frame = _loading_bg_video["cap"].read()
                        except Exception:
                            ret, frame = False, None
                    elif _loading_bg_video["backend"] == "imageio" and _loading_bg_video["reader"] is not None:
                        try:
                            frame = _loading_bg_video["reader"].get_next_data()
                            ret = frame is not None
                        except Exception:
                            ret = False
                            try:
                                _loading_bg_video["reader"].close()
                            except Exception:
                                pass
                            try:
                                import imageio.v2 as _iio
                                _loading_bg_video["reader"] = _iio.get_reader(_loading_bg_video["path"], format="ffmpeg")
                                frame = _loading_bg_video["reader"].get_next_data()
                                ret = frame is not None
                            except Exception:
                                ret, frame = False, None
                    if not ret:
                        break
                    try:
                        if _loading_bg_video["backend"] == "cv2":
                            import cv2
                            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        fh_v, fw_v = frame.shape[:2]
                        if len(frame.shape) >= 3 and frame.shape[2] == 4:
                            surface = pygame.image.frombuffer(frame.tobytes(), (fw_v, fh_v), "RGBA").convert_alpha()
                        else:
                            surface = pygame.image.frombuffer(frame.tobytes(), (fw_v, fh_v), "RGB").convert()
                        _loading_bg_video["frame_surface"] = pygame.transform.smoothscale(surface, (W, H))
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
            log_top = by + bh + 110
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
                # Entry text â€” color by type
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
        fortune_spell_entries = []
        fortune_glossary_terms = []
        _spell_library_data_path = os.path.join(DOCS_DIR, "spell_library_data.json")
        try:
            _raw_spells = []
            _spell_payload = None
            _offline_spell_path = docs_or_resource_path("spell_library_data.json")
            if os.path.exists(_offline_spell_path):
                with open(_offline_spell_path, "r", encoding="utf-8") as _sf:
                    _spell_payload = json.load(_sf)
            else:
                with open(docs_or_resource_path("glossary.json"), "r", encoding="utf-8") as _gf:
                    _spell_payload = json.load(_gf)
            _raw_spells = _spell_payload.get("spells", []) if isinstance(_spell_payload, dict) else []
            fortune_spell_entries = []
            for _s in _raw_spells:
                if not isinstance(_s, dict):
                    continue
                _name = str(_s.get("name", "")).strip()
                if not _name:
                    continue
                _url = str(_s.get("url", "")).strip()
                _lv = _s.get("level", None)
                _lv = _lv if isinstance(_lv, int) and 0 <= _lv <= 9 else None
                _school = str(_s.get("school", "Unknown") or "Unknown").strip() or "Unknown"
                _classes = sorted({
                    str(_c).strip().title()
                    for _c in (_s.get("classes") or [])
                    if str(_c).strip()
                })
                fortune_spell_entries.append({
                    "name": _name,
                    "url": _url,
                    "level": _lv,
                    "school": _school,
                    "classes": _classes,
                })
            fortune_spell_entries.sort(key=lambda _s: _s["name"].lower())
        except Exception as _ex:
            log_event(f"Could not load spell list glossary.json: {_ex}", is_error=True)
            fortune_spell_entries = []

        def _norm_spell_name(_s):
            return re.sub(r"[^a-z0-9]+", "", str(_s).lower())

        _spell_meta_cache = {}
        _spell_meta_cache_path = os.path.join(DOCS_DIR, "spell_metadata_cache.json")
        try:
            if os.path.exists(_spell_meta_cache_path):
                with open(_spell_meta_cache_path, "r", encoding="utf-8") as _cf:
                    _loaded_cache = json.load(_cf)
                if isinstance(_loaded_cache, dict):
                    _spell_meta_cache = _loaded_cache
        except Exception as _ex:
            log_event(f"Could not read spell metadata cache: {_ex}", is_error=True)
        _spell_meta_cache_dirty = False
        _spell_library_data_dirty = not os.path.exists(_spell_library_data_path)
        for _sp in fortune_spell_entries:
            _nm_key = _norm_spell_name(_sp.get("name", ""))
            if not _nm_key:
                continue
            _sp_level = _sp.get("level", None)
            _sp_school = str(_sp.get("school", "Unknown") or "Unknown")
            _sp_classes = [str(_c).strip() for _c in (_sp.get("classes") or []) if str(_c).strip()]
            _has_meta = (isinstance(_sp_level, int) and 0 <= _sp_level <= 9) or (_sp_school != "Unknown") or bool(_sp_classes)
            if _has_meta and _nm_key not in _spell_meta_cache:
                _spell_meta_cache[_nm_key] = {
                    "url": str(_sp.get("url", "")).strip(),
                    "level": _sp_level if isinstance(_sp_level, int) and 0 <= _sp_level <= 9 else None,
                    "school": _sp_school,
                    "classes": sorted({str(_c).strip().title() for _c in _sp_classes if str(_c).strip()}),
                    "source": "offline",
                }

        def _clean_html_text(_s):
            _t = re.sub(r"<[^>]+>", "", str(_s))
            return re.sub(r"\s+", " ", _t).strip()

        def _parse_aidedd_spell_meta_from_html(_html):
            _level = None
            _school = "Unknown"
            _classes = []

            _ecole = None
            _m_ecole = re.search(r"<div class=['\"]ecole['\"]>(.*?)</div>", _html, re.I | re.S)
            if _m_ecole:
                _ecole = _clean_html_text(_m_ecole.group(1))
            _ecole_l = (_ecole or "").lower()

            # Old pages: "level 2 - transmutation"
            _m_old = re.search(r"level\s*(\d+|cantrip)\s*[-–]\s*([a-zA-Z]+)", _ecole_l, re.I)
            if _m_old:
                _lv = _m_old.group(1).strip().lower()
                _level = 0 if _lv == "cantrip" else int(_lv)
                _school = _m_old.group(2).strip().title()

            # New pages: "Level 2 Abjuration (Bard, Cleric, ...)"
            _m_new = re.search(r"level\s*(\d+)\s+([a-zA-Z]+)\s*\(([^)]*)\)", _ecole or "", re.I)
            if _m_new:
                _level = int(_m_new.group(1))
                _school = _m_new.group(2).strip().title()
                _cls_txt = _m_new.group(3).strip()
                if _cls_txt:
                    _classes.extend([_c.strip().title() for _c in _cls_txt.split(",") if _c.strip()])

            _m_new_cantrip = re.search(r"(cantrip)\s+([a-zA-Z]+)\s*\(([^)]*)\)", _ecole or "", re.I)
            if _m_new_cantrip:
                _level = 0
                _school = _m_new_cantrip.group(2).strip().title()
                _cls_txt = _m_new_cantrip.group(3).strip()
                if _cls_txt:
                    _classes.extend([_c.strip().title() for _c in _cls_txt.split(",") if _c.strip()])

            # Old pages: classes in spans class='classe'
            for _m_cls in re.finditer(r"class=['\"]classe['\"]>([^<]+)<", _html, re.I):
                _cn = _clean_html_text(_m_cls.group(1)).title()
                if _cn:
                    _classes.append(_cn)

            _classes = sorted({c for c in _classes if c})
            if not (isinstance(_level, int) and 0 <= _level <= 9):
                _level = None
            if not _school:
                _school = "Unknown"
            return _level, _school, _classes

        fortune_spell_class_options = ["all"]
        fortune_spell_school_options = ["all"]

        def _format_glossary_term(_term):
            _clean = re.sub(r"\s+", " ", str(_term).strip())
            if not _clean:
                return ""

            def _capitalize_word(_match):
                _word = _match.group(0)
                if len(_word) > 1 and _word.isupper():
                    return _word
                return _word[:1].upper() + _word[1:].lower()

            return re.sub(r"[A-Za-z]+(?:'[A-Za-z]+)?", _capitalize_word, _clean)

        def _collect_bold_terms(_node, _acc):
            if isinstance(_node, dict):
                for _v in _node.values():
                    _collect_bold_terms(_v, _acc)
            elif isinstance(_node, list):
                for _v in _node:
                    _collect_bold_terms(_v, _acc)
            elif isinstance(_node, str):
                for _m in re.findall(r"\*\*(.*?)\*\*", _node):
                    _t = _format_glossary_term(_m)
                    if _t:
                        _acc.add(_t)

        _term_set = set()
        _collect_bold_terms(cards_raw, _term_set)
        fortune_glossary_terms = sorted(_term_set, key=lambda _t: _t.lower())
        
        _menu_element_files = [
            "Draw_Button_Image.png",
            "Stack_Button_Image.png",
            "History_Button.png",
            "Turn_Undead_Button.png",
            "Destroy_Undead_Button.png",
            "Settings_Menu_Image.png",
            "Draw_of_Fate_Token.png",
            "Side_Panel_Image.png",
            "Rest_Button.png",
            "Fortune_Card_Stamp.png",
            "Major_Fortune_Card Stamp.png",
            "Glossary_Button.png",
            "Spell_Library.png",
        ]
        preloaded_ui_images = {}
        hand_tex, view_tex, preview_tex_hd, preview_bgs, thumb_tex, total_steps, cur_step = {}, {}, {}, {}, {}, len(cards_raw) * 4 + 3 + len(_menu_element_files), 0
        def _asset_pct(step): return (step / max(1, total_steps)) * 0.9
        _loading_pct_cur = 0.0
        def _animate_loading_step(target_pct, status, thumb=None, duration=1.0):
            nonlocal _loading_pct_cur
            start_pct = _loading_pct_cur
            target_pct = max(start_pct, target_pct)
            _st = time.time()
            while True:
                _el = time.time() - _st
                _t = clamp(_el / max(0.01, duration), 0.0, 1.0)
                # Smoothstep for fluid progress motion.
                _ts = _t * _t * (3.0 - 2.0 * _t)
                _cur = start_pct + (target_pct - start_pct) * _ts
                draw_loading_screen(_cur, status, thumb)
                for _ev in pygame.event.get():
                    if _ev.type == pygame.QUIT:
                        pygame.quit()
                        return False
                if _t >= 1.0:
                    break
            _loading_pct_cur = target_pct
            return True
        THUMB_H, THUMB_W = 185, 132
        for c in cards_raw:
            cid, cname, img_path = c['id'], c['name'], os.path.join(IMAGES_DIR, c['image'])
            hand_tex[cid] = load_image_safe(img_path, (HAND_CARD_W, HAND_CARD_H), cname); cur_step += 1
            if not _animate_loading_step(_asset_pct(cur_step), f"Hand Texture: {cname}", hand_tex[cid], duration=0.1): return
            view_tex[cid] = load_image_safe(img_path, (VIEW_CARD_W, VIEW_CARD_H), cname); cur_step += 1
            if not _animate_loading_step(_asset_pct(cur_step), f"Grid Texture: {cname}", hand_tex[cid], duration=0.1): return
            thumb_tex[cid] = pygame.transform.smoothscale(hand_tex[cid], (THUMB_W, THUMB_H))
            prev_h, prev_w = int(H * 0.80), int(int(H * 0.80) * (HAND_CARD_W / HAND_CARD_H))
            preview_tex_hd[cid] = load_image_safe(img_path, (prev_w, prev_h), cname); cur_step += 1
            if not _animate_loading_step(_asset_pct(cur_step), f"HD View: {cname}", hand_tex[cid], duration=0.1): return
            found = next((f for f in os.listdir(IMAGES_DIR) if f.lower().startswith(f"{cid}-") and f.lower().endswith("_bg.png")), None); preview_bgs[cid] = pygame.transform.smoothscale(pygame.image.load(os.path.join(IMAGES_DIR, found)).convert(), (W, H)) if found else pygame.Surface((W,H)); cur_step += 1
            if not _animate_loading_step(_asset_pct(cur_step), f"Backdrop: {cname}", hand_tex[cid], duration=0.1): return
        
        menu_bg, normal_bg, deck_back_sm, v_face_hand = load_image_safe(os.path.join(IMAGES_DIR, MENU_BG_IMAGE), (W, H)), load_image_safe(os.path.join(IMAGES_DIR, NORMAL_BG_IMAGE), (W, H)), load_image_safe(os.path.join(IMAGES_DIR, DECK_BACK_IMAGE), (160, 224)), load_image_safe(os.path.join(IMAGES_DIR, VANISHED_CARD_IMAGE), (HAND_CARD_W, HAND_CARD_H))
        deck_pile_frame = load_image_safe(os.path.join(IMAGES_DIR, DECK_PILE_IMAGE), (210, 310))
        vanish_pile_frame = load_image_safe(os.path.join(IMAGES_DIR, VANISH_PILE_IMAGE), (210, 310))
        _pile_tint = pygame.Surface((210, 310), pygame.SRCALPHA)
        _pile_tint.fill((60, 60, 70, 75))
        deck_pile_frame.blit(_pile_tint, (0, 0))
        vanish_pile_frame.blit(_pile_tint, (0, 0))
        deck_pile_frame = fade_edges_to_alpha(deck_pile_frame, feather=26)
        vanish_pile_frame = fade_edges_to_alpha(vanish_pile_frame, feather=26)
        cur_step += 1
        if not _animate_loading_step(_asset_pct(cur_step), "Interface Textures", v_face_hand, duration=0.1): return
        v_face_view, v_face_deck = pygame.transform.smoothscale(v_face_hand, (VIEW_CARD_W, VIEW_CARD_H)), pygame.transform.smoothscale(v_face_hand, (160, 224))
        cur_step += 1
        if not _animate_loading_step(_asset_pct(cur_step), "Finalizing Visual Assets", v_face_hand, duration=0.1): return

        for _fname in _menu_element_files:
            _fp = os.path.join(IMAGES_DIR, _fname)
            _img = None
            try:
                if os.path.exists(_fp):
                    _img = pygame.image.load(_fp).convert_alpha()
            except Exception as _ex:
                log_event(f"Could not load UI element {_fname}: {_ex}", is_error=True)
            preloaded_ui_images[_fname] = _img
            cur_step += 1
            _label = os.path.splitext(_fname)[0].replace("_", " ")
            if not _animate_loading_step(_asset_pct(cur_step), f"Main Menu Element: {_label}", _img if _img is not None else v_face_hand, duration=0.1): return

        glow_gold, glow_purple, game = make_glow(HAND_CARD_W, HAND_CARD_H, GOLD), make_glow(HAND_CARD_W, HAND_CARD_H, PURPLE_TAP), Game(cards_raw)

        # RENDERING TOOLS
        f_rich_reg = pygame.font.SysFont("georgia", 18)
        f_rich_bold = pygame.font.SysFont("georgia", 18, bold=True)
        rich_renderer = RichTextRenderer(f_rich_reg, f_rich_bold)

        f_p_reg = pygame.font.SysFont("georgia", 26)
        f_p_bold = pygame.font.SysFont("georgia", 26, bold=True)
        p_rich_renderer = RichTextRenderer(f_p_reg, f_p_bold)
        prebuilt_fortune_back_cache = {}

        def _build_mode_back_surface_loading(cid, mode, w, h):
            mode_key = mode if mode in ["fortune", "major"] else "effect"
            cd = game.cards[cid]
            surf = pygame.Surface((w, h), pygame.SRCALPHA)
            draw_round_rect(surf, (0, 0, w, h), (20, 25, 40, 255), 12)
            pygame.draw.rect(surf, (180, 160, 100), (0, 0, w, h), 3, 12)
            margin = 10
            top_h = max(48, (h // 2) - 24)
            box_w = w - margin * 2
            top_box = pygame.Surface((box_w, top_h), pygame.SRCALPHA)
            rich_renderer.draw_rich_box(top_box, top_box.get_rect(), cd.get(f"{mode_key}_inverted", "..."), 0, show_scrollbar=False)
            top_box = pygame.transform.rotate(top_box, 180)
            surf.blit(top_box, (margin, 10))
            bottom_box = pygame.Rect(margin, (h // 2) + 6, box_w, top_h)
            rich_renderer.draw_rich_box(surf, bottom_box, cd.get(f"{mode_key}_upright", "..."), 0, show_scrollbar=False)
            return surf

        _prep_total = max(1, len(game.ids))
        _prep_thumb = None
        for _idx, _cid in enumerate(game.ids, start=1):
            prebuilt_fortune_back_cache[(_cid, "fortune", 168, 242)] = _build_mode_back_surface_loading(_cid, "fortune", 168, 242)
            prebuilt_fortune_back_cache[(_cid, "major", 152, 214)] = _build_mode_back_surface_loading(_cid, "major", 152, 214)
            _prep_thumb = thumb_tex.get(_cid)
            for _ev in pygame.event.get():
                if _ev.type == pygame.QUIT:
                    pygame.quit()
                    return
        cur_step += 1
        if not _animate_loading_step(_asset_pct(cur_step), "Preparing Fortune Selection", _prep_thumb, duration=0.1): return

        # Last 10%: spells + options/settings
        _spell_total = max(1, len(fortune_spell_entries))
        _spell_loading_update_every = 5
        for _i, _sp in enumerate(fortune_spell_entries, start=1):
            _nm_key = _norm_spell_name(_sp.get("name", ""))
            _url = str(_sp.get("url", "")).strip()
            _cached = _spell_meta_cache.get(_nm_key) if isinstance(_spell_meta_cache, dict) else None
            _prev_level = _sp.get("level", None)
            _prev_school = str(_sp.get("school", "Unknown") or "Unknown")
            _prev_classes = sorted({str(_c).strip().title() for _c in (_sp.get("classes") or []) if str(_c).strip()})
            _level = _prev_level if isinstance(_prev_level, int) and 0 <= _prev_level <= 9 else None
            _school = _prev_school if _prev_school else "Unknown"
            _classes = _prev_classes
            _need_fetch = not ((isinstance(_level, int) and 0 <= _level <= 9) or (_school != "Unknown") or bool(_classes))
            if isinstance(_cached, dict):
                _c_url = str(_cached.get("url", "")).strip()
                _c_level = _cached.get("level", None)
                _c_school = str(_cached.get("school", "Unknown") or "Unknown")
                _c_classes = [str(_c).strip() for _c in (_cached.get("classes") or []) if str(_c).strip()]
                if _c_url == _url and (_c_level is None or isinstance(_c_level, int)) and _c_school and isinstance(_c_classes, list):
                    _level = _c_level if isinstance(_c_level, int) and 0 <= _c_level <= 9 else None
                    _school = _c_school
                    _classes = _c_classes
                    _need_fetch = False
            if _need_fetch and _url:
                try:
                    import urllib.request as _urlrq
                    _html = _urlrq.urlopen(_url, timeout=8).read().decode("utf-8", "ignore")
                    _level, _school, _classes = _parse_aidedd_spell_meta_from_html(_html)
                    _spell_meta_cache[_nm_key] = {
                        "url": _url,
                        "level": _level,
                        "school": _school,
                        "classes": _classes,
                        "source": "aidedd",
                    }
                    _spell_meta_cache_dirty = True
                except Exception:
                    pass

            _sp["level"] = _level if isinstance(_level, int) and 0 <= _level <= 9 else None
            _sp["school"] = _school if _school else "Unknown"
            _sp["classes"] = sorted({str(_c).strip().title() for _c in _classes}) if isinstance(_classes, list) else []
            if _sp["level"] != _prev_level or _sp["school"] != _prev_school or _sp["classes"] != _prev_classes:
                _spell_library_data_dirty = True

            _frac = _i / _spell_total
            if (_i % _spell_loading_update_every == 0) or (_i == _spell_total):
                draw_loading_screen(0.9 + (_frac * 0.05), f"Loading spells... {int(_frac * 100)}%")
            for _ev in pygame.event.get():
                if _ev.type == pygame.QUIT:
                    pygame.quit()
                    return

        if _spell_meta_cache_dirty:
            try:
                with open(_spell_meta_cache_path, "w", encoding="utf-8") as _cf:
                    json.dump(_spell_meta_cache, _cf, indent=2)
            except Exception as _ex:
                log_event(f"Could not write spell metadata cache: {_ex}", is_error=True)

        if _spell_library_data_dirty or not os.path.exists(_spell_library_data_path):
            try:
                _spells_out = [
                    {
                        "name": str(_s.get("name", "")).strip(),
                        "url": str(_s.get("url", "")).strip(),
                        "level": (_s.get("level") if isinstance(_s.get("level"), int) and 0 <= _s.get("level") <= 9 else None),
                        "school": str(_s.get("school", "Unknown") or "Unknown"),
                        "classes": sorted({str(_c).strip().title() for _c in (_s.get("classes") or []) if str(_c).strip()}),
                    }
                    for _s in fortune_spell_entries
                    if isinstance(_s, dict) and str(_s.get("name", "")).strip()
                ]
                _spells_out.sort(key=lambda _s: _s["name"].lower())
                with open(_spell_library_data_path, "w", encoding="utf-8") as _sf:
                    json.dump({
                        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "source": "offline_spell_library",
                        "spells": _spells_out,
                    }, _sf, indent=2)
            except Exception as _ex:
                log_event(f"Could not write offline spell library data: {_ex}", is_error=True)

        fortune_spell_class_options = ["all"] + sorted({c for _s in fortune_spell_entries for c in (_s.get("classes") or [])}, key=lambda x: x.lower())
        fortune_spell_school_options = ["all"] + sorted({str(_s.get("school", "Unknown")) for _s in fortune_spell_entries}, key=lambda x: x.lower())

        # Final 5%: options/settings
        user_settings = load_user_settings()
        _settings_stage_seconds = 2.5
        _settings_start = time.time()
        while True:
            _elapsed = time.time() - _settings_start
            _frac = clamp(_elapsed / _settings_stage_seconds, 0.0, 1.0)
            draw_loading_screen(0.95 + (_frac * 0.05), f"Loading options... {int(_frac * 100)}%")
            for _ev in pygame.event.get():
                if _ev.type == pygame.QUIT:
                    pygame.quit()
                    return
            if _frac >= 1.0:
                break

        # Keep the loading background video active until the loading screen is fully done.
        _close_loading_bg_video()

        # BUTTON IMAGES
        def _load_btn_img(fname):
            if fname in preloaded_ui_images:
                return preloaded_ui_images.get(fname)
            p = os.path.join(IMAGES_DIR, fname)
            if os.path.exists(p):
                return pygame.image.load(p).convert_alpha()
            return None
        _img_draw = _load_btn_img("Draw_Button_Image.png")
        _img_stack = _load_btn_img("Stack_Button_Image.png")
        _img_history = _load_btn_img("History_Button.png")
        _img_turn_undead = _load_btn_img("Turn_Undead_Button.png")
        _img_destroy_undead = _load_btn_img("Destroy_Undead_Button.png")
        _img_divine_intervention = _load_btn_img("Divine_Intervention.png")
        _img_undo = _load_btn_img("Undo_Button.png")
        _img_redo = _load_btn_img("Redo_Button.png")
        _img_settings = _load_btn_img("Settings_Menu_Image.png")
        _img_dof_token = _load_btn_img("Draw_of_Fate_Token.png")
        _img_side_panel = _load_btn_img("Side_Panel_Image.png")
        _img_rest = _load_btn_img("Rest_Button.png")
        _img_fortune_stamp = _load_btn_img("Fortune_Card_Stamp.png")
        _img_major_stamp = _load_btn_img("Major_Fortune_Card Stamp.png")
        _img_continue = _load_btn_img("Continue_Button.png")
        _img_new_game = _load_btn_img("New_Game_Button.png")
        _img_load_game = _load_btn_img("Load_Button.png")
        _img_options = _load_btn_img("Options_Button.png")
        _img_exit = _load_btn_img("Exit_Button.png")
        _img_library = _load_btn_img("Library_Button.png")
        _img_fortune_loadout_menu = _load_btn_img("Card_Menu.png")
        _img_ppf = _load_btn_img("PP&F_Button.png")
        _img_main_menu = _load_btn_img("Main_Menu_Button.png")
        _img_save = _load_btn_img("Save_Button.png")
        _img_save_as = _load_btn_img("Save_As_Button.png")
        _img_fate_card = _load_btn_img("Fate_Card_Button.png")
        _img_spell_list = _load_btn_img("Spell_List.png")
        _img_library_bg = _load_btn_img("Library_BG.png")
        _img_spell_library_bg = _load_btn_img("Spell_Library_BG.png")
        _img_glossary_bg = _load_btn_img("Glossary_BG.png")

        def _draw_promotion_stamp(_card_rect, _is_major=False, _inverted=False):
            _src = _img_major_stamp if _is_major else _img_fortune_stamp
            if _src is None:
                return
            _stamp_h = max(26, int(_card_rect.h * 0.22))
            _scale = _stamp_h / max(1, _src.get_height())
            _stamp_w = max(26, int(_src.get_width() * _scale))
            _stamp = pygame.transform.smoothscale(_src, (_stamp_w, _stamp_h))
            if _inverted:
                _stamp = pygame.transform.rotate(_stamp, 180)
                _sx = _card_rect.x + 6
                _sy = _card_rect.bottom - _stamp_h - 6
            else:
                _sx = _card_rect.right - _stamp_w - 6
                _sy = _card_rect.y + 6
            screen.blit(_stamp, (_sx, _sy))

        def _load_sfx(path):
            try:
                return pygame.mixer.Sound(path) if os.path.exists(path) else None
            except Exception:
                return None
        _sfx_button_press = _load_sfx(BUTTON_PRESS_SOUND)
        _sfx_turnpage = _load_sfx(TURNPAGE_SOUND)
        _sfx_major_promo = _load_sfx(MAJOR_PROMOTION_SOUND)
        _sfx_fortune_promo = _load_sfx(FORTUNE_PROMOTION_SOUND)
        _sfx_pot_of_greed = _load_sfx(os.path.join(VIDEOS_DIR, "I SUMMON POT OF GREED.wav"))

        # UI BUTTONS
        ui_x, ui_w = PADDING+PANEL_INNER_PAD, PANEL_W-PANEL_INNER_PAD*2
        lvl_change_dd = FantasyLevelStepper((ui_x + 15, PADDING + 45, ui_w - 30, 42), 1, 20, 1)
        past_present_future_btn = Button((ui_x, 115, ui_w, 360), "Past, Present and Future (3/3)", gold=True, image=_img_ppf)
        fated_card_btn = Button((ui_x, 305, ui_w, 360), "Fated Card Button", danger=True, fire=True, image=_img_fate_card)
        reset_major_btn = Button((ui_x, 675, ui_w, 35), "Weekly", danger=True)
        btn_half_w = (ui_w - 10) // 2
        btn_d1 = Button((ui_x, 480, btn_half_w, 45), "Draw 1", True, image=_img_draw)
        stack_btn = Button((ui_x + btn_half_w + 10, 480, btn_half_w, 45), "Stack Top", primary=True, image=_img_stack)
        short_rest_btn = Button((0, 0, 50, 50), "Short", warning=True)
        rest_btn = Button((0, 0, 50, 50), "Long", gold=True)
        draw_of_fate_slider = IntSlider((ui_x + 35, H - 200, ui_w - 70, 34), 0, 6, game.draw_of_fate_uses)
        turn_undead_btn = Button((ui_x, H - 160, (ui_w - 10) // 2, 42), "Turn Undead", green=True, image=_img_turn_undead)
        destroy_undead_btn = Button((ui_x + (ui_w - 10) // 2 + 10, H - 160, (ui_w - 10) // 2, 42), "Destroy Undead", danger=True, image=_img_destroy_undead)
        undo_btn = Button((ui_x, H - 110, 90, 90), "", warning=True, image=_img_undo)
        divine_intervention_btn = Button((ui_x, H - 110, 90, 90), "", gold=True, image=_img_divine_intervention)
        redo_btn = Button((ui_x, H - 110, 90, 90), "", primary=True, image=_img_redo)
        quit_btn = Button((W-160, PADDING + 45, 140, 35), "Exit game", danger=True, image=_img_exit)
        menu_btn = Button((W-160, PADDING + 85, 140, 35), "Main Menu", warning=True, image=_img_main_menu)
        save_btn = Button((W-160, PADDING + 125, 140, 35), "Save", primary=True, image=_img_save)
        save_as_btn = Button((W-160, PADDING + 145, 140, 35), "Save As", primary=True, image=_img_save_as)
        load_btn = Button((W-160, PADDING + 165, 140, 35), "Load", primary=True, image=_img_load_game)
        normal_settings_btn = Button((W-160, PADDING + 185, 140, 35), "Options", primary=True, image=_img_options)
        library_btn = Button((W-160, PADDING + 205, 140, 35), "Library", gold=True, image=_img_library)
        history_btn = Button((W-240, H-810, 210, 210), "View History", primary=True, image=_img_history)
        hamburger_btn = Button((W-50, PADDING, 35, 35), "\u2630", image=_img_settings)
        rest_menu_btn = Button((W-240, H-810, 150, 150), "Rest", primary=True, image=_img_rest)
        rest_menu_open = False
        top_menu_open = False
        exit_view_btn = Button((PADDING, PADDING, 160, 45), "Exit View", primary=True)
        
        menu_box_rect = pygame.Rect(W//2 - 190, H//2 - 350, 380, 820)
        menu_lvl_dd = FantasyLevelStepper((menu_box_rect.centerx - 90, menu_box_rect.y+68, 180, 56), 1, 20, 1)
        start_game_btn = Button((menu_box_rect.centerx - 90, menu_box_rect.y+269, 180, 95), "Continue", primary=True, fantasy=True, image=_img_continue, pulse_frame=True)
        new_game_btn = Button((menu_box_rect.centerx - 90, menu_box_rect.y+160, 180, 95), "New Game", primary=True, fantasy=True, image=_img_new_game)
        menu_load_btn = Button((menu_box_rect.centerx - 90, menu_box_rect.y+378, 180, 95), "Load Game", primary=True, fantasy=True, image=_img_load_game)
        menu_library_btn = Button((menu_box_rect.centerx - 90, menu_box_rect.y+487, 180, 95), "Library", gold=True, fantasy=True, image=_img_library)
        settings_btn = Button((menu_box_rect.centerx - 90, menu_box_rect.y+596, 180, 95), "Settings", fantasy=True, image=_img_options)
        menu_quit_btn = Button((menu_box_rect.centerx - 90, menu_box_rect.y+705, 180, 95), "Exit game", danger=True, fantasy=True, image=_img_exit)
        library_box_rect = pygame.Rect(W//2 - 270, H//2 - 240, 540, 620)
        library_loadout_btn = Button((library_box_rect.centerx - 120, library_box_rect.y + 168, 240, 110), "Fortune Loadout", gold=True, fantasy=True, image=_img_fortune_loadout_menu, pulse_frame=True)
        library_glossary_btn = Button((library_box_rect.centerx - 120, library_box_rect.y + 298, 240, 110), "Glossary", cyan=True, fantasy=True, image=preloaded_ui_images.get("Glossary_Button.png"), pulse_frame=True)
        library_spell_list_btn = Button((library_box_rect.centerx - 120, library_box_rect.y + 428, 240, 110), "Spell List", pink=True, fantasy=True, image=_img_spell_list, pulse_frame=True)
        library_back_btn = Button((library_box_rect.centerx - 110, library_box_rect.bottom - 72, 220, 46), "Main Menu", warning=True, fantasy=True)
        def _library_inner_panel_rect():
            return pygame.Rect(library_box_rect.x + 56, library_box_rect.y + 132, library_box_rect.w - 112, library_box_rect.h - 170)

        def _layout_library_buttons():
            _panel = _library_inner_panel_rect()
            _main_w = min(240, _panel.w - 96)
            _main_h = 94
            _back_w = min(220, _panel.w - 110)
            _back_h = 48
            _gap = 14
            _total_h = (_main_h * 3) + _back_h + (_gap * 3)
            _start_y = _panel.y + max(18, (_panel.h - _total_h) // 2)
            _btn_x = _panel.centerx - (_main_w // 2)
            library_loadout_btn.rect = pygame.Rect(_btn_x, _start_y, _main_w, _main_h)
            library_glossary_btn.rect = pygame.Rect(_btn_x, library_loadout_btn.rect.bottom + _gap, _main_w, _main_h)
            library_spell_list_btn.rect = pygame.Rect(_btn_x, library_glossary_btn.rect.bottom + _gap, _main_w, _main_h)
            library_back_btn.rect = pygame.Rect(_panel.centerx - (_back_w // 2), library_spell_list_btn.rect.bottom + _gap, _back_w, _back_h)
        slot_menu_box_rect = pygame.Rect(W//2 - 420, H//2 - 300, 665, 640)
        slot_autosave_box_rect = pygame.Rect(slot_menu_box_rect.right + 24, slot_menu_box_rect.y, 340, slot_menu_box_rect.h)
        slot_buttons = [
            Button((0, 0, 0, 0), f"Slot {i+1}", primary=True, fantasy=True)
            for i in range(MAX_AUTOSAVE_SLOTS)
        ]
        slot_load_file_btn = Button((slot_menu_box_rect.x + 60, slot_menu_box_rect.bottom - 82, 250, 50), "Load From File", primary=True, fantasy=True)
        slot_autosave_dropdown = Dropdown((slot_autosave_box_rect.x + 38, slot_autosave_box_rect.y + 210, slot_autosave_box_rect.w - 76, 42), [(i, f"AUTO {i}") for i in range(1, MAX_AUTOSAVE_SLOTS + 1)], max_visible=7, fantasy=True)
        slot_autosave_load_btn = Button((slot_autosave_box_rect.x + 38, slot_autosave_box_rect.y + 430, slot_autosave_box_rect.w - 76, 46), "Load AUTO", primary=True, fantasy=True)
        slot_back_btn = Button((slot_menu_box_rect.right - 310, slot_menu_box_rect.bottom - 82, 250, 50), "Back", warning=True, fantasy=True)
        slot_menu_mode = "load"
        slot_menu_return_mode = "menu"
        confirm_dialog = None
        confirm_box_rect = pygame.Rect(W//2 - 250, H//2 - 115, 500, 230)
        confirm_no_btn = Button((confirm_box_rect.x + 55, confirm_box_rect.bottom - 68, 160, 42), "Decline", warning=True, fantasy=True)
        confirm_yes_btn = Button((confirm_box_rect.right - 215, confirm_box_rect.bottom - 68, 160, 42), "Confirm", danger=True, fantasy=True)
        fortune_setup_box = pygame.Rect(50, 38, W - 100, H - 76)
        fortune_loadout_buttons = [
            Button((0, 0, 0, 0), f"Loadout {i+1}", primary=True, fantasy=True)
            for i in range(len(game.fortune_loadouts))
        ]
        fortune_clear_btn = Button((fortune_setup_box.x + 40, fortune_setup_box.bottom - 72, 210, 46), "Clear Loadout", danger=True, fantasy=True)
        fortune_save_btn = Button((fortune_setup_box.x + 265, fortune_setup_box.bottom - 72, 210, 46), "Save Setup", primary=True, fantasy=True)
        fortune_save_file_btn = Button((fortune_setup_box.x + 490, fortune_setup_box.bottom - 72, 150, 46), "Save To File", primary=True, fantasy=True)
        fortune_load_file_btn = Button((fortune_setup_box.x + 650, fortune_setup_box.bottom - 72, 150, 46), "Load From File", primary=True, fantasy=True)
        fortune_back_btn = Button((fortune_setup_box.centerx + 60, fortune_setup_box.bottom - 72, 210, 46), "Back to Library", warning=True, fantasy=True)
        fortune_glossary_btn = Button((fortune_setup_box.right - 340, fortune_setup_box.bottom - 126, 140, 94), "Glossary", cyan=True, fantasy=True, image=preloaded_ui_images.get("Glossary_Button.png"), pulse_frame=True)
        fortune_spell_library_btn = Button((fortune_setup_box.right - 185, fortune_setup_box.bottom - 126, 140, 94), "Spell Library", pink=True, fantasy=True, image=preloaded_ui_images.get("Spell_Library.png"), pulse_frame=True)
        fortune_view_back_btn = Button((fortune_setup_box.x + 40, fortune_setup_box.bottom - 72, 210, 46), "Back to Loadout", warning=True, fantasy=True)
        fortune_lvl_dd = FantasyLevelStepper((fortune_setup_box.right - 270, fortune_setup_box.y + 24, 230, 46), 1, 20, game.level)
        fortune_card_buttons = []
        fortune_section_headers = []
        fortune_card_states = {}
        f_fortune_title = pygame.font.SysFont("timesnewroman", 54, bold=True)
        f_fortune_header = pygame.font.SysFont("georgia", 30, bold=True)
        f_fortune_body = pygame.font.SysFont("georgia", 22, bold=True)
        f_fortune_small = pygame.font.SysFont("georgia", 18, bold=True)
        f_fortune_subtitle = pygame.font.SysFont("georgia", 20, bold=True)
        f_fortune_subtitle.set_underline(True)

        def _layout_fortune_footer_image_buttons():
            _grid_clip = _fortune_grid_clip_rect()
            _right_col_gap = 22
            _right_col_x = _grid_clip.right + _right_col_gap
            _right_col_r = pygame.Rect(_right_col_x, _grid_clip.y, fortune_setup_box.right - 34 - _right_col_x, _grid_clip.h)
            _title_band_h = 30
            _mid_gap = 18
            _right_box_h = (_right_col_r.h - (_title_band_h * 2) - _mid_gap) // 2
            _right_top_box = pygame.Rect(_right_col_r.x, _right_col_r.y + _title_band_h, _right_col_r.w, _right_box_h)
            _right_bottom_title_r = pygame.Rect(_right_col_r.x, _right_top_box.bottom + _mid_gap, _right_col_r.w, _title_band_h)
            _right_bottom_box = pygame.Rect(_right_col_r.x, _right_bottom_title_r.bottom, _right_col_r.w, _right_box_h)
            _footer_top = max(_right_bottom_box.bottom + 12, _grid_clip.bottom + 12 + f_fortune_small.get_linesize() + 10)
            _footer_bottom = fortune_setup_box.bottom - 26
            _left_bound = max(fortune_back_btn.rect.right + 18, _right_col_r.x)
            _right_bound = fortune_setup_box.right - 35
            _available_w = max(120, _right_bound - _left_bound)
            _available_h = max(46, _footer_bottom - _footer_top)
            _gap = 14
            _aspect = 2528 / 1696
            _btn_h = _available_h
            _btn_w = int(round(_btn_h * _aspect))
            if (_btn_w * 2) + _gap > _available_w:
                _btn_w = max(80, (_available_w - _gap) // 2)
                _btn_h = max(46, int(round(_btn_w / _aspect)))
            _btn_y = _footer_bottom - _btn_h
            _spell_x = _right_bound - _btn_w
            _glossary_x = _spell_x - _gap - _btn_w
            fortune_glossary_btn.rect = pygame.Rect(_glossary_x, _btn_y, _btn_w, _btn_h)
            fortune_spell_library_btn.rect = pygame.Rect(_spell_x, _btn_y, _btn_w, _btn_h)

        def _layout_fortune_loadout_buttons():
            _cols = 5
            _rows = max(1, math.ceil(len(fortune_loadout_buttons) / _cols))
            _gap_x = 14
            _gap_y = 10
            _x = fortune_setup_box.x + 40
            _y = fortune_setup_box.y + 108
            _usable_w = fortune_setup_box.w - 80
            _btn_w = (_usable_w - ((_cols - 1) * _gap_x)) // _cols
            _btn_h = 42 if _rows > 1 else 50
            for _idx, _btn in enumerate(fortune_loadout_buttons):
                _col = _idx % _cols
                _row = _idx // _cols
                _btn.rect = pygame.Rect(_x + _col * (_btn_w + _gap_x), _y + _row * (_btn_h + _gap_y), _btn_w, _btn_h)

        def _fortune_loadout_button_bottom():
            if not fortune_loadout_buttons:
                return fortune_setup_box.y + 108
            return max(_btn.rect.bottom for _btn in fortune_loadout_buttons)

        _layout_fortune_loadout_buttons()
        settings_box_rect = pygame.Rect(W//2 - 330, H//2 - 290, 660, 680)
        settings_music_dd = Dropdown((settings_box_rect.x + 260, settings_box_rect.y + 150, 250, 42), [("on", "On"), ("off", "Off")], fantasy=True)
        settings_music_slider = IntSlider((settings_box_rect.x + 260, settings_box_rect.y + 220, 250, 36), 0, 100, 70)
        settings_sound_btn = Button((settings_box_rect.x + 70, settings_box_rect.y + 310, 220, 48), "Audio: ON", primary=True, fantasy=True)
        settings_fx_btn = Button((settings_box_rect.x + 360, settings_box_rect.y + 310, 220, 48), "FX: ON", primary=True, fantasy=True)
        settings_menu_video_btn = Button((settings_box_rect.x + 70, settings_box_rect.y + 372, 220, 48), "Menu Vids: ON", primary=True, fantasy=True)
        settings_card_video_btn = Button((settings_box_rect.x + 360, settings_box_rect.y + 372, 220, 48), "Card Videos: ON", primary=True, fantasy=True)
        settings_autosave_btn = Button((settings_box_rect.x + 70, settings_box_rect.y + 462, 220, 48), "Autosave: OFF", primary=True, fantasy=True)
        settings_autosave_minus_btn = Button((settings_box_rect.x + 360, settings_box_rect.y + 462, 56, 48), "<", warning=True, fantasy=True)
        settings_autosave_plus_btn = Button((settings_box_rect.x + 522, settings_box_rect.y + 462, 56, 48), ">", warning=True, fantasy=True)
        settings_back_btn = Button((settings_box_rect.x + 70, settings_box_rect.y + 580, 220, 48), "Main Menu", warning=True, fantasy=True)
        settings_exit_btn = Button((settings_box_rect.x + 360, settings_box_rect.y + 580, 220, 48), "Exit Game", danger=True, fantasy=True)
        settings_return_mode = "menu"
        menu_music_enabled = user_settings["menu_music_enabled"]
        menu_music_volume = user_settings["menu_music_volume"]
        audio_enabled = user_settings["audio_enabled"]
        sfx_enabled = user_settings["sfx_enabled"]
        menu_videos_enabled = user_settings["menu_videos_enabled"]
        card_videos_enabled = user_settings["card_videos_enabled"]
        autosave_enabled = user_settings["autosave_enabled"]
        autosave_interval_min = user_settings["autosave_interval_min"]
        settings_music_slider.set_value(menu_music_volume)
        settings_music_dd.selected_index = 0 if menu_music_enabled else 1
        game.audio_enabled = audio_enabled
        game.sfx_enabled = sfx_enabled
        current_menu_music_track = None
        Button.click_sound = _sfx_button_press
        try: Button.click_channel = pygame.mixer.Channel(0)
        except: Button.click_channel = None
        Button.sfx_enabled = sfx_enabled
        game.sfx_channel = Button.click_channel
        def play_sfx(sound_obj, priority=False):
            if game.audio_enabled and game.sfx_enabled and sound_obj is not None:
                try:
                    if game.sfx_channel is not None:
                        if priority:
                            game.sfx_channel.stop()
                            game.sfx_channel.play(sound_obj)
                        elif not game.sfx_channel.get_busy():
                            game.sfx_channel.play(sound_obj)
                    else:
                        sound_obj.play()
                except: pass
        def play_turnpage_sfx():
            play_sfx(_sfx_turnpage)
        
        screen_mode, running, scroll_y, preview_cid, card_fire_particles = "menu", True, 0, None, []
        preview_state = {'mode': 'normal', 'orientation': 'upright'}
        preview_locked_mode = False
        preview_scrolls = {"current": 0, "max": 0}
        prophet_remaining_draws, current_roll_anim = 0, None
        divine_roll_anim = None
        divine_roll_result = None
        previous_viewer_mode = None
        fortune_spell_list_scroll = 0
        fortune_glossary_scroll = 0
        fortune_spell_search = ""
        fortune_spell_filter = "all"
        fortune_spell_class_filter = "all"
        fortune_spell_school_filter = "all"
        fortune_spell_search_active = False
        _hover_card_token = None
        history_overlay_open, history_scroll = False, 0
        dof_token_fizzles = []
        _prev_dof_uses = game.draw_of_fate_uses
        history_sb_dragging = False
        grid_sb_dragging = False
        preview_sb_dragging = False
        spell_list_sb_dragging = False
        glossary_sb_dragging = False
        autosave_last_time = time.time()
        autosave_next_slot = 1
        fool_video_state = {
            "cap": None,
            "fps": 30.0,
            "frame_interval": 1.0 / 30.0,
            "accum": 0.0,
            "frame_surface": None,
            "post_action": None
        }
        greedy_pot_state = {
            "frames": [],
            "durations": [],
            "frame_index": 0,
            "frame_timer": 0.0,
            "active": False,
            "post_action": None,
            "background": None,
        }
        normal_zone_y_offset = -50
        normal_card_zone_y_offset = 0
        fortune_major_card_zone_y_offset = -50
        card_video_paths = {}
        if os.path.isdir(VIDEOS_DIR):
            for fname in os.listdir(VIDEOS_DIR):
                lower = fname.lower()
                if not lower.endswith(".mp4"):
                    continue
                prefix = fname.split("-", 1)[0]
                if prefix.isdigit():
                    card_video_paths[int(prefix)] = os.path.join(VIDEOS_DIR, fname)

        # Looping background video state for selection/deck/vanished screens
        def _open_loop_video(filename):
            path = os.path.join(VIDEOS_DIR, filename)
            state = {"cap": None, "fps": 30.0, "frame_interval": 1.0/30.0, "accum": 0.0, "frame_surface": None, "path": path, "attempted_open": False}
            return state

        def _ensure_loop_video_open(state):
            if state["cap"] is not None or state.get("attempted_open", False):
                return
            state["attempted_open"] = True
            try:
                import cv2
                cap = cv2.VideoCapture(state["path"])
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
        vanished_bg_video = _open_loop_video("Vanished_BG.mp4")

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
                game.major_fortune_activation_pending = False
            cf = v_face_hand if h['id'] in game.vanished else hand_tex[h['id']]
            cf = pygame.transform.rotate(cf, 180) if h['orientation']=="inverted" else cf
            game.fizzles.append(VanishFizzle(h['id'], cf, v_face_hand, (hx, hy), h['mode'], h['orientation'], game))
            game.add_history(f"{game.cards[h['id']]['name']} was Used and Vanished.", [h['id']])

        def start_fool_video(card_id, post_action):
            if not card_videos_enabled:
                post_action()
                return False
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

        def _load_greedy_pot_frames():
            if greedy_pot_state["frames"]:
                return True
            gif_path = os.path.join(IMAGES_DIR, "greedy-pot.gif")
            if not os.path.exists(gif_path):
                gif_path = os.path.join(VIDEOS_DIR, "greedy-pot.gif")
            if not os.path.exists(gif_path):
                log_event("greedy-pot.gif not found for The World popup.", is_error=True)
                return False
            try:
                from PIL import Image, ImageSequence
                with Image.open(gif_path) as gif_img:
                    for frame in ImageSequence.Iterator(gif_img):
                        rgba_frame = frame.convert("RGBA")
                        frame_surface = pygame.image.fromstring(rgba_frame.tobytes(), rgba_frame.size, "RGBA").convert_alpha()
                        greedy_pot_state["frames"].append(frame_surface)
                        greedy_pot_state["durations"].append(max(0.03, float(frame.info.get("duration", gif_img.info.get("duration", 100))) / 1000.0))
            except Exception as ex:
                log_event(f"Failed to load greedy-pot.gif: {ex}", is_error=True)
                greedy_pot_state["frames"].clear()
                greedy_pot_state["durations"].clear()
                return False
            return bool(greedy_pot_state["frames"])

        def start_greedy_pot_popup(post_action):
            nonlocal screen_mode
            if not _load_greedy_pot_frames():
                post_action()
                return False
            greedy_pot_state["frame_index"] = 0
            greedy_pot_state["frame_timer"] = 0.0
            greedy_pot_state["active"] = True
            greedy_pot_state["post_action"] = post_action
            greedy_pot_state["background"] = screen.copy()
            play_sfx(_sfx_pot_of_greed, priority=True)
            screen_mode = "greedy_pot_popup"
            return True

        def stop_greedy_pot_popup(play_action=True):
            nonlocal screen_mode
            pending = greedy_pot_state["post_action"]
            greedy_pot_state["frame_index"] = 0
            greedy_pot_state["frame_timer"] = 0.0
            greedy_pot_state["active"] = False
            greedy_pot_state["post_action"] = None
            greedy_pot_state["background"] = None
            screen_mode = "normal"
            if play_action and pending:
                pending()

        def _persist_settings():
            save_user_settings({
                "menu_music_enabled": menu_music_enabled,
                "menu_music_volume": menu_music_volume,
                "audio_enabled": audio_enabled,
                "sfx_enabled": sfx_enabled,
                "menu_videos_enabled": menu_videos_enabled,
                "card_videos_enabled": card_videos_enabled,
                "autosave_enabled": autosave_enabled,
                "autosave_interval_min": autosave_interval_min,
            })

        def _open_settings(return_mode):
            nonlocal screen_mode, settings_return_mode
            settings_return_mode = return_mode
            screen_mode = "settings"

        def apply_level_reset(new_level):
            game.level = new_level
            game.normalize_fortune_loadouts()
            game.enforce_fortune_selection()
            game.hand_limit = game.get_base_limit()
            if game.level >= 17:
                total = game.reset_for_level_change(skip_draw=True)
                return "prophet_selection", total - 1
            game.reset_for_level_change()
            return "normal", 0

        def _get_divine_intervention_threshold():
            if game.level < 10:
                return 0
            return min(20, game.level)

        def _get_divine_intervention_status_text():
            if game.divine_intervention_used_this_week:
                return "Weekly Reset"
            if game.divine_intervention_failed_until_long_rest:
                return "Long Rest"
            return None

        def _slot_path(slot_idx):
            return os.path.join(SAVE_DIR, f"slot_{slot_idx}.json")

        def _autosave_path(slot_idx):
            return os.path.join(SAVE_DIR, f"autosave_{slot_idx}.json")

        def _load_payload_from_path(path):
            if not path or not os.path.exists(path):
                return None
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as ex:
                log_event(f"Failed to read payload {path}: {ex}", True)
                return None

        def _load_slot_payload(slot_idx):
            return _load_payload_from_path(_slot_path(slot_idx))

        def _load_autosave_payload(slot_idx):
            return _load_payload_from_path(_autosave_path(slot_idx))

        def _slot_button_label(slot_idx):
            payload = _load_slot_payload(slot_idx)
            if not payload:
                return f"Slot ({slot_idx}) - Empty"
            saved_at = payload.get("saved_at", "Unknown time")
            lvl = payload.get("game", {}).get("level", 1)
            day = int(clamp(payload.get("game", {}).get("days_passed", 0) + 1, 1, 7))
            return f"Slot ({slot_idx}) - L{lvl} D{day} - {saved_at}"

        def _refresh_slot_labels():
            for i, b in enumerate(slot_buttons, start=1):
                b.text = _slot_button_label(i) if i <= MAX_SAVE_SLOTS else ""
            _auto_items = []
            for _i in range(1, MAX_AUTOSAVE_SLOTS + 1):
                _p = _load_autosave_payload(_i)
                _label = f"AUTO {_i}"
                _auto_items.append((_i, _label))
            slot_autosave_dropdown.items = _auto_items
            slot_autosave_dropdown.selected_index = clamp(slot_autosave_dropdown.selected_index, 0, max(0, len(_auto_items) - 1))

        def _layout_slot_buttons():
            _count = MAX_SAVE_SLOTS
            _cols = 1
            _bw = 430
            _bh = 86
            _gap_x = 0
            _gap_y = 24
            _start_x = slot_menu_box_rect.x + 60
            _start_y = slot_menu_box_rect.y + 182
            for _idx, _btn in enumerate(slot_buttons, start=1):
                if _idx > _count:
                    _btn.rect = pygame.Rect(0, 0, 0, 0)
                    continue
                _col = (_idx - 1) % _cols
                _row = (_idx - 1) // _cols
                _x = _start_x + _col * (_bw + _gap_x)
                _y = _start_y + _row * (_bh + _gap_y)
                _btn.rect = pygame.Rect(_x, _y, _bw, _bh)

        def _slot_has_data(slot_idx):
            return _load_slot_payload(slot_idx) is not None

        def _build_save_payload():
            return {
                "version": 1,
                "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "screen_mode": screen_mode,
                "scroll_y": scroll_y,
                "history_overlay_open": history_overlay_open,
                "history_scroll": history_scroll,
                "top_menu_open": False,
                "rest_menu_open": False,
                "game": game.to_save_payload()
            }

        def _write_slot(slot_idx):
            try:
                os.makedirs(SAVE_DIR, exist_ok=True)
                with open(_slot_path(slot_idx), "w", encoding="utf-8") as f:
                    json.dump(_build_save_payload(), f, indent=2)
                game.toast_msg = f"Saved to slot {slot_idx}"
                game.toast_timer = TOAST_DURATION
                return True
            except Exception as ex:
                log_event(f"Failed to save slot {slot_idx}: {ex}", True)
                game.toast_msg = f"Save failed (slot {slot_idx})"
                game.toast_timer = TOAST_DURATION
                return False

        def _write_autosave(slot_idx):
            try:
                os.makedirs(SAVE_DIR, exist_ok=True)
                _payload = _build_save_payload()
                _payload["save_kind"] = "autosave"
                with open(_autosave_path(slot_idx), "w", encoding="utf-8") as f:
                    json.dump(_payload, f, indent=2)
                return True
            except Exception as ex:
                log_event(f"Failed to write autosave slot {slot_idx}: {ex}", True)
                return False

        def _write_save_as_dialog():
            try:
                try:
                    pygame.event.set_grab(False)
                except Exception:
                    pass
                import tkinter as _tk
                from tkinter import filedialog as _fd
                _root = _tk.Tk()
                _root.withdraw()
                _root.attributes("-topmost", True)
                _default_name = f"tarot_save_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                _path = _fd.asksaveasfilename(
                    title="Save As",
                    defaultextension=".json",
                    initialdir=SAVE_DIR,
                    initialfile=_default_name,
                    filetypes=[("JSON Save Files", "*.json"), ("All Files", "*.*")],
                )
                try:
                    _root.destroy()
                except Exception:
                    pass
                if not _path:
                    return False
                _dir = os.path.dirname(_path)
                if _dir:
                    os.makedirs(_dir, exist_ok=True)
                with open(_path, "w", encoding="utf-8") as f:
                    json.dump(_build_save_payload(), f, indent=2)
                game.toast_msg = f"Saved to {os.path.basename(_path)}"
                game.toast_timer = TOAST_DURATION
                return True
            except Exception as ex:
                log_event(f"Failed to save via Save As dialog: {ex}", True)
                game.toast_msg = "Save As failed."
                game.toast_timer = TOAST_DURATION
                return False
            finally:
                try:
                    pygame.event.set_grab(True)
                except Exception:
                    pass

        def _read_payload_from_dialog():
            try:
                try:
                    pygame.event.set_grab(False)
                except Exception:
                    pass
                import tkinter as _tk
                from tkinter import filedialog as _fd
                _root = _tk.Tk()
                _root.withdraw()
                _root.attributes("-topmost", True)
                _path = _fd.askopenfilename(
                    title="Load Save File",
                    initialdir=SAVE_DIR,
                    filetypes=[("JSON Save Files", "*.json"), ("All Files", "*.*")],
                )
                try:
                    _root.destroy()
                except Exception:
                    pass
                return _path or None
            except Exception as ex:
                log_event(f"Failed to open load dialog: {ex}", True)
                game.toast_msg = "Load dialog failed."
                game.toast_timer = TOAST_DURATION
                return None
            finally:
                try:
                    pygame.event.set_grab(True)
                except Exception:
                    pass

        def _apply_loaded_payload(payload, loaded_label="save file"):
            nonlocal screen_mode, scroll_y, history_overlay_open, history_scroll, top_menu_open, rest_menu_open, autosave_last_time
            if not payload or "game" not in payload:
                game.toast_msg = "Selected file is not a valid save."
                game.toast_timer = TOAST_DURATION
                return False
            game.load_from_payload(payload["game"])
            game.audio_enabled = audio_enabled
            game.sfx_enabled = sfx_enabled
            game.sfx_channel = Button.click_channel
            draw_of_fate_slider.set_value(game.draw_of_fate_uses)
            lvl_change_dd.selected_index = clamp(game.level - 1, 0, 19)
            menu_lvl_dd.selected_index = clamp(game.level - 1, 0, 19)
            screen_mode = payload.get("screen_mode", "normal")
            scroll_y = payload.get("scroll_y", 0)
            history_overlay_open = bool(payload.get("history_overlay_open", False))
            history_scroll = int(payload.get("history_scroll", 0))
            top_menu_open = False
            rest_menu_open = False
            autosave_last_time = time.time()
            game.toast_msg = f"Loaded {loaded_label}"
            game.toast_timer = TOAST_DURATION
            return True

        def _read_slot(slot_idx):
            payload = _load_slot_payload(slot_idx)
            if not payload or "game" not in payload:
                game.toast_msg = f"Slot {slot_idx} is empty."
                game.toast_timer = TOAST_DURATION
                return False
            return _apply_loaded_payload(payload, f"slot {slot_idx}")

        def _start_new_game():
            nonlocal game, screen_mode, scroll_y, prophet_remaining_draws, autosave_last_time
            _prev_loadouts = copy.deepcopy(game.fortune_loadouts)
            _prev_active = game.active_fortune_loadout
            game = Game(cards_raw)
            game.level = menu_lvl_dd.get_selected()
            game.fortune_loadouts = _prev_loadouts
            game.active_fortune_loadout = _prev_active
            game.normalize_fortune_loadouts()
            lvl_change_dd.selected_index = game.level - 1
            game.hand_limit = game.get_base_limit()
            game.draw_of_fate_uses = game.get_draw_of_fate_uses_by_level()
            game.draw_of_fate_current = game.draw_of_fate_uses
            draw_of_fate_slider.set_value(game.draw_of_fate_uses)
            game.audio_enabled = audio_enabled
            game.sfx_enabled = sfx_enabled
            game.sfx_channel = Button.click_channel
            autosave_last_time = time.time()
            if game.level >= 17:
                total = game.long_rest(skip_draw=True)
                prophet_remaining_draws = total - 1
                screen_mode, scroll_y = "prophet_selection", 0
            else:
                game.long_rest()
                screen_mode = "normal"

        def _load_most_recent_save():
            _candidates = []
            for _slot_idx in range(1, MAX_SAVE_SLOTS + 1):
                _payload = _load_slot_payload(_slot_idx)
                if _payload and "game" in _payload:
                    _candidates.append((_payload.get("saved_at", ""), f"slot {_slot_idx}", _payload))
            for _slot_idx in range(1, MAX_AUTOSAVE_SLOTS + 1):
                _payload = _load_autosave_payload(_slot_idx)
                if _payload and "game" in _payload:
                    _candidates.append((_payload.get("saved_at", ""), f"autosave {_slot_idx}", _payload))
            if not _candidates:
                game.toast_msg = "No saved game found."
                game.toast_timer = TOAST_DURATION
                return False
            _candidates.sort(key=lambda _entry: _entry[0], reverse=True)
            _, _label, _payload = _candidates[0]
            return _apply_loaded_payload(_payload, _label)

        game.normalize_fortune_loadouts()
        fortune_setup_return_mode = "library"
        library_return_mode = "menu"
        fortune_scroll_y = 0
        fortune_selected_loadout_idx = game.active_fortune_loadout
        fortune_edit_loadout = copy.deepcopy(game.fortune_loadouts[fortune_selected_loadout_idx])
        fortune_name_edit_idx = None
        fortune_name_input = ""
        fortune_back_cache = dict(prebuilt_fortune_back_cache)

        FORTUNE_LOADOUT_DIR = os.path.join(DOCS_DIR, "loadouts")

        def _clamp_loadout_for_current_level(loadout):
            if not isinstance(loadout, dict):
                return {"name": f"Loadout {fortune_selected_loadout_idx + 1}", "fortune_ids": [], "major_id": None}
            _clamped = copy.deepcopy(loadout)
            _allowed_fortune = set(game.get_unlocked_fortune_ids())
            _cap = game.get_fortune_option_cap()
            _fortune_ids = []
            for _cid in _clamped.get("fortune_ids", []):
                try:
                    _cid = int(_cid)
                except Exception:
                    continue
                if _cid in _allowed_fortune and _cid not in _fortune_ids:
                    _fortune_ids.append(_cid)
                if len(_fortune_ids) >= _cap:
                    break
            _clamped["fortune_ids"] = _fortune_ids
            _major_id = _clamped.get("major_id")
            try:
                _major_id = int(_major_id) if _major_id is not None else None
            except Exception:
                _major_id = None
            _clamped["major_id"] = _major_id if (game.level >= 17 and _major_id in MAJOR_UNLOCKS_17) else None
            if not _clamped.get("name"):
                _clamped["name"] = f"Loadout {fortune_selected_loadout_idx + 1}"
            return _clamped

        def _fortune_slots_summary():
            return f"{len(fortune_edit_loadout.get('fortune_ids', []))}/{game.get_fortune_option_cap()}"

        def _fortune_loadout_slot_path(loadout_idx):
            return os.path.join(FORTUNE_LOADOUT_DIR, f"loadout_{loadout_idx + 1}.json")

        def _persist_fortune_loadout_slot(loadout_idx):
            try:
                os.makedirs(FORTUNE_LOADOUT_DIR, exist_ok=True)
                _ld = game.fortune_loadouts[loadout_idx]
                with open(_fortune_loadout_slot_path(loadout_idx), "w", encoding="utf-8") as f:
                    json.dump({
                        "version": 1,
                        "slot_index": loadout_idx,
                        "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "loadout": {
                            "name": str(_ld.get("name", f"Loadout {loadout_idx + 1}"))[:15],
                            "fortune_ids": list(_ld.get("fortune_ids", [])),
                            "major_id": _ld.get("major_id"),
                        },
                    }, f, indent=2)
                return True
            except Exception as ex:
                log_event(f"Failed to persist fortune loadout slot {loadout_idx + 1}: {ex}", True)
                return False

        def _load_persisted_fortune_loadouts():
            try:
                os.makedirs(FORTUNE_LOADOUT_DIR, exist_ok=True)
            except Exception:
                pass
            for _idx in range(len(game.fortune_loadouts)):
                _path = _fortune_loadout_slot_path(_idx)
                if not os.path.exists(_path):
                    continue
                try:
                    with open(_path, "r", encoding="utf-8") as f:
                        _payload = json.load(f)
                    _raw = _payload.get("loadout", _payload)
                    if not isinstance(_raw, dict):
                        continue
                    game.fortune_loadouts[_idx] = {
                        "name": str(_raw.get("name", f"Loadout {_idx + 1}")).strip()[:15] or f"Loadout {_idx + 1}",
                        "fortune_ids": list(_raw.get("fortune_ids", [])),
                        "major_id": _raw.get("major_id"),
                    }
                except Exception as ex:
                    log_event(f"Failed to load fortune loadout slot {_idx + 1}: {ex}", True)
            game.normalize_fortune_loadouts()

        _load_persisted_fortune_loadouts()
        fortune_edit_loadout = copy.deepcopy(game.fortune_loadouts[fortune_selected_loadout_idx])

        def _open_library(return_mode):
            nonlocal screen_mode, library_return_mode
            library_return_mode = return_mode
            screen_mode = "library"

        def _open_fortune_setup(return_mode):
            nonlocal screen_mode, fortune_setup_return_mode, fortune_selected_loadout_idx, fortune_scroll_y, fortune_edit_loadout, fortune_name_edit_idx, fortune_name_input
            fortune_setup_return_mode = return_mode
            _load_persisted_fortune_loadouts()
            fortune_selected_loadout_idx = game.active_fortune_loadout
            fortune_edit_loadout = _clamp_loadout_for_current_level(game.fortune_loadouts[fortune_selected_loadout_idx])
            fortune_name_edit_idx = None
            fortune_name_input = ""
            fortune_scroll_y = 0
            screen_mode = "fortune_setup"

        def _persist_fortune_setup():
            nonlocal fortune_edit_loadout
            game.normalize_fortune_loadouts()
            _draft = _clamp_loadout_for_current_level(fortune_edit_loadout if isinstance(fortune_edit_loadout, dict) else {})
            _fortune_ids = []
            for _cid in _draft.get("fortune_ids", []):
                try:
                    _fortune_ids.append(int(_cid))
                except Exception:
                    continue
            _major_id = _draft.get("major_id")
            try:
                _major_id = int(_major_id) if _major_id is not None else None
            except Exception:
                _major_id = None
            game.fortune_loadouts[fortune_selected_loadout_idx] = {
                "name": game.fortune_loadouts[fortune_selected_loadout_idx].get("name", f"Loadout {fortune_selected_loadout_idx + 1}"),
                "fortune_ids": _fortune_ids,
                "major_id": _major_id,
            }
            game.active_fortune_loadout = fortune_selected_loadout_idx
            game.normalize_fortune_loadouts()
            _persist_fortune_loadout_slot(fortune_selected_loadout_idx)
            fortune_edit_loadout = _clamp_loadout_for_current_level(game.fortune_loadouts[fortune_selected_loadout_idx])
            game.enforce_fortune_selection()
            game.toast_msg = f"Fortune setup saved ({_fortune_slots_summary()})."
            game.toast_timer = TOAST_DURATION

        def _fortune_loadout_has_data(loadout_idx):
            try:
                _ld = game.fortune_loadouts[loadout_idx]
            except Exception:
                return False
            return bool(_ld.get("fortune_ids") or _ld.get("major_id") is not None)

        def _build_fortune_loadout_file_payload():
            _draft = _clamp_loadout_for_current_level(fortune_edit_loadout if isinstance(fortune_edit_loadout, dict) else {})
            return {
                "version": 1,
                "kind": "fortune_loadout",
                "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "slot_index": fortune_selected_loadout_idx,
                "level": game.level,
                "loadout": {
                    "name": _draft.get("name", f"Loadout {fortune_selected_loadout_idx + 1}"),
                    "fortune_ids": list(_draft.get("fortune_ids", [])),
                    "major_id": _draft.get("major_id"),
                },
            }

        def _write_fortune_loadout_to_dialog():
            try:
                try:
                    pygame.event.set_grab(False)
                except Exception:
                    pass
                import tkinter as _tk
                from tkinter import filedialog as _fd
                _root = _tk.Tk()
                _root.withdraw()
                _root.attributes("-topmost", True)
                _default_name = f"fortune_loadout_{fortune_selected_loadout_idx + 1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                _path = _fd.asksaveasfilename(
                    title="Save Loadout To File",
                    defaultextension=".json",
                    initialdir=SAVE_DIR,
                    initialfile=_default_name,
                    filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
                )
                try:
                    _root.destroy()
                except Exception:
                    pass
                if not _path:
                    return False
                _dir = os.path.dirname(_path)
                if _dir:
                    os.makedirs(_dir, exist_ok=True)
                with open(_path, "w", encoding="utf-8") as f:
                    json.dump(_build_fortune_loadout_file_payload(), f, indent=2)
                game.toast_msg = f"Loadout file saved: {os.path.basename(_path)}"
                game.toast_timer = TOAST_DURATION
                return True
            except Exception as ex:
                log_event(f"Failed to save fortune loadout file: {ex}", True)
                game.toast_msg = "Loadout file save failed."
                game.toast_timer = TOAST_DURATION
                return False
            finally:
                try:
                    pygame.event.set_grab(True)
                except Exception:
                    pass

        def _read_fortune_loadout_from_dialog():
            try:
                try:
                    pygame.event.set_grab(False)
                except Exception:
                    pass
                import tkinter as _tk
                from tkinter import filedialog as _fd
                _root = _tk.Tk()
                _root.withdraw()
                _root.attributes("-topmost", True)
                _path = _fd.askopenfilename(
                    title="Load Loadout File",
                    initialdir=SAVE_DIR,
                    filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
                )
                try:
                    _root.destroy()
                except Exception:
                    pass
                if not _path:
                    return None
                with open(_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as ex:
                log_event(f"Failed to open fortune loadout file: {ex}", True)
                game.toast_msg = "Loadout file open failed."
                game.toast_timer = TOAST_DURATION
                return None
            finally:
                try:
                    pygame.event.set_grab(True)
                except Exception:
                    pass

        def _apply_loaded_fortune_loadout_payload(payload):
            nonlocal fortune_edit_loadout
            if not isinstance(payload, dict):
                game.toast_msg = "Invalid loadout file."
                game.toast_timer = TOAST_DURATION
                return False
            _raw_loadout = payload.get("loadout", payload)
            if not isinstance(_raw_loadout, dict):
                game.toast_msg = "Invalid loadout file."
                game.toast_timer = TOAST_DURATION
                return False
            _normalized = {
                "name": str(_raw_loadout.get("name", f"Loadout {fortune_selected_loadout_idx + 1}")).strip() or f"Loadout {fortune_selected_loadout_idx + 1}",
                "fortune_ids": list(_raw_loadout.get("fortune_ids", [])),
                "major_id": _raw_loadout.get("major_id"),
            }
            game.fortune_loadouts[fortune_selected_loadout_idx] = copy.deepcopy(_normalized)
            game.normalize_fortune_loadouts()
            fortune_edit_loadout = _clamp_loadout_for_current_level(game.fortune_loadouts[fortune_selected_loadout_idx])
            game.toast_msg = f"Loaded file into Loadout {fortune_selected_loadout_idx + 1}."
            game.toast_timer = TOAST_DURATION
            return True

        def _play_click_sfx():
            if Button.sfx_enabled and Button.click_sound is not None:
                try:
                    if Button.click_channel is not None and not Button.click_channel.get_busy():
                        Button.click_channel.play(Button.click_sound)
                    elif Button.click_channel is None:
                        Button.click_sound.play()
                except Exception:
                    pass

        def _fortune_grid_clip_rect():
            _full_w = fortune_setup_box.w - 68
            _top = _fortune_loadout_button_bottom() + 62
            _bottom = fortune_setup_box.bottom - 240
            return pygame.Rect(fortune_setup_box.x + 34, _top, _full_w // 2, max(120, _bottom - _top))

        def _fortune_grid_metrics():
            clip = _fortune_grid_clip_rect()
            card_w = 168
            card_h = 242
            gap_x = 44
            gap_y = 94
            cols = min(5, max(1, (clip.w + gap_x) // (card_w + gap_x)))
            base_x = clip.x + 8
            return clip, card_w, card_h, gap_x, gap_y, cols, base_x

        def _fortune_checkbox_rect(card_rect):
            _size = 24
            return pygame.Rect(card_rect.centerx - (_size // 2), card_rect.bottom + 18, _size, _size)

        def _fortune_max_scroll():
            _build_fortune_card_buttons()
            clip = _fortune_grid_clip_rect()
            if not fortune_card_buttons and not fortune_section_headers:
                return 0
            _bottom = clip.y
            for _hdr in fortune_section_headers:
                _bottom = max(_bottom, _hdr[1] + _hdr[2])
            for _item in fortune_card_buttons:
                _bottom = max(_bottom, _item[1].bottom, _fortune_checkbox_rect(_item[1]).bottom)
            content_h = max(0, (_bottom - clip.y) + fortune_scroll_y)
            return max(0, content_h - clip.h)

        def _get_fortune_card_state(cid, mode):
            _key = (cid, mode)
            if _key not in fortune_card_states:
                fortune_card_states[_key] = {
                    "orientation": "upright",
                    "scroll_up": 0,
                    "scroll_inv": 0,
                    "max_sc_up": 0,
                    "max_sc_inv": 0,
                }
            return fortune_card_states[_key]

        def _build_fortune_card_buttons():
            nonlocal fortune_card_buttons, fortune_section_headers
            clip, card_w, card_h, gap_x, gap_y, cols, base_x = _fortune_grid_metrics()
            content_y = 0
            header_h = 30
            _checkbox_probe = _fortune_checkbox_rect(pygame.Rect(0, 0, card_w, card_h))
            checkbox_clearance = max(0, _checkbox_probe.bottom - card_h) + 14
            section_gap = 28
            fortune_card_buttons = []
            fortune_section_headers = []
            _levels = [6, 9, 13]
            for _lvl in _levels:
                _ids = list(FORTUNE_UNLOCKS.get(_lvl, []))
                _unlocked = game.level >= _lvl
                _title = f"FORTUNE UNLOCK {_lvl}" + ("" if _unlocked else " (LOCKED)")
                _hy = clip.y + content_y - fortune_scroll_y
                fortune_section_headers.append((_title, _hy, header_h, _unlocked))
                content_y += header_h + 8
                if _unlocked and _ids:
                    for _idx, _cid in enumerate(_ids):
                        _col = _idx % cols
                        _row = _idx // cols
                        _x = base_x + _col * (card_w + gap_x)
                        _y = clip.y + content_y + _row * (card_h + gap_y) - fortune_scroll_y
                        fortune_card_buttons.append((_cid, pygame.Rect(_x, _y, card_w, card_h), "fortune"))
                    _rows = math.ceil(len(_ids) / max(1, cols))
                    content_y += _rows * card_h + max(0, _rows - 1) * gap_y + checkbox_clearance
                content_y += section_gap

            _mj_unlocked = game.level >= 17
            _mj_title = "Major Fortune Unlock: Level 17 - CHOOSE ONE!" + ("" if _mj_unlocked else " (LOCKED)")
            _mhy = clip.y + content_y - fortune_scroll_y
            fortune_section_headers.append((_mj_title, _mhy, header_h, _mj_unlocked))
            content_y += header_h + 8
            if _mj_unlocked:
                for _idx, _cid in enumerate(MAJOR_FORTUNE_IDS):
                    _col = _idx % cols
                    _row = _idx // cols
                    _x = base_x + _col * (card_w + gap_x)
                    _y = clip.y + content_y + _row * (card_h + gap_y) - fortune_scroll_y
                    fortune_card_buttons.append((_cid, pygame.Rect(_x, _y, card_w, card_h), "major"))

        def _get_selected_stamp_mode(cid):
            _active_ld = game.get_active_fortune_loadout()
            if _active_ld.get("major_id") == cid:
                return "major"
            if cid in _active_ld.get("fortune_ids", []):
                return "fortune"
            return None

        def _build_spell_grid_layout(panel_rect, spells, scroll_y):
            cols = 4
            gap_x = 10
            gap_y = 10
            pad = 10
            header_h = 28
            item_h = 44
            item_w = max(120, int((panel_rect.w - pad * 2 - gap_x * (cols - 1)) / cols))
            ordered_levels = [
                (0, "Cantrips"),
                (1, "Level 1"),
                (2, "Level 2"),
                (3, "Level 3"),
                (4, "Level 4"),
                (5, "Level 5"),
                (6, "Level 6"),
                (7, "Level 7"),
                (8, "Level 8"),
                (9, "Level 9"),
                (None, "Unknown Level"),
            ]
            _items = []
            y = panel_rect.y + pad - scroll_y
            for _lvl, _lbl in ordered_levels:
                _group = [s for s in spells if s.get("level") == _lvl]
                if not _group:
                    continue
                _items.append(("header", pygame.Rect(panel_rect.x + pad, y, panel_rect.w - pad * 2, header_h), _lbl, None))
                y += header_h + 6
                for i, _sp in enumerate(_group):
                    col = i % cols
                    row = i // cols
                    rx = panel_rect.x + pad + col * (item_w + gap_x)
                    ry = y + row * (item_h + gap_y)
                    _items.append(("spell", pygame.Rect(rx, ry, item_w, item_h), _sp.get("name", ""), _sp))
                rows = (len(_group) + cols - 1) // cols
                y += rows * (item_h + gap_y) + 12
            total_h = max(0, y - (panel_rect.y + pad - scroll_y))
            return _items, total_h

        def _fantasy_scrollbar_geometry(panel_rect, content_h, scroll_value):
            _clip = panel_rect.inflate(-14, -12)
            _track_w = 14
            _track_rect = pygame.Rect(_clip.right - _track_w, _clip.y, _track_w, _clip.h)
            _max_scroll = max(0, content_h - _clip.h)
            if _max_scroll <= 0:
                _handle_h = _track_rect.h
                _handle_y = _track_rect.y
            else:
                _handle_h = max(24, int(_track_rect.h * min(1.0, _clip.h / max(1, content_h))))
                _scroll_ratio = clamp(scroll_value / max(1, _max_scroll), 0.0, 1.0)
                _handle_y = _track_rect.y + int((_track_rect.h - _handle_h) * _scroll_ratio)
            _handle_rect = pygame.Rect(_track_rect.x, _handle_y, _track_rect.w, _handle_h)
            return _clip, _track_rect, _handle_rect, _max_scroll

        def _draw_fantasy_scrollbar(surf, track_rect, handle_rect, edge_col, fill_col):
            draw_round_rect(surf, track_rect, (26, 22, 32, 215), 8)
            pygame.draw.rect(surf, edge_col, track_rect, 1, 8)
            draw_round_rect(surf, handle_rect, fill_col, 8)
            pygame.draw.rect(surf, edge_col, handle_rect, 2, 8)
            pygame.draw.circle(surf, (248, 236, 188), (handle_rect.centerx, handle_rect.centery), 3)

        def _blit_alpha_round_rect(dest_surf, rect, color, radius):
            _panel_surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
            draw_round_rect(_panel_surf, (0, 0, rect.w, rect.h), color, radius)
            dest_surf.blit(_panel_surf, rect.topleft)

        def _spell_top_controls_layout():
            top_margin = 40
            top_gap = 12
            search_rect = pygame.Rect(fortune_setup_box.x + top_margin, fortune_setup_box.y + 118, 0, 38)
            search_w = max(260, int((fortune_setup_box.w - (top_margin * 2) - top_gap) * 0.44))
            search_rect.w = search_w
            filter_y = fortune_setup_box.y + 118
            filter_labels = {"all": "All", "cantrip": "0", "1_3": "1-3", "4_6": "4-6", "7_9": "7-9", "unknown": "?"}
            filter_order = ["all", "cantrip", "1_3", "4_6", "7_9", "unknown"]
            available_w = fortune_setup_box.right - top_margin - (search_rect.right + top_gap)
            filter_gap = 8
            filter_w = max(52, int((available_w - (filter_gap * (len(filter_order) - 1))) / len(filter_order)))
            filter_h = 38
            filter_start_x = search_rect.right + top_gap
            filter_rects = {}
            for i, k in enumerate(filter_order):
                filter_rects[k] = pygame.Rect(filter_start_x + (filter_w + filter_gap) * i, filter_y, filter_w, filter_h)
            class_rect = pygame.Rect(fortune_setup_box.x + top_margin, search_rect.bottom + 8, (fortune_setup_box.w - top_margin * 2 - 10) // 2, 34)
            school_rect = pygame.Rect(class_rect.right + 10, class_rect.y, class_rect.w, 34)
            return search_rect, filter_rects, filter_labels, class_rect, school_rect

        def _get_mode_back_surface(cid, mode, w, h):
            key = (cid, mode, w, h)
            if key in fortune_back_cache:
                return fortune_back_cache[key]
            mode_key = mode if mode in ["fortune", "major"] else "effect"
            cd = game.cards[cid]
            surf = pygame.Surface((w, h), pygame.SRCALPHA)
            draw_round_rect(surf, (0, 0, w, h), (20, 25, 40, 255), 12)
            pygame.draw.rect(surf, (180, 160, 100), (0, 0, w, h), 3, 12)
            margin = 10
            top_h = max(48, (h // 2) - 24)
            box_w = w - margin * 2
            top_box = pygame.Surface((box_w, top_h), pygame.SRCALPHA)
            rich_renderer.draw_rich_box(top_box, top_box.get_rect(), cd.get(f"{mode_key}_inverted", "..."), 0, show_scrollbar=False)
            top_box = pygame.transform.rotate(top_box, 180)
            surf.blit(top_box, (margin, 10))
            bottom_box = pygame.Rect(margin, (h // 2) + 6, box_w, top_h)
            rich_renderer.draw_rich_box(surf, bottom_box, cd.get(f"{mode_key}_upright", "..."), 0, show_scrollbar=False)
            fortune_back_cache[key] = surf
            return surf

        def _get_interactive_mode_back_surface(cid, mode, w, h, card_state):
            mode_key = mode if mode in ["fortune", "major"] else "effect"
            cd = game.cards[cid]
            surf = pygame.Surface((w, h), pygame.SRCALPHA)
            draw_round_rect(surf, (0, 0, w, h), (20, 25, 40, 255), 12)
            pygame.draw.rect(surf, (180, 160, 100), (0, 0, w, h), 3, 12)
            margin = 10
            top_h = max(48, (h // 2) - 24)
            box_w = w - margin * 2
            top_box = pygame.Surface((box_w, top_h), pygame.SRCALPHA)
            _upright = (card_state.get("orientation") == "upright")
            # Upright: top box disabled, bottom box enabled.
            # Inverted: card rotates 180 degrees, so original top box lands at bottom and becomes the enabled box.
            card_state["max_sc_inv"] = rich_renderer.draw_rich_box(
                top_box,
                top_box.get_rect(),
                cd.get(f"{mode_key}_inverted", "..."),
                card_state.get("scroll_inv", 0) if not _upright else 0,
                show_scrollbar=not _upright,
            )
            top_box = pygame.transform.rotate(top_box, 180)
            surf.blit(top_box, (margin, 10))
            bottom_box = pygame.Rect(margin, (h // 2) + 6, box_w, top_h)
            card_state["max_sc_up"] = rich_renderer.draw_rich_box(
                surf,
                bottom_box,
                cd.get(f"{mode_key}_upright", "..."),
                card_state.get("scroll_up", 0) if _upright else 0,
                show_scrollbar=_upright,
            )
            if not _upright:
                surf = pygame.transform.rotate(surf, 180)
            return surf

        def get_draw_of_fate_rect():
            dt_box_w, dt_box_h = PANEL_W - 120, 90
            dt_box_x = PADDING + (PANEL_W - dt_box_w) // 2
            dt_box_y = H - dt_box_h - 35
            return pygame.Rect(dt_box_x, dt_box_y - 405, dt_box_w, 34)

        def get_seer_dice_rect():
            dt_box_w, dt_box_h = PANEL_W - 120, 90
            dt_box_x = PADDING + (PANEL_W - dt_box_w) // 2
            dt_box_y = H - dt_box_h - 45
            return pygame.Rect(dt_box_x, dt_box_y, dt_box_w, dt_box_h)

        while running:
            dt = clock.tick(FPS)/1000.0; m_pos = pygame.mouse.get_pos(); 
            try:
                pygame.event.set_grab(True)
            except:
                pass
            game.toast_timer = max(0.0, game.toast_timer - dt)
            game.shuffle_anim_timer = max(0.0, game.shuffle_anim_timer - dt)
            if autosave_enabled and screen_mode not in ("menu", "settings", "slot_menu", "fool_video", "greedy_pot_popup"):
                _autosave_interval_s = autosave_interval_min * 60
                if (time.time() - autosave_last_time) >= _autosave_interval_s:
                    if _write_autosave(autosave_next_slot):
                        log_event(f"Autosaved to slot {autosave_next_slot}.")
                        autosave_next_slot = (autosave_next_slot % MAX_AUTOSAVE_SLOTS) + 1
                    autosave_last_time = time.time()
            draw_of_fate_slider.rect = get_draw_of_fate_rect()
            fate_r = get_draw_of_fate_rect()
            half_w = (fate_r.w - 10) // 2
            turn_undead_btn.rect = pygame.Rect(fate_r.x, fate_r.bottom + 8, half_w, half_w)
            destroy_undead_btn.rect = pygame.Rect(fate_r.x + half_w + 10, fate_r.bottom + 8, half_w, half_w)
            _seer_rect = get_seer_dice_rect()
            _divine_size = 90
            _divine_gap = 18
            _divine_y = H - _divine_size - 18
            divine_intervention_btn.rect = pygame.Rect((W - _divine_size) // 2, _divine_y, _divine_size, _divine_size)
            undo_btn.rect = pygame.Rect(divine_intervention_btn.rect.x - _divine_size - _divine_gap, _divine_y, _divine_size, _divine_size)
            redo_btn.rect = pygame.Rect(divine_intervention_btn.rect.right + _divine_gap, _divine_y, _divine_size, _divine_size)
            _major_zone_x = PANEL_W + 60 + HAND_GRID_SPACING_X
            _major_zone_y = 80 + normal_card_zone_y_offset + HAND_GRID_SPACING_Y + fortune_major_card_zone_y_offset
            _zone_btn_x = _major_zone_x + HAND_CARD_W + 50
            _zone_btn_w = max(180, min(260, W - _zone_btn_x - 80))
            _zone_btn_h = 104
            _zone_btn_gap = 18
            _ppf_y = _major_zone_y + _zone_btn_h + _zone_btn_gap
            library_btn.rect = pygame.Rect(_zone_btn_x, _ppf_y - _zone_btn_h - _zone_btn_gap, _zone_btn_w, _zone_btn_h)
            past_present_future_btn.rect = pygame.Rect(_zone_btn_x, _ppf_y, _zone_btn_w, _zone_btn_h)
            fated_card_btn.rect = pygame.Rect(_zone_btn_x, _ppf_y + _zone_btn_h + _zone_btn_gap, _zone_btn_w, _zone_btn_h)
            # Position Draw 1 / Stack Top just above the Draw of Fate title
            _div_top = fate_r.y - 105  # divider_box top
            _title_y = _div_top - 38   # Draw of Fate label y
            _d1_half = (ui_w - 10) // 2
            btn_d1.rect = pygame.Rect(ui_x, _title_y - 108, _d1_half, 90)
            stack_btn.rect = pygame.Rect(ui_x + _d1_half + 10, _title_y - 108, _d1_half, 90)

            if card_videos_enabled and screen_mode == "fool_video" and fool_video_state["cap"] is not None:
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
            if screen_mode == "greedy_pot_popup" and greedy_pot_state["active"] and greedy_pot_state["frames"]:
                greedy_pot_state["frame_timer"] += dt
                while greedy_pot_state["frame_timer"] >= greedy_pot_state["durations"][greedy_pot_state["frame_index"]]:
                    greedy_pot_state["frame_timer"] -= greedy_pot_state["durations"][greedy_pot_state["frame_index"]]
                    greedy_pot_state["frame_index"] += 1
                    if greedy_pot_state["frame_index"] >= len(greedy_pot_state["frames"]):
                        stop_greedy_pot_popup(play_action=True)
                        break
            
            # Update looping background videos only when their screen is active
            _active_loop_videos = []
            if screen_mode in ("prophet_selection", "ppf_selection"):
                _active_loop_videos = [prophet_bg_video]
            elif screen_mode == "deck":
                _active_loop_videos = [deck_bg_video]
            elif screen_mode == "vanish_view":
                _active_loop_videos = [vanished_bg_video]
            for _bgv in _active_loop_videos:
                if menu_videos_enabled:
                    _ensure_loop_video_open(_bgv)
                if menu_videos_enabled and _bgv["cap"] is not None:
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
            if divine_roll_anim:
                divine_roll_anim.update(dt)
                if divine_roll_anim.done:
                    if divine_roll_result is not None:
                        _di_roll, _di_threshold, _di_result = divine_roll_result
                        game.add_history(f"Divine Intervention: rolled {_di_roll} vs <= {_di_threshold}. {_di_result}.")
                        divine_roll_result = None
                    divine_roll_anim = None

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
            divine_intervention_btn.disabled = (
                game.level < 10 or
                game.divine_intervention_used_this_week or
                game.divine_intervention_failed_until_long_rest
            )
            past_present_future_btn.text = f"Past, Present and Future ({game.ppf_charges}/3)"
            past_present_future_btn.disabled = (game.ppf_charges <= 0 or game.level < 6 or len(game.fortune_zone) >= 1 or len(game.get_allowed_fortune_ids()) < 1)
            fated_card_btn.disabled = (game.major_fortune_used_this_week or len(game.major_zone) > 0 or game.level < 17 or game.get_allowed_major_id() is None)
            
            is_animating = (
                current_roll_anim is not None or
                divine_roll_anim is not None or
                game.is_drawing or
                len(game.fizzles) > 0 or
                len(dof_token_fizzles) > 0 or
                game.shuffle_anim_timer > 0 or
                screen_mode in ("fool_video", "greedy_pot_popup")
            )
            undo_btn.disabled = is_animating or (len(game.history) == 0)
            redo_btn.disabled = is_animating or (len(game.redo_history) == 0)
            
            for e in pygame.event.get():
                if current_roll_anim or divine_roll_anim: continue 
                if e.type == pygame.QUIT:
                    running = False
                if confirm_dialog is not None:
                    if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                        confirm_dialog = None
                        continue
                    if confirm_yes_btn.handle_event(e):
                        _action = confirm_dialog.get("on_confirm")
                        confirm_dialog = None
                        if callable(_action):
                            _action()
                        continue
                    if confirm_no_btn.handle_event(e):
                        confirm_dialog = None
                        continue
                    continue
                if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                    if screen_mode == "fool_video":
                        stop_card_video(play_action=True)
                        screen_mode = "normal"
                        continue
                    if screen_mode == "greedy_pot_popup":
                        continue
                    if screen_mode == "preview_view":
                        preview_sb_dragging = False
                        preview_locked_mode = False
                        if previous_viewer_mode:
                            screen_mode = previous_viewer_mode
                            previous_viewer_mode = None
                        else:
                            screen_mode = "normal"
                        continue
                    if screen_mode == "settings":
                        screen_mode = settings_return_mode
                        continue
                    if screen_mode == "slot_menu":
                        screen_mode = slot_menu_return_mode
                        continue
                    if screen_mode in ("fortune_spell_list_view", "fortune_glossary_view"):
                        screen_mode = "library"
                        continue
                    if screen_mode == "library":
                        screen_mode = "normal" if library_return_mode == "normal" else "menu"
                        continue
                    if screen_mode == "fortune_setup":
                        game.normalize_fortune_loadouts()
                        screen_mode = "library"
                        continue
                    if screen_mode in ("deck", "vanish_view"):
                        rest_menu_open = False
                        top_menu_open = False
                        history_overlay_open = False
                        screen_mode = "normal"
                        continue
                    # Only allow Escape to open menu if NOT in Normal View
                    if screen_mode not in ("normal", "fool_video", "greedy_pot_popup"):
                        rest_menu_open = False
                        top_menu_open = False
                        history_overlay_open = False
                        screen_mode = "menu"
                        continue
                    # In Normal View, Escape does nothing
                if screen_mode in ("fool_video", "greedy_pot_popup"):
                    continue
                
                if screen_mode == "menu":
                    if menu_lvl_dd.handle_event(e):
                        selected_level = menu_lvl_dd.get_selected()
                        game.level = selected_level
                        game.normalize_fortune_loadouts()
                        game.enforce_fortune_selection()
                        game.draw_of_fate_uses = game.get_draw_of_fate_uses_by_level()
                        game.draw_of_fate_current = game.draw_of_fate_uses
                        draw_of_fate_slider.set_value(game.draw_of_fate_uses)
                        lvl_change_dd.selected_index = game.level - 1
                    if start_game_btn.handle_event(e):
                        _load_most_recent_save()
                    if new_game_btn.handle_event(e):
                        _start_new_game()
                    if menu_load_btn.handle_event(e):
                        slot_menu_mode = "load"
                        slot_menu_return_mode = "menu"
                        _refresh_slot_labels()
                        _layout_slot_buttons()
                        screen_mode = "slot_menu"
                    if settings_btn.handle_event(e):
                        _open_settings("menu")
                    if menu_library_btn.handle_event(e):
                        _open_library("menu")
                    if menu_quit_btn.handle_event(e): running = False

                elif screen_mode == "library":
                    _layout_library_buttons()
                    if library_loadout_btn.handle_event(e):
                        _open_fortune_setup("library")
                    if library_glossary_btn.handle_event(e):
                        fortune_glossary_scroll = 0
                        screen_mode = "fortune_glossary_view"
                    if library_spell_list_btn.handle_event(e):
                        fortune_spell_list_scroll = 0
                        fortune_spell_search = ""
                        fortune_spell_filter = "all"
                        fortune_spell_class_filter = "all"
                        fortune_spell_school_filter = "all"
                        fortune_spell_search_active = False
                        screen_mode = "fortune_spell_list_view"
                    if library_back_btn.handle_event(e):
                        screen_mode = "normal" if library_return_mode == "normal" else "menu"
                
                elif screen_mode == "slot_menu":
                    if slot_menu_mode == "load":
                        slot_autosave_dropdown.handle_event(e)
                    for _i, _btn in enumerate(slot_buttons, start=1):
                        if _btn.rect.w <= 0:
                            continue
                        if _btn.handle_event(e):
                            if slot_menu_mode == "save":
                                def _do_slot_save(_slot_idx=_i):
                                    _write_slot(_slot_idx)
                                    _refresh_slot_labels()
                                if _slot_has_data(_i):
                                    confirm_dialog = {
                                        "title": "Overwrite Save Slot?",
                                        "message": f"Slot {_i} already has save data. This will overwrite it.",
                                        "on_confirm": _do_slot_save,
                                    }
                                else:
                                    _do_slot_save()
                            else:
                                if _read_slot(_i):
                                    pass
                            break
                    if slot_menu_mode == "load" and slot_load_file_btn.handle_event(e):
                        _path = _read_payload_from_dialog()
                        if _path:
                            _payload = _load_payload_from_path(_path)
                            if _apply_loaded_payload(_payload, os.path.basename(_path)):
                                screen_mode = "normal"
                    if slot_menu_mode == "load" and slot_autosave_load_btn.handle_event(e):
                        _auto_idx = slot_autosave_dropdown.get_selected()
                        _payload = _load_autosave_payload(_auto_idx)
                        if _payload:
                            if _apply_loaded_payload(_payload, f"AUTO {_auto_idx}"):
                                screen_mode = "normal"
                        else:
                            game.toast_msg = f"AUTO {_auto_idx} is empty."
                            game.toast_timer = TOAST_DURATION
                    if slot_back_btn.handle_event(e):
                        screen_mode = slot_menu_return_mode

                elif screen_mode == "settings":
                    if settings_music_dd.handle_event(e):
                        menu_music_enabled = (settings_music_dd.get_selected() == "on")
                        _persist_settings()
                    if settings_music_slider.handle_event(e):
                        menu_music_volume = settings_music_slider.value
                        _persist_settings()
                    if settings_sound_btn.handle_event(e):
                        audio_enabled = not audio_enabled
                        game.audio_enabled = audio_enabled
                        if not audio_enabled:
                            try:
                                pygame.mixer.stop()
                                pygame.mixer.music.stop()
                            except Exception:
                                pass
                            current_menu_music_track = None
                        _persist_settings()
                    if settings_fx_btn.handle_event(e):
                        sfx_enabled = not sfx_enabled
                        game.sfx_enabled = sfx_enabled
                        Button.sfx_enabled = sfx_enabled
                        _persist_settings()
                    if settings_menu_video_btn.handle_event(e):
                        menu_videos_enabled = not menu_videos_enabled
                        _persist_settings()
                    if settings_card_video_btn.handle_event(e):
                        card_videos_enabled = not card_videos_enabled
                        if not card_videos_enabled and screen_mode == "fool_video" and fool_video_state["cap"] is not None:
                            stop_card_video(play_action=True)
                        _persist_settings()
                    if settings_autosave_btn.handle_event(e):
                        autosave_enabled = not autosave_enabled
                        autosave_last_time = time.time()
                        _persist_settings()
                    if settings_autosave_minus_btn.handle_event(e):
                        autosave_interval_min = max(5, autosave_interval_min - 5)
                        autosave_last_time = time.time()
                        _persist_settings()
                    if settings_autosave_plus_btn.handle_event(e):
                        autosave_interval_min = min(30, autosave_interval_min + 5)
                        autosave_last_time = time.time()
                        _persist_settings()
                    if settings_back_btn.handle_event(e):
                        screen_mode = settings_return_mode
                    if settings_exit_btn.handle_event(e):
                        running = False

                elif screen_mode == "fortune_setup":
                    _layout_fortune_footer_image_buttons()
                    if fortune_name_edit_idx is not None and e.type == pygame.KEYDOWN:
                        if e.key == pygame.K_RETURN:
                            _new_name = fortune_name_input.strip()[:15] or f"Loadout {fortune_name_edit_idx + 1}"
                            game.fortune_loadouts[fortune_name_edit_idx]["name"] = _new_name
                            if fortune_name_edit_idx == fortune_selected_loadout_idx:
                                fortune_edit_loadout["name"] = _new_name
                            game.normalize_fortune_loadouts()
                            _persist_fortune_loadout_slot(fortune_name_edit_idx)
                            fortune_name_edit_idx = None
                            fortune_name_input = ""
                            continue
                        if e.key == pygame.K_ESCAPE:
                            fortune_name_edit_idx = None
                            fortune_name_input = ""
                            continue
                        if e.key == pygame.K_BACKSPACE:
                            fortune_name_input = fortune_name_input[:-1]
                            continue
                        if e.unicode and e.unicode.isprintable() and len(fortune_name_input) < 15:
                            fortune_name_input += e.unicode
                            continue
                    fortune_lvl_dd.set_value(game.level)
                    if fortune_lvl_dd.handle_event(e):
                        game.level = fortune_lvl_dd.get_selected()
                        game.draw_of_fate_uses = game.get_draw_of_fate_uses_by_level()
                        game.draw_of_fate_current = game.draw_of_fate_uses
                        draw_of_fate_slider.set_value(game.draw_of_fate_uses)
                        menu_lvl_dd.set_value(game.level)
                        lvl_change_dd.set_value(game.level)
                        game.normalize_fortune_loadouts()
                        fortune_edit_loadout = _clamp_loadout_for_current_level(game.fortune_loadouts[fortune_selected_loadout_idx])
                        game.enforce_fortune_selection()
                    if e.type == pygame.MOUSEWHEEL:
                        _consumed_card_scroll = False
                        _grid_clip = _fortune_grid_clip_rect()
                        if _grid_clip.collidepoint(m_pos):
                            _build_fortune_card_buttons()
                            for _cid, _rect, _mode in fortune_card_buttons:
                                if _rect.collidepoint(m_pos):
                                    _card_state = _get_fortune_card_state(_cid, _mode)
                                    _top_half = m_pos[1] < _rect.y + (_rect.h // 2)
                                    if _card_state.get("orientation") == "inverted" and _top_half:
                                        pass
                                    elif _top_half:
                                        _card_state["scroll_inv"] = clamp(_card_state.get("scroll_inv", 0) - e.y * 25, 0, _card_state.get("max_sc_inv", 0))
                                    else:
                                        _scroll_key = "scroll_inv" if _card_state.get("orientation") == "inverted" else "scroll_up"
                                        _max_key = "max_sc_inv" if _card_state.get("orientation") == "inverted" else "max_sc_up"
                                        _card_state[_scroll_key] = clamp(_card_state.get(_scroll_key, 0) - e.y * 25, 0, _card_state.get(_max_key, 0))
                                    _consumed_card_scroll = True
                                    break
                            if not _consumed_card_scroll:
                                fortune_scroll_y = int(clamp(fortune_scroll_y - e.y * 50, 0, _fortune_max_scroll()))
                    for _idx, _btn in enumerate(fortune_loadout_buttons):
                        _btn.warning = (_idx == fortune_selected_loadout_idx)
                        _btn.primary = (_idx != fortune_selected_loadout_idx)
                        if _btn.handle_event(e):
                            if fortune_selected_loadout_idx == _idx:
                                fortune_name_edit_idx = _idx
                                fortune_name_input = str(game.fortune_loadouts[_idx].get("name", f"Loadout {_idx + 1}"))[:15]
                            else:
                                fortune_name_edit_idx = None
                                fortune_name_input = ""
                                fortune_selected_loadout_idx = _idx
                                fortune_edit_loadout = _clamp_loadout_for_current_level(game.fortune_loadouts[_idx])
                    active_ld = fortune_edit_loadout
                    _build_fortune_card_buttons()
                    _grid_clip = _fortune_grid_clip_rect()
                    for _cid, _rect, _mode in fortune_card_buttons:
                        if _rect.bottom < _grid_clip.y or _rect.top > _grid_clip.bottom:
                            continue
                        _cb = _fortune_checkbox_rect(_rect)
                        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and _grid_clip.collidepoint(e.pos) and _cb.collidepoint(e.pos):
                            _play_click_sfx()
                            if _mode == "major":
                                active_ld["major_id"] = None if active_ld.get("major_id") == _cid else _cid
                            else:
                                pool = active_ld.setdefault("fortune_ids", [])
                                if _cid in pool:
                                    pool.remove(_cid)
                                elif len(pool) < game.get_fortune_option_cap():
                                    pool.append(_cid)
                                else:
                                    game.toast_msg = f"This loadout is full. At your current level you can save up to {game.get_fortune_option_cap()} Fortune cards."
                                    game.toast_timer = TOAST_DURATION
                        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and _grid_clip.collidepoint(e.pos) and _rect.collidepoint(e.pos):
                            _play_click_sfx()
                            previous_viewer_mode = "fortune_setup"
                            preview_cid = _cid
                            preview_state = {'mode': _mode, 'orientation': 'upright'}
                            preview_scrolls = {"current": 0, "max": 0}
                            preview_locked_mode = True
                            screen_mode = "preview_view"
                            break
                        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 2 and _grid_clip.collidepoint(e.pos) and _rect.collidepoint(e.pos):
                            _card_state = _get_fortune_card_state(_cid, _mode)
                            _card_state["orientation"] = "inverted" if _card_state.get("orientation") == "upright" else "upright"
                            _card_state["scroll_up"] = 0
                            _card_state["scroll_inv"] = 0
                            play_turnpage_sfx()
                            break
                    if fortune_clear_btn.handle_event(e):
                        active_ld["fortune_ids"] = []
                        active_ld["major_id"] = None
                    if fortune_save_btn.handle_event(e):
                        _active_idx = fortune_selected_loadout_idx
                        def _do_fortune_save():
                            _persist_fortune_setup()
                        if _fortune_loadout_has_data(_active_idx):
                            confirm_dialog = {
                                "title": "Overwrite Loadout?",
                                "message": f"Loadout {_active_idx + 1} already has saved cards. This will overwrite that setup.",
                                "on_confirm": _do_fortune_save,
                            }
                        else:
                            _do_fortune_save()
                    if fortune_save_file_btn.handle_event(e):
                        _write_fortune_loadout_to_dialog()
                    if fortune_load_file_btn.handle_event(e):
                        _payload = _read_fortune_loadout_from_dialog()
                        if _payload is not None:
                            _apply_loaded_fortune_loadout_payload(_payload)
                    if fortune_back_btn.handle_event(e):
                        fortune_name_edit_idx = None
                        fortune_name_input = ""
                        game.normalize_fortune_loadouts()
                        screen_mode = "library"

                elif screen_mode == "fortune_spell_list_view":
                    _search_rect, _filter_rects, _filter_labels, _class_rect, _school_rect = _spell_top_controls_layout()
                    _spell_panel = pygame.Rect(fortune_setup_box.x + 40, _class_rect.bottom + 8, fortune_setup_box.w - 80, fortune_setup_box.h - ((_class_rect.bottom + 8) - fortune_setup_box.y) - 110)
                    _query = fortune_spell_search.strip().lower()
                    _filtered_spells = []
                    for _sp in fortune_spell_entries:
                        _name = str(_sp.get("name", ""))
                        _name_l = _name.lower()
                        if _query and _query not in _name_l:
                            continue
                        _lvl = _sp.get("level")
                        if fortune_spell_filter == "cantrip" and _lvl != 0:
                            continue
                        if fortune_spell_filter == "1_3" and not (isinstance(_lvl, int) and 1 <= _lvl <= 3):
                            continue
                        if fortune_spell_filter == "4_6" and not (isinstance(_lvl, int) and 4 <= _lvl <= 6):
                            continue
                        if fortune_spell_filter == "7_9" and not (isinstance(_lvl, int) and 7 <= _lvl <= 9):
                            continue
                        if fortune_spell_filter == "unknown" and _lvl is not None:
                            continue
                        if fortune_spell_class_filter != "all" and fortune_spell_class_filter not in (_sp.get("classes") or []):
                            continue
                        if fortune_spell_school_filter != "all" and fortune_spell_school_filter != str(_sp.get("school", "Unknown")):
                            continue
                        _filtered_spells.append(_sp)
                    _layout_items, _layout_total_h = _build_spell_grid_layout(_spell_panel, _filtered_spells, fortune_spell_list_scroll)
                    _spell_clip, _spell_track_rect, _spell_handle_rect, _spell_max_scroll = _fantasy_scrollbar_geometry(_spell_panel, _layout_total_h, fortune_spell_list_scroll)
                    fortune_spell_list_scroll = int(clamp(fortune_spell_list_scroll, 0, _spell_max_scroll))
                    if e.type == pygame.MOUSEBUTTONUP and e.button == 1:
                        spell_list_sb_dragging = False
                    if e.type == pygame.MOUSEMOTION and spell_list_sb_dragging and _spell_max_scroll > 0:
                        _rel = clamp(e.pos[1] - _spell_track_rect.y - (_spell_handle_rect.h // 2), 0, _spell_track_rect.h - _spell_handle_rect.h)
                        fortune_spell_list_scroll = int(_rel / max(1, _spell_track_rect.h - _spell_handle_rect.h) * _spell_max_scroll)
                    if e.type == pygame.MOUSEWHEEL and _spell_panel.collidepoint(m_pos):
                        fortune_spell_list_scroll = int(clamp(fortune_spell_list_scroll - e.y * 40, 0, _spell_max_scroll))
                    if e.type == pygame.KEYDOWN and fortune_spell_search_active:
                        if e.key == pygame.K_BACKSPACE:
                            fortune_spell_search = fortune_spell_search[:-1]
                            fortune_spell_list_scroll = 0
                        elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_TAB):
                            pass
                        elif e.unicode and e.unicode.isprintable():
                            if len(fortune_spell_search) < 48:
                                fortune_spell_search += e.unicode
                                fortune_spell_list_scroll = 0
                    if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                        if _spell_max_scroll > 0 and _spell_track_rect.collidepoint(e.pos):
                            spell_list_sb_dragging = True
                            _rel = clamp(e.pos[1] - _spell_track_rect.y - (_spell_handle_rect.h // 2), 0, _spell_track_rect.h - _spell_handle_rect.h)
                            fortune_spell_list_scroll = int(_rel / max(1, _spell_track_rect.h - _spell_handle_rect.h) * _spell_max_scroll)
                            continue
                        if _search_rect.collidepoint(e.pos):
                            fortune_spell_search_active = True
                        else:
                            fortune_spell_search_active = False
                            for _fm, _fr in _filter_rects.items():
                                if _fr.collidepoint(e.pos):
                                    fortune_spell_filter = _fm
                                    fortune_spell_list_scroll = 0
                                    break
                            if _class_rect.collidepoint(e.pos):
                                _cur_i = fortune_spell_class_options.index(fortune_spell_class_filter) if fortune_spell_class_filter in fortune_spell_class_options else 0
                                _cur_i = (_cur_i + 1) % max(1, len(fortune_spell_class_options))
                                fortune_spell_class_filter = fortune_spell_class_options[_cur_i]
                                fortune_spell_list_scroll = 0
                            elif _school_rect.collidepoint(e.pos):
                                _cur_i = fortune_spell_school_options.index(fortune_spell_school_filter) if fortune_spell_school_filter in fortune_spell_school_options else 0
                                _cur_i = (_cur_i + 1) % max(1, len(fortune_spell_school_options))
                                fortune_spell_school_filter = fortune_spell_school_options[_cur_i]
                                fortune_spell_list_scroll = 0
                        if _spell_panel.collidepoint(e.pos):
                            for _kind, _rect, _text, _spell_obj in _layout_items:
                                if _kind != "spell":
                                    continue
                                if _rect.collidepoint(e.pos):
                                    _url = _spell_obj.get("url", "")
                                    if _url:
                                        webbrowser.open(_url)
                                    break
                    if fortune_view_back_btn.handle_event(e):
                        screen_mode = "library"
                        fortune_spell_search_active = False

                elif screen_mode == "fortune_glossary_view":
                    _glossary_panel = pygame.Rect(fortune_setup_box.x + 40, fortune_setup_box.y + 120, fortune_setup_box.w - 80, fortune_setup_box.h - 230)
                    _glossary_cols = 4
                    _row_h = 44
                    _row_gap = 10
                    _visible_h = _glossary_panel.h - 20
                    _glossary_rows = max(1, math.ceil(len(fortune_glossary_terms) / _glossary_cols))
                    _content_h = (_glossary_rows * _row_h) + max(0, (_glossary_rows - 1) * _row_gap)
                    _glossary_clip, _glossary_track_rect, _glossary_handle_rect, _glossary_max_scroll = _fantasy_scrollbar_geometry(_glossary_panel, _content_h, fortune_glossary_scroll)
                    if e.type == pygame.MOUSEBUTTONUP and e.button == 1:
                        glossary_sb_dragging = False
                    if e.type == pygame.MOUSEMOTION and glossary_sb_dragging and _glossary_max_scroll > 0:
                        _rel = clamp(e.pos[1] - _glossary_track_rect.y - (_glossary_handle_rect.h // 2), 0, _glossary_track_rect.h - _glossary_handle_rect.h)
                        fortune_glossary_scroll = int(_rel / max(1, _glossary_track_rect.h - _glossary_handle_rect.h) * _glossary_max_scroll)
                    if e.type == pygame.MOUSEWHEEL and _glossary_panel.collidepoint(m_pos):
                        fortune_glossary_scroll = int(clamp(fortune_glossary_scroll - e.y * 48, 0, _glossary_max_scroll))
                    if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and _glossary_max_scroll > 0 and _glossary_track_rect.collidepoint(e.pos):
                        glossary_sb_dragging = True
                        _rel = clamp(e.pos[1] - _glossary_track_rect.y - (_glossary_handle_rect.h // 2), 0, _glossary_track_rect.h - _glossary_handle_rect.h)
                        fortune_glossary_scroll = int(_rel / max(1, _glossary_track_rect.h - _glossary_handle_rect.h) * _glossary_max_scroll)
                        continue
                    if fortune_view_back_btn.handle_event(e):
                        screen_mode = "library"
                
                elif screen_mode == "preview_view":
                    if exit_view_btn.handle_event(e): 
                        preview_sb_dragging = False
                        if previous_viewer_mode:
                            screen_mode = previous_viewer_mode
                            previous_viewer_mode = None
                        else:
                            screen_mode = "normal"
                        preview_locked_mode = False
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
                        elif e.button == 2: preview_state['orientation'] = "inverted" if preview_state['orientation'] == "upright" else "upright"; play_turnpage_sfx()
                        elif e.button == 3:
                            if preview_locked_mode:
                                continue
                            if preview_state['mode'] != "normal":
                                preview_state['mode'] = "normal"
                            else:
                                if preview_cid in MAJOR_FORTUNE_IDS:
                                    if game.can_promote_card(preview_cid, to_major=True):
                                        preview_state['mode'] = "major"
                                    else:
                                        if game.major_fortune_used_this_week:
                                            game.toast_msg, game.toast_timer = "Major Fortune is on weekly cooldown. You must wait for the weekly reset, which happens after 7 long rests."
                                        else:
                                            game.toast_msg, game.toast_timer = "This card cannot enter Major mode right now. Make sure it is the Major card selected in your active Fortune loadout."
                                else:
                                    if game.can_promote_card(preview_cid, to_major=False):
                                        preview_state['mode'] = "fortune"
                                    else:
                                        game.toast_msg, game.toast_timer = "This card cannot enter Fortune mode right now. Make sure it is selected in your active Fortune loadout."
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
                    if e.type == pygame.MOUSEMOTION:
                        _new_hover = None
                        for _zone_name, _zone, _sy, _sx in (
                            [( "hand", h, 80, PANEL_W+60) for h in game.hand] +
                            [( "fortune", f, 80+HAND_GRID_SPACING_Y, PANEL_W+60) for f in game.fortune_zone] +
                            [( "major", m, 80+HAND_GRID_SPACING_Y, PANEL_W+60+HAND_GRID_SPACING_X) for m in game.major_zone]
                        ):
                            if _zone.get('is_vanishing') or _zone.get('tapped'):
                                continue
                            _list_ref = game.hand if _zone_name == "hand" else (game.fortune_zone if _zone_name == "fortune" else game.major_zone)
                            try:
                                _idx = _list_ref.index(_zone)
                            except ValueError:
                                continue
                            _hx, _hy = _sx + (_idx % 4) * HAND_GRID_SPACING_X, _sy + (_idx // 4) * HAND_GRID_SPACING_Y
                            if pygame.Rect(_hx, _hy, HAND_CARD_W, HAND_CARD_H).collidepoint(e.pos):
                                _new_hover = (_zone_name, _zone.get('id'), _idx)
                                break
                        if _new_hover is not None and _new_hover != _hover_card_token:
                            play_turnpage_sfx()
                        _hover_card_token = _new_hover
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

                        def _history_thumb_hit(_pos):
                            _clip_rect_ev = pygame.Rect(_ho_rect.x + 10, _ho_rect.y + 50, _clip_w_ev, _clip_h_ev)
                            if not _clip_rect_ev.collidepoint(_pos):
                                return None
                            def _wrap_ev(_font, _text, _max_w):
                                if _max_w <= 0:
                                    return [_text]
                                _words = _text.split(' ')
                                _lines, _cur = [], ''
                                for _w in _words:
                                    _test = (_cur + ' ' + _w).strip()
                                    if _font.size(_test)[0] <= _max_w:
                                        _cur = _test
                                    else:
                                        if _cur:
                                            _lines.append(_cur)
                                        _cur = _w
                                if _cur:
                                    _lines.append(_cur)
                                return _lines if _lines else ['']
                            _base_row_h = 38
                            _thumb_row_h = max(_base_row_h, THUMB_H + 8)
                            _line_h = f_tiny.get_linesize()
                            _local_x = _pos[0] - _clip_rect_ev.x
                            _local_y = _pos[1] - _clip_rect_ev.y
                            _y_cursor = 0
                            for _entry in reversed(game.history_log):
                                if isinstance(_entry, dict):
                                    _txt = _entry["text"]
                                    _cids = _entry.get("card_ids", [])
                                else:
                                    _txt = _entry
                                    _cids = []
                                _has_thumbs = any(_ci in thumb_tex for _ci in _cids)
                                _thumb_total_w = sum((THUMB_W + 4) for _ci in _cids if _ci in thumb_tex)
                                _text_max_w = _clip_rect_ev.w - 20 - _thumb_total_w
                                _lines = _wrap_ev(f_tiny, _txt, _text_max_w)
                                _text_block_h = len(_lines) * _line_h
                                _row_h = max(_thumb_row_h if _has_thumbs else _base_row_h, _text_block_h + 8)
                                _y_pos = _y_cursor - history_scroll
                                _y_cursor += _row_h
                                if not (-_row_h < _y_pos < _clip_rect_ev.h):
                                    continue
                                _tx = 20
                                for _ci in _cids:
                                    if _ci in thumb_tex:
                                        _thumb_rect = pygame.Rect(_tx, _y_pos + (_row_h - THUMB_H) // 2, THUMB_W, THUMB_H)
                                        if _thumb_rect.collidepoint((_local_x, _local_y)):
                                            return _ci
                                        _tx += THUMB_W + 4
                            return None

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
                                # Click on scrollbar track â€” jump to position and start drag
                                history_sb_dragging = True
                                _tch = _ho_total_content_h()
                                _max_scroll = max(0, _tch - _clip_h_ev)
                                if _max_scroll > 0 and _track_h_ev > _sb_w_ev:
                                    _rel_y = clamp(e.pos[1] - _track_y_ev - _sb_w_ev // 2, 0, _track_h_ev - _sb_w_ev)
                                    history_scroll = int(_rel_y / (_track_h_ev - _sb_w_ev) * _max_scroll)
                                continue
                            _thumb_cid = _history_thumb_hit(e.pos)
                            if _thumb_cid is not None:
                                previous_viewer_mode = "normal"
                                preview_cid = _thumb_cid
                                preview_scrolls = {"current":0,"max":0}
                                preview_locked_mode = False
                                history_overlay_open = False
                                screen_mode = "preview_view"
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
                    if library_btn.handle_event(e):
                        _open_library("normal")
                    if game.level >= 6 and past_present_future_btn.handle_event(e) and not past_present_future_btn.disabled: screen_mode, scroll_y = "ppf_selection", 0
                    if game.level >= 2 and rest_menu_open and short_rest_btn.handle_event(e): game.short_rest(); rest_menu_open = False
                    if game.level >= 2 and turn_undead_btn.handle_event(e): game.save_state(); game.draw_of_fate_current = max(0, game.draw_of_fate_current - 1); game.add_history("Used Turn Undead.")
                    if game.level >= 2 and destroy_undead_btn.handle_event(e): game.save_state(); game.draw_of_fate_current = max(0, game.draw_of_fate_current - 2); game.add_history("Used Destroy Undead.")
                    if game.level >= 10 and divine_intervention_btn.handle_event(e) and not divine_intervention_btn.disabled:
                        game.save_state()
                        _di_threshold = _get_divine_intervention_threshold()
                        _di_roll = random.randint(1, 100)
                        _di_success = _di_roll <= _di_threshold
                        if _di_success:
                            game.divine_intervention_used_this_week = True
                            game.divine_intervention_failed_until_long_rest = False
                            _di_result = "Succeeded. Disabled until weekly reset."
                        else:
                            game.divine_intervention_failed_until_long_rest = True
                            _di_result = "Failed. Disabled until long rest."
                        divine_roll_anim = D100RollAnimation(_di_roll, W, H)
                        divine_roll_result = (_di_roll, _di_threshold, _di_result)
                        continue
                    if game.level >= 17 and rest_menu_open and reset_major_btn.handle_event(e): game.major_fortune_used_this_week = False; game.major_fortune_activation_pending = False; rest_menu_open = False
                    if rest_menu_open and rest_btn.handle_event(e):
                        if game.level >= 17: total = game.long_rest(skip_draw=True); prophet_remaining_draws = total - 1; screen_mode, scroll_y = "prophet_selection", 0
                        else: game.long_rest()
                        rest_menu_open = False
                    if undo_btn.handle_event(e): game.undo()
                    if redo_btn.handle_event(e): game.redo()
                    draw_of_fate_slider.set_value(game.draw_of_fate_uses)
                    _top_icon_sz = 70
                    _top_btn_w = 140
                    _top_gap = 10
                    hamburger_btn.rect = pygame.Rect(W - _top_icon_sz - 20, PADDING, _top_icon_sz, _top_icon_sz)
                    load_btn.rect = pygame.Rect(hamburger_btn.rect.x - _top_gap - _top_btn_w, PADDING, _top_btn_w, _top_icon_sz)
                    save_as_btn.rect = pygame.Rect(load_btn.rect.x - _top_gap - _top_btn_w, PADDING, _top_btn_w, _top_icon_sz)
                    save_btn.rect = pygame.Rect(save_as_btn.rect.x - _top_gap - _top_btn_w, PADDING, _top_btn_w, _top_icon_sz)
                    if history_btn.handle_event(e): history_overlay_open = not history_overlay_open; history_scroll = 0
                    if save_btn.handle_event(e):
                        slot_menu_mode = "save"
                        slot_menu_return_mode = "normal"
                        _refresh_slot_labels()
                        _layout_slot_buttons()
                        screen_mode = "slot_menu"
                    elif save_as_btn.handle_event(e):
                        _write_save_as_dialog()
                    elif load_btn.handle_event(e):
                        slot_menu_mode = "load"
                        slot_menu_return_mode = "normal"
                        _refresh_slot_labels()
                        _layout_slot_buttons()
                        screen_mode = "slot_menu"
                    if rest_menu_btn.handle_event(e): rest_menu_open = not rest_menu_open
                    elif rest_menu_open and e.type == pygame.MOUSEBUTTONDOWN:
                        # Close rest menu if clicking outside it
                        _rm_item_h = 35
                        _rm_gap = 5
                        _rm_pad = 5
                        _rm_count = 1 + (1 if game.level >= 2 else 0) + (1 if game.level >= 17 else 0)
                        _rm_h = (_rm_pad * 2) + (_rm_count * _rm_item_h) + ((_rm_count - 1) * _rm_gap)
                        _rm_y = rest_menu_btn.rect.y - _rm_h - 5
                        _rm_area = pygame.Rect(rest_menu_btn.rect.x, _rm_y, rest_menu_btn.rect.w, (rest_menu_btn.rect.bottom - _rm_y))
                        if not _rm_area.collidepoint(e.pos): rest_menu_open = False
                    if hamburger_btn.handle_event(e): top_menu_open = not top_menu_open
                    elif top_menu_open:
                        _menu_item_h = 70
                        _menu_gap = 4
                        _menu_pad = 8
                        _menu_count = 3
                        _menu_h = (_menu_pad * 2) + (_menu_count * _menu_item_h) + ((_menu_count - 1) * _menu_gap)
                        _menu_bg_x = hamburger_btn.rect.right - 160
                        _menu_bg_y = hamburger_btn.rect.bottom + 13
                        if quit_btn.handle_event(e): running = False
                        elif menu_btn.handle_event(e): screen_mode = "menu"; top_menu_open = False
                        elif normal_settings_btn.handle_event(e):
                            _open_settings("normal")
                            top_menu_open = False
                        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                            _menu_area = pygame.Rect(_menu_bg_x, hamburger_btn.rect.y, 160, (_menu_bg_y - hamburger_btn.rect.y) + _menu_h)
                            if not _menu_area.collidepoint(e.pos): top_menu_open = False
                    if game.level >= 17:
                        if not fated_card_btn.disabled and fated_card_btn.handle_event(e):
                            game.save_state()
                            game.major_fortune_used_this_week = True
                            game.major_fortune_activation_pending = True
                            screen_mode, scroll_y = "major_selection", 0
                    
                    if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                        if mz_rect.collidepoint(e.pos): screen_mode, scroll_y = "deck", 0
                        elif vz_rect.collidepoint(e.pos): screen_mode, scroll_y = "vanish_view", 0
                    
                    if game.level >= 6 and e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                        dt_box = get_seer_dice_rect()
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
                        for zone, sy, sx in [(game.hand, 80 + normal_card_zone_y_offset, PANEL_W+60), (game.fortune_zone, 80 + normal_card_zone_y_offset + HAND_GRID_SPACING_Y + fortune_major_card_zone_y_offset, PANEL_W+60), (game.major_zone, 80 + normal_card_zone_y_offset + HAND_GRID_SPACING_Y + fortune_major_card_zone_y_offset, PANEL_W+60+HAND_GRID_SPACING_X)]:
                            for i, h in enumerate(zone):
                                x, y = sx+(i%4)*HAND_GRID_SPACING_X, sy+(i//4)*HAND_GRID_SPACING_Y
                                if pygame.Rect(x, y, HAND_CARD_W, HAND_CARD_H).collidepoint(m_pos) and h['flip'] >= 0.5:
                                    if m_pos[1] < y + HAND_CARD_H // 2: h['scroll_inv'] = clamp(h['scroll_inv'] - e.y*25, 0, h['max_sc_inv'])
                                    else: h['scroll_up'] = clamp(h['scroll_up'] - e.y*25, 0, h['max_sc_up'])
                    
                    if e.type == pygame.MOUSEBUTTONDOWN:
                        for h, zone, sy, sx in (
                            [(h, game.hand, 80 + normal_card_zone_y_offset, PANEL_W+60) for h in game.hand] +
                            [(f, game.fortune_zone, 80 + normal_card_zone_y_offset + HAND_GRID_SPACING_Y + fortune_major_card_zone_y_offset, PANEL_W+60) for f in game.fortune_zone] +
                            [(m, game.major_zone, 80 + normal_card_zone_y_offset + HAND_GRID_SPACING_Y + fortune_major_card_zone_y_offset, PANEL_W+60+HAND_GRID_SPACING_X) for m in game.major_zone]
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
                                    if h['id'] == 20 and h['mode'] == 'normal' and h['orientation'] == 'upright':
                                        if random.randint(1, 20) == 1:
                                            start_greedy_pot_popup(lambda hh=h, x=hx, y=hy: execute_card_use_action(hh, x, y))
                                        else:
                                            execute_card_use_action(h, hx, hy)
                                    elif ((zone == game.fortune_zone and h['mode'] == 'fortune') or (zone == game.major_zone and h['mode'] == 'major')) and not h.get('tapped'):
                                        started = start_fool_video(h['id'], lambda hh=h, x=hx, y=hy: execute_card_use_action(hh, x, y))
                                        if started:
                                            screen_mode = "fool_video"
                                    else:
                                        execute_card_use_action(h, hx, hy)
                                    break
                                # If they click the card itself (not a button) to preview it
                                elif card_rect.collidepoint(e.pos) and not h.get('tapped'):
                                    preview_cid, screen_mode = h['id'], "preview_view"
                                    preview_locked_mode = False
                                    preview_scrolls = {"current":0,"max":0}
                                    break
                                    
                            # 2. Middle Click Logic (Flip Orientation)
                            elif e.button == 2 and card_rect.collidepoint(e.pos) and not h.get('tapped'):
                                game.save_state()
                                h['orientation'] = 'inverted' if h['orientation'] == 'upright' else 'upright'
                                h['scroll_up'] = 0
                                h['scroll_inv'] = 0
                                play_turnpage_sfx()
                                break
                                
                            # 3. Right Click Logic (Move between zones)
                            elif e.button == 3 and card_rect.collidepoint(e.pos) and not h.get('tapped'):
                                game.save_state()
                                if zone == game.hand:
                                    if h['id'] in MAJOR_FORTUNE_IDS and game.level >= 17 and len(game.major_zone) < 1 and game.can_promote_card(h['id'], to_major=True):
                                        play_sfx(_sfx_major_promo, priority=True)
                                        game.hand.remove(h); h['mode'] = 'major'; game.major_zone.append(h)
                                        game.add_history(f"{game.cards[h['id']]['name']} moved to Major Zone.", [h['id']])
                                    elif game.level >= 6 and len(game.fortune_zone) < 1 and h['id'] not in MAJOR_FORTUNE_IDS and game.can_promote_card(h['id'], to_major=False):
                                        play_sfx(_sfx_fortune_promo, priority=True)
                                        game.hand.remove(h); h['mode'] = 'fortune'; game.fortune_zone.append(h)
                                        game.add_history(f"{game.cards[h['id']]['name']} moved to Fortune Zone.", [h['id']])
                                    else:
                                        if h['id'] in MAJOR_FORTUNE_IDS and game.major_fortune_used_this_week:
                                            game.toast_msg, game.toast_timer = "Cannot promote this Major Fortune card because the weekly cooldown is active. It unlocks again after the weekly reset (7 long rests).", TOAST_DURATION
                                        else:
                                            game.toast_msg, game.toast_timer = "This card cannot be promoted right now because it is not enabled in your active Fortune loadout.", TOAST_DURATION
                                else:
                                    if h in game.fortune_zone:
                                        if h.get('ppf_added'):
                                            game.toast_msg, game.toast_timer = "This Fortune card was added by Past, Present and Future, so it cannot be demoted back to your hand.", TOAST_DURATION
                                        else:
                                            game.fortune_zone.remove(h)
                                            h['mode'] = 'normal'
                                            game.hand.append(h)
                                            game.add_history(f"{game.cards[h['id']]['name']} returned to Hand.", [h['id']])
                                    elif h in game.major_zone:
                                        if h.get('major_added'):
                                            game.toast_msg, game.toast_timer = "This Major Fortune card was added by the Fated Card Button feature, so it cannot be moved back to your hand.", TOAST_DURATION
                                        else:
                                            game.major_zone.remove(h)
                                            h['mode'] = 'normal'
                                            game.hand.append(h)
                                            game.add_history(f"{game.cards[h['id']]['name']} returned to Hand.", [h['id']])
                                break

                elif screen_mode in ["deck", "vanish_view", "world_restore_view", "prophet_selection", "ppf_selection", "stack_selection", "major_selection"]:
                    if exit_view_btn.handle_event(e):
                        if screen_mode == "major_selection":
                            game.major_fortune_activation_pending = False
                        screen_mode = "normal"; grid_sb_dragging = False
                    if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE and screen_mode in ["deck", "vanish_view"]:
                        screen_mode = "normal"
                        grid_sb_dragging = False
                        continue
                    # Grid scrollbar drag support
                    if e.type == pygame.MOUSEBUTTONUP and e.button == 1:
                        grid_sb_dragging = False
                    # Compute scrollbar track geometry for grid views
                    hi_ev, fi_ev = [h['id'] for h in game.hand], [f['id'] for f in (game.fortune_zone+game.major_zone)]
                    _g_cur_list = []
                    if screen_mode == "ppf_selection": _g_cur_list = [c for c in game.ids if c in game.get_allowed_fortune_ids() and c not in MAJOR_FORTUNE_IDS and c not in game.vanished and c not in hi_ev and c not in fi_ev]
                    elif screen_mode == "world_restore_view": _g_cur_list = [vid for vid in game.vanished if vid != 20]
                    elif screen_mode == "deck": _g_cur_list = game.deck
                    elif screen_mode == "vanish_view": _g_cur_list = game.vanished
                    elif screen_mode == "prophet_selection": _g_cur_list = [c for c in game.ids if c != 20 and c not in hi_ev and c not in fi_ev]
                    elif screen_mode == "stack_selection": _g_cur_list = [c for c in game.deck if c != 20]
                    elif screen_mode == "major_selection": _g_cur_list = [c for c in MAJOR_FORTUNE_IDS if c == game.get_allowed_major_id() and c not in game.vanished and c not in hi_ev and c not in fi_ev]
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
                                    preview_locked_mode = False
                                    break
                    if e.type == pygame.MOUSEWHEEL:
                        hi, fi = [h['id'] for h in game.hand], [f['id'] for f in (game.fortune_zone+game.major_zone)]
                        cur_list = []
                        if screen_mode == "ppf_selection": cur_list = [c for c in game.ids if c in game.get_allowed_fortune_ids() and c not in MAJOR_FORTUNE_IDS and c not in game.vanished and c not in hi and c not in fi]
                        elif screen_mode == "world_restore_view": cur_list = [vid for vid in game.vanished if vid != 20]
                        elif screen_mode == "deck": cur_list = game.deck
                        elif screen_mode == "vanish_view": cur_list = game.vanished
                        elif screen_mode == "prophet_selection": cur_list = [c for c in game.ids if c != 20 and c not in hi and c not in fi]
                        elif screen_mode == "stack_selection": cur_list = [c for c in game.deck if c != 20]
                        elif screen_mode == "major_selection": cur_list = [c for c in MAJOR_FORTUNE_IDS if c == game.get_allowed_major_id() and c not in game.vanished and c not in hi and c not in fi]
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
                            if screen_mode == "ppf_selection": cur_list = [c for c in game.ids if c in game.get_allowed_fortune_ids() and c not in MAJOR_FORTUNE_IDS and c not in game.vanished and c not in hi and c not in fi]
                            elif screen_mode == "world_restore_view": cur_list = [vid for vid in game.vanished if vid != 20]
                            elif screen_mode == "deck": cur_list = game.deck
                            elif screen_mode == "vanish_view": cur_list = game.vanished
                            elif screen_mode == "prophet_selection": cur_list = [c for c in game.ids if c != 20 and c not in hi and c not in fi]
                            elif screen_mode == "stack_selection": cur_list = [c for c in game.deck if c != 20]
                            elif screen_mode == "major_selection": cur_list = [c for c in MAJOR_FORTUNE_IDS if c == game.get_allowed_major_id() and c not in game.vanished and c not in hi and c not in fi]
                            for i, cid in enumerate(cur_list):
                                gx, gy = VIEW_START_X+(i%6)*CELL_W, VIEW_START_Y+(i//6)*CELL_H-scroll_y+160
                                if pygame.Rect(gx, gy, VIEW_CARD_W, VIEW_CARD_H).collidepoint(e.pos):
                                    if screen_mode == "ppf_selection":
                                        if game.can_promote_card(cid, to_major=False):
                                            play_sfx(_sfx_fortune_promo, priority=True)
                                            game.save_state()
                                            game.fortune_zone.append({"id": cid, "mode": "fortune", "orientation": "upright", "flip": 0.0, "scroll_up": 0, "scroll_inv": 0, "max_sc_up": 0, "max_sc_inv": 0, "is_vanishing": False, "tapped": False, "ppf_added": True})
                                            game.ppf_charges -= 1
                                            game.add_history(f"Past, Present and Future: {game.cards[cid]['name']} added to Fortune Zone.", [cid])
                                            game.rebuild_deck()
                                            screen_mode = "normal"
                                        else:
                                            game.toast_msg, game.toast_timer = "That card cannot be added by Past, Present and Future because it is not enabled in your active Fortune loadout.", TOAST_DURATION
                                    elif screen_mode == "major_selection":
                                        if game.major_fortune_activation_pending and cid == game.get_allowed_major_id():
                                            play_sfx(_sfx_major_promo, priority=True)
                                            game.save_state()
                                            game.major_zone.append({"id": cid, "mode": "major", "orientation": "upright", "flip": 0.0, "scroll_up": 0, "scroll_inv": 0, "max_sc_up": 0, "max_sc_inv": 0, "is_vanishing": False, "tapped": False, "major_added": True})
                                            game.major_fortune_used_this_week = True
                                            game.major_fortune_activation_pending = False
                                            game.add_history(f"Major Fortune: {game.cards[cid]['name']} activated.", [cid])
                                            game.rebuild_deck()
                                            screen_mode = "normal"
                                        else:
                                            game.toast_msg, game.toast_timer = "That Major card cannot be added right now. It must be the Major card selected in your active Fortune loadout, and the weekly cooldown must be available.", TOAST_DURATION
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
                                    else: preview_cid, screen_mode = cid, "preview_view"; preview_scrolls = {"current":0,"max":0}; preview_locked_mode = False
                                    break

            # --- DRAWING ---
            screen.fill((10, 12, 18))
            # Play screen-specific music for menu-style views.
            _menu_music_track = {
                "library": LIBRARY_MUSIC,
                "fortune_spell_list_view": SPELL_LIBRARY_MUSIC,
                "fortune_glossary_view": GLOSSARY_MUSIC,
                "ppf_selection": PPF_BG_MUSIC,
                "major_selection": PPF_BG_MUSIC,
            }.get(screen_mode, MAIN_MENU_MUSIC)
            if not os.path.exists(_menu_music_track):
                _menu_music_track = MAIN_MENU_MUSIC
            if screen_mode in ["menu", "library", "settings", "slot_menu", "fortune_setup", "fortune_spell_list_view", "fortune_glossary_view", "ppf_selection", "major_selection"] and menu_music_enabled and audio_enabled:
                try:
                    pygame.mixer.music.set_volume(menu_music_volume / 100.0)
                except Exception:
                    pass
                if current_menu_music_track != _menu_music_track or not pygame.mixer.music.get_busy() or pygame.mixer.music.get_pos() == -1:
                    try:
                        pygame.mixer.music.load(_menu_music_track)
                        pygame.mixer.music.play(-1)
                        current_menu_music_track = _menu_music_track
                    except Exception as e:
                        log_event(f"Music error: {e}", True)
            else:
                if pygame.mixer.music.get_busy():
                    pygame.mixer.music.stop()
                current_menu_music_track = None
            
            if screen_mode == "menu":
                screen.blit(menu_bg, (0, 0))
                # Fantasy-style vignette + ornate frame
                _vignette = pygame.Surface((W, H), pygame.SRCALPHA)
                _vignette.fill((10, 6, 14, 95))
                screen.blit(_vignette, (0, 0))
                _frame_outer = menu_box_rect.inflate(48, 52)
                _frame_mid = _frame_outer.inflate(-10, -10)
                _frame_inner = menu_box_rect.copy()
                draw_round_rect(screen, _frame_outer, (36, 20, 12, 215), 24)
                pygame.draw.rect(screen, (120, 86, 42, 220), _frame_outer, 3, 24)
                draw_round_rect(screen, _frame_mid, (22, 15, 10, 215), 22)
                pygame.draw.rect(screen, (184, 138, 66, 220), _frame_mid, 2, 22)
                draw_round_rect(screen, _frame_inner, (18, 14, 24, 220), 20)
                pygame.draw.rect(screen, (235, 190, 60, 150), _frame_inner, 1, 20)
                for _cx, _cy in [(_frame_outer.x + 22, _frame_outer.y + 22), (_frame_outer.right - 22, _frame_outer.y + 22), (_frame_outer.x + 22, _frame_outer.bottom - 22), (_frame_outer.right - 22, _frame_outer.bottom - 22)]:
                    pygame.draw.circle(screen, (235, 190, 60, 230), (_cx, _cy), 7, 2)
                    pygame.draw.circle(screen, (130, 86, 32, 200), (_cx, _cy), 3)
                _title_shadow = f_preview_title.render("DIVINE SEER DOMAIN", True, (25, 12, 6))
                _title_main = f_preview_title.render("DIVINE SEER DOMAIN", True, GOLD)
                screen.blit(_title_shadow, (W//2 - 218, menu_box_rect.y - 102))
                screen.blit(_title_main, (W//2 - 220, menu_box_rect.y - 104))
                _sub = f_small.render("Draw the veil. Read the fate.", True, (206, 176, 120))
                screen.blit(_sub, (W//2 - _sub.get_width()//2, menu_box_rect.y - 50))
                
                f_choose_level = pygame.font.SysFont("georgia", 32, bold=True)
                _level_panel = pygame.Rect(menu_box_rect.x + 36, menu_box_rect.y + 18, menu_box_rect.w - 72, 120)
                draw_round_rect(screen, _level_panel, (22, 18, 30, 205), 16)
                pygame.draw.rect(screen, (235, 190, 60, 120), _level_panel, 1, 16)
                choose_lvl_surf = f_choose_level.render("Choose player level", True, (220, 210, 160))
                choose_lvl_x = menu_box_rect.centerx - choose_lvl_surf.get_width()//2
                choose_lvl_y = _level_panel.y + 10
                screen.blit(choose_lvl_surf, (choose_lvl_x, choose_lvl_y))
                menu_lvl_dd.draw_base(screen, f_small)
                start_game_btn.draw(screen, f_small, dt)
                new_game_btn.draw(screen, f_small, dt)
                menu_load_btn.draw(screen, f_small, dt)
                menu_library_btn.draw(screen, f_small, dt)
                settings_btn.draw(screen, f_small, dt)
                menu_quit_btn.draw(screen, f_small, dt)
                menu_lvl_dd.draw_menu(screen, f_small)

            elif screen_mode == "library":
                if _img_library_bg is not None:
                    screen.blit(pygame.transform.smoothscale(_img_library_bg, (W, H)), (0, 0))
                else:
                    screen.blit(menu_bg, (0, 0))
                _vignette = pygame.Surface((W, H), pygame.SRCALPHA)
                _vignette.fill((10, 6, 14, 105))
                screen.blit(_vignette, (0, 0))
                _outer = library_box_rect.inflate(26, 30)
                draw_round_rect(screen, _outer, (36, 20, 12, 220), 24)
                pygame.draw.rect(screen, (120, 86, 42, 220), _outer, 3, 24)
                draw_round_rect(screen, library_box_rect, (18, 14, 24, 235), 20)
                pygame.draw.rect(screen, (235, 190, 60, 170), library_box_rect, 2, 20)
                _title = f_preview_title.render("THE LIBRARY", True, GOLD)
                _title_shadow = f_preview_title.render("THE LIBRARY", True, (25, 12, 6))
                screen.blit(_title_shadow, (_outer.centerx - _title_shadow.get_width() // 2 + 2, library_box_rect.y + 34))
                screen.blit(_title, (_outer.centerx - _title.get_width() // 2, library_box_rect.y + 32))
                _hint = f_small.render("Choose a path through the archive.", True, (206, 176, 120))
                screen.blit(_hint, (library_box_rect.centerx - _hint.get_width() // 2, library_box_rect.y + 94))
                _glyph_panel = _library_inner_panel_rect()
                draw_round_rect(screen, _glyph_panel, (20, 18, 30, 155), 18)
                pygame.draw.rect(screen, (235, 190, 60, 70), _glyph_panel, 1, 18)
                _layout_library_buttons()
                library_loadout_btn.draw(screen, f_small, dt)
                library_glossary_btn.draw(screen, f_small, dt)
                library_spell_list_btn.draw(screen, f_small, dt)
                library_back_btn.text = "Back" if library_return_mode == "normal" else "Main Menu"
                library_back_btn.draw(screen, f_small, dt)

            elif screen_mode == "slot_menu":
                screen.blit(menu_bg, (0, 0))
                _vignette = pygame.Surface((W, H), pygame.SRCALPHA)
                _vignette.fill((10, 6, 14, 110))
                screen.blit(_vignette, (0, 0))
                _outer = slot_menu_box_rect.inflate(20, 24)
                draw_round_rect(screen, _outer, (36, 20, 12, 220), 24)
                pygame.draw.rect(screen, (120, 86, 42, 220), _outer, 3, 24)
                draw_round_rect(screen, slot_menu_box_rect, (18, 14, 24, 230), 20)
                pygame.draw.rect(screen, (235, 190, 60, 170), slot_menu_box_rect, 2, 20)
                _title_txt = "SAVE SLOTS" if slot_menu_mode == "save" else "LOAD SLOTS"
                _st = f_preview_title.render(_title_txt, True, GOLD)
                screen.blit(_st, (slot_menu_box_rect.centerx - _st.get_width() // 2, slot_menu_box_rect.y + 20))
                _hint_txt = "Choose a save slot" if slot_menu_mode == "save" else "Choose a save slot, autosave, or file"
                _hint = f_tiny.render(_hint_txt, True, (205, 178, 126))
                screen.blit(_hint, (slot_menu_box_rect.centerx - _hint.get_width() // 2, slot_menu_box_rect.y + 72))
                _layout_slot_buttons()
                _left_panel = pygame.Rect(slot_menu_box_rect.x + 42, slot_menu_box_rect.y + 120, 490, 416)
                draw_round_rect(screen, _left_panel, (20, 18, 30, 120), 12)
                pygame.draw.rect(screen, (235, 190, 60, 60), _left_panel, 1, 12)
                _manual_hdr = f_small.render("Manual Slots", True, (236, 214, 170))
                screen.blit(_manual_hdr, (_left_panel.x + 16, _left_panel.y + 12))
                if slot_menu_mode == "load":
                    _auto_outer = slot_autosave_box_rect.inflate(20, 24)
                    draw_round_rect(screen, _auto_outer, (36, 20, 12, 220), 24)
                    pygame.draw.rect(screen, (120, 86, 42, 220), _auto_outer, 3, 24)
                    draw_round_rect(screen, slot_autosave_box_rect, (18, 14, 24, 230), 20)
                    pygame.draw.rect(screen, (235, 190, 60, 170), slot_autosave_box_rect, 2, 20)
                    _auto_hdr = f_preview_title.render("AUTO SAVES", True, GOLD)
                    screen.blit(_auto_hdr, (slot_autosave_box_rect.centerx - _auto_hdr.get_width() // 2, slot_autosave_box_rect.y + 20))
                    _auto_hint = f_tiny.render("Scroll dropdown list", True, (205, 178, 126))
                    screen.blit(_auto_hint, (slot_autosave_box_rect.centerx - _auto_hint.get_width() // 2, slot_autosave_box_rect.y + 92))
                    _auto_hint2 = f_tiny.render("Select an autosave to load", True, (205, 178, 126))
                    screen.blit(_auto_hint2, (slot_autosave_box_rect.centerx - _auto_hint2.get_width() // 2, slot_autosave_box_rect.y + 110))
                    slot_autosave_dropdown.draw_base(screen, f_tiny)
                    slot_autosave_load_btn.draw(screen, f_tiny, dt)
                for _b in slot_buttons:
                    if _b.rect.w > 0:
                        _b.draw(screen, f_tiny, dt)
                if slot_menu_mode == "load":
                    slot_autosave_dropdown.draw_menu(screen, f_tiny)
                    slot_load_file_btn.draw(screen, f_tiny, dt)
                slot_back_btn.draw(screen, f_small, dt)
             
            elif screen_mode == "settings":
                screen.blit(menu_bg, (0, 0))
                _vignette = pygame.Surface((W, H), pygame.SRCALPHA)
                _vignette.fill((10, 6, 14, 105))
                screen.blit(_vignette, (0, 0))
                _s_outer = settings_box_rect.inflate(16, 20)
                draw_round_rect(screen, _s_outer, (36, 20, 12, 220), 24)
                pygame.draw.rect(screen, (120, 86, 42, 220), _s_outer, 3, 24)
                draw_round_rect(screen, settings_box_rect, (18, 14, 24, 230), 20)
                pygame.draw.rect(screen, (235, 190, 60, 170), settings_box_rect, 2, 20)
                _st = f_preview_title.render("SETTINGS", True, GOLD)
                screen.blit(_st, (settings_box_rect.centerx - _st.get_width() // 2, settings_box_rect.y + 22))
                _hint = f_tiny.render(f"Press Escape to return to {'Normal View' if settings_return_mode == 'normal' else 'Main Menu'}", True, (205, 178, 126))
                screen.blit(_hint, (settings_box_rect.centerx - _hint.get_width() // 2, settings_box_rect.y + 78))

                _lbl1 = f_small.render("Menu Music", True, (232, 215, 176))
                _lbl2 = f_small.render("Music Volume", True, (232, 215, 176))
                _lbl3 = f_small.render("Global Toggles", True, (232, 215, 176))
                _lbl4 = f_small.render("Autosave", True, (232, 215, 176))
                screen.blit(_lbl1, (settings_box_rect.x + 80, settings_box_rect.y + 154))
                screen.blit(_lbl2, (settings_box_rect.x + 80, settings_box_rect.y + 222))
                screen.blit(_lbl4, (settings_box_rect.x + 80, settings_box_rect.y + 470))

                _toggle_panel = pygame.Rect(settings_box_rect.x + 52, settings_box_rect.y + 258, settings_box_rect.w - 104, 310)
                draw_round_rect(screen, _toggle_panel, (20, 18, 30, 160), 14)
                pygame.draw.rect(screen, (235, 190, 60, 80), _toggle_panel, 1, 14)
                screen.blit(_lbl3, (_toggle_panel.centerx - _lbl3.get_width() // 2, _toggle_panel.y + 8))

                settings_music_dd.draw_base(screen, f_small)
                settings_music_slider.draw(screen, f_tiny)
                settings_sound_btn.text = f"Audio: {'ON' if audio_enabled else 'OFF'}"
                settings_fx_btn.text = f"Sound FX: {'ON' if sfx_enabled else 'OFF'}"
                settings_menu_video_btn.text = f"Menu Vids: {'ON' if menu_videos_enabled else 'PAUSED'}"
                settings_card_video_btn.text = f"Card Videos: {'ON' if card_videos_enabled else 'OFF'}"
                settings_autosave_btn.text = f"Autosave: {'ON' if autosave_enabled else 'OFF'}"
                settings_back_btn.text = "Back" if settings_return_mode == "normal" else "Main Menu"
                for _btn, _state in [
                    (settings_sound_btn, audio_enabled),
                    (settings_fx_btn, sfx_enabled),
                    (settings_menu_video_btn, menu_videos_enabled),
                    (settings_card_video_btn, card_videos_enabled),
                    (settings_autosave_btn, autosave_enabled),
                ]:
                    _btn.green = bool(_state)
                    _btn.danger = not bool(_state)
                    _btn.primary = False
                settings_sound_btn.draw(screen, f_small, dt)
                settings_fx_btn.draw(screen, f_small, dt)
                settings_menu_video_btn.draw(screen, f_tiny, dt)
                settings_card_video_btn.draw(screen, f_small, dt)
                settings_autosave_btn.draw(screen, f_small, dt)
                settings_autosave_minus_btn.draw(screen, f_small, dt)
                _auto_box = pygame.Rect(settings_autosave_minus_btn.rect.right + 16, settings_autosave_minus_btn.rect.y + 7, 72, 34)
                draw_round_rect(screen, _auto_box, (20, 18, 30, 220), 8)
                pygame.draw.rect(screen, (235, 190, 60, 130), _auto_box, 1, 8)
                _auto_txt = f_small.render(f"{autosave_interval_min}m", True, (236, 218, 182))
                screen.blit(_auto_txt, (_auto_box.centerx - _auto_txt.get_width() // 2, _auto_box.centery - _auto_txt.get_height() // 2))
                _lbl5 = f_small.render("Autosave Interval", True, (232, 215, 176))
                screen.blit(_lbl5, (_auto_box.centerx - _lbl5.get_width() // 2, _auto_box.bottom + 10))
                settings_autosave_plus_btn.draw(screen, f_small, dt)
                settings_back_btn.draw(screen, f_small, dt)
                settings_exit_btn.draw(screen, f_small, dt)
                settings_music_dd.draw_menu(screen, f_small)

            elif screen_mode == "fortune_setup":
                if _img_library_bg is not None:
                    screen.blit(pygame.transform.smoothscale(_img_library_bg, (W, H)), (0, 0))
                else:
                    screen.blit(menu_bg, (0, 0))
                _vignette = pygame.Surface((W, H), pygame.SRCALPHA)
                _vignette.fill((10, 6, 14, 110))
                screen.blit(_vignette, (0, 0))
                _outer = fortune_setup_box.inflate(22, 24)
                _blit_alpha_round_rect(screen, _outer, (36, 20, 12, 108), 24)
                pygame.draw.rect(screen, (120, 86, 42, 220), _outer, 3, 24)
                _blit_alpha_round_rect(screen, fortune_setup_box, (18, 14, 24, 84), 20)
                pygame.draw.rect(screen, (235, 190, 60, 180), fortune_setup_box, 2, 20)
                _title = f_fortune_title.render("FORTUNE CARD SELECTION", True, GOLD)
                screen.blit(_title, (fortune_setup_box.centerx - _title.get_width() // 2, fortune_setup_box.y + 20))
                _hint = f_fortune_small.render("SELECT THE ONLY CARDS THAT CAN BE PROMOTED TO FORTUNE / MAJOR FORTUNE", True, (228, 204, 156))
                screen.blit(_hint, (fortune_setup_box.centerx - _hint.get_width() // 2, fortune_setup_box.y + 78))
                _slot_info_y = _fortune_loadout_button_bottom() + 14
                _slots = f_fortune_body.render(_fortune_slots_summary(), True, (230, 215, 175))
                screen.blit(_slots, (fortune_setup_box.x + 40, _slot_info_y))
                fortune_lvl_dd.set_value(game.level)
                fortune_lvl_dd.draw_base(screen, f_fortune_body)
                # Draw 'Select Level' text below the level selector
                _select_level_text = f_fortune_small.render("Select Level", True, (232, 215, 176))
                _lvl_dd_rect = fortune_lvl_dd.rect if hasattr(fortune_lvl_dd, 'rect') else pygame.Rect(fortune_setup_box.right - 270, fortune_setup_box.y + 24, 230, 46)
                screen.blit(_select_level_text, (_lvl_dd_rect.centerx - _select_level_text.get_width() // 2, _lvl_dd_rect.bottom + 4))
                active_ld = fortune_edit_loadout
                for _idx, _btn in enumerate(fortune_loadout_buttons):
                    _base_name = str(game.fortune_loadouts[_idx].get("name", f"Loadout {_idx + 1}"))[:15]
                    _btn.text = f"{fortune_name_input}_" if fortune_name_edit_idx == _idx else _base_name
                    _btn.warning = (_idx == fortune_selected_loadout_idx)
                    _btn.primary = (_idx != fortune_selected_loadout_idx)
                    _btn.draw(screen, f_fortune_small, dt)
                _mj_hdr = f_fortune_small.render("MAJOR FORTUNE CARDS ARE LISTED LAST", True, (238, 175, 175))
                screen.blit(_mj_hdr, (fortune_setup_box.x + 40, _slot_info_y + 29))
                _build_fortune_card_buttons()
                _grid_clip = _fortune_grid_clip_rect()
                _right_col_gap = 22
                _right_col_x = _grid_clip.right + _right_col_gap
                _right_col_r = pygame.Rect(_right_col_x, _grid_clip.y, fortune_setup_box.right - 34 - _right_col_x, _grid_clip.h)
                _title_band_h = 30
                _mid_gap = 18
                _right_box_h = (_right_col_r.h - (_title_band_h * 2) - _mid_gap) // 2
                _right_top_title_r = pygame.Rect(_right_col_r.x, _right_col_r.y, _right_col_r.w, _title_band_h)
                _right_top_box = pygame.Rect(_right_col_r.x, _right_top_title_r.bottom, _right_col_r.w, _right_box_h)
                _right_bottom_title_r = pygame.Rect(_right_col_r.x, _right_top_box.bottom + _mid_gap, _right_col_r.w, _title_band_h)
                _right_bottom_box = pygame.Rect(_right_col_r.x, _right_bottom_title_r.bottom, _right_col_r.w, _right_box_h)
                _clip_prev = screen.get_clip()
                screen.set_clip(_grid_clip)
                for _hdr, _hy, _hh, _unlocked in fortune_section_headers:
                    _hdr_box = pygame.Rect(_grid_clip.x + 4, _hy, _grid_clip.w - 8, _hh)
                    draw_round_rect(screen, _hdr_box, (26, 22, 32, 210), 8)
                    pygame.draw.rect(screen, (220, 186, 108) if _unlocked else (130, 96, 76), _hdr_box, 1, 8)
                    _hc = (236, 214, 170) if _unlocked else (165, 128, 112)
                    _hs = f_fortune_small.render(_hdr, True, _hc)
                    screen.blit(_hs, (_hdr_box.x + 10, _hdr_box.centery - _hs.get_height() // 2))
                for _cid, _rect, _mode in fortune_card_buttons:
                    _show_back = _rect.collidepoint(m_pos)
                    _card_state = _get_fortune_card_state(_cid, _mode)
                    if _show_back:
                        _face = _get_interactive_mode_back_surface(_cid, _mode, _rect.w, _rect.h, _card_state)
                    else:
                        _base_face = view_tex[_cid]
                        _face = pygame.transform.rotate(_base_face, 180) if _card_state.get("orientation") == "inverted" else _base_face
                    _art = pygame.transform.smoothscale(_face, (_rect.w, _rect.h))
                    screen.blit(_art, _rect.topleft)
                    _selected = (active_ld.get("major_id") == _cid) if _mode == "major" else (_cid in active_ld.get("fortune_ids", []))
                    draw_card_glitter(screen, _rect, pygame.time.get_ticks() / 1000.0, "red" if _mode == "major" else "gold")
                    _hover = _rect.collidepoint(m_pos)
                    if _selected:
                        _sel_glow = pygame.Surface((_rect.w + 20, _rect.h + 20), pygame.SRCALPHA)
                        _gcol = (235, 120, 95, 120) if _mode == "major" else (235, 190, 60, 120)
                        pygame.draw.rect(_sel_glow, _gcol, _sel_glow.get_rect(), 8, 14)
                        screen.blit(_sel_glow, (_rect.x - 10, _rect.y - 10))
                    _edge = (255, 120, 120) if (_selected and _mode == "major") else (GOLD if _selected else ((225, 190, 120) if _hover else (120, 86, 62)))
                    pygame.draw.rect(screen, _edge, _rect, 3, 12)
                    if _selected and not _hover:
                        _draw_promotion_stamp(_rect, _is_major=(_mode == "major"), _inverted=(_card_state.get("orientation") == "inverted"))
                    _cb = _fortune_checkbox_rect(_rect)
                    _cb_bg = (52, 24, 24, 228) if (_mode == "major" and _selected) else ((56, 44, 20, 228) if _selected else (18, 22, 18, 220))
                    _cb_edge = (255, 140, 120) if _mode == "major" else ((255, 222, 132) if _selected else (232, 204, 146))
                    draw_round_rect(screen, _cb, _cb_bg, 7)
                    pygame.draw.rect(screen, _cb_edge, _cb, 2, 7)
                    if _selected:
                        _glow_r = _cb.inflate(10, 10)
                        _glow_surf = pygame.Surface((_glow_r.w, _glow_r.h), pygame.SRCALPHA)
                        pygame.draw.rect(_glow_surf, (255, 190, 110, 70) if _mode != "major" else (255, 120, 120, 70), _glow_surf.get_rect(), border_radius=9)
                        screen.blit(_glow_surf, _glow_r.topleft)
                        _p1 = (_cb.x + 5, _cb.centery)
                        _p2 = (_cb.x + 10, _cb.bottom - 5)
                        _p3 = (_cb.right - 5, _cb.y + 5)
                        _tick_col = (255, 214, 102) if _mode != "major" else (255, 170, 160)
                        pygame.draw.line(screen, _tick_col, _p1, _p2, 3)
                        pygame.draw.line(screen, _tick_col, _p2, _p3, 3)
                screen.set_clip(_clip_prev)
                pygame.draw.rect(screen, (235, 190, 60, 80), _grid_clip, 1, 8)
                draw_round_rect(screen, _right_top_title_r, (28, 22, 32, 220), 10)
                pygame.draw.rect(screen, (220, 186, 108), _right_top_title_r, 1, 10)
                draw_round_rect(screen, _right_top_box, (20, 18, 30, 225), 12)
                pygame.draw.rect(screen, (220, 186, 108), _right_top_box, 2, 12)
                draw_round_rect(screen, _right_bottom_title_r, (28, 22, 32, 220), 10)
                pygame.draw.rect(screen, (220, 186, 108), _right_bottom_title_r, 1, 10)
                draw_round_rect(screen, _right_bottom_box, (20, 18, 30, 225), 12)
                pygame.draw.rect(screen, (220, 186, 108), _right_bottom_box, 2, 12)

                # CUSTOM TITLE SLOT (TOP): replace this title text.
                _rt_title = f_fortune_small.render("Fortune Cards", True, (236, 214, 170))
                screen.blit(_rt_title, (_right_top_title_r.x + 12, _right_top_title_r.centery - _rt_title.get_height() // 2))
                # CUSTOM TEXT SLOT (TOP BOX): replace these lines with your own text/content.
                def _wrap_to_width(_txt, _font, _max_w):
                    _txt = str(_txt)
                    if not _txt.strip():
                        return [""]
                    _words = _txt.split(" ")
                    _lines = []
                    _cur = _words[0]
                    for _w in _words[1:]:
                        _cand = f"{_cur} {_w}"
                        if _font.size(_cand)[0] <= _max_w:
                            _cur = _cand
                        else:
                            _lines.append(_cur)
                            _cur = _w
                    _lines.append(_cur)
                    return _lines
                _top_box_source_lines = [
                    "At 6th level, you gain Three special Fortune cards within your Tarot deck.",
                    "Each of these Fortune cards has different ability than displayed on the Tarot Table, but still has a different effect depending on whether it is Upright or Reverse. When you draw a Fortune card you can choose to apply its Fortune card ability, or its Tarot Table ability. You can hold one Tapped Fortune card in addition to your hand size.",
                    "",
                    "Past, Present and Future",
                    "Once per turn, (or as a free action out of combat) you can choose to pull One Fortune Card from your deck and use its effect without having to roll on the Tarot Table. You can use this feature up to three times per long rest.",
                    "",
                    "",
                    "You gain two additional Fortune card options at 9th, 13th, and 17th level. Also each time you gain a Level, you can replace one of your Fortune Cards for another.",
                ]
                _top_max_w = _right_top_box.w - 28
                _top_lines = []
                for _src in _top_box_source_lines:
                    _top_lines.extend(_wrap_to_width(_src, f_fortune_small, _top_max_w))
                _ty = _right_top_box.y + 14
                for _line in _top_lines:
                    _is_ppf_title = (_line == "Past, Present and Future")
                    _line_col = (238, 210, 162) if _is_ppf_title else (218, 196, 152)
                    _line_font = f_fortune_subtitle if _is_ppf_title else f_fortune_small
                    _lh = _line_font.get_linesize()
                    if _ty + _lh > _right_top_box.bottom - 10:
                        break
                    _line_txt = _line_font.render(_line, True, _line_col)
                    screen.blit(_line_txt, (_right_top_box.x + 14, _ty))
                    _ty += _lh
                # CUSTOM TITLE SLOT (BOTTOM): replace this title text.
                _rb_title = f_fortune_small.render("Major Fortune Cards", True, (236, 214, 170))
                screen.blit(_rb_title, (_right_bottom_title_r.x + 12, _right_bottom_title_r.centery - _rb_title.get_height() // 2))
                _bottom_box_source_lines = [
                    "At 17th Level, you add one of three Major fortune cards to your deck.",
                    "Each of these Major Fortune Cards has different ability than displayed on the Tarot Table, but still has a different effect depending on whether it is Upright or Reverse.",
                    "When you draw a Major Fortune card you can choose to apply its Major Fortune card ability, or its Tarot Table ability.",
                    "You can choose to pull this Major Fortune Card from your deck and use its effect without having to roll on the Tarot Table.",
                    "This card is called a Fated Card.",
                    "Once used the Major Fortune Card cannot be used again until a week has passed.",
                ]
                _bottom_max_w = _right_bottom_box.w - 28
                _bottom_lines = []
                for _src in _bottom_box_source_lines:
                    _bottom_lines.extend(_wrap_to_width(_src, f_fortune_small, _bottom_max_w))
                _by = _right_bottom_box.y + 14
                for _line in _bottom_lines:
                    _blh = f_fortune_small.get_linesize()
                    if _by + _blh > _right_bottom_box.bottom - 10:
                        break
                    _line_txt = f_fortune_small.render(_line, True, (218, 196, 152))
                    screen.blit(_line_txt, (_right_bottom_box.x + 14, _by))
                    _by += _blh

                _ctrl = f_fortune_small.render("LEFT CLICK CARD/CHECKBOX: SELECT    HOVER CARD: FLIP", True, (220, 201, 154))
                _bottom_text_y = _grid_clip.bottom + 12
                screen.blit(_ctrl, (fortune_setup_box.centerx - _ctrl.get_width() // 2, _bottom_text_y))
                fortune_back_btn.text = "Back to Library"
                fortune_clear_btn.draw(screen, f_fortune_small, dt)
                fortune_save_btn.draw(screen, f_fortune_small, dt)
                fortune_save_file_btn.draw(screen, f_fortune_small, dt)
                fortune_load_file_btn.draw(screen, f_fortune_small, dt)
                fortune_back_btn.draw(screen, f_fortune_small, dt)

            elif screen_mode == "fortune_spell_list_view":
                _pink_edge = (236, 126, 194)
                _pink_soft = (245, 188, 224)
                _pink_bg = (44, 20, 44)
                if _img_spell_library_bg is not None:
                    screen.blit(pygame.transform.smoothscale(_img_spell_library_bg, (W, H)), (0, 0))
                else:
                    screen.blit(menu_bg, (0, 0))
                _vignette = pygame.Surface((W, H), pygame.SRCALPHA)
                _vignette.fill((10, 6, 14, 110))
                screen.blit(_vignette, (0, 0))
                _outer = fortune_setup_box.inflate(22, 24)
                _blit_alpha_round_rect(screen, _outer, (36, 20, 12, 108), 24)
                pygame.draw.rect(screen, _pink_edge, _outer, 3, 24)
                _blit_alpha_round_rect(screen, fortune_setup_box, (18, 14, 24, 84), 20)
                pygame.draw.rect(screen, _pink_edge, fortune_setup_box, 2, 20)
                _title = f_fortune_title.render("SPELL LIST", True, _pink_soft)
                screen.blit(_title, (fortune_setup_box.centerx - _title.get_width() // 2, fortune_setup_box.y + 20))
                _hint = f_fortune_small.render("Search + filter at top. Click a spell to open its reference page.", True, (236, 208, 228))
                screen.blit(_hint, (fortune_setup_box.centerx - _hint.get_width() // 2, fortune_setup_box.y + 82))
                _search_rect, _filter_rects, _filter_labels, _class_rect, _school_rect = _spell_top_controls_layout()
                draw_round_rect(screen, _search_rect, (20, 18, 30, 230), 10)
                pygame.draw.rect(screen, _pink_soft if fortune_spell_search_active else _pink_edge, _search_rect, 2, 10)
                _search_label = "Search spells..."
                _search_txt = fortune_spell_search if fortune_spell_search else _search_label
                _search_col = (244, 222, 238) if fortune_spell_search else (166, 138, 158)
                _search_s = f_fortune_small.render(_search_txt, True, _search_col)
                screen.blit(_search_s, (_search_rect.x + 12, _search_rect.centery - _search_s.get_height() // 2))
                if fortune_spell_search_active and (pygame.time.get_ticks() // 500) % 2 == 0:
                    _cx = _search_rect.x + 12 + _search_s.get_width() + 2
                    pygame.draw.line(screen, _pink_soft, (_cx, _search_rect.y + 9), (_cx, _search_rect.bottom - 9), 2)
                for _fm, _fr in _filter_rects.items():
                    _active = (fortune_spell_filter == _fm)
                    draw_round_rect(screen, _fr, _pink_bg if _active else (24, 20, 34, 220), 9)
                    pygame.draw.rect(screen, _pink_soft if _active else _pink_edge, _fr, 2, 9)
                    _lbl = _filter_labels[_fm]
                    _ls = f_fortune_small.render(_lbl, True, (252, 228, 244) if _active else (228, 196, 214))
                    screen.blit(_ls, (_fr.centerx - _ls.get_width() // 2, _fr.centery - _ls.get_height() // 2))

                _class_txt = str(fortune_spell_class_filter if fortune_spell_class_filter != "all" else "All")
                _school_txt = str(fortune_spell_school_filter if fortune_spell_school_filter != "all" else "All")
                for _r, _label, _value in [(_class_rect, "Class", _class_txt), (_school_rect, "School", _school_txt)]:
                    draw_round_rect(screen, _r, (24, 20, 34, 220), 9)
                    pygame.draw.rect(screen, _pink_edge, _r, 2, 9)
                    _t = f_fortune_small.render(f"{_label}: {_value}", True, (236, 208, 228))
                    if _t.get_width() > _r.w - 16:
                        _cut = max(4, int(len(f"{_label}: {_value}") * ((_r.w - 30) / max(1, _t.get_width()))))
                        _s = f"{_label}: {_value}"[:_cut] + "..."
                        _t = f_fortune_small.render(_s, True, (236, 208, 228))
                    screen.blit(_t, (_r.x + 10, _r.centery - _t.get_height() // 2))

                _panel = pygame.Rect(fortune_setup_box.x + 40, _class_rect.bottom + 8, fortune_setup_box.w - 80, fortune_setup_box.h - ((_class_rect.bottom + 8) - fortune_setup_box.y) - 110)
                _blit_alpha_round_rect(screen, _panel, (20, 18, 30, 96), 12)
                pygame.draw.rect(screen, _pink_edge, _panel, 2, 12)
                _query = fortune_spell_search.strip().lower()
                _filtered_spells = []
                for _sp in fortune_spell_entries:
                    _name = str(_sp.get("name", ""))
                    _name_l = _name.lower()
                    if _query and _query not in _name_l:
                        continue
                    _lvl = _sp.get("level")
                    if fortune_spell_filter == "cantrip" and _lvl != 0:
                        continue
                    if fortune_spell_filter == "1_3" and not (isinstance(_lvl, int) and 1 <= _lvl <= 3):
                        continue
                    if fortune_spell_filter == "4_6" and not (isinstance(_lvl, int) and 4 <= _lvl <= 6):
                        continue
                    if fortune_spell_filter == "7_9" and not (isinstance(_lvl, int) and 7 <= _lvl <= 9):
                        continue
                    if fortune_spell_filter == "unknown" and _lvl is not None:
                        continue
                    if fortune_spell_class_filter != "all" and fortune_spell_class_filter not in (_sp.get("classes") or []):
                        continue
                    if fortune_spell_school_filter != "all" and fortune_spell_school_filter != str(_sp.get("school", "Unknown")):
                        continue
                    _filtered_spells.append(_sp)
                _layout_items, _layout_total_h = _build_spell_grid_layout(_panel, _filtered_spells, fortune_spell_list_scroll)
                _clip, _sb_track_rect, _sb_handle_rect, _spell_max_scroll_draw = _fantasy_scrollbar_geometry(_panel, _layout_total_h, fortune_spell_list_scroll)
                _clip_prev = screen.get_clip()
                screen.set_clip(_clip)
                for _kind, _rr, _text, _spell_obj in _layout_items:
                    if _rr.bottom < _clip.y or _rr.top > _clip.bottom:
                        continue
                    if _kind == "header":
                        draw_round_rect(screen, _rr, (26, 22, 32, 220), 8)
                        pygame.draw.rect(screen, _pink_edge, _rr, 1, 8)
                        _hs = f_fortune_small.render(_text, True, _pink_soft)
                        screen.blit(_hs, (_rr.x + 10, _rr.centery - _hs.get_height() // 2))
                    else:
                        _hover = _rr.collidepoint(m_pos)
                        draw_round_rect(screen, _rr, _pink_bg if _hover else (24, 20, 34, 210), 8)
                        pygame.draw.rect(screen, (236, 126, 194, 140), _rr, 1, 8)
                        _txt = f_fortune_small.render(_text, True, (244, 222, 238))
                        screen.blit(_txt, (_rr.x + 10, _rr.centery - _txt.get_height() // 2))
                screen.set_clip(_clip_prev)
                if _spell_max_scroll_draw > 0:
                    _draw_fantasy_scrollbar(screen, _sb_track_rect, _sb_handle_rect, _pink_edge, _pink_soft)
                if not _filtered_spells:
                    _none = f_fortune_small.render("No spells match your search/filter.", True, (244, 178, 206))
                    screen.blit(_none, (_panel.centerx - _none.get_width() // 2, _panel.centery - _none.get_height() // 2))
                fortune_view_back_btn.text = "Back to Library"
                fortune_view_back_btn.draw(screen, f_fortune_small, dt)

            elif screen_mode == "fortune_glossary_view":
                _cyan_edge = (102, 220, 255)
                _cyan_soft = (186, 242, 255)
                if _img_glossary_bg is not None:
                    screen.blit(pygame.transform.smoothscale(_img_glossary_bg, (W, H)), (0, 0))
                else:
                    screen.blit(menu_bg, (0, 0))
                _vignette = pygame.Surface((W, H), pygame.SRCALPHA)
                _vignette.fill((10, 6, 14, 110))
                screen.blit(_vignette, (0, 0))
                _outer = fortune_setup_box.inflate(22, 24)
                _blit_alpha_round_rect(screen, _outer, (36, 20, 12, 108), 24)
                pygame.draw.rect(screen, _cyan_edge, _outer, 3, 24)
                _blit_alpha_round_rect(screen, fortune_setup_box, (18, 14, 24, 84), 20)
                pygame.draw.rect(screen, _cyan_edge, fortune_setup_box, 2, 20)
                _title = f_fortune_title.render("GLOSSARY", True, _cyan_soft)
                screen.blit(_title, (fortune_setup_box.centerx - _title.get_width() // 2, fortune_setup_box.y + 20))
                _hint = f_fortune_small.render("Card rule keywords collected from highlighted terms", True, (206, 238, 248))
                screen.blit(_hint, (fortune_setup_box.centerx - _hint.get_width() // 2, fortune_setup_box.y + 82))
                _panel = pygame.Rect(fortune_setup_box.x + 40, fortune_setup_box.y + 120, fortune_setup_box.w - 80, fortune_setup_box.h - 230)
                _blit_alpha_round_rect(screen, _panel, (20, 18, 30, 96), 12)
                pygame.draw.rect(screen, _cyan_edge, _panel, 2, 12)
                _cols = 4
                _row_h = 44
                _col_gap = 14
                _row_gap = 10
                _glossary_rows = max(1, math.ceil(len(fortune_glossary_terms) / _cols))
                _content_h = (_glossary_rows * _row_h) + max(0, (_glossary_rows - 1) * _row_gap)
                _clip, _sb_track_rect, _sb_handle_rect, _glossary_max_scroll_draw = _fantasy_scrollbar_geometry(_panel, _content_h, fortune_glossary_scroll)
                _item_w = (_clip.w - ((_cols - 1) * _col_gap)) // _cols
                _clip_prev = screen.get_clip()
                screen.set_clip(_clip)
                for _i, _term in enumerate(fortune_glossary_terms):
                    _col = _i % _cols
                    _row = _i // _cols
                    _rx = _clip.x + _col * (_item_w + _col_gap)
                    _ry = _clip.y + 2 + (_row * (_row_h + _row_gap)) - fortune_glossary_scroll
                    _rr = pygame.Rect(_rx, _ry, _item_w, _row_h)
                    if _rr.bottom < _clip.y or _rr.top > _clip.bottom:
                        continue
                    _hover = _rr.collidepoint(m_pos)
                    draw_round_rect(screen, _rr, (28, 26, 40, 220) if _hover else (24, 20, 34, 210), 8)
                    pygame.draw.rect(screen, (102, 220, 255, 130), _rr, 1, 8)
                    _txt = f_fortune_small.render(_term, True, (214, 246, 255))
                    if _txt.get_width() > _rr.w - 20:
                        _term_draw = _term
                        while len(_term_draw) > 4 and f_fortune_small.size(_term_draw + "...")[0] > _rr.w - 20:
                            _term_draw = _term_draw[:-1]
                        _txt = f_fortune_small.render(_term_draw + "...", True, (214, 246, 255))
                    screen.blit(_txt, (_rr.centerx - _txt.get_width() // 2, _rr.centery - _txt.get_height() // 2))
                screen.set_clip(_clip_prev)
                if _glossary_max_scroll_draw > 0:
                    _draw_fantasy_scrollbar(screen, _sb_track_rect, _sb_handle_rect, _cyan_edge, _cyan_soft)
                fortune_view_back_btn.text = "Back to Library"
                fortune_view_back_btn.draw(screen, f_fortune_small, dt)
            
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
                undo_btn.draw(screen, f_tiny, dt)
                divine_intervention_btn.draw(screen, f_tiny, dt)
                redo_btn.draw(screen, f_tiny, dt)

                # 2. SEER DICE TABLE
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
                    dt_box = get_seer_dice_rect()
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
                line_y = 80 + normal_zone_y_offset + HAND_CARD_H + 95
                pygame.draw.line(screen, (255, 255, 255, 180), (PANEL_W + 60, line_y), (W - 60, line_y), 3)

                # 5. ZONE LABELS
                zone_x = PANEL_W + 60
                _hand_zone_box = pygame.Rect(zone_x, 33 + normal_zone_y_offset + 50, 170, 36)
                draw_round_rect(screen, _hand_zone_box, (10, 10, 10, 220), 8)
                pygame.draw.rect(screen, (230, 240, 255), _hand_zone_box, 1, 8)
                _hand_zone_s = f_hand_header.render("Hand Zone", True, (230,240,255))
                screen.blit(_hand_zone_s, (_hand_zone_box.x + 14, _hand_zone_box.centery - _hand_zone_s.get_height() // 2))
                if game.level >= 6:
                    draw_round_rect(screen, (zone_x, 38 + normal_zone_y_offset + HAND_GRID_SPACING_Y - 5, 200, 32), (20,25,40,200), 8)
                    pygame.draw.rect(screen, GOLD, (zone_x, 38 + normal_zone_y_offset + HAND_GRID_SPACING_Y - 5, 200, 32), 1, 8)
                    screen.blit(f_small.render("Fortune Card Zone", True, GOLD), (zone_x + 10, 38 + normal_zone_y_offset + HAND_GRID_SPACING_Y))
                if game.level >= 17:
                    mx = zone_x + HAND_GRID_SPACING_X
                    draw_round_rect(screen, (mx, 38 + normal_zone_y_offset + HAND_GRID_SPACING_Y - 5, 180, 32), (20,25,40,200), 8)
                    pygame.draw.rect(screen, (255,100,100), (mx, 38 + normal_zone_y_offset + HAND_GRID_SPACING_Y - 5, 180, 32), 1, 8)
                    screen.blit(f_small.render("Major Card Zone", True, (255,120,120)), (mx + 10, 38 + normal_zone_y_offset + HAND_GRID_SPACING_Y))
                library_btn.draw(screen, f_small, dt)
                if game.level >= 6:
                    past_present_future_btn.draw(screen, f_tiny, dt)
                if game.level >= 17:
                    fated_card_btn.draw(screen, f_small, dt)

                # 6. DRAW CARDS
                for p in card_fire_particles[:]: p.update(); (p.life <= 0 and card_fire_particles.remove(p))
                for zone, sy, sx in [(game.hand, 80 + normal_card_zone_y_offset, PANEL_W+60), (game.fortune_zone, 80 + normal_card_zone_y_offset + HAND_GRID_SPACING_Y + fortune_major_card_zone_y_offset, PANEL_W+60), (game.major_zone, 80 + normal_card_zone_y_offset + HAND_GRID_SPACING_Y + fortune_major_card_zone_y_offset, PANEL_W+60+HAND_GRID_SPACING_X)]:
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
                        _draw_rect = pygame.Rect(card_x, y, sw, HAND_CARD_H)
                        screen.blit(pygame.transform.smoothscale(content, (sw, HAND_CARD_H)), _draw_rect.topleft)
                        _stamp_mode = _get_selected_stamp_mode(h['id'])
                        if _stamp_mode and h['flip'] <= 0.01 and h['id'] not in game.vanished:
                            _draw_promotion_stamp(_draw_rect, _is_major=(_stamp_mode == "major"), _inverted=(h.get('orientation') == "inverted"))
                        if zone == game.fortune_zone:
                            draw_card_glitter(screen, _draw_rect, pygame.time.get_ticks() / 1000.0, "gold")
                        elif zone == game.major_zone:
                            draw_card_glitter(screen, _draw_rect, pygame.time.get_ticks() / 1000.0, "red")
                        
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

                # 6. DECK & VANISHED PILE
                _pile_w, _pile_h = 210, 310
                _pile_y = H - 340
                vz_rect = pygame.Rect(W - 460, _pile_y, _pile_w, _pile_h)
                mz_rect = pygame.Rect(W - 240, _pile_y, _pile_w, _pile_h)
                _hist_sz = 150
                _rest_sz = 100
                _menu_sz = 100
                _btn_gap = 10
                # History button directly above deck
                history_btn.rect = pygame.Rect(mz_rect.x + (mz_rect.w - _hist_sz) // 2, mz_rect.y - _hist_sz - _btn_gap, _hist_sz, _hist_sz)
                history_btn.draw(screen, f_tiny, dt)
                # Settings menu back to top-right
                _controls_y = vz_rect.bottom - _rest_sz
                _controls_x = vz_rect.x - ((_rest_sz * 2) + _btn_gap)
                _top_icon_sz = 70
                _top_btn_w = 140
                _top_gap = 10
                hamburger_btn.rect = pygame.Rect(W - _top_icon_sz - 20, PADDING, _top_icon_sz, _top_icon_sz)
                load_btn.rect = pygame.Rect(hamburger_btn.rect.x - _top_gap - _top_btn_w, PADDING, _top_btn_w, _top_icon_sz)
                save_as_btn.rect = pygame.Rect(load_btn.rect.x - _top_gap - _top_btn_w, PADDING, _top_btn_w, _top_icon_sz)
                save_btn.rect = pygame.Rect(save_as_btn.rect.x - _top_gap - _top_btn_w, PADDING, _top_btn_w, _top_icon_sz)
                save_btn.draw(screen, f_tiny, dt)
                save_as_btn.draw(screen, f_tiny, dt)
                load_btn.draw(screen, f_tiny, dt)
                hamburger_btn.draw(screen, f_tiny, dt)
                if top_menu_open:
                    _menu_item_h = 70
                    _menu_gap = 4
                    _menu_pad = 8
                    _menu_count = 4
                    _menu_h = (_menu_pad * 2) + (_menu_count * _menu_item_h) + ((_menu_count - 1) * _menu_gap)
                    _menu_bg = pygame.Rect(hamburger_btn.rect.right - 160, hamburger_btn.rect.bottom + 13, 160, _menu_h)
                    draw_round_rect(screen, _menu_bg, (18, 24, 38, 230), 10)
                    pygame.draw.rect(screen, (255, 255, 255, 40), _menu_bg, 1, 10)
                    _menu_item_w = _menu_bg.w - 20
                    menu_btn.rect = pygame.Rect(_menu_bg.x + 10, _menu_bg.y + _menu_pad, _menu_item_w, _menu_item_h)
                    normal_settings_btn.rect = pygame.Rect(_menu_bg.x + 10, menu_btn.rect.bottom + _menu_gap, _menu_item_w, _menu_item_h)
                    quit_btn.rect = pygame.Rect(_menu_bg.x + 10, normal_settings_btn.rect.bottom + _menu_gap, _menu_item_w, _menu_item_h)
                    menu_btn.draw(screen, f_tiny, dt)
                    normal_settings_btn.draw(screen, f_tiny, dt)
                    quit_btn.draw(screen, f_tiny, dt)
                rest_menu_btn.rect = pygame.Rect(_controls_x + _menu_sz + _btn_gap, _controls_y, _rest_sz, _rest_sz)
                _day_box = pygame.Rect(rest_menu_btn.rect.x - 10, rest_menu_btn.rect.y - 58, 120, 42)
                _current_day = int(clamp(game.days_passed + 1, 1, 7))
                draw_round_rect(screen, _day_box, (22, 18, 34, 235), 10)
                pygame.draw.rect(screen, (212, 168, 96), _day_box, 1, 10)
                _day_text = f_small.render(f"Day {_current_day} of 7", True, (248, 231, 199))
                screen.blit(_day_text, (_day_box.centerx - _day_text.get_width() // 2, _day_box.centery - _day_text.get_height() // 2))
                rest_menu_btn.draw(screen, f_tiny, dt)
                if rest_menu_open:
                    _rm_x = rest_menu_btn.rect.x
                    _rm_item_h = 35
                    _rm_gap = 5
                    _rm_pad = 5
                    _rm_count = 1 + (1 if game.level >= 2 else 0) + (1 if game.level >= 17 else 0)
                    _rm_h = (_rm_pad * 2) + (_rm_count * _rm_item_h) + ((_rm_count - 1) * _rm_gap)
                    _rm_y = rest_menu_btn.rect.y - _rm_h - 5
                    _rm_bg = pygame.Rect(_rm_x, _rm_y, _rest_sz, _rm_h)
                    draw_round_rect(screen, _rm_bg, (18, 24, 38, 235), 10)
                    pygame.draw.rect(screen, GOLD, _rm_bg, 1, 10)
                    _btn_w = _rest_sz - 10
                    _cur_y = _rm_y + _rm_pad
                    if game.level >= 2:
                        short_rest_btn.rect = pygame.Rect(_rm_x + 5, _cur_y, _btn_w, _rm_item_h)
                        short_rest_btn.draw(screen, f_tiny, dt)
                        _cur_y += _rm_item_h + _rm_gap
                    rest_btn.rect = pygame.Rect(_rm_x + 5, _cur_y, _btn_w, _rm_item_h)
                    rest_btn.draw(screen, f_tiny, dt)
                    _cur_y += _rm_item_h + _rm_gap
                    if game.level >= 17:
                        reset_major_btn.rect = pygame.Rect(_rm_x + 5, _cur_y, _btn_w, _rm_item_h)
                        reset_major_btn.draw(screen, f_tiny, dt)
                
                screen.blit(vanish_pile_frame, vz_rect.topleft)
                screen.blit(deck_pile_frame, mz_rect.topleft)
                _vz_lbl = f_small.render("Vanished Pile", True, GOLD)
                _mz_lbl = f_small.render("Main Deck", True, GOLD)
                _title_h = 30
                _vz_title_box = pygame.Rect(vz_rect.x + 10, vz_rect.y + 12, vz_rect.w - 20, _title_h)
                _mz_title_box = pygame.Rect(mz_rect.x + 10, mz_rect.y + 12, mz_rect.w - 20, _title_h)
                draw_round_rect(screen, _vz_title_box, (0, 0, 0, 165), 8)
                draw_round_rect(screen, _mz_title_box, (0, 0, 0, 165), 8)
                screen.blit(_vz_lbl, (_vz_title_box.centerx - _vz_lbl.get_width() // 2, _vz_title_box.centery - _vz_lbl.get_height() // 2))
                screen.blit(_mz_lbl, (_mz_title_box.centerx - _mz_lbl.get_width() // 2, _mz_title_box.centery - _mz_lbl.get_height() // 2))

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

            elif screen_mode == "greedy_pot_popup":
                background = greedy_pot_state.get("background")
                if background is not None:
                    screen.blit(background, (0, 0))
                else:
                    screen.fill((8, 6, 18))
                overlay = pygame.Surface((W, H), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 120))
                screen.blit(overlay, (0, 0))
                if greedy_pot_state["frames"]:
                    frame_surface = greedy_pot_state["frames"][min(greedy_pot_state["frame_index"], len(greedy_pot_state["frames"]) - 1)]
                    fw, fh = frame_surface.get_size()
                    max_w = int(W * 0.46)
                    max_h = int(H * 0.46)
                    scale = min(max_w / fw, max_h / fh, 1.0)
                    dw, dh = max(1, int(fw * scale)), max(1, int(fh * scale))
                    gif_frame = pygame.transform.smoothscale(frame_surface, (dw, dh))
                    screen.blit(gif_frame, ((W - dw) // 2, (H - dh) // 2))

            elif screen_mode in ["deck", "vanish_view", "world_restore_view", "prophet_selection", "ppf_selection", "stack_selection", "major_selection"]:
                # Render looping video background for prophet_selection and deck
                _active_bg = None
                if screen_mode in ("prophet_selection", "ppf_selection"): _active_bg = prophet_bg_video
                elif screen_mode == "deck": _active_bg = deck_bg_video
                elif screen_mode == "vanish_view": _active_bg = vanished_bg_video
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
                if screen_mode == "ppf_selection": cur_list = [c for c in game.ids if c in game.get_allowed_fortune_ids() and c not in MAJOR_FORTUNE_IDS and c not in game.vanished and c not in hi and c not in fi]
                elif screen_mode == "world_restore_view": cur_list = [vid for vid in game.vanished if vid != 20]
                elif screen_mode == "deck": cur_list = game.deck
                elif screen_mode == "vanish_view": cur_list = game.vanished
                elif screen_mode == "prophet_selection": cur_list = [c for c in game.ids if c != 20 and c not in hi and c not in fi]
                elif screen_mode == "stack_selection": cur_list = [c for c in game.deck if c != 20]
                elif screen_mode == "major_selection": cur_list = [c for c in MAJOR_FORTUNE_IDS if c == game.get_allowed_major_id() and c not in game.vanished and c not in hi and c not in fi]
                
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
                    if -VIEW_CARD_H < gy < H:
                        screen.blit(v_face_view if screen_mode=="vanish_view" else view_tex[cid], (gx, gy))
                        if screen_mode != "vanish_view":
                            _stamp_mode = _get_selected_stamp_mode(cid)
                            if _stamp_mode:
                                _draw_promotion_stamp(pygame.Rect(gx, gy, VIEW_CARD_W, VIEW_CARD_H), _is_major=(_stamp_mode == "major"), _inverted=False)
                        if screen_mode == "vanish_view":
                            name = game.cards[cid]["name"]
                            name_font = pygame.font.SysFont("timesnewroman", 18, bold=True)
                            name_surf = name_font.render(name, True, (255,255,255))
                            name_rect = name_surf.get_rect(center=(gx+VIEW_CARD_W//2, gy+VIEW_CARD_H+16))
                            screen.blit(name_surf, name_rect)
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

            if current_roll_anim:
                current_roll_anim.draw(screen, f_seer_dice_sim, f_seer_massive)
            if divine_roll_anim:
                divine_roll_anim.draw(screen, f_seer_dice_sim, f_seer_massive)

            if confirm_dialog is not None:
                _ov = pygame.Surface((W, H), pygame.SRCALPHA)
                _ov.fill((0, 0, 0, 150))
                screen.blit(_ov, (0, 0))
                _outer = confirm_box_rect.inflate(16, 18)
                draw_round_rect(screen, _outer, (36, 20, 12, 230), 24)
                pygame.draw.rect(screen, (120, 86, 42, 220), _outer, 3, 24)
                draw_round_rect(screen, confirm_box_rect, (18, 14, 24, 240), 20)
                pygame.draw.rect(screen, (235, 190, 60, 180), confirm_box_rect, 2, 20)
                _ct = f_preview_title.render(str(confirm_dialog.get("title", "Confirm")), True, GOLD)
                screen.blit(_ct, (_outer.centerx - _ct.get_width() // 2, confirm_box_rect.y + 20))
                _msg = str(confirm_dialog.get("message", "Are you sure?"))
                _words = _msg.split()
                _lines = []
                _cur = ""
                _max_w = confirm_box_rect.w - 60
                for _w in _words:
                    _test = f"{_cur} {_w}".strip()
                    if not _cur or f_small.size(_test)[0] <= _max_w:
                        _cur = _test
                    else:
                        _lines.append(_cur)
                        _cur = _w
                if _cur:
                    _lines.append(_cur)
                _yy = confirm_box_rect.y + 82
                for _line in _lines[:3]:
                    _ls = f_small.render(_line, True, (225, 206, 170))
                    screen.blit(_ls, (confirm_box_rect.centerx - _ls.get_width() // 2, _yy))
                    _yy += _ls.get_height() + 8
                confirm_yes_btn.draw(screen, f_small, dt)
                confirm_no_btn.draw(screen, f_small, dt)

            if game.toast_timer > 0:
                t_surf = f_small.render(game.toast_msg, True, (255,255,255))
                pygame.draw.rect(screen, (0,0,0,180), (W//2-200, 20, 400, 40), border_radius=10)
                screen.blit(t_surf, t_surf.get_rect(center=(W//2, 40)))
            
            pygame.display.flip()

    except Exception: log_event(traceback.format_exc(), True); pygame.quit(); sys.exit()
