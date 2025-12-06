from typing import TYPE_CHECKING
from PyQt5.QtCore import QRect, Qt
from PyQt5.QtGui import QColor, QFont, QPainter

from tech_effects import apply_techs_to_unit
from tech_effects import EFFECT_MAP, BOOL_EFFECT_MAP, GLOBAL_EFFECT_MAP

if TYPE_CHECKING:
    from overlay_ins_menu import OverlayINS


# -------------------------------------------------------------------------
# SIDEBAR: UNIT LIST 
# -------------------------------------------------------------------------
def draw_unit_list(ov: "OverlayINS", p: QPainter) -> None:
    p.setClipRect(ov.unit_list_rect)
    start = ov.unit_scroll_offset
    rows = ov.unit_list_rect.height() // ov.line_height
    y = ov.unit_list_rect.top()

    p.setFont(QFont("Consolas", 9))
    
    for i in range(start, min(len(ov.filtered_units), start + rows + 1)):
        u = ov.filtered_units[i]
        r = QRect(ov.unit_list_rect.left(), y, ov.unit_list_rect.width(), ov.line_height)

        if u == ov.selected_unit_b:
            p.fillRect(r, QColor(0, 100, 255, 80))
        if u == ov.selected_unit_c:
            p.fillRect(r, QColor(255, 160, 0, 80))
        if u == ov.selected_unit_d:
            p.fillRect(r, QColor(80, 200, 130, 80))

        p.setPen(QColor(150, 150, 150))
        p.drawText(r.left() + 4, r.bottom() - 4, str(u.id))
        p.setPen(Qt.white)
        p.drawText(r.left() + 55, r.bottom() - 4, u.name[:60])
        y += ov.line_height

    p.setClipping(False)


# -------------------------------------------------------------------------
# MAIN AREA: COMPARISON & TECH IMPACT
# -------------------------------------------------------------------------
def draw_comparison_table(ov: "OverlayINS", p: QPainter, rect: QRect) -> None:
    
    y = rect.top() + 10
    label_w = 140
    rest_w = rect.width() - label_w
    col_w = rest_w // 3

    x_label = rect.left()
    x_b = x_label + label_w
    x_c = x_b + col_w
    x_d = x_c + col_w

    tab_h = 18
    tab_w = 90
    tab_y = rect.top() + 4

    ov.tab_compare_rect = QRect(rect.left() + 6, tab_y, tab_w, tab_h)
    ov.tab_tech_rect = QRect(rect.left() + 6 + tab_w + 4, tab_y, tab_w, tab_h)

    p.setFont(QFont("Segoe UI", 8, QFont.Bold))

    # Compare Tab
    p.setBrush(QColor(60, 60, 80) if ov.view_mode == "compare" else QColor(30, 30, 40))
    p.setPen(Qt.NoPen)
    p.drawRect(ov.tab_compare_rect)
    p.setPen(QColor(230, 230, 230))
    p.drawText(ov.tab_compare_rect, Qt.AlignCenter, "COMPARE")

    # Tech Impact Tab
    p.setBrush(QColor(60, 60, 80) if ov.view_mode == "tech_impact" else QColor(30, 30, 40))
    p.setPen(Qt.NoPen)
    p.drawRect(ov.tab_tech_rect)
    p.setPen(QColor(230, 230, 230))
    p.drawText(ov.tab_tech_rect, Qt.AlignCenter, "TECH IMPACT")

    # UNIT TITLES
    y = tab_y + tab_h + 4
    p.setFont(QFont("Segoe UI", 9, QFont.Bold))

    name_b = ov.selected_unit_b.name if ov.selected_unit_b else "Unit B (LMB)"
    name_c = ov.selected_unit_c.name if ov.selected_unit_c else "Unit C (RMB)"
    name_d = ov.selected_unit_d.name if ov.selected_unit_d else "Unit D (MMB)"

    p.setPen(QColor(120, 200, 255))
    p.drawText(QRect(x_b, y, col_w, 32), Qt.AlignCenter | Qt.TextWordWrap, name_b)
    p.setPen(QColor(255, 180, 90))
    p.drawText(QRect(x_c, y, col_w, 32), Qt.AlignCenter | Qt.TextWordWrap, name_c)
    p.setPen(QColor(150, 230, 170))
    p.drawText(QRect(x_d, y, col_w, 32), Qt.AlignCenter | Qt.TextWordWrap, name_d)

    controls_y = y + 32
    btn_h = 18
    btn_w = 90

    p.setFont(QFont("Segoe UI", 8, QFont.Bold))

    ov.btn_lock_rect = QRect(x_b + (col_w - btn_w) // 2, controls_y, btn_w, btn_h)
    p.setBrush(QColor(0, 120, 220) if ov.lock_b else QColor(40, 40, 40))
    p.drawRect(ov.btn_lock_rect)
    p.setPen(Qt.white)
    p.drawText(ov.btn_lock_rect, Qt.AlignCenter, "LOCK B")

    ov.btn_b_to_c_rect = QRect(x_c + (col_w - btn_w) // 2, controls_y, btn_w, btn_h)
    p.setBrush(QColor(40, 40, 40))
    p.drawRect(ov.btn_b_to_c_rect)
    p.drawText(ov.btn_b_to_c_rect, Qt.AlignCenter, "B → C")

    ov.btn_c_to_d_rect = QRect(x_d + (col_w - btn_w) // 2, controls_y, btn_w, btn_h)
    p.setBrush(QColor(40, 40, 40))
    p.drawRect(ov.btn_c_to_d_rect)
    p.drawText(ov.btn_c_to_d_rect, Qt.AlignCenter, "C → D")

    y = controls_y + btn_h + 4

    if ov.focus_search and ov.view_mode == "compare":
        return

    ov.tech_checkbox_rects = {"b": {}, "c": {}, "d": {}}
    p.setFont(QFont("Consolas", 9))

    max_tech_rows = 0

    def draw_tech_column(unit, key: str, col_x: int):
        nonlocal max_tech_rows
        if not unit or not unit.tech_ids:
            return
        row_y = y
        for tid in unit.tech_ids:
            short = ov.tech_light.get(tid, {}).get("short_title", "") or f"Tech {tid}"

            box = QRect(col_x + 4, row_y, 12, 12)
            ov.tech_checkbox_rects[key][tid] = box

            p.setPen(QColor(200, 200, 200))
            p.setBrush(QColor(40, 40, 40))
            p.drawRect(box)

            if tid in ov.active_techs.get(key, set()):
                p.drawLine(box.left() + 2, box.center().y(), box.center().x(), box.bottom() - 2)
                p.drawLine(box.center().x(), box.bottom() - 2, box.right() - 2, box.top() + 2)

            p.setPen(QColor(200, 200, 200))
            p.drawText(QRect(box.right() + 4, row_y - 2, col_w - 20, 16),
                       Qt.AlignLeft | Qt.AlignVCenter, short)
            row_y += 16

        max_tech_rows = max(max_tech_rows, (row_y - y) // 16)

    draw_tech_column(ov.selected_unit_b, "b", x_b)
    draw_tech_column(ov.selected_unit_c, "c", x_c)
    draw_tech_column(ov.selected_unit_d, "d", x_d)

    y += max_tech_rows * 16 + 6

    p.setPen(QColor(70, 70, 80))
    p.drawLine(rect.left() + 4, y, rect.right() - 4, y)
    y += 4

    if ov.view_mode == "tech_impact":
        _draw_tech_impact_view(ov, p, rect, y)
        return

    _draw_compare_stats_table(ov, p, rect, x_label, x_b, x_c, x_d, col_w, y)
    
    
def _draw_compare_stats_table(
    ov: "OverlayINS",
    p: QPainter,
    rect: QRect,
    x_label: int,
    x_b: int,
    x_c: int,
    x_d: int,
    col_w: int,
    start_y: int,
) -> None:
    """
    Standard Comparison View.
    Lists all unit stats (Speed, Attack, etc.) side-by-side.
    Green text indicates values boosted by techs.
    """

    label_w = 140
    row_h = 18

    # Fields that are boolean flags (1/0)
    bool_fields = {
        "nbc", "ecm", "indirect_fire", "ballistic_art",
        "no_eff_loss_move", "ftl", "survey", "river_xing",
        "airdrop", "air_tanker", "air_refuel", "amph",
        "bridge_build", "engineering", "stand_off",
        "move_fire_penalty", "no_land_cap", "has_production",
    }

    def fmt(u, attr, rng_attr=None):
        if not u or not attr:
            return "-"
        v = getattr(u, attr, None)

        if attr in bool_fields:
            return "✔" if v else ""

        if isinstance(v, float):
            txt = f"{v:.2f}".rstrip("0").rstrip(".")
        else:
            txt = str(v)

        if rng_attr:
            r = getattr(u, rng_attr, 0)
            if r:
                txt += f" ({r} km)"
        return txt

    def fmt_dual_range(u, attr, def_attr):
        """
        Format attack values with their range in km.
        No RAW, no DEF, no weird formatting.
        Ex: "58 (24 km)"
        """
        if not u:
            return ("-", False)

        v = getattr(u, attr, None)
        if v is None or v == 0:
            return ("-", False)

        # Format attack value
        if isinstance(v, float):
            txt = f"{v:.2f}".rstrip("0").rstrip(".")
        else:
            txt = str(v)

        # MISSILE RANGE CASE (special_41_B)
        missile_range_raw = getattr(u, 'missile_range_km', 0.0)
        if missile_range_raw > 0:
            displayed_range = int(missile_range_raw * 4)
            return (f"{txt} ({displayed_range} km)", False)

        # MAP ATTRIBUTES → RANGE FIELDS
        range_map = {
            'soft': 'range_ground',
            'hard': 'range_ground',
            'fort': 'range_ground',
            'naval_surf': 'range_surf',
            'naval_sub': 'range_sub',
            'air_low': 'range_air',
            'air_mid': 'range_air',
            'air_high': 'range_air',
        }

        if attr in range_map:
            raw = getattr(u, range_map[attr], 0)
            if raw > 0:
                return (f"{txt} ({raw} km)", False)

        return (txt, False)

    # Apply tech modifiers
    ub = apply_techs_to_unit(ov.selected_unit_b, ov.active_techs["b"], ov.tech_light)
    uc = apply_techs_to_unit(ov.selected_unit_c, ov.active_techs["c"], ov.tech_light)
    ud = apply_techs_to_unit(ov.selected_unit_d, ov.active_techs["d"], ov.tech_light)

    rows = [

        # GENERAL INFO
        ("ID / Class", "id", "class_num"),
        ("Name", "name", None),
        ("Model Code", "model_code", None),
        ("Region", "region", None),
        ("Tech Level", "tech_level", None),
        ("Year", "year", None),
        ("Default Strength", "strength", None),
        ("Personnel", "personnel", None),
        ("Crew", "crew", None),
        ("Weight (t)", "weight", None),
        ("Cargo Capacity", "cargo_cap", None),
        ("Carrier Capacity", "carrier_cap", None),
        ("Country of Origin", "region", None),
        ("-", None, None),

        # MOVEMENT
        ("Movement Type", "move_type", None),
        ("Speed (km/h)", "speed", None),
        ("Move Range (km)", "move_range", None),
        ("Fuel Capacity (t)", "fuel_cap", None),
        ("Fuel Consumption", "fuel_consumption", None),
        ("Combat Time", "combat_time", None),
        ("Reaction Time", "reaction_time", None),
        ("Transport Capacity", "transport_cap", None),
        ("-", None, None),

        # ATTACKS
        ("Soft Attack", "soft", "dual_range"),
        ("Hard Attack", "hard", "dual_range"),
        ("Fort Attack", "fort", "dual_range"),
        ("Close Combat", "close_combat", None),
        ("-", None, None),

        ("Low Air Attack", "air_low", "dual_range"),
        ("Mid Air Attack", "air_mid", "dual_range"),
        ("High Air Attack", "air_high", "dual_range"),
        ("-", None, None),

        ("Naval Surface Attack", "naval_surf", "dual_range"),
        ("Naval Sub Attack", "naval_sub", "dual_range"),
        ("-", None, None),

        ("Indirect Artillery", "indirect_fire", None),
        ("Ballistic Artillery", "ballistic_art", None),
        ("Stand-Off Attack", "stand_off", None),
        ("-", None, None),

        # DEFENSE
        ("Ground Defense", "def_ground", None),
        ("Air Defense", "def_air", None),
        ("Indirect Defense", "def_indirect", None),
        ("Close Defense", "def_close", None),
        ("Stealth Rating", "stealth", None),
        ("ECM Equipped", "ecm", None),
        ("NBC Protection", "nbc", None),
        ("-", None, None),

        # RANGES
        ("Ground Attack Range", "range_ground_km", None),
        ("Air Attack Range", "range_air_km", None),
        ("Surface Attack Range", "range_surface_km", None),
        ("Sub Attack Range", "range_sub_km", None),
        ("-", None, None),

        # SPOTTING
        ("Spotting (Visual)", "spot1_range_km", None),
        ("Spotting (Radar)", "spot2_range_km", None),
        ("Spotting Strength (Visual)", "spot1_strength", None),
        ("Spotting Strength (Radar)", "spot2_strength", None),
        ("Initiative", "initiative", None),
        ("-", None, None),

        # MISSILES
        ("Missile Capacity", "missile_cap", None),
        ("Missile Size Capacity", "missile_size_max", None),
        ("Missile Launch Type", "launch_types_str", None),
        ("-", None, None),

        # TECH
        ("Tech Requirement 1", "tech_req_1", None),
        ("Tech Requirement 2", "tech_req_2", None),
        ("Upgrades To", "upgrade_unit", None),
        ("Refit To", "refit_to", None),
        ("Replace By", "replace_by", None),
        ("-", None, None),

        # MANUFACTURING (ACCURATE SRU)
        ("Price / Days to Build", "cost_days", None),
        ("Military Goods Needed", "mg_cost", None),
        ("Annual Maintenance", "maintenance_mg", None),
        ("Uranium Required", "uranium_req", None),
        ("Year Available", "year", None),
        ("-", None, None),

        # SPECIAL TRAITS
        ("Airdrop", "airdrop", None),
        ("Air Tanker", "air_tanker", None),
        ("Air Refuel", "air_refuel", None),
        ("Amphibious", "amph", None),
        ("Engineering", "engineering", None),
        ("River Crossing", "river_xing", None),
        ("No Eff Loss Move", "no_eff_loss_move", None),
        ("Move Fire Penalty", "move_fire_penalty", None),
        ("Low Visibility", "low_visibility", None),
        ("-", None, None),
    ]

    visible = rect.bottom() - start_y - 4
    max_rows = max(1, visible // row_h)

    ov.max_stats_scroll = max(0, len(rows) - max_rows)
    start_i = max(0, min(ov.stats_scroll_offset, ov.max_stats_scroll))
    end_i = min(len(rows), start_i + max_rows)

    p.setFont(QFont("Consolas", 10))
    y = start_y

    for idx in range(start_i, end_i):
        label, attr, rng_attr = rows[idx]

        if label == "-":
            p.setPen(QColor(60, 60, 70))
            p.drawLine(rect.left() + 4, y + row_h // 2, rect.right() - 4, y + row_h // 2)
            y += row_h
            continue

        p.setPen(QColor(170, 170, 170))
        p.drawText(QRect(x_label + 6, y, label_w, row_h),
                   Qt.AlignLeft | Qt.AlignVCenter, label)

        def draw_cell(base, mod, x, base_color):
            if not mod:
                p.setPen(base_color)
                p.drawText(QRect(x, y, col_w, row_h), Qt.AlignCenter, "-")
                return

            # Check if this row uses dual range display
            if rng_attr == "dual_range":
                txt, has_def = fmt_dual_range(mod, attr, None)
                
                changed = False
                if base and attr:
                    try:
                        changed = getattr(base, attr) != getattr(mod, attr)
                    except Exception:
                        changed = False

                if changed:
                    p.setPen(QColor(120, 255, 120))
                else:
                    p.setPen(base_color)
                
                # Draw attack value and RAW range in normal color
                parts = txt.split(" RAW:")
                base_txt = parts[0]
                p.drawText(QRect(x, y, col_w, row_h), Qt.AlignCenter, base_txt)
                
                # If we have range info, draw it with color coding
                if len(parts) > 1:
                    raw_def_parts = parts[1].split(" DEF:")
                    
                    # Calculate text width for positioning
                    metrics = p.fontMetrics()
                    base_width = metrics.horizontalAdvance(base_txt)
                    
                    # Draw RAW in yellow/gold
                    raw_txt = " RAW:" + raw_def_parts[0]
                    p.setPen(QColor(255, 200, 50))  # Yellow/gold for RAW
                    p.drawText(QRect(x + col_w//2 + base_width//2, y, col_w, row_h), 
                             Qt.AlignLeft | Qt.AlignVCenter, raw_txt)
                    
                    # Draw DEF in gray (if exists)
                    if len(raw_def_parts) > 1 and has_def:
                        def_txt = " DEF:" + raw_def_parts[1]
                        raw_width = metrics.horizontalAdvance(raw_txt)
                        p.setPen(QColor(150, 150, 150))  # Gray for DEF
                        p.drawText(QRect(x + col_w//2 + base_width//2 + raw_width, y, col_w, row_h), 
                                 Qt.AlignLeft | Qt.AlignVCenter, def_txt)
                
                return
            
            # Standard formatting for non-dual-range rows
            txt = fmt(mod, attr, rng_attr)

            changed = False
            if base and attr:
                try:
                    changed = getattr(base, attr) != getattr(mod, attr)
                except Exception:
                    changed = False

            if changed:
                p.setPen(QColor(120, 255, 120))
            else:
                p.setPen(base_color)

            p.drawText(QRect(x, y, col_w, row_h),
                       Qt.AlignCenter, txt)

        draw_cell(ov.selected_unit_b, ub, x_b, QColor(130, 210, 255))
        draw_cell(ov.selected_unit_c, uc, x_c, QColor(255, 180, 110))
        draw_cell(ov.selected_unit_d, ud, x_d, QColor(150, 230, 170))

        y += row_h


# -------------------------------------------------------------------------
# VIEW: TECH IMPACT (FULL PATCH)
# -------------------------------------------------------------------------
def _draw_tech_impact_view(ov: "OverlayINS", p: QPainter, rect: QRect, start_y: int) -> None:
    """
    Tech Impact View:
      - Shows tech name
      - Shows global effects
      - Shows unlocked units
      - Shows stat modifications to existing units
      - Uses build_tech_impact_unit_list() to merge unlocks + effects
    """

    tid = ov.selected_tech_for_impact
    p.setFont(QFont("Consolas", 10))
    y = start_y
    ov.techimpact_unit_rects = {}

    # -----------------------------------------
    # 1. HEADER
    # -----------------------------------------
    if tid:
        info = ov.tech_light.get(tid, {})
        title = info.get("short_title", f"Tech {tid}")
        header_text = f"{title} (ID {tid})"
        p.setPen(QColor(240, 240, 140))
    else:
        header_text = "Select a Tech"
        p.setPen(QColor(180, 180, 180))

    p.drawText(QRect(rect.left() + 8, y, rect.width() - 16, 20),
               Qt.AlignLeft, header_text)
    y += 24
    
    # -----------------------------------------
    # 2. UNITS UNLOCKED BY THIS TECH
    # -----------------------------------------
    if tid and tid in ov.tech_unlocks:
        units = ov.tech_unlocks[tid]
    else:
        units = []

    # -----------------------------------------
    # 2. SEARCH BOX
    # -----------------------------------------
    search_h = 20
    ov.tech_search_rect = QRect(rect.left() + 8, y, rect.width() - 16, search_h)
    p.setBrush(QColor(25, 25, 32))
    p.setPen(QColor(150, 150, 80) if ov.tech_search_focus else QColor(60, 60, 80))
    p.drawRect(ov.tech_search_rect)

    txt = ov.tech_search if ov.tech_search else "Search tech name or ID..."
    if ov.tech_search_focus:
        txt += "|"
    p.setPen(QColor(240, 240, 240) if ov.tech_search else QColor(100, 100, 100))
    p.drawText(ov.tech_search_rect.adjusted(5, 0, 0, 0), Qt.AlignVCenter, txt)
    y += search_h + 4

    # -----------------------------------------
    # 2b. DROPDOWN (ACTIVE WHILE TYPING)
    # -----------------------------------------
    if ov.tech_search and ov.tech_search_focus:
        q = ov.tech_search.lower().strip()
        results = []
        for t_id, tinfo in ov.tech_light.items():
            name = tinfo.get("short_title", "").lower()
            if q in name or q == str(t_id):
                results.append((t_id, tinfo.get("short_title", f"Tech {t_id}")))

        results = results[:ov.tech_search_max_display]

        ov.tech_search_result_rects = []

        for t_id, label in results:
            r = QRect(rect.left() + 12, y, rect.width() - 24, 18)
            ov.tech_search_result_rects.append((r, t_id))
            p.setBrush(QColor(40, 40, 55))
            p.setPen(Qt.NoPen)
            p.drawRect(r)
            p.setPen(QColor(220, 220, 220))
            p.drawText(r.adjusted(4, 0, 0, 0), Qt.AlignVCenter, f"{t_id} – {label}")
            y += 18

        y += 6
        return

    if tid is None:
        p.setPen(QColor(200, 200, 200))
        p.drawText(QRect(rect.left() + 10, y + 10, rect.width() - 20, 40),
                   Qt.AlignLeft | Qt.TextWordWrap,
                   "Right-click a tech in the list above, or use search.")
        return

    info = ov.tech_light.get(tid, {})

    # -----------------------------------------
    # 3. GLOBAL EFFECTS
    # -----------------------------------------
    global_lines = []
    for eff in info.get("effects", []):
        eid = eff["effect_id"]
        val = eff["value"]
        if eid in GLOBAL_EFFECT_MAP:
            name = GLOBAL_EFFECT_MAP[eid]
            pct = f"{val:+.1%}"
            global_lines.append(f" • {name}: {pct}")

    if global_lines:
        p.setFont(QFont("Segoe UI", 9, QFont.Bold))
        p.setPen(QColor(100, 255, 255))
        p.drawText(QRect(rect.left() + 8, y, 400, 16), Qt.AlignLeft, "GLOBAL BONUSES:")
        y += 18

        p.setFont(QFont("Consolas", 10))
        p.setPen(QColor(180, 255, 255))
        for line in global_lines:
            p.drawText(QRect(rect.left() + 12, y, rect.width(), 16), Qt.AlignLeft, line)
            y += 16
        y += 8

    # -----------------------------------------
    # 4. UNLOCKED UNITS
    # -----------------------------------------
    unlocked_units = ov.tech_unlocks.get(tid, [])
    if unlocked_units:
        p.setFont(QFont("Segoe UI", 9, QFont.Bold))
        p.setPen(QColor(255, 200, 80))
        p.drawText(QRect(rect.left() + 8, y, 400, 16),
                   Qt.AlignLeft, f"UNLOCKS UNITS ({len(unlocked_units)}):")
        y += 18

        names = [u.name for u in unlocked_units]
        disp = ", ".join(names[:8])
        if len(names) > 8:
            disp += f", +{len(names)-8} more..."

        p.setFont(QFont("Consolas", 9))
        p.setPen(QColor(215, 215, 215))
        box = QRect(rect.left() + 16, y, rect.width() - 40, 200)
        bounding = p.boundingRect(box, Qt.AlignLeft | Qt.TextWordWrap, disp)
        p.drawText(box, Qt.AlignLeft | Qt.TextWordWrap, disp)
        y += bounding.height() + 12

    # -----------------------------------------
    # 5. UNIT IMPACT SEARCH BOX
    # -----------------------------------------
    ov.impact_unit_search_rect = QRect(rect.left() + 8, y, rect.width() - 16, search_h)
    p.setBrush(QColor(25, 25, 32))
    p.setPen(QColor(150, 150, 80) if ov.focus_impact_unit_search else QColor(60, 60, 80))
    p.drawRect(ov.impact_unit_search_rect)

    utxt = ov.impact_unit_search if ov.impact_unit_search else "Filter units by name..."
    if ov.focus_impact_unit_search:
        utxt += "|"
    p.setPen(QColor(240, 240, 240) if ov.impact_unit_search else QColor(100, 100, 100))
    p.drawText(ov.impact_unit_search_rect.adjusted(5, 0, 0, 0), Qt.AlignVCenter, utxt)
    y += search_h + 8

    # -----------------------------------------
    # 6. MERGED LIST (EFFECTS + UNLOCKS)
    # -----------------------------------------
    units = ov.build_tech_impact_unit_list(tid)

    # Filter by search
    q = ov.impact_unit_search.lower().strip()
    if q:
        units = [item for item in units if q in item["unit"].name.lower()]

    # Nothing?
    if not units:
        p.setPen(QColor(160,160,160))
        msg = "No units match filter." if q else "This tech does not change unit stats."
        p.drawText(QRect(rect.left() + 12, y, rect.width()-16, 20),
                   Qt.AlignLeft, msg)
        return

    ov._cached_impact_units = units

    # -----------------------------------------
    # 7. COLLECT ALL ATTRIBUTES
    # -----------------------------------------
    seen = set()
    all_attrs = []

    for item in units:
        rows = item["effects"]
        for attr, label, base, boosted in rows:
            if attr not in seen:
                seen.add(attr)
                all_attrs.append((attr, label))

    name_w = 260
    col_w = 200

    p.setPen(QColor(180,180,180))
    p.setFont(QFont("Consolas", 10, QFont.Bold))
    p.drawText(QRect(rect.left() + 8, y, name_w, 20), Qt.AlignLeft, "Unit Modified")

    xcol = rect.left() + 8 + name_w
    for attr, label in all_attrs:
        p.drawText(QRect(xcol, y, col_w, 20), Qt.AlignCenter, label)
        xcol += col_w

    y += 24

    # -----------------------------------------
    # 8. SCROLLING
    # -----------------------------------------
    row_h = 18
    list_start_y = y
    visible_h = rect.bottom() - y - 4

    max_rows = max(1, visible_h // row_h)
    ov.techimpact_max_scroll = max(0, len(units) - max_rows)

    s = max(0, min(ov.techimpact_scroll_offset, ov.techimpact_max_scroll))
    vis = units[s : s + max_rows]

    ov.techimpact_scroll_start_y = list_start_y
    ov.techimpact_visible_h = visible_h

    # Scrollbar
    ov.techimpact_scrollbar_track_rect = QRect()
    ov.techimpact_scrollbar_handle_rect = QRect()

    if len(units) > max_rows and visible_h > 0:
        sb_w = 20
        sb_x = rect.right() - sb_w - 4
        sb_h = visible_h

        ov.techimpact_scrollbar_track_rect = QRect(sb_x, list_start_y, sb_w, sb_h)
        p.setBrush(QColor(30, 30, 35))
        p.setPen(Qt.NoPen)
        p.drawRect(ov.techimpact_scrollbar_track_rect)

        ratio = max_rows / len(units)
        handle_h = max(40, int(ratio * sb_h))

        if ov.techimpact_max_scroll > 0:
            scroll_ratio = s / ov.techimpact_max_scroll
            available = sb_h - handle_h
            handle_y = list_start_y + int(scroll_ratio * available)
        else:
            handle_y = list_start_y

        ov.techimpact_scrollbar_handle_rect = QRect(sb_x, handle_y, sb_w, handle_h)
        p.setBrush(QColor(90, 90, 110) if not ov.techimpact_dragging else QColor(130, 130, 170))
        p.drawRect(ov.techimpact_scrollbar_handle_rect)

    # -----------------------------------------
    # 9. DRAW VISIBLE ROWS
    # -----------------------------------------
    p.setFont(QFont("Consolas", 10))
    ov.techimpact_unit_rects = {}

    for item in vis:
        u = item["unit"]
        rows = item["effects"]
        unlock = item["unlock"]

        row_rect = QRect(rect.left() + 8, y, rect.width() - 32, row_h)
        ov.techimpact_unit_rects[u.id] = row_rect

        # Name
        if unlock:
            p.setPen(QColor(255, 200, 100))
        else:
            p.setPen(QColor(220, 220, 220))

        p.drawText(QRect(rect.left() + 8, y, name_w, row_h),
                   Qt.AlignLeft, u.name[:35])

        # Effects
        modmap = {attr: (base, boosted)
                  for (attr, label, base, boosted) in rows}

        xcol = rect.left() + 8 + name_w
        for attr, label in all_attrs:
            if attr in modmap:
                base, boosted = modmap[attr]

                def clean(v):
                    try:
                        v = float(v)
                        return f"{v:.2f}".rstrip("0").rstrip(".")
                    except:
                        return str(v)

                if base != boosted:
                    p.setPen(QColor(120, 255, 120))
                    pct = ""
                    if isinstance(base, (int, float)) and base != 0:
                        pct = f" ({(boosted-base)/base*100:+.0f}%)"

                    vb = clean(base)
                    vm = clean(boosted)

                    txt = f"{vb}->{vm}{pct}"
                else:
                    p.setPen(QColor(180,180,180))
                    txt = "-"
            else:
                p.setPen(QColor(90,90,90))
                txt = "-"

            p.drawText(QRect(xcol, y, col_w, row_h), Qt.AlignCenter, txt)
            xcol += col_w

        y += row_h
