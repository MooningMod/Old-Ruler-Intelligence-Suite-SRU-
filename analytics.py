import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from matplotlib.widgets import CheckButtons, Button
import matplotlib.dates as mdates
from pathlib import Path
import os
import sys
import numpy as np
import datetime

# Ensure local imports
sys.path.append(str(Path(__file__).parent))
from data_logger import get_existing_logs

# ---- THEMES: PAPER DOSSIER & NIGHT OPS ----

PAPER_THEME = {
    "bg": "#E3DAC9",        # warm paper
    "fg": "#2A2A2A",        # ink
    "accent": "#550000",    # red seal
    "accent2": "#004400",   # intel green
    "frame_border": "#555555",
    "button_bg": "#D1C7B7",
    "button_active": "#C0B5A5",
    "footer_fg": "#555555",
    "plot_bg": "#F0E6D2",
    "grid_color": "#B0A58F",
}

NIGHT_THEME = {
    "bg": "#101316",        # dark ops background
    "fg": "#E5E5E5",        # light ink
    "accent": "#9B1C1C",    # dark red
    "accent2": "#00A86B",   # tactical green
    "frame_border": "#444444",
    "button_bg": "#1F252B",
    "button_active": "#2C343D",
    "footer_fg": "#888888",
    "plot_bg": "#181D22",
    "grid_color": "#333A42",
}

# ---- PLOT STYLE BASE ----
plt.style.use('default')
plt.rcParams.update({
    'font.size': 10,
    'axes.titlesize': 14,
    'axes.labelsize': 12,
    'figure.titlesize': 16,
    'axes.grid': True,
})

# ---- PATHS ----
BASE_DIR = Path.home() / "Documents" / "SRU_Logger"
LOGS_DIR = BASE_DIR / "logs"

# ---- CATEGORY MAP ----
CATEGORY_MAP = {
    "Economy": ["GameDate", "Treasury", "Credit Rating", "Inflation", "Unemployment", "GDP/c", "Bond Debt"],
    "Resources - Stock": ["GameDate", "Agriculture", "Rubber", "Timber", "Petroleum", "Coal", "Metal Ore",
                          "Uranium", "Electric Power", "Consumer Goods", "Industry Goods", "Military Goods"],
    "Resources - Production Costs": ["GameDate", "Agriculture Production Cost", "Rubber Production Cost",
                                     "Timber Production Cost", "Petroleum Production Cost", "Coal Production Cost",
                                     "Metal Ore Production Cost", "Uranium Production Cost",
                                     "Electric Power Production Cost", "Consumer Goods Production Cost",
                                     "Industry Goods Production Cost", "Military Goods Production Cost"],
    "Resources - Market Prices": ["GameDate", "Agriculture Market Price", "Rubber Market Price",
                                  "Timber Market Price", "Petroleum Market Price", "Coal Market Price",
                                  "Metal Ore Market Price", "Uranium Market Price", "Electric Power Market Price",
                                  "Consumer Goods Market Price", "Industry Goods Market Price",
                                  "Military Goods Market Price"],
    "Resources - Trades": ["GameDate", "Agriculture Trades", "Rubber Trades", "Timber Trades", "Petroleum Trades",
                           "Coal Trades", "Metal Ore Trades", "Uranium Trades", "Electric Power Trades",
                           "Consumer Goods Trades", "Industry Goods Trades", "Military Goods Trades"],
    "Demographics": ["GameDate", "Population", "Emigration", "Immigration", "Births", "Deaths", "Tourism"],
    "Politics & Military": ["GameDate", "Domestic Approval", "Military Approval", "Literacy", "Treaty Integrity",
                            "Subsidy Rate", "Active Personnel", "Reserve Personnel"],
    "Social Spending": ["GameDate", "Health Care", "Education", "Infrastructure", "Environment",
                        "Family Subsidy", "Law Enforcement", "Culture Subsidy", "Social Assistance"],
    "Research": ["GameDate", "Research Efficiency"],
}

# ---- FORMATTING ----
PERCENT_COLS = {
    "Domestic Approval", "Military Approval", "Inflation", "Unemployment",
    "Research Efficiency", "Subsidy Rate", "Treaty Integrity",
    "Credit Rating", "Tourism", "Literacy"
}
MILLION_COLS = {"Treasury", "Bond Debt"}
THOUSAND_COLS = {"Population", "Active Personnel", "Reserve Personnel"}

META_COLS = {
    "Timestamp", "Game Date", "GameDate", "GameDate_str",
    "Nation", "GameName", "Game Name", "Game Version"
}


def _format_value(col: str, val):
    if pd.isna(val):
        return ""
    if isinstance(val, (int, float)):
        if col in MILLION_COLS:
            return f"{val/1_000_000:,.2f} M"
        if col in THOUSAND_COLS:
            return f"{val/1_000:,.1f} K"
        if col in PERCENT_COLS:
            return f"{val*100:.1f}%"
        if "Trades" in col:
            return f"{val:,.0f}"
        if "Price" in col or "Cost" in col or "GDP/c" in col:
            return f"${val:,.2f}"
        return f"{val:,.0f}"
    if isinstance(val, pd.Timestamp):
        return val.strftime('%Y-%m-%d')
    return str(val)


def _resource_names_from_stock():
    return ["Agriculture", "Rubber", "Timber", "Petroleum", "Coal", "Metal Ore",
            "Uranium", "Electric Power", "Consumer Goods", "Industry Goods", "Military Goods"]


def _cols_for_resource(res_name: str):
    return {
        "stock": res_name,
        "cost": f"{res_name} Production Cost",
        "price": f"{res_name} Market Price",
        "trades": f"{res_name} Trades"
    }


def prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Normalizza il dataframe"""
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]

    if "Game Date" in df.columns and "GameDate" not in df.columns:
        df = df.rename(columns={"Game Date": "GameDate"})

    if "GameDate" not in df.columns:
        for alt in ["Date", "DATE", "date", "Timestamp"]:
            if alt in df.columns:
                df["GameDate"] = df[alt]
                break
        else:
            df["GameDate"] = range(1, len(df) + 1)

    try:
        df["GameDate"] = pd.to_datetime(df["GameDate"], errors="coerce")
        if df["GameDate"].isna().all():
            df["GameDate"] = pd.to_datetime(df["GameDate"], unit='s', errors='coerce')
    except Exception:
        pass

    original_len = len(df)
    df = df.dropna(subset=["GameDate"]).reset_index(drop=True)
    if len(df) < original_len:
        print(f"Removed {original_len - len(df)} rows with invalid dates")

    if pd.api.types.is_datetime64_any_dtype(df["GameDate"]):
        df = df.sort_values("GameDate").reset_index(drop=True)

    try:
        df["GameDate_str"] = df["GameDate"].dt.strftime("%Y-%m-%d")
    except Exception:
        df["GameDate_str"] = df["GameDate"].astype(str)

    return df


# ---- MAIN APP ----
class AnalyticsApp:
    def __init__(self, root, initial_log: str = None):
        self.root = root
        self.root.title("Economic Intelligence Division")
        self.root.geometry("1400x750")
        self.root.minsize(1000, 600)

        # Theme state
        self.theme_mode = tk.StringVar(value="paper")
        self.style = ttk.Style()

        self.df = None
        self.selected_log = None
        self.metric_vars = {}
        self.time_granularity = tk.StringVar(value="auto")
        self.logs = []
        self.log_files_map = {}
        self.initial_log = initial_log  # Store for later loading

        # Matplotlib figure will be created in setup_ui
        self.fig = None
        self.ax = None

        self._configure_theme()   # configure base ttk theme
        self.setup_ui()
        self.apply_theme()        # apply colors to widgets and plots
        self.load_logs()
        
        # Load initial log if provided
        if initial_log and os.path.exists(initial_log):
            self.root.after(100, lambda: self._load_log_from_path(initial_log))

    # ---------- THEME MANAGEMENT ----------

    def _current_theme(self):
        return PAPER_THEME if self.theme_mode.get() == "paper" else NIGHT_THEME

    def _configure_theme(self):
        """Base ttk theme setup (called once)."""
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

    def apply_theme(self):
        """Apply current theme to widgets and matplotlib."""
        theme = self._current_theme()

        # Root background (only for this window)
        self.root.configure(bg=theme["bg"])

        # Specific ttk styling - DO NOT use "." to avoid infecting parent windows
        # self.style.configure(".", ...) is REMOVED to prevent theme leakage
        
        self.style.configure("TFrame", background=theme["bg"])
        self.style.configure("TLabelframe", background=theme["bg"], bordercolor=theme["frame_border"])
        self.style.configure(
            "TLabelframe.Label",
            background=theme["bg"],
            foreground=theme["accent"],
            font=("Courier New", 11, "bold"),
        )
        self.style.configure("TLabel", background=theme["bg"], foreground=theme["fg"])
        self.style.configure(
            "TButton",
            background=theme["button_bg"],
            foreground=theme["fg"],
            borderwidth=1,
            font=("Courier New", 10, "bold"),
        )
        self.style.map(
            "TButton",
            background=[("active", theme["button_active"])],
        )
        self.style.configure("TCheckbutton", background=theme["bg"], foreground=theme["fg"])
        self.style.configure(
            "Treeview",
            background=theme["bg"],
            foreground=theme["fg"],
            fieldbackground=theme["bg"],
        )

        # Specific widgets that use native Tk colors
        if hasattr(self, "log_listbox"):
            self.log_listbox.configure(
                bg=theme["bg"],
                fg=theme["fg"],
                highlightbackground=theme["frame_border"],
                selectbackground=theme["accent2"],
                selectforeground=theme["bg"],
            )
        if hasattr(self, "metrics_canvas"):
            self.metrics_canvas.configure(
                bg=theme["bg"],
                highlightbackground=theme["frame_border"]
            )

        if hasattr(self, "title_label"):
            self.title_label.configure(
                foreground=theme["accent2"],
                font=("Courier New", 16, "bold"),
            )
        if hasattr(self, "intel_badge"):
            self.intel_badge.configure(
                foreground=theme["accent"],
                background=theme["bg"],
                font=("Courier New", 12, "bold"),
            )
        if hasattr(self, "footer_label"):
            self.footer_label.configure(
                foreground=theme["footer_fg"],
                background=theme["bg"],
            )

        # Theme button text
        if hasattr(self, "theme_btn"):
            if self.theme_mode.get() == "paper":
                self.theme_btn.configure(text="Night Ops: OFF")
            else:
                self.theme_btn.configure(text="Night Ops: ON")

        # Matplotlib figure / axes
        if self.fig is not None and self.ax is not None:
            self.fig.patch.set_facecolor(theme["bg"])
            self.ax.set_facecolor(theme["plot_bg"])

            # Axes styling
            for spine in self.ax.spines.values():
                spine.set_color(theme["frame_border"])
            self.ax.tick_params(colors=theme["fg"])
            self.ax.xaxis.label.set_color(theme["fg"])
            self.ax.yaxis.label.set_color(theme["fg"])
            self.ax.title.set_color(theme["accent2"])
            self.ax.grid(color=theme["grid_color"], alpha=0.4)

            if hasattr(self, "canvas_mpl"):
                self.fig.tight_layout()
                self.canvas_mpl.draw_idle()

    def toggle_theme(self):
        """Toggle between Paper Dossier and Night Ops Mode."""
        self.theme_mode.set("night" if self.theme_mode.get() == "paper" else "paper")
        self.apply_theme()
        # Redraw plot with new colors
        self.update_display()

    # ---------- UI SETUP ----------

    def setup_ui(self):
        # ---- PANED WINDOW ----
        paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # ---- LEFT SIDEBAR ----
        left = ttk.Frame(paned, width=280)
        paned.add(left, weight=0)

        # Logs section
        logs_frame = ttk.LabelFrame(left, text=" INTEL DOSSIERS ", padding=5)
        logs_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        btn_frame = ttk.Frame(logs_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Button(btn_frame, text="🔄 Refresh", command=self.load_logs).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="📂 Open CSV...", command=self._open_csv_dialog).pack(side=tk.LEFT)

        self.log_listbox = tk.Listbox(logs_frame, font=('Courier New', 10), activestyle="none")
        self.log_listbox.pack(fill=tk.BOTH, expand=True)
        log_scroll = ttk.Scrollbar(logs_frame, orient="vertical", command=self.log_listbox.yview)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_listbox.configure(yscrollcommand=log_scroll.set)
        self.log_listbox.bind("<<ListboxSelect>>", self.on_log_select)

        # Page & Metrics section
        page_frame = ttk.LabelFrame(left, text=" VIEW & METRICS ", padding=5)
        page_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(page_frame, text="Category:").pack(anchor="w", pady=(0, 2))
        self.category_var = tk.StringVar(value="Economy")
        self.category_menu = ttk.Combobox(
            page_frame,
            textvariable=self.category_var,
            values=list(CATEGORY_MAP.keys()),
            state="disabled",
            width=28
        )
        self.category_menu.pack(fill=tk.X, pady=(0, 5))
        self.category_var.trace_add('write', self._on_category_change)

        ttk.Label(page_frame, text="Time Scale:").pack(anchor="w", pady=(5, 2))
        gran_frame = ttk.Frame(page_frame)
        gran_frame.pack(fill=tk.X, pady=(0, 5))

        self.granularity_radios = []
        granularities = [("Auto", "auto"), ("Daily", "day"), ("Weekly", "week"),
                         ("Monthly", "month"), ("Yearly", "year")]
        for text, value in granularities:
            rb = ttk.Radiobutton(
                gran_frame,
                text=text,
                variable=self.time_granularity,
                value=value,
                command=self.update_display
            )
            rb.pack(side=tk.LEFT, padx=(0, 5))
            self.granularity_radios.append(rb)

        ttk.Label(page_frame, text="Year:").pack(anchor="w", pady=(5, 2))
        self.year_var = tk.StringVar(value="All")
        self.year_menu = ttk.Combobox(page_frame, textvariable=self.year_var, state="disabled", width=10)
        self.year_menu.pack(anchor="w", pady=(0, 10))
        self.year_var.trace_add('write', self.update_display)

        # Metrics checkboxes
        metrics_outer = ttk.LabelFrame(page_frame, text=" METRICS ", padding=5)
        metrics_outer.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        self.metrics_canvas = tk.Canvas(metrics_outer, borderwidth=0, highlightthickness=0)
        self.metrics_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        metrics_scroll = ttk.Scrollbar(metrics_outer, orient="vertical", command=self.metrics_canvas.yview)
        metrics_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.metrics_canvas.configure(yscrollcommand=metrics_scroll.set)

        self.metrics_inner = ttk.Frame(self.metrics_canvas)
        self.metrics_canvas.create_window((0, 0), window=self.metrics_inner, anchor="nw")
        self.metrics_inner.bind(
            "<Configure>",
            lambda e: self.metrics_canvas.configure(scrollregion=self.metrics_canvas.bbox("all"))
        )

        def _on_metrics_mousewheel(event):
            self.metrics_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        self.metrics_canvas.bind("<MouseWheel>", _on_metrics_mousewheel)

        # Select/Clear buttons
        sel_frame = ttk.Frame(page_frame)
        sel_frame.pack(fill=tk.X, pady=(0.2, 0.2))
        ttk.Button(sel_frame, text="Select All", command=lambda: self._set_all_metrics(True)).pack(
            side=tk.LEFT, padx=(0.2, 0.2))
        ttk.Button(sel_frame, text="Clear All", command=lambda: self._set_all_metrics(False)).pack(side=tk.LEFT)

        # ---- RIGHT SIDE WITH SCROLLBAR ----
        right_container = ttk.Frame(paned)
        paned.add(right_container, weight=1)

        # Canvas + Scrollbar
        canvas = tk.Canvas(right_container, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(right_container, orient="vertical", command=canvas.yview)
        right = ttk.Frame(canvas)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas_frame = canvas.create_window((0, 0), window=right, anchor="nw")

        def configure_scroll_region(event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(canvas_frame, width=canvas.winfo_width())

        right.bind("<Configure>", configure_scroll_region)
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(canvas_frame, width=e.width))

        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind("<MouseWheel>", on_mousewheel)
        canvas.bind("<Enter>", lambda e: canvas.bind("<MouseWheel>", on_mousewheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind("<MouseWheel>"))

        # HEADER: title + intel badge + theme toggle
        header_frame = ttk.Frame(right)
        header_frame.pack(fill=tk.X, pady=(5, 5))

        self.intel_badge = ttk.Label(header_frame, text="◆ ECONOMIC INTELLIGENCE DIVISION")
        self.intel_badge.pack(side=tk.LEFT, padx=(5, 10))

        self.title_label = ttk.Label(
            header_frame,
            text="Select a log to begin",
            font=('Courier New', 16, 'bold')
        )
        self.title_label.pack(side=tk.LEFT, padx=5)

        self.theme_btn = ttk.Button(
            header_frame,
            text="Night Ops: OFF",
            command=self.toggle_theme
        )
        self.theme_btn.pack(side=tk.RIGHT, padx=5)

        # Chart section
        chart_frame = ttk.LabelFrame(right, text=" STRATEGIC OVERVIEW ", padding=5)
        chart_frame.pack(fill=tk.X, padx=10, pady=(0, 5))
        chart_frame.configure(height=400)

        self.fig = Figure(figsize=(10, 4), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas_mpl = FigureCanvasTkAgg(self.fig, master=chart_frame)
        self.canvas_widget = self.canvas_mpl.get_tk_widget()
        self.canvas_widget.pack(fill=tk.BOTH, expand=True)

        toolbar_frame = ttk.Frame(chart_frame)
        toolbar_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.toolbar = NavigationToolbar2Tk(self.canvas_mpl, toolbar_frame)
        self.toolbar.update()

        # Buttons
        btn_frame = ttk.Frame(right)
        btn_frame.pack(pady=8)

        self.interactive_btn = ttk.Button(
            btn_frame,
            text="📈 Interactive Chart",
            command=self.show_interactive_chart,
            state="disabled"
        )
        self.interactive_btn.pack(side=tk.LEFT, padx=6)

        self.resource_btn = ttk.Button(
            btn_frame,
            text="📊 Resource Comparison",
            command=self.show_resource_comparison,
            state="disabled"
        )
        self.resource_btn.pack(side=tk.LEFT, padx=6)

        self.export_btn = ttk.Button(
            btn_frame,
            text="💾 Export Plot",
            command=self._export_plot,
            state="disabled"
        )
        self.export_btn.pack(side=tk.LEFT, padx=6)

        # Table section
        table_frame = ttk.LabelFrame(right, text=" LAST 20 ENTRIES (INTEL FEED) ", padding=5)
        table_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        table_frame.configure(height=250)

        self.tree = ttk.Treeview(table_frame, show='headings', height=10)
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side='right', fill='y')
        hsb.pack(side='bottom', fill='x')
        self.tree.pack(fill='both', expand=True)

        ttk.Separator(right, orient='horizontal').pack(fill=tk.X, pady=10)
        self.footer_label = ttk.Label(
            right,
            text="Ruler Intelligence Suite – Intel Analysis Division. Made by Mooning.",
            foreground="#555",
        )
        self.footer_label.pack(pady=(0, 10))

    # ---------- LOG / DATA HANDLING ----------

    def load_logs(self):
        self.log_listbox.delete(0, tk.END)
        self.logs = get_existing_logs()
        self.log_files_map = {}

        if not self.logs:
            self.log_listbox.insert(tk.END, "No log files found.")
            return

        for log in self.logs:
            display_name = log.get('display_name', log.get('name', 'Unknown'))
            self.log_files_map[display_name] = log
            self.log_listbox.insert(tk.END, display_name)

    def _open_csv_dialog(self):
        path = filedialog.askopenfilename(
            title="Select CSV log",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialdir=str(LOGS_DIR) if LOGS_DIR.exists() else str(Path.home())
        )
        if path and os.path.exists(path):
            self._load_log_from_path(path)

    def _load_log_from_path(self, path: str):
        """Carica un log da un percorso specifico"""
        try:
            encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'iso-8859-1']
            df = None
            for encoding in encodings:
                try:
                    df = pd.read_csv(path, encoding=encoding)
                    break
                except (UnicodeDecodeError, KeyError):
                    continue

            if df is None:
                df = pd.read_csv(path)

            df = prepare_dataframe(df)
            df = df.dropna(axis=1, how='all').sort_values('GameDate')

            self.df = df

            basename = os.path.basename(path)
            self.selected_log = {
                'display_name': basename,
                'file_path': path,
                'path': path
            }

            # Title update
            self.title_label.config(text=f"{basename} • INTEL ANALYSIS")

            # Enable controls
            self.category_menu.config(state="readonly")
            self.year_menu.config(state="readonly")
            self.interactive_btn.config(state="normal")
            self.export_btn.config(state="normal")

            for rb in self.granularity_radios:
                rb.config(state="normal")

            years = ["All"] + sorted([str(y) for y in df['GameDate'].dt.year.unique()])
            self.year_menu['values'] = years
            self.year_var.set("All")

            self._rebuild_metrics_checkboxes()
            self.update_display()

            # Add to list if not present
            if basename not in self.log_listbox.get(0, tk.END):
                self.log_listbox.insert(0, basename)
                self.logs.insert(0, self.selected_log)
                self.log_files_map[basename] = self.selected_log

        except Exception as e:
            messagebox.showerror("Load Error", f"Cannot read log file:\n{e}")

    def on_log_select(self, event=None):
        if not self.log_listbox.curselection():
            return
        idx = self.log_listbox.curselection()[0]

        display_name = self.log_listbox.get(idx)

        if display_name in self.log_files_map:
            self.selected_log = self.log_files_map[display_name]
        elif idx < len(self.logs):
            self.selected_log = self.logs[idx]
        else:
            return

        file_path = (
            self.selected_log.get("file_path") or
            self.selected_log.get("path") or
            self.selected_log.get("file") or
            self.selected_log.get("filepath")
        )

        if not file_path or not os.path.exists(file_path):
            messagebox.showerror("Error", f"Log file not found:\n{file_path}")
            return

        self._load_log_from_path(file_path)

    # ---------- METRICS & DISPLAY ----------

    def _on_category_change(self, *args):
        self._rebuild_metrics_checkboxes()
        self.update_display()
        cat = self.category_var.get()
        state = "normal" if cat.startswith("Resources") else "disabled"
        self.resource_btn.config(state=state)

    def _get_available_metrics(self):
        if self.df is None:
            return []
        cols = CATEGORY_MAP.get(self.category_var.get(), [])
        return [c for c in cols if c != 'GameDate' and c in self.df.columns]

    def _rebuild_metrics_checkboxes(self):
        for child in self.metrics_inner.winfo_children():
            child.destroy()
        self.metric_vars.clear()

        metrics = self._get_available_metrics()
        for i, name in enumerate(metrics):
            var = tk.BooleanVar(value=(i < 3))
            chk = ttk.Checkbutton(
                self.metrics_inner,
                text=name,
                variable=var,
                command=self.update_display
            )
            chk.pack(anchor="w", padx=2, pady=1)
            self.metric_vars[name] = var

        self.metrics_canvas.configure(scrollregion=self.metrics_canvas.bbox("all"))

    def _set_all_metrics(self, state: bool):
        for var in self.metric_vars.values():
            var.set(state)
        self.update_display()

    def _apply_time_granularity(self, df: pd.DataFrame) -> pd.DataFrame:
        gran = self.time_granularity.get()
        if gran in ("auto", "day"):
            return df

        df = df.copy()
        if "GameDate" not in df.columns:
            return df

        df = df.set_index("GameDate")

        for col in df.columns:
            try:
                df[col] = pd.to_numeric(df[col])
            except Exception:
                pass

        numeric_cols = df.select_dtypes(include=["number"]).columns
        df_num = df[numeric_cols]

        try:
            if gran == "week":
                df_res = df_num.resample("W").mean()
            elif gran == "month":
                df_res = df_num.resample("MS").mean()
            elif gran == "year":
                df_res = df_num.resample("YS").mean()
            else:
                return df.reset_index()
        except Exception:
            return df.reset_index()

        df_res = df_res.reset_index()
        df_res["GameDate_str"] = df_res["GameDate"].dt.strftime("%Y-%m-%d")
        return df_res

    def _setup_time_axis(self, dates):
        granularity = self.time_granularity.get()

        if granularity == "auto":
            date_range = dates.max() - dates.min()
            if date_range.days > 365 * 5:
                self.ax.xaxis.set_major_locator(mdates.YearLocator())
                self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
            elif date_range.days > 180:
                self.ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
                self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
            elif date_range.days > 30:
                self.ax.xaxis.set_major_locator(mdates.MonthLocator())
                self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
            else:
                self.ax.xaxis.set_major_locator(mdates.DayLocator())
                self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%d %b'))
        elif granularity == "day":
            self.ax.xaxis.set_major_locator(mdates.DayLocator())
            self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%d %b'))
        elif granularity == "week":
            self.ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO))
            self.ax.xaxis.set_major_formatter(mdates.DateFormatter('W%W %Y'))
        elif granularity == "month":
            self.ax.xaxis.set_major_locator(mdates.MonthLocator())
            self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
        elif granularity == "year":
            self.ax.xaxis.set_major_locator(mdates.YearLocator())
            self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))

    def update_display(self, *args):
        if self.df is None:
            return

        theme = self._current_theme()

        temp_df = self.df.copy()
        if self.year_var.get() != "All":
            temp_df = temp_df[temp_df['GameDate'].dt.year == int(self.year_var.get())]

        temp_df = self._apply_time_granularity(temp_df)

        selected = [name for name, var in self.metric_vars.items() if var.get()]

        # Update plot
        self.ax.clear()
        self.ax.set_facecolor(theme["plot_bg"])

        # line colors: intel palette
        colors = ['#004400', '#550000', '#0A1A3A', '#556B2F', '#B36B00', '#808080', '#AA8800', '#333366']

        if selected:
            x = temp_df["GameDate"]
            if pd.api.types.is_datetime64_any_dtype(x):
                self._setup_time_axis(x)

            for i, col in enumerate(selected):
                if col in temp_df.columns:
                    try:
                        y = pd.to_numeric(temp_df[col], errors="coerce")
                        color = colors[i % len(colors)]
                        self.ax.plot(x, y, label=col, color=color, linewidth=1.5, alpha=0.85, marker='o', markersize=3)
                    except Exception:
                        continue

            self.ax.set_xlabel("Game Date", color=theme["fg"])
            self.ax.set_ylabel("Value", color=theme["fg"])
            self.ax.grid(True, alpha=0.4, color=theme["grid_color"])
            self.ax.tick_params(axis='x', rotation=45, colors=theme["fg"])
            self.ax.tick_params(axis='y', colors=theme["fg"])

            if self.selected_log:
                title = f"{self.selected_log.get('display_name', 'Unknown')} • {self.category_var.get()}"
                self.ax.set_title(title, fontsize=12, fontweight='bold', color=theme["accent2"])

            legend = self.ax.legend(loc="best", fontsize='small')
            if legend:
                for text in legend.get_texts():
                    text.set_color(theme["fg"])
                       # FIX: legend in Night Ops
                if self.theme_mode.get() == "night":
                    legend.get_frame().set_facecolor("#1A1F24")   # sfondo scuro
                    legend.get_frame().set_edgecolor("#444444")
                    legend.get_frame().set_alpha(0.9)
                else:
                    legend.get_frame().set_facecolor("#F0E6D2")
                    legend.get_frame().set_edgecolor("#555555")
                    legend.get_frame().set_alpha(0.95)

        self.fig.tight_layout()
        self.canvas_mpl.draw()

        # Update table
        self.tree.delete(*self.tree.get_children())
        if selected:
            last_rows = temp_df.tail(20)
            cols = ["GameDate_str"] + selected

            self.tree["columns"] = cols
            self.tree["show"] = "headings"

            for c in cols:
                header = "GameDate" if c == "GameDate_str" else c
                self.tree.heading(c, text=header)
                width = max(100, min(200, len(header) * 8 + 20))
                self.tree.column(c, width=width, anchor="center")

            for _, row in last_rows.iterrows():
                values = []
                for c in cols:
                    if c == "GameDate_str":
                        values.append(row.get("GameDate_str", ""))
                    else:
                        values.append(_format_value(c, row.get(c, "")))
                self.tree.insert("", "end", values=values)

    def _export_plot(self):
        if self.df is None:
            messagebox.showwarning("No Data", "No data to export")
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("All files", "*.*")],
            initialfile=f"SR2030_plot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        )
        if filename:
            try:
                self.fig.savefig(filename, dpi=300, bbox_inches='tight')
                messagebox.showinfo("Success", f"Plot exported to:\n{filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Could not export plot:\n{e}")

    @staticmethod
    def _robust_rescale_axis(ax):
        ymin = None
        ymax = None
        for line in ax.get_lines():
            if not line.get_visible():
                continue
            y = np.asarray(line.get_ydata(), dtype=float)
            y = y[np.isfinite(y)]
            if y.size == 0:
                continue
            low = float(np.min(y))
            high = float(np.max(y))
            ymin = low if ymin is None else min(ymin, low)
            ymax = high if ymax is None else max(ymax, high)
        if ymin is None or ymax is None:
            return
        if ymin == ymax:
            pad = 1.0 if ymin == 0 else abs(ymin) * 0.05
            ax.set_ylim(ymin - pad, ymax + pad)
        else:
            pad = (ymax - ymin) * 0.10
            ax.set_ylim(ymin - pad, ymax + pad)

    # ---------- INTERACTIVE CHART ----------

    def show_interactive_chart(self):
        """Show interactive chart with checkboxes (original SR2030 style)"""
        if self.df is None:
            return

        try:
            theme = self._current_theme()

            gdf = self.df.copy()
            if self.year_var.get() != "All":
                gdf = gdf[gdf['GameDate'].dt.year == int(self.year_var.get())]
            gdf = self._apply_time_granularity(gdf)

            metrics = [name for name, var in self.metric_vars.items() if var.get()]
            if not metrics:
                return messagebox.showwarning("No Data", "No metrics selected")

            fig, ax1 = plt.subplots(figsize=(14, 8))
            fig.subplots_adjust(left=0.22, right=0.94, bottom=0.1)

            fig.patch.set_facecolor(theme["bg"])
            ax1.set_facecolor(theme["plot_bg"])

            lines, labels, label_texts = [], [], {}
            ax2 = None

            # Right axis for Treasury
            if "Treasury" in metrics:
                ax2 = ax1.twinx()
                tre = gdf["Treasury"]
                t_line, = ax2.plot(gdf["GameDate"], tre, linewidth=2.5,
                                   label="Treasury (Right Axis)",
                                   color="#004400")
                lines.append(t_line)
                labels.append("Treasury (Right Axis)")
                metrics.remove("Treasury")
                texts = []
                if not gdf.empty and pd.notna(tre.iloc[-1]):
                    txt = ax2.text(
                        gdf["GameDate"].iloc[-1],
                        tre.iloc[-1],
                        _format_value("Treasury", tre.iloc[-1]),
                        fontsize=9, fontweight='bold',
                        ha='left', va='center', clip_on=True,
                        color=theme["fg"]
                    )
                    texts.append(txt)
                label_texts["Treasury (Right Axis)"] = texts
                ax2.set_ylabel("Treasury", color=theme["fg"])
                ax2.ticklabel_format(style='plain', axis='y')
                ax2.tick_params(colors=theme["fg"])

            # Other metrics (left axis)
            intel_colors = ['#550000', '#0A1A3A', '#556B2F', '#B36B00', '#808080', '#AA8800', '#333366']
            for i, col in enumerate(metrics):
                if col not in gdf.columns:
                    continue
                series = gdf[col]
                color = intel_colors[i % len(intel_colors)]
                line, = ax1.plot(gdf["GameDate"], series, marker='o', label=col, color=color)
                lines.append(line)
                labels.append(col)
                texts = []
                for x, y in zip(gdf["GameDate"], series):
                    if pd.notna(y):
                        txt = ax1.text(
                            x, y, _format_value(col, y),
                            fontsize=7, ha='center', va='bottom',
                            alpha=0.8, clip_on=True,
                            color=theme["fg"]
                        )
                        texts.append(txt)
                label_texts[col] = texts

            ax1.set_xlabel("Date", color=theme["fg"])
            ax1.set_ylabel("Value", color=theme["fg"])

            game_name = self.selected_log.get('game_name', self.selected_log.get('display_name', 'Unknown Game'))
            ax1.set_title(f"{game_name} • {self.category_var.get()} – INTEL VIEW",
                          fontsize=16, fontweight='bold', color=theme["accent2"])

            for spine in ax1.spines.values():
                spine.set_color(theme["frame_border"])
            ax1.tick_params(colors=theme["fg"])
            ax1.grid(True, linestyle='--', linewidth=0.5, color=theme["grid_color"])

            # Checkbox area
            rax = plt.axes([0.025, 0.25, 0.16, 0.45])
            rax.set_facecolor((0.12, 0.14, 0.16, 0.9) if self.theme_mode.get() == "night" else (0.97, 0.97, 0.97, 0.75))
            vis = [ln.get_visible() for ln in lines]
            check = CheckButtons(rax, labels, vis)
            for lbl in check.labels:
                lbl.set_fontsize(10)
                lbl.set_color(theme["fg"])

            # Buttons
            ax_btn = plt.axes([0.025, 0.72, 0.16, 0.05])
            toggle_btn = Button(ax_btn, "Hide / Show All",
                                color=(0.2, 0.23, 0.27) if self.theme_mode.get() == "night" else (0.9, 0.9, 0.9),
                                hovercolor=(0.3, 0.35, 0.4) if self.theme_mode.get() == "night" else (0.8, 0.8, 0.8))
            ax_rescale = plt.axes([0.025, 0.80, 0.16, 0.05])
            rescale_btn = Button(ax_rescale, "Rescale Axes",
                                 color=(0.2, 0.23, 0.27) if self.theme_mode.get() == "night" else (0.9, 0.9, 0.9),
                                 hovercolor=(0.3, 0.35, 0.4) if self.theme_mode.get() == "night" else (0.8, 0.8, 0.8))

            all_visible = True

            def robust_rescale(event=None):
                self._robust_rescale_axis(ax1)
                if ax2:
                    self._robust_rescale_axis(ax2)
                fig.canvas.draw_idle()

            def toggle_all(event):
                nonlocal all_visible
                all_visible = not all_visible
                for line in lines:
                    line.set_visible(all_visible)
                for texts in label_texts.values():
                    for t in texts:
                        t.set_visible(all_visible)
                robust_rescale()

            toggle_btn.on_clicked(toggle_all)
            rescale_btn.on_clicked(robust_rescale)

            def toggle(label):
                i = labels.index(label)
                line = lines[i]
                new_vis = not line.get_visible()
                line.set_visible(new_vis)
                for t in label_texts.get(label, []):
                    t.set_visible(new_vis)
                robust_rescale()

            check.on_clicked(toggle)

            # Legend
            l1, lab1 = ax1.get_legend_handles_labels()
            if ax2:
                l2, lab2 = ax2.get_legend_handles_labels()
                leg = ax1.legend(l1 + l2, lab1 + lab2, loc='best', fontsize=9)
            else:
                leg = ax1.legend(l1, lab1, loc='best', fontsize=9)
            if leg:
                for text in leg.get_texts():
                    text.set_color(theme["fg"])

            fig.autofmt_xdate(rotation=45)
            robust_rescale()
            plt.show()

        except Exception as e:
            messagebox.showerror("Chart Error", f"Cannot create chart:\n{e}")

    # ---------- RESOURCE COMPARISON ----------

    def show_resource_comparison(self):
        """Show resource comparison chart"""
        if self.df is None:
            return

        # Resource selector dialog
        resource_dialog = tk.Toplevel(self.root)
        resource_dialog.title("Select Resource")
        resource_dialog.geometry("300x400")
        resource_dialog.transient(self.root)
        resource_dialog.grab_set()

        theme = self._current_theme()
        resource_dialog.configure(bg=theme["bg"])

        ttk.Label(resource_dialog, text="Select a resource:", font=('Courier New', 12, 'bold')).pack(pady=10)

        resources = _resource_names_from_stock()
        selected_resource = tk.StringVar(value=resources[0])

        listbox = tk.Listbox(resource_dialog, height=11)
        for res in resources:
            listbox.insert(tk.END, res)
        listbox.selection_set(0)
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        def on_select():
            if listbox.curselection():
                selected_resource.set(listbox.get(listbox.curselection()[0]))
                resource_dialog.destroy()
                self._show_resource_chart(selected_resource.get())

        ttk.Button(resource_dialog, text="Show Chart", command=on_select).pack(pady=10)
        resource_dialog.wait_window()

    def _show_resource_chart(self, res_name: str):
        try:
            theme = self._current_theme()
            cols = _cols_for_resource(res_name)
            gdf = self.df.copy()

            if self.year_var.get() != "All":
                gdf = gdf[gdf['GameDate'].dt.year == int(self.year_var.get())]
            gdf = self._apply_time_granularity(gdf)

            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 9), sharex=True)
            fig.subplots_adjust(hspace=0.25)

            fig.patch.set_facecolor(theme["bg"])
            ax1.set_facecolor(theme["plot_bg"])
            ax2.set_facecolor(theme["plot_bg"])

            # TOP: prices
            if cols["cost"] in gdf.columns:
                ax1.plot(gdf["GameDate"], gdf[cols["cost"]], marker='o',
                         label=f"{res_name} Production Cost", color="#0A1A3A")
                for x, y in zip(gdf["GameDate"], gdf[cols["cost"]]):
                    if pd.notna(y):
                        ax1.text(x, y, f"${y:.2f}", fontsize=7, ha='center', va='bottom',
                                 clip_on=True, color=theme["fg"])

            if cols["price"] in gdf.columns:
                ax1.plot(gdf["GameDate"], gdf[cols["price"]], marker='o',
                         label=f"{res_name} Market Price", color="#B36B00")
                for x, y in zip(gdf["GameDate"], gdf[cols["price"]]):
                    if pd.notna(y):
                        ax1.text(x, y, f"${y:.2f}", fontsize=7, ha='center', va='bottom',
                                 clip_on=True, color=theme["fg"])

            ax1.legend(loc='best')
            ax1.set_ylabel("Price / Cost", color=theme["fg"])
            ax1.grid(True, linestyle='--', linewidth=0.5, color=theme["grid_color"])
            ax1.tick_params(colors=theme["fg"])

            # BOTTOM: stock/trades
            if cols["stock"] in gdf.columns:
                ax2.plot(gdf["GameDate"], gdf[cols["stock"]], marker='o',
                         label=f"{res_name} Stock", color="#004400")
                for x, y in zip(gdf["GameDate"], gdf[cols["stock"]]):
                    if pd.notna(y):
                        ax2.text(x, y, f"{y:,.0f}", fontsize=7, ha='center', va='bottom',
                                 clip_on=True, color=theme["fg"])

            if cols["trades"] in gdf.columns:
                ax2.plot(gdf["GameDate"], gdf[cols["trades"]], marker='o',
                         label=f"{res_name} Imports (Trades)", color="#550000")
                for x, y in zip(gdf["GameDate"], gdf[cols["trades"]]):
                    if pd.notna(y):
                        ax2.text(x, y, f"{y:,.0f}", fontsize=7, ha='center', va='bottom',
                                 clip_on=True, color=theme["fg"])

            ax2.legend(loc='best')
            ax2.set_ylabel("Stock / Imports", color=theme["fg"])
            ax2.grid(True, linestyle='--', linewidth=0.5, color=theme["grid_color"])
            ax2.tick_params(colors=theme["fg"])

            for ax in (ax1, ax2):
                for spine in ax.spines.values():
                    spine.set_color(theme["frame_border"])

            game_name = self.selected_log.get('game_name', self.selected_log.get('display_name', 'Unknown Game'))
            fig.suptitle(f"{game_name} • {res_name} — Resource Overview",
                         fontsize=16, fontweight='bold', color=theme["accent2"])
            fig.autofmt_xdate(rotation=45)

            self._robust_rescale_axis(ax1)
            self._robust_rescale_axis(ax2)

            plt.show()
        except Exception as e:
            messagebox.showerror("Chart Error", f"Cannot create resource chart:\n{e}")


def show_simple_analytics(log_file: str = None):
    """Entry point for standalone or launcher use.
    
    Args:
        log_file: Optional path to a CSV log file to open immediately
    """
    root = tk.Toplevel() if tk._default_root else tk.Tk()
    AnalyticsApp(root, initial_log=log_file)
    if not tk._default_root:
        root.mainloop()


if __name__ == "__main__":
    import sys
    initial_log = sys.argv[1] if len(sys.argv) > 1 else None
    root = tk.Tk()
    AnalyticsApp(root, initial_log=initial_log)
    root.mainloop()
