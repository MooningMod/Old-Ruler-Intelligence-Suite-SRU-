import sys
import ctypes
from pathlib import Path
mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "SRU_OVERLAY_MUTEX")

from PyQt5.QtCore import Qt, QRect, QTimer
from PyQt5.QtGui import QPainter, QColor, QFont
from PyQt5.QtWidgets import QWidget, QApplication

# Import official effect logic from your updated tech_effects.py
from tech_effects import EFFECT_MAP as CORE_EFFECT_MAP, BOOL_EFFECT_MAP

try:
    import pymem
    import pymem.process
except ImportError:
    pymem = None
    print("[Memory] WARNING: pymem is not installed. Selected unit reading is disabled.")

from unit_parser import parse_default_unit, Unit, load_range_database
from tech_parser import load_tech_file
# UPDATED IMPORT
from painters import draw_unit_list, draw_comparison_table
from events import handle_mouse_press, handle_wheel

# =============================================================================
# TECH LABEL MAP (UPDATED TO OFFICIAL DOCS)
# =============================================================================
TECH_LABEL_MAP = {
    # --- Attack Values ---
    140: "Soft Attack", 
    141: "Hard Attack", 
    142: "Fortification Att.",
    143: "Low Air Attack", 
    144: "Mid Air Attack", 
    145: "High Air Attack",
    146: "Naval Surface Att.", 
    147: "Submarine Att.",     
    148: "Close Combat",

    # --- Ranges ---
    150: "Ground Range", 
    151: "Air Range", 
    152: "Naval Range", 
    153: "Sub Range",

    # --- Defense ---
    154: "Ground Defense", 
    155: "Tactical Air Defense", 
    156: "Indirect Def (Art)", 
    157: "Close Defense",

    # --- Specs ---
    158: "Speed (km/h)", 
    159: "Stealth Rating", 
    160: "Initiative", 
    161: "Combat Time (Ammo)",

    # --- Logistics ---
    162: "Fuel Consumption",  # 1.0 = +100% consumo (negativo)
    163: "Missile Capacity", 
    164: "Unit Efficiency",   # Morale/Quality base
    165: "Ammo Capacity",
    166: "Fuel Tank Size",     # Capacità serbatoio

    # --- Spotting ---
    167: "Spotting Range (Vis)", 
    168: "Spotting Range (Rad)",
    169: "Spotting Str (Vis)",    
    170: "Spotting Str (Rad)",
}

class OverlayINS(QWidget):

    # ORIGINAL offset for in-game selected unit
    SELECTED_UNIT_OFFSET = 0x1038358

    # NEW offset: selected blueprint
    BLUEPRINT_OFFSET = 0x1036F40

    def __init__(self, 
                 default_unit_path: str | None = None, 
                 default_ttrx_path: str | None = None,
                 default_spotting_path: str | None = None,
                 range_database_path: str | None = None):
        super().__init__()

        # --------------------------
        # NEW STATE TRACKING
        # --------------------------
        self.last_unit_id = None
        self.last_blueprint_id = None
        # --------------------------

        # --- Tech Impact Scrollbar State ---
        self.techimpact_dragging = False
        self.techimpact_drag_offset = 0

        self.units: list[Unit] = []
        self.filtered_units: list[Unit] = []
        self.tech_unlocks: dict[int, list[Unit]] = {}

        self.selected_unit_b = None
        self.selected_unit_c = None
        self.selected_unit_d = None

        self.tech_light = {}
        self.tech_full = {}

        self.active_techs = {"b": set(), "c": set(), "d": set()}
        self.tech_checkbox_rects = {"b": {}, "c": {}, "d": {}}

        self.lock_b = False
        self.btn_lock_rect = QRect()
        self.btn_b_to_c_rect = QRect()
        self.btn_c_to_d_rect = QRect()

        self.search_query = ""
        self.selected_category = "all"
        self.focus_search = False

        self.line_height = 22
        self.unit_scroll_offset = 0
        self.stats_scroll_offset = 0
        self.max_stats_scroll = 0

        self.close_btn_rect = QRect()
        self.unit_list_rect = QRect()
        self.search_rect = QRect()
        self.stats_rect = QRect()
        self.category_button_rects = []

        self.view_mode = "compare"
        self.selected_tech_for_impact = None
        self.tab_compare_rect = QRect()
        self.tab_tech_rect = QRect()

        self.tech_search = ""
        self.tech_search_focus = False
        self.tech_search_results = []
        self.tech_search_max_display = 6
        self.tech_search_rect = QRect()
        self.tech_search_result_rects = []

        self.impact_unit_search = ""
        self.focus_impact_unit_search = False
        self.impact_unit_search_rect = QRect()

        self.techimpact_unit_rects = {}
        self.techimpact_scroll_offset = 0
        self.techimpact_max_scroll = 0

        self.techimpact_scrollbar_track_rect = QRect()
        self.techimpact_scrollbar_handle_rect = QRect()

        self.menu_visible = False
        self.key_was_pressed = False

        self.pm = None
        self.base_addr = None
        self.last_raw_selected_id = None

        # INIT WINDOW
        self.init_window()

        # Loaders
        self.load_range_database(range_database_path)
        self.load_units(default_unit_path)
        self.load_techs(default_ttrx_path)

        self._calculate_tech_unlocks()
        self.update_filter()
        self._attach_process()

        # TIMER
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.game_loop)
        self.timer.start(30)
    
        
    # =========================================================================
    # NEW — READ BLUEPRINT
    # =========================================================================
    def _read_blueprint_id(self) -> int | None:
        if pymem is None:
            return None
        if not self.pm or not self.base_addr:
            self._attach_process()
            if not self.pm:
                return None

        try:
            addr = self.base_addr + self.BLUEPRINT_OFFSET
            val = self.pm.read_int(addr)
            if val > 0:
                return val
            return None
        except:
            return None


    # =========================================================================
    # NEW — HANDLE BLUEPRINT CHANGE
    # =========================================================================
    def _on_blueprint_selected(self, bp_id: int):
        unit = self._get_unit_by_id(bp_id)
        if not unit:
            return

        if self.selected_unit_b and self.selected_unit_b.id != bp_id:
            self.selected_unit_c = self.selected_unit_b

        if not self.lock_b:
            self.selected_unit_b = unit

        print(f"[Overlay] Blueprint selected → {bp_id}")
        self.update()


    # =========================================================================
    # NEW — HANDLE UNIT CHANGE
    # =========================================================================
    def _on_unit_selected(self, unit_id: int):
        unit = self._get_unit_by_id(unit_id)
        if not unit:
            return

        if self.selected_unit_b and self.selected_unit_b.id != unit_id:
            self.selected_unit_c = self.selected_unit_b

        if not self.lock_b:
            self.selected_unit_b = unit

        print(f"[Overlay] Unit selected → {unit_id}")
        self.update()

    def _attach_process(self):
        if pymem is None:
            return
        try:
            self.pm = pymem.Pymem("SupremeRulerUltimate.exe")
            mod = pymem.process.module_from_name(self.pm.process_handle,
                                                 "SupremeRulerUltimate.exe")
            self.base_addr = mod.lpBaseOfDll
            print(f"[Memory] Attached to SRU, base = {hex(self.base_addr)}")
        except Exception:
            self.pm = None
            self.base_addr = None

    def _read_selected_unit_raw(self) -> int | None:
        if pymem is None:
            return None

        if not self.pm or not self.base_addr:
            self._attach_process()
            if not self.pm:
                return None

        try:
            addr = self.base_addr + self.SELECTED_UNIT_OFFSET
            val = self.pm.read_int(addr)
            self.last_raw_selected_id = val

            if val <= 0:
                return None

            return val

        except Exception:
            # Reset pm on failure
            self.pm = None
            self.base_addr = None
            return None

    def _read_selected_unit_obj(self):
        uid = self._read_selected_unit_raw()
        if uid is None:
            return None

        for u in self.units:
            if u.id == uid:
                return u
        return None
        

    # =========================================================================
    # UPDATED GAME LOOP
    # =========================================================================
    def game_loop(self):
        # Handle INS toggling
        try:
            pressed = (ctypes.windll.user32.GetAsyncKeyState(0x2D) & 0x8000)
            if pressed:
                if not self.key_was_pressed:
                    self.toggle_menu()
                    self.key_was_pressed = True
            else:
                self.key_was_pressed = False
        except Exception:
            pass

        if not self.menu_visible:
            return

        # --- CHECK SELECTED UNIT ---
        new_uid = self._read_selected_unit_raw()
        if new_uid and new_uid != self.last_unit_id:
            self.last_unit_id = new_uid
            self._on_unit_selected(new_uid)

        # --- CHECK SELECTED BLUEPRINT ---
        new_bp = self._read_blueprint_id()
        if new_bp and new_bp != self.last_blueprint_id:
            self.last_blueprint_id = new_bp
            self._on_blueprint_selected(new_bp)        
 

    # ------------------------------------------------------------- Init / load
    def init_window(self):
        screen = QApplication.primaryScreen()
        g = screen.geometry() if screen else QRect(0, 0, 1920, 1080)
        self.setGeometry(g)
        self.setWindowTitle("Intelligence Division")

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.hide()

    def load_range_database(self, range_database_path: str | None):
        """Load unit range stats database from CSV (silent if not found)"""
        paths = []
        
        # User-specified path
        if range_database_path:
            paths.append(Path(range_database_path))
        
        # Same directory as overlay script/exe
        paths.append(Path(__file__).parent / "unit_rangestats_database.csv")
        
        # Current working directory (launcher location)
        paths.append(Path.cwd() / "unit_rangestats_database.csv")
        
        for p in paths:
            if p and p.exists():
                load_range_database(str(p))
                return

    def load_units(self, default_unit_path: str | None):
        paths = [
            Path(default_unit_path) if default_unit_path else None,
            Path(r"C:\Program Files (x86)\Steam\steamapps\common\Supreme Ruler Ultimate\Maps\DATA\DEFAULT.UNIT"),
            Path(__file__).with_name("DEFAULT.UNIT"),
        ]
        for p in paths:
            if p and p.exists():
                try:
                    self.units = parse_default_unit(str(p))
                    print(f"[Units] Loaded {len(self.units)} units from {p}")
                    return
                except Exception as e:
                    print(f"[Units] Error loading units from {p}: {e}")
        print("[Units] WARNING: no DEFAULT.UNIT loaded")

    def load_techs(self, default_ttrx_path: str | None = None):
        paths = []
        if default_ttrx_path:
            paths.append(Path(default_ttrx_path))
        paths.append(Path(r"C:\Program Files (x86)\Steam\steamapps\common\Supreme Ruler Ultimate\Maps\DATA\DEFAULT.TTRX"))
        paths.append(Path(__file__).with_name("DEFAULT.TTRX"))
        
        for p in paths:
            if p and p.exists():
                try:
                    self.tech_light, self.tech_full = load_tech_file(str(p))
                    print(f"[Tech] Loaded {len(self.tech_light)} techs from {p}")
                    return
                except Exception as e:
                    print(f"[Tech] Error loading techs from {p}: {e}")
                    
        print("[Tech] WARNING: no DEFAULT.TTRX loaded, tech bonuses disabled.")

    def _calculate_tech_unlocks(self):
        self.tech_unlocks = {}
        print("[System] Tech unlock mapping skipped for SRU (not supported).")

        
    # --------------------------------------------------------------- Filtering
    def _unit_category(self, u: Unit) -> str:
        c = u.class_num
        if 0 <= c <= 6:
            return "land"
        if 7 <= c <= 14:
            return "air"
        if 15 <= c <= 20:
            return "naval"
        return "unknown"

    def update_filter(self):
        q = self.search_query.strip().lower()
        cat = self.selected_category
        res: list[Unit] = []
        
        if not q and cat == "all":
            self.filtered_units = list(self.units)
            self.unit_scroll_offset = 0
            return

        for u in self.units:
            if cat != "all" and self._unit_category(u) != cat:
                continue
            if q and not u.matches(q):
                continue
            res.append(u)
        self.filtered_units = res
        self.unit_scroll_offset = 0

    # -------------------------------------------------------------- Toggle UI
    def toggle_menu(self):
        if not self.menu_visible:
            self.menu_visible = True
            u = self._read_selected_unit_obj()
            if u:
                # In SRU: cambiamo solo l'unità, ma non resettare le tech attive.
                self.selected_unit_b = u
            self.show()
            self.activateWindow()
            self.raise_()
        else:
            self.menu_visible = False
            self.hide()
            self.focus_search = False
            # Reset special focus
            self.tech_search_focus = False
            self.focus_impact_unit_search = False

    # ------------------------------------------------------------- Qt events
    def keyPressEvent(self, event):
        if not self.menu_visible:
            return
        
        # If no search field has focus, check global hotkeys (e.g., Lock)
        no_focus_active = not (self.focus_search or self.tech_search_focus or self.focus_impact_unit_search)

        # Toggle Lock B
        if no_focus_active and event.key() == Qt.Key_L:
            self.lock_b = not self.lock_b
            self.update()
            return

        # ----------------------------------------
        # 1. Main Unit Search (Filter)
        # ----------------------------------------
        if self.focus_search:
            key = event.key()
            if key in (Qt.Key_Return, Qt.Key_Enter):
                self.focus_search = False
            elif key == Qt.Key_Escape:
                self.search_query = ""
                self.update_filter()
                self.focus_search = False 
            elif key == Qt.Key_Backspace:
                self.search_query = self.search_query[:-1]
                self.update_filter()
            else:
                ch = event.text()
                if ch and ch.isprintable():
                    self.search_query += ch
                    self.update_filter()
            self.update()
            return
            
        # ----------------------------------------
        # 2. Tech Search (Find Tech by ID/Name)
        # ----------------------------------------
        elif self.tech_search_focus and self.view_mode == "tech_impact":
             key = event.key()
             if key in (Qt.Key_Return, Qt.Key_Enter):
                if self.tech_search_results:
                    self.selected_tech_for_impact = self.tech_search_results[0][0]
                self.update()
                return
             elif key == Qt.Key_Backspace:
                self.tech_search = self.tech_search[:-1]
                self.update()
                return
             elif key == Qt.Key_Escape:
                self.tech_search = ""
                self.tech_search_results = []
                self.update()
                return
             else:
                ch = event.text()
                if ch and ch.isprintable():
                    self.tech_search += ch
                    self.update()
             return

        # ----------------------------------------
        # 3. Impact Unit Filter (Find unit in Tech view)
        # ----------------------------------------
        elif self.focus_impact_unit_search and self.view_mode == "tech_impact":
             key = event.key()
             if key in (Qt.Key_Return, Qt.Key_Enter):
                self.focus_impact_unit_search = False
                self.update()
                return
             elif key == Qt.Key_Backspace:
                self.impact_unit_search = self.impact_unit_search[:-1]
                self.techimpact_scroll_offset = 0 # reset scroll
                self.update()
                return
             elif key == Qt.Key_Escape:
                self.impact_unit_search = ""
                self.focus_impact_unit_search = False
                self.techimpact_scroll_offset = 0
                self.update()
                return
             else:
                ch = event.text()
                if ch and ch.isprintable():
                    self.impact_unit_search += ch
                    self.techimpact_scroll_offset = 0
                    self.update()
             return

    def wheelEvent(self, event):
        if not self.menu_visible:
            return
        handle_wheel(self, event)

    # -------------------------------------------------------------
    # MOUSE EVENTS (Fixed Logic)
    # -------------------------------------------------------------

    def mousePressEvent(self, event):
        if not self.menu_visible:
            return

        pos = event.pos()

        # ==============================================================
        # 1. PRIORITY FIX: CHECK DROPDOWN SELECTION FIRST!
        # ==============================================================
        if self.view_mode == "tech_impact" and self.tech_search_focus:
            for rect, tid in getattr(self, "tech_search_result_rects", []):
                if rect.contains(pos):
                    # APPLY SELECTION
                    self.selected_tech_for_impact = tid
                    
                    # Update text box info
                    info = self.tech_light.get(tid, {})
                    self.tech_search = info.get("short_title", f"Tech {tid}")

                    # Close menu
                    self.tech_search_results = []
                    self.tech_search_result_rects = []
                    self.tech_search_focus = False

                    self.update()
                    return  # <--- STOP HERE! Click consumed.

        # ------------------------------------------------------------------
        # 2. FOCUS HANDLING for the three search boxes
        # ------------------------------------------------------------------
        if self.search_rect.contains(pos):
            self.focus_search = True
            self.tech_search_focus = False
            self.focus_impact_unit_search = False

        elif self.view_mode == "tech_impact" and self.tech_search_rect.contains(pos):
            self.focus_search = False
            self.tech_search_focus = True
            self.focus_impact_unit_search = False

        elif self.view_mode == "tech_impact" and hasattr(self, "impact_unit_search_rect") \
             and self.impact_unit_search_rect.contains(pos):
            self.focus_search = False
            self.tech_search_focus = False
            self.focus_impact_unit_search = True

        else:
            self.focus_search = False
            self.tech_search_focus = False
            self.focus_impact_unit_search = False

        # ------------------------------------------------------------------
        # 3. Delegate general interactions
        # ------------------------------------------------------------------
        handle_mouse_press(self, event)

        # ------------------------------------------------------------------
        # 4. SPECIAL INTERACTIONS FOR TECH IMPACT MODE
        # ------------------------------------------------------------------
        if self.view_mode == "tech_impact":

            # A) Check Scrollbar Handle
            if hasattr(self, "techimpact_scrollbar_handle_rect") and \
               not self.techimpact_scrollbar_handle_rect.isNull() and \
               self.techimpact_scrollbar_handle_rect.contains(pos):
               
                self.techimpact_dragging = True
                self.techimpact_drag_offset = pos.y() - self.techimpact_scrollbar_handle_rect.top()
                self.update()
                return

            # B) Check Scrollbar Track
            if hasattr(self, "techimpact_scrollbar_track_rect") and \
               not self.techimpact_scrollbar_track_rect.isNull() and \
               self.techimpact_scrollbar_track_rect.contains(pos):
               
                track_top = self.techimpact_scrollbar_track_rect.top()
                track_h = self.techimpact_scrollbar_track_rect.height()
                
                if track_h > 0:
                    rel_y = pos.y() - track_top
                    ratio = rel_y / track_h
                    self.techimpact_scroll_offset = int(ratio * self.techimpact_max_scroll)
                    self.update()
                return

            # C) Selecting a UNIT from the Tech Impact list
            btn = event.button()
            for uid, rect in self.techimpact_unit_rects.items():
                if rect.contains(pos):
                    u = self._get_unit_by_id(uid)
                    if btn == Qt.LeftButton:
                        self.selected_unit_b = u
                    elif btn == Qt.RightButton:
                        self.selected_unit_d = u
                    elif btn == Qt.MiddleButton:
                        self.selected_unit_c = u
                    self.focus_impact_unit_search = False
                    self.update()
                    return

        self.update()

    def mouseMoveEvent(self, event):
        if not self.menu_visible:
            return
        if self.view_mode == "tech_impact" and self.techimpact_dragging:
            pos = event.pos()
            if hasattr(self, "techimpact_scroll_start_y"):
                relative_y = pos.y() - self.techimpact_scroll_start_y - self.techimpact_drag_offset
                track_h = self.techimpact_scrollbar_track_rect.height()
                handle_h = self.techimpact_scrollbar_handle_rect.height()
                available_h = track_h - handle_h
                
                if available_h > 0:
                    ratio = relative_y / available_h
                    ratio = max(0.0, min(1.0, ratio))
                    new_offset = int(ratio * self.techimpact_max_scroll)
                    if new_offset != self.techimpact_scroll_offset:
                        self.techimpact_scroll_offset = new_offset
                        self.update()
            return

    def mouseReleaseEvent(self, event):
        if self.techimpact_dragging:
            self.techimpact_dragging = False
            self.techimpact_drag_offset = 0
            self.update()

    # ------------------------------------------------------------- Painting UI
    def paintEvent(self, event):
        if not self.menu_visible:
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, False)

        full = self.rect()
        panel_w = 1100
        panel_h = full.height() - 60
        px = full.width() - panel_w - 20
        py = 30

        bg_rect = QRect(px, py, panel_w, panel_h)
        p.setBrush(QColor(20, 25, 30, 240))
        p.setPen(QColor(0, 100, 160))
        p.drawRect(bg_rect)

        # Close button
        btn_size = 24
        self.close_btn_rect = QRect(px + panel_w - btn_size - 6, py + 6, btn_size, btn_size)
        p.setBrush(QColor(170, 40, 40))
        p.setPen(Qt.NoPen)
        p.drawRect(self.close_btn_rect)
        p.setPen(Qt.white)
        p.setFont(QFont("Segoe UI", 10, QFont.Bold))
        p.drawText(self.close_btn_rect, Qt.AlignCenter, "X")

        # Debug line
        debug_rect = QRect(px + 10, py + 6, panel_w - btn_size - 30, 20)
        p.setPen(QColor(170, 170, 170))
        p.setFont(QFont("Consolas", 9))
        rid = self.last_raw_selected_id if self.last_raw_selected_id is not None else "-"
        lock_txt = "LOCK B: ON" if self.lock_b else "LOCK B: OFF"
        p.drawText(
            debug_rect,
            Qt.AlignVCenter | Qt.AlignLeft,
            f"Selected ID (raw): {rid}   | {lock_txt}   | L=B  R=C  M=D",
        )

        # Search bar (Units)
        self.search_rect = QRect(px + 10, py + 30, panel_w - 50, 26)
        p.setBrush(QColor(10, 10, 10))
        p.setPen(QColor(255, 200, 0) if self.focus_search else QColor(100, 100, 100))
        p.drawRect(self.search_rect)
        p.setPen(Qt.white)
        p.setFont(QFont("Consolas", 10))
        
        display_text = self.search_query
        if self.focus_search and (len(display_text) == 0 or (ctypes.windll.kernel32.GetTickCount() // 500) % 2 == 0):
             display_text += "|"
        elif not self.focus_search and not self.search_query:
             display_text = "Search Unit..."
             p.setPen(QColor(150, 150, 150))

        p.drawText(
            self.search_rect.adjusted(6, 0, 0, 0),
            Qt.AlignVCenter,
            display_text,
        )

        # Category buttons
        cats = ["all", "land", "air", "sea"]
        cx = px + 10
        cy = py + 30 + 26 + 4
        btn_w = (panel_w - 20) // 4
        self.category_button_rects = []
        p.setFont(QFont("Segoe UI", 9, QFont.Bold))
        for c in cats:
            cid = "naval" if c == "sea" else c
            r = QRect(cx, cy, btn_w - 2, 22)
            self.category_button_rects.append((r, cid))
            p.setBrush(QColor(0, 100, 180) if self.selected_category == cid else QColor(40, 40, 40))
            p.setPen(Qt.NoPen)
            p.drawRect(r)
            p.setPen(Qt.white)
            p.drawText(r, Qt.AlignCenter, c.upper())
            cx += btn_w

        # Unit list (Left Sidebar)
        list_y = cy + 22 + 4
        list_h = int(panel_h * 0.23)
        self.unit_list_rect = QRect(px + 10, list_y, panel_w - 20, list_h)
        p.setBrush(QColor(15, 15, 20))
        p.setPen(QColor(55, 55, 65))
        p.drawRect(self.unit_list_rect)
        draw_unit_list(self, p)

        # Stats area (Right Side)
        stats_y = list_y + list_h + 8
        stats_h = panel_h - (stats_y - py) - 8
        self.stats_rect = QRect(px + 10, stats_y, panel_w - 20, stats_h)
        p.setBrush(QColor(10, 12, 16))
        p.setPen(QColor(55, 55, 65))
        p.drawRect(self.stats_rect)
        draw_comparison_table(self, p, self.stats_rect)

    def _get_unit_by_id(self, uid: int):
        for u in self.units:
            if u.id == uid:
                return u
        return None
        
    def get_tech_modified_stats(self, unit, tech_id):
        """
        Returns only the unit values modified by the tech.
        Format: (attr, label, base, boosted)
        """
        info = self.tech_light.get(tech_id)
        if not info:
            return []

        rows = []

        for eff in info["effects"]:
            eid = eff["effect_id"]
            val = eff["value"]

            # --- CASE A: Boolean Effects (On/Off) ---
            if eid in BOOL_EFFECT_MAP:
                attr = BOOL_EFFECT_MAP[eid]
                base = getattr(unit, attr, 0)
                if base == 0:
                    label = TECH_LABEL_MAP.get(eid, attr.replace("_", " ").title())
                    rows.append((attr, label, 0.0, 1.0))
                continue

            # --- CASE B: Numeric Effects (Attack, Defense, etc.) ---
            if eid not in CORE_EFFECT_MAP:
                continue

            attr, mode = CORE_EFFECT_MAP[eid]
            label = TECH_LABEL_MAP.get(eid, f"{attr.capitalize()} ({eid})")

            base = getattr(unit, attr, None)
            if base is None:
                continue
            
            try:
                if mode == "mul":
                    boosted = base * (1.0 + float(val))
                else:
                    boosted = base + float(val)
            except Exception:
                continue

            if abs(boosted - base) < 0.001:
                continue

            rows.append((attr, label, base, boosted))

        return rows
        # -------------------------------------------------------------
    # Build merged unit list for Tech Impact View
    # -------------------------------------------------------------
    def build_tech_impact_unit_list(self, tech_id):
        """
        Returns a clean merged list of:
        - units affected by the tech (effects)
        - units unlocked by the tech (req_tech_id)
        Deduplicated, sorted, and labeled.
        """
        effect_units = []
        unlock_units = []

        # 1) Units with EFFECTS
        for u in self.units:
            effects = self.get_tech_modified_stats(u, tech_id)
            if effects:
                effect_units.append((u, effects))

        # 2) Units UNLOCKED by tech
        unlock_list = self.tech_unlocks.get(tech_id, [])
        for u in unlock_list:
            unlock_units.append((u, []))

        # 3) Merge + dedupe
        merged = {}

        # Units with effects first
        for u, eff in effect_units:
            merged[u.id] = {
                "unit": u,
                "effects": eff,
                "unlock": False
            }

        # Add unlocked units
        for u, eff in unlock_units:
            if u.id not in merged:
                merged[u.id] = {
                    "unit": u,
                    "effects": [],
                    "unlock": True
                }
            else:
                merged[u.id]["unlock"] = True

        # 4) Sort: effects first, then unlock
        final_list = list(merged.values())
        final_list.sort(key=lambda x: (not x["effects"], not x["unlock"], x["unit"].id))

        return final_list

        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    overlay = OverlayINS()
    sys.exit(app.exec_())