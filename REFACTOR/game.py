try:
    from .core import *
except ImportError:
    from core import *

# ----------------------------
# 7. GAME CONTROLLER
# ----------------------------

FORTUNE_LOADOUT_SLOT_COUNT = 10

class Game:
    def __init__(self, cards_data):
        self.cards = {c['id']: c for c in cards_data}; self.ids = [c['id'] for c in cards_data]
        self.deck, self.hand, self.fortune_zone, self.major_zone, self.vanished, self.history, self.redo_history = [], [], [], [], [], [], []
        self.stacked, self.first_three_ids, self.seer_dice_table = None, [], []
        self.days_until_major, self.days_passed, self.shuffle_time, self.history_log, self.fizzles = 0, 0, 0.0, [], []
        self.toast_msg, self.toast_timer, self.level, self.used_major_ids = "", 0.0, 1, []
        self.hand_limit, self.ppf_charges, self.draw_queue, self.draw_timer, self.is_drawing = 1, 3, [], 0.0, False
        self.major_fortune_used_this_week, self.shuffle_anim_timer = False, 0.0
        self.major_fortune_activation_pending = False
        self.divine_intervention_used_this_week = False
        self.divine_intervention_failed_until_long_rest = False
        self.seer_slots_filled_today = 0
        self.draw_of_fate_uses = 0
        self.draw_of_fate_current = 0
        self.audio_enabled = True
        self.sfx_enabled = True
        self.sfx_channel = None
        self.fortune_loadouts = [
            {"name": f"Loadout {i + 1}", "fortune_ids": [], "major_id": None}
            for i in range(FORTUNE_LOADOUT_SLOT_COUNT)
        ]
        self.active_fortune_loadout = 0
        self.rebuild_deck(); self.shuffle_deck(play_sound=False)
        self.draw_of_fate_uses = self.get_draw_of_fate_uses_by_level()
        self.draw_of_fate_current = self.draw_of_fate_uses

    def get_base_limit(self): return 3 if self.level >= 12 else (2 if self.level >= 6 else 1)
    def get_fortune_option_cap(self):
        if self.level >= 17:
            return 9
        if self.level >= 13:
            return 7
        if self.level >= 9:
            return 5
        if self.level >= 6:
            return 3
        return 0
    def get_unlocked_fortune_ids(self):
        unlocked = []
        for lvl, ids in sorted(FORTUNE_UNLOCKS.items()):
            if self.level >= lvl:
                unlocked.extend(ids)
        ordered = []
        for cid in unlocked:
            if cid not in ordered:
                ordered.append(cid)
        return ordered
    def get_unlocked_major_ids(self):
        return list(MAJOR_UNLOCKS_17) if self.level >= 17 else []
    def normalize_fortune_loadouts(self):
        all_fortune = []
        for _ids in FORTUNE_UNLOCKS.values():
            for _cid in _ids:
                if _cid not in all_fortune:
                    all_fortune.append(_cid)
        all_fortune = set(all_fortune)
        all_major = set(MAJOR_UNLOCKS_17)
        while len(self.fortune_loadouts) < FORTUNE_LOADOUT_SLOT_COUNT:
            self.fortune_loadouts.append({"name": f"Loadout {len(self.fortune_loadouts) + 1}", "fortune_ids": [], "major_id": None})
        self.fortune_loadouts = self.fortune_loadouts[:FORTUNE_LOADOUT_SLOT_COUNT]
        for i, ld in enumerate(self.fortune_loadouts):
            if not isinstance(ld, dict):
                self.fortune_loadouts[i] = {"name": f"Loadout {i + 1}", "fortune_ids": [], "major_id": None}
                continue
            fortune_ids = []
            for cid in ld.get("fortune_ids", []):
                try:
                    cid = int(cid)
                except Exception:
                    continue
                if cid in all_fortune:
                    fortune_ids.append(cid)
            deduped = []
            for cid in fortune_ids:
                if cid not in deduped:
                    deduped.append(cid)
            ld["fortune_ids"] = deduped
            major_id = ld.get("major_id")
            try:
                major_id = int(major_id) if major_id is not None else None
            except Exception:
                major_id = None
            ld["major_id"] = major_id if major_id in all_major else None
            if not ld.get("name"):
                ld["name"] = f"Loadout {i + 1}"
        self.active_fortune_loadout = int(clamp(self.active_fortune_loadout, 0, len(self.fortune_loadouts) - 1))
    def get_active_fortune_loadout(self):
        self.normalize_fortune_loadouts()
        return self.fortune_loadouts[self.active_fortune_loadout]
    def get_allowed_fortune_ids(self):
        if self.level < 6:
            return []
        unlocked = set(self.get_unlocked_fortune_ids())
        cap = self.get_fortune_option_cap()
        allowed = []
        for cid in self.get_active_fortune_loadout().get("fortune_ids", []):
            if cid in unlocked and cid not in allowed:
                allowed.append(cid)
            if len(allowed) >= cap:
                break
        return allowed
    def get_allowed_major_id(self):
        if self.level < 17:
            return None
        major_id = self.get_active_fortune_loadout().get("major_id")
        return major_id if major_id in MAJOR_UNLOCKS_17 else None
    def can_promote_card(self, card_id, to_major=False):
        if to_major:
            return self.level >= 17 and (not self.major_fortune_used_this_week) and card_id == self.get_allowed_major_id()
        return self.level >= 6 and card_id in self.get_allowed_fortune_ids()
    def is_card_promotion_enabled(self, card_id):
        return self.can_promote_card(card_id, to_major=False) or self.can_promote_card(card_id, to_major=True)
    def enforce_fortune_selection(self, add_history_entry=True):
        allowed_fortune = set(self.get_allowed_fortune_ids())
        allowed_major = self.get_allowed_major_id()
        moved = []
        for h in self.fortune_zone[:]:
            if h.get("id") not in allowed_fortune:
                self.fortune_zone.remove(h)
                h["mode"] = "normal"
                h["ppf_added"] = False
                self.hand.append(h)
                moved.append(h.get("id"))
        for h in self.major_zone[:]:
            if h.get("id") != allowed_major:
                self.major_zone.remove(h)
                h["mode"] = "normal"
                h["major_added"] = False
                self.hand.append(h)
                moved.append(h.get("id"))
        if moved and add_history_entry:
            self.add_history("Fortune setup changed: ineligible promoted cards returned to Hand.", moved)
        if moved:
            self.rebuild_deck()
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
        
    def _build_state_snapshot(self):
        return {"deck": list(self.deck), "hand": [copy.deepcopy(h) for h in self.hand], "fortune_zone": [copy.deepcopy(f) for f in self.fortune_zone], "major_zone": [copy.deepcopy(f) for f in self.major_zone], "vanished": list(self.vanished), "stacked": self.stacked, "f3": list(self.first_three_ids), "cd": self.days_until_major, "days": self.days_passed, "limit": self.hand_limit, "table": list(self.seer_dice_table), "history": [copy.copy(e) for e in self.history_log], "level": self.level, "ppf": self.ppf_charges, "used_major": list(self.used_major_ids), "major_cooldown": self.major_fortune_used_this_week, "major_pending": self.major_fortune_activation_pending, "divine_weekly": self.divine_intervention_used_this_week, "divine_rest": self.divine_intervention_failed_until_long_rest, "seer_filled": self.seer_slots_filled_today, "draw_of_fate": self.draw_of_fate_uses, "draw_of_fate_cur": self.draw_of_fate_current, "fortune_loadouts": copy.deepcopy(self.fortune_loadouts), "active_fortune_loadout": self.active_fortune_loadout}

    def _apply_state_snapshot(self, s):
        self.deck, self.hand, self.fortune_zone, self.major_zone, self.vanished, self.stacked, self.first_three_ids, self.days_until_major, self.days_passed, self.hand_limit, self.seer_dice_table, self.history_log, self.level, self.ppf_charges, self.used_major_ids, self.major_fortune_used_this_week, self.major_fortune_activation_pending, self.divine_intervention_used_this_week, self.divine_intervention_failed_until_long_rest, self.seer_slots_filled_today, self.draw_of_fate_uses, self.draw_of_fate_current = s["deck"], s["hand"], s.get("fortune_zone", []), s.get("major_zone", []), s["vanished"], s["stacked"], s["f3"], s["cd"], s["days"], s["limit"], s["table"], s.get("history", []), s.get("level", 1), s.get("ppf", 3), s.get("used_major", []), s.get("major_cooldown", False), s.get("major_pending", False), s.get("divine_weekly", False), s.get("divine_rest", False), s.get("seer_filled", 0), s.get("draw_of_fate", 0), s.get("draw_of_fate_cur", 0)
        self.fortune_loadouts = copy.deepcopy(s.get("fortune_loadouts", self.fortune_loadouts))
        self.active_fortune_loadout = s.get("active_fortune_loadout", self.active_fortune_loadout)
        self.normalize_fortune_loadouts()

    def save_state(self): 
        self.history.append(self._build_state_snapshot())
        self.redo_history = []
        if len(self.history) > 50: self.history.pop(0)
        
    def undo(self):
        if not self.history: return
        self.redo_history.append(self._build_state_snapshot())
        if len(self.redo_history) > 50: self.redo_history.pop(0)
        s = self.history.pop(); self._apply_state_snapshot(s)
        # Flush transient animation queues to stop them from resolving post-undo
        self.draw_queue = []
        self.is_drawing = False
        self.fizzles = []
        self.shuffle_anim_timer = 0.0
        self.add_history("Undo: Reverted to previous state.")

    def redo(self):
        if not self.redo_history: return
        self.history.append(self._build_state_snapshot())
        if len(self.history) > 50: self.history.pop(0)
        s = self.redo_history.pop()
        self._apply_state_snapshot(s)
        self.draw_queue = []
        self.is_drawing = False
        self.fizzles = []
        self.shuffle_anim_timer = 0.0
        self.add_history("Redo: Reapplied undone state.")

    def to_save_payload(self):
        return {
            "deck": list(self.deck),
            "hand": [copy.deepcopy(h) for h in self.hand],
            "fortune_zone": [copy.deepcopy(f) for f in self.fortune_zone],
            "major_zone": [copy.deepcopy(f) for f in self.major_zone],
            "vanished": list(self.vanished),
            "stacked": self.stacked,
            "first_three_ids": list(self.first_three_ids),
            "seer_dice_table": list(self.seer_dice_table),
            "days_until_major": self.days_until_major,
            "days_passed": self.days_passed,
            "shuffle_time": self.shuffle_time,
            "history_log": [copy.deepcopy(e) for e in self.history_log],
            "history": [copy.deepcopy(h) for h in self.history],
            "redo_history": [copy.deepcopy(h) for h in self.redo_history],
            "toast_msg": self.toast_msg,
            "toast_timer": self.toast_timer,
            "level": self.level,
            "used_major_ids": list(self.used_major_ids),
            "hand_limit": self.hand_limit,
            "ppf_charges": self.ppf_charges,
            "draw_queue": list(self.draw_queue),
            "draw_timer": self.draw_timer,
            "is_drawing": self.is_drawing,
            "major_fortune_used_this_week": self.major_fortune_used_this_week,
            "major_fortune_activation_pending": self.major_fortune_activation_pending,
            "divine_intervention_used_this_week": self.divine_intervention_used_this_week,
            "divine_intervention_failed_until_long_rest": self.divine_intervention_failed_until_long_rest,
            "shuffle_anim_timer": self.shuffle_anim_timer,
            "seer_slots_filled_today": self.seer_slots_filled_today,
            "draw_of_fate_uses": self.draw_of_fate_uses,
            "draw_of_fate_current": self.draw_of_fate_current,
            "fortune_loadouts": copy.deepcopy(self.fortune_loadouts),
            "active_fortune_loadout": self.active_fortune_loadout
        }

    def load_from_payload(self, payload):
        self.deck = list(payload.get("deck", []))
        self.hand = [copy.deepcopy(h) for h in payload.get("hand", [])]
        self.fortune_zone = [copy.deepcopy(f) for f in payload.get("fortune_zone", [])]
        self.major_zone = [copy.deepcopy(f) for f in payload.get("major_zone", [])]
        self.vanished = list(payload.get("vanished", []))
        self.stacked = payload.get("stacked")
        self.first_three_ids = list(payload.get("first_three_ids", []))
        self.seer_dice_table = list(payload.get("seer_dice_table", []))
        self.days_until_major = payload.get("days_until_major", 0)
        self.days_passed = payload.get("days_passed", 0)
        self.shuffle_time = payload.get("shuffle_time", 0.0)
        self.history_log = [copy.deepcopy(e) for e in payload.get("history_log", [])]
        self.history = [copy.deepcopy(h) for h in payload.get("history", [])]
        self.redo_history = [copy.deepcopy(h) for h in payload.get("redo_history", [])]
        self.toast_msg = payload.get("toast_msg", "")
        self.toast_timer = payload.get("toast_timer", 0.0)
        self.level = payload.get("level", 1)
        self.used_major_ids = list(payload.get("used_major_ids", []))
        self.hand_limit = payload.get("hand_limit", self.get_base_limit())
        self.ppf_charges = payload.get("ppf_charges", 3)
        self.draw_queue = list(payload.get("draw_queue", []))
        self.draw_timer = payload.get("draw_timer", 0.0)
        self.is_drawing = bool(payload.get("is_drawing", False))
        self.major_fortune_used_this_week = bool(payload.get("major_fortune_used_this_week", False))
        self.major_fortune_activation_pending = bool(payload.get("major_fortune_activation_pending", False))
        self.divine_intervention_used_this_week = bool(payload.get("divine_intervention_used_this_week", False))
        self.divine_intervention_failed_until_long_rest = bool(payload.get("divine_intervention_failed_until_long_rest", False))
        self.shuffle_anim_timer = payload.get("shuffle_anim_timer", 0.0)
        self.seer_slots_filled_today = payload.get("seer_slots_filled_today", 0)
        self.draw_of_fate_uses = payload.get("draw_of_fate_uses", self.get_draw_of_fate_uses_by_level())
        self.draw_of_fate_current = payload.get("draw_of_fate_current", self.draw_of_fate_uses)
        self.fortune_loadouts = copy.deepcopy(payload.get("fortune_loadouts", self.fortune_loadouts))
        self.active_fortune_loadout = payload.get("active_fortune_loadout", self.active_fortune_loadout)
        self.normalize_fortune_loadouts()
        self.enforce_fortune_selection(add_history_entry=False)

    def rebuild_deck(self):
        possessed_ids = [h['id'] for h in (self.hand + self.fortune_zone + self.major_zone)]
        self.deck = [cid for cid in self.ids if cid not in possessed_ids and cid not in self.vanished]

    def shuffle_deck(self, play_sound=True, trigger_anim=True):
        random.shuffle(self.deck)
        self.stacked = None 
        if trigger_anim: self.shuffle_anim_timer = SHUFFLE_ANIM_DURATION
        if play_sound and self.audio_enabled and self.sfx_enabled: 
            try:
                s = pygame.mixer.Sound(SHUFFLE_SOUND)
                if self.sfx_channel is not None:
                    if not self.sfx_channel.get_busy():
                        self.sfx_channel.play(s)
                else:
                    s.play()
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
        self.draw_of_fate_current = self.draw_of_fate_uses
        self.divine_intervention_failed_until_long_rest = False
        self.vanished = []
        self.rebuild_deck()
        if self.days_passed >= 7:
            self.days_passed = 0
            self.major_fortune_used_this_week = False
            self.major_fortune_activation_pending = False
            self.divine_intervention_used_this_week = False
        self.shuffle_deck()
        self.add_history(f"Long Rest (Day {self.days_passed}): Hand returned to deck. Deck shuffled.")
        if not skip_draw: self.initiate_bulk_draw(self.hand_limit)
        return self.hand_limit

    def reset_for_level_change(self, skip_draw=False):
        self.save_state()
        for h in (self.hand + self.fortune_zone + self.major_zone):
            if h['id'] not in self.vanished and h['id'] not in self.deck:
                self.deck.append(h['id'])
        self.hand = []
        self.fortune_zone = []
        self.major_zone = []
        self.stacked = None
        self.first_three_ids = []
        self.seer_dice_table = []
        self.seer_slots_filled_today = 0
        self.hand_limit = self.get_base_limit()
        self.draw_of_fate_uses = self.get_draw_of_fate_uses_by_level()
        self.draw_of_fate_current = self.draw_of_fate_uses
        self.rebuild_deck()
        self.shuffle_deck()
        self.add_history(f"Level changed to {self.level}: hand returned to deck. Deck shuffled.")
        if not skip_draw:
            self.initiate_bulk_draw(self.hand_limit)
        return self.hand_limit

    def short_rest(self):
        self.save_state()
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
        self.draw_queue, self.is_drawing = [], False
        self.shuffle_deck(play_sound=False, trigger_anim=False)

    def check_has_tapped_effect(self, card_dict):
        """Helper to cleanly evaluate if a given card dictionary possesses a tapped effect based on its mode and orientation."""
        cd = self.cards[card_dict['id']]
        mode = card_dict['mode']
        ori = card_dict['orientation']
        if mode == 'normal': return cd.get(f'tapped_{ori}', False)
        if mode == 'fortune': return cd.get(f'tapped_fortune_{ori}', False)
        if mode == 'major': return cd.get(f'tapped_major_{ori}', False)
        return False
