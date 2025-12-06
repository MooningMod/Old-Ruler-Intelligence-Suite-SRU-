# events.py
from typing import TYPE_CHECKING

from PyQt5.QtCore import Qt

if TYPE_CHECKING:
    from overlay_ins_menu import OverlayINS


# -------------------------------------------------------------------------
# KEYBOARD HANDLER
# -------------------------------------------------------------------------
def handle_key_press(ov: "OverlayINS", event) -> None:
    # Se stiamo scrivendo nella TECH SEARCH (Tech Impact)
    if ov.view_mode == "tech_impact" and ov.tech_search_focus:
        key = event.key()

        if key in (Qt.Key_Return, Qt.Key_Enter):
            # seleziona il primo risultato
            if ov.tech_search_results:
                ov.selected_tech_for_impact = ov.tech_search_results[0][0]
            ov.update()
            return

        elif key == Qt.Key_Backspace:
            ov.tech_search = ov.tech_search[:-1]
            ov.update()
            return

        elif key == Qt.Key_Escape:
            ov.tech_search = ""
            ov.tech_search_results = []
            ov.update()
            return

        else:
            ch = event.text()
            if ch and ch.isprintable():
                ov.tech_search += ch
                ov.update()
            return

    # Se stiamo scrivendo nella SEARCH UNIT (compare mode)
    if ov.focus_search:
        key = event.key()

        if key in (Qt.Key_Return, Qt.Key_Enter):
            ov.focus_search = False
            return

        elif key == Qt.Key_Escape:
            ov.search_query = ""
            ov.update_filter()
            return

        elif key == Qt.Key_Backspace:
            ov.search_query = ov.search_query[:-1]
            ov.update_filter()
            return

        else:
            ch = event.text()
            if ch and ch.isprintable():
                ov.search_query += ch
                ov.update_filter()
            return

    # Toggle lock B (solo se NON sei in search)
    if not ov.focus_search and event.key() == Qt.Key_L:
        ov.lock_b = not ov.lock_b
        ov.update()
        return


# -------------------------------------------------------------------------
# MOUSE WHEEL (scroll)
# -------------------------------------------------------------------------
def handle_wheel(ov: "OverlayINS", event) -> None:
    pos = event.pos()
    delta = event.angleDelta().y()
    direction = 1 if delta < 0 else -1

    # Scroll lista unità
    if ov.unit_list_rect.contains(pos):
        max_offset = max(0, len(ov.filtered_units) - 10)
        ov.unit_scroll_offset = max(
            0, min(max_offset, ov.unit_scroll_offset + direction * 3)
        )
        ov.update()
        return

    # Scroll tabella compare
    if ov.stats_rect.contains(pos) and ov.view_mode == "compare":
        ov.stats_scroll_offset = max(
            0, min(ov.max_stats_scroll, ov.stats_scroll_offset + direction)
        )
        ov.update()
        return

    # Scroll TECH IMPACT
    if ov.stats_rect.contains(pos) and ov.view_mode == "tech_impact":
        ov.techimpact_scroll_offset = max(
            0, min(ov.techimpact_max_scroll, ov.techimpact_scroll_offset + direction)
        )
        ov.update()
        return


# -------------------------------------------------------------------------
# MOUSE PRESS (click)
# -------------------------------------------------------------------------
def handle_mouse_press(ov: "OverlayINS", event) -> None:
    pos = event.pos()

    # Tabs
    if ov.tab_compare_rect.contains(pos):
        ov.view_mode = "compare"
        ov.update()
        return

    if ov.tab_tech_rect.contains(pos):
        ov.view_mode = "tech_impact"
        ov.update()
        return

    # Close
    if ov.close_btn_rect.contains(pos):
        ov.toggle_menu()
        return

    # (Il focus delle search bar adesso è gestito in overlay_ins_menu.mousePressEvent)

    # Category filter
    for r, cid in ov.category_button_rects:
        if r.contains(pos):
            ov.selected_category = cid
            ov.update_filter()
            ov.update()
            return

    # Header buttons
    if ov.btn_lock_rect.contains(pos):
        ov.lock_b = not ov.lock_b
        ov.update()
        return

    if ov.btn_b_to_c_rect.contains(pos):
        if ov.selected_unit_b:
            ov.selected_unit_c = ov.selected_unit_b
            ov.active_techs["c"] = set(ov.active_techs["b"])
        ov.update()
        return

    if ov.btn_c_to_d_rect.contains(pos):
        if ov.selected_unit_c:
            ov.selected_unit_d = ov.selected_unit_c
            ov.active_techs["d"] = set(ov.active_techs["c"])
        ov.update()
        return

    # --- TECH CHECKBOXES ---
    for key in ("b", "c", "d"):
        for tid, r in ov.tech_checkbox_rects.get(key, {}).items():
            if r.contains(pos):

                # Right click → Tech Impact
                if event.button() == Qt.RightButton:
                    ov.view_mode = "tech_impact"
                    ov.selected_tech_for_impact = tid
                    ov.update()
                    return

                # Left click → toggle attivo / non attivo
                if tid in ov.active_techs[key]:
                    ov.active_techs[key].remove(tid)
                else:
                    ov.active_techs[key].add(tid)

                ov.update()
                return

    # --- UNIT SELECTION LIST ---
    if ov.unit_list_rect.contains(pos):
        row = (pos.y() - ov.unit_list_rect.top()) // ov.line_height
        idx = ov.unit_scroll_offset + row

        if 0 <= idx < len(ov.filtered_units):
            u = ov.filtered_units[idx]

            if event.button() == Qt.LeftButton:
                ov.selected_unit_b = u
                ov.active_techs["b"] = set(u.tech_ids)

            elif event.button() == Qt.RightButton:
                ov.selected_unit_c = u
                ov.active_techs["c"] = set(u.tech_ids)

            elif event.button() == Qt.MiddleButton:
                ov.selected_unit_d = u
                ov.active_techs["d"] = set(u.tech_ids)

            ov.update()
            return

    # Da qui in giù NON gestiamo più la tech search:
    # è tutta in overlay_ins_menu.mousePressEvent (unit filter + tech search results).
