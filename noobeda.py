#!/usr/bin/env python3
"""
NoobEDA - The Zero-Bloat, Beginner-Friendly FPGA & Digital Design Studio
Cross-Platform GUI orchestrator for open-source EDA tools:
GHDL, Yosys, GTKWave, Icarus Verilog, netlistsvg, and openFPGALoader.
"""

import os
import sys
import re
import json
import shutil
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# Enable High-DPI awareness on Windows for crisp typography
if sys.platform.startswith("win"):
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

# ==============================================================================
# Dynamic Toolchain Discovery (Cross-Platform: Windows / Linux / macOS)
# ==============================================================================
def configure_toolchain_environment():
    """Configures environment variables and PATH for toolchains across platforms."""
    # If OSS CAD Suite is present on Windows, prioritize its lib and bin to prevent 0xC0000139 DLL collisions
    if sys.platform.startswith("win"):
        oss_candidates = [
            r"C:\tools\oss-cad-suite",
            os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "oss-cad-suite"),
        ]
        for oss in oss_candidates:
            if os.path.isdir(oss):
                os.environ["YOSYSHQ_ROOT"] = oss + os.sep
                bin_dir = os.path.join(oss, "bin")
                lib_dir = os.path.join(oss, "lib")
                os.environ["PATH"] = f"{bin_dir}{os.pathsep}{lib_dir}{os.pathsep}" + os.environ.get("PATH", "")
                break

configure_toolchain_environment()

def get_candidate_tool_dirs():
    """Returns candidate tool installation paths across operating systems."""
    dirs = []
    if sys.platform.startswith("win"):
        appdata = os.environ.get("APPDATA", "")
        localappdata = os.environ.get("LOCALAPPDATA", "")
        prog_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        prog_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")

        candidates = [
            r"C:\tools\oss-cad-suite\bin",
            r"C:\tools\oss-cad-suite\lib",
            r"C:\tools\gtkwave-win64\gtkwave64\bin",
            r"C:\tools\ghdl\bin",
            os.path.join(appdata, "npm"),
            os.path.join(localappdata, "Programs", "Python"),
            os.path.join(prog_files, "oss-cad-suite", "bin"),
            os.path.join(prog_files, "ghdl", "bin"),
            os.path.join(prog_files, "gtkwave", "bin"),
            os.path.join(prog_files_x86, "GHDL", "bin"),
        ]
        dirs.extend([p for p in candidates if os.path.isdir(p)])
    else:
        home = os.path.expanduser("~")
        candidates = [
            "/usr/bin",
            "/usr/local/bin",
            "/opt/homebrew/bin",
            "/opt/homebrew/sbin",
            "/opt/local/bin",
            os.path.join(home, ".local", "bin"),
            os.path.join(home, ".cargo", "bin"),
            os.path.join(home, "node_modules", ".bin"),
            "/usr/lib/ghdl",
        ]
        dirs.extend([p for p in candidates if os.path.isdir(p)])
    return dirs

# Inject candidate directories into PATH temporarily if not already present
for p in get_candidate_tool_dirs():
    if p not in os.environ.get("PATH", ""):
        os.environ["PATH"] = f"{p}{os.pathsep}" + os.environ.get("PATH", "")

def find_binary(name):
    """Dynamically locate an executable in PATH with cross-platform fallback."""
    found = shutil.which(name)
    if found:
        return found
    if sys.platform.startswith("win"):
        for ext in [".cmd", ".exe", ".bat"]:
            found = shutil.which(f"{name}{ext}")
            if found:
                return found
    return name

GHDL_BIN = find_binary("ghdl")
YOSYS_BIN = find_binary("yosys")
IVERILOG_BIN = find_binary("iverilog")
VVP_BIN = find_binary("vvp")
GTKWAVE_BIN = find_binary("gtkwave")
OPENFPGA_BIN = find_binary("openFPGALoader")
NETLISTSVG_BIN = find_binary("netlistsvg")

def extract_hdl_entities(filepath):
    """Parses HDL source file to find declared entity (VHDL) or module (Verilog) names."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception:
        return []

    lower_ext = os.path.splitext(filepath)[1].lower()
    if lower_ext in [".vhd", ".vhdl"]:
        matches = re.findall(r"(?i)\bentity\s+([a-zA-Z0-9_]+)\s+is", content)
        return matches
    elif lower_ext in [".v", ".sv"]:
        matches = re.findall(r"(?i)\bmodule\s+([a-zA-Z0-9_]+)\b", content)
        return matches
    return []

def sanitize_netlist_json(json_path):
    """Sanitizes Yosys JSON netlist to strictly satisfy netlistsvg schema (tri-states and inouts)."""
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        def sanitize_val(val):
            if isinstance(val, list):
                return [sanitize_val(x) for x in val]
            elif isinstance(val, dict):
                return {k: sanitize_val(v) for k, v in val.items()}
            elif val in ("z", "Z", "Z0", "Z1", "z0", "z1"):
                return "x"
            return val

        for mod in data.get("modules", {}).values():
            for port in mod.get("ports", {}).values():
                if port.get("direction") == "inout":
                    port["direction"] = "output"
            for cell in mod.get("cells", {}).values():
                if "connections" in cell:
                    cell["connections"] = sanitize_val(cell["connections"])

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        return True
    except Exception as e:
        print(f"Netlist sanitization notice: {e}")
        return False

# ==============================================================================
# Main Application
# ==============================================================================
class NoobEDAApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("NoobEDA - Open-Source FPGA & Digital Design Studio")
        self.geometry("1260x820")
        self.minsize(980, 680)
        self.configure(bg="#181825")

        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.configure_styles()

        # Workspace State - Empty by default for fresh session adaptability
        self.work_dir = tk.StringVar(value="")
        self.hdl_file = tk.StringVar(value="")
        self.top_module = tk.StringVar(value="")
        self.tb_file = tk.StringVar(value="")
        self.cable_mode = tk.StringVar(value="USB-Blaster (JTAG)")

        # Process management for aborting tasks safely
        self.current_process = None

        # Terminal command history
        self._cmd_history = []
        self._history_idx = 0

        # Drag-and-drop state
        self._dragged_file = None
        self._drag_data = {}

        # Branding Icon (Cross-Platform)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        ico_path = os.path.join(base_dir, "assets", "logo.ico")
        png_path = os.path.join(base_dir, "assets", "logo.png")
        if sys.platform.startswith("win") and os.path.exists(ico_path):
            try:
                self.iconbitmap(ico_path)
            except Exception:
                pass
        elif os.path.exists(png_path):
            try:
                self._app_icon = tk.PhotoImage(file=png_path)
                self.iconphoto(True, self._app_icon)
            except Exception:
                pass

        # File maps for dropdown selection
        self._design_map = {}
        self._tb_map = {}

        self.create_layout()

    def configure_styles(self):
        dark_bg = "#181825"
        card_bg = "#1e1e2e"
        accent_blue = "#89b4fa"
        fg_white = "#cdd6f4"
        entry_bg = "#313244"

        self.style.configure(".", background=dark_bg, foreground=fg_white, font=("Segoe UI", 10))
        self.style.configure("TFrame", background=dark_bg)
        self.style.configure("Card.TFrame", background=card_bg, relief="flat")
        self.style.configure("TLabel", background=dark_bg, foreground=fg_white)
        self.style.configure("Card.TLabel", background=card_bg, foreground=fg_white)
        self.style.configure("Header.TLabel", background=card_bg, foreground=accent_blue, font=("Segoe UI", 11, "bold"))
        self.style.configure("Title.TLabel", background=dark_bg, foreground="#cba6f7", font=("Segoe UI", 15, "bold"))

        self.style.configure("TButton", font=("Segoe UI", 9, "bold"), padding=6, background=entry_bg, foreground=fg_white)
        self.style.map("TButton", background=[("active", "#45475a")])

        self.style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), padding=6, background="#3b82f6", foreground="#ffffff")
        self.style.map("Primary.TButton", background=[("active", "#2563eb")])

        self.style.configure("Success.TButton", font=("Segoe UI", 10, "bold"), padding=6, background="#10b981", foreground="#ffffff")
        self.style.map("Success.TButton", background=[("active", "#059669")])

        self.style.configure("Warning.TButton", font=("Segoe UI", 10, "bold"), padding=6, background="#f59e0b", foreground="#111827")
        self.style.map("Warning.TButton", background=[("active", "#d97706")])

        self.style.configure("TNotebook", background=dark_bg, tabmargins=[2, 5, 2, 0])
        self.style.configure("TNotebook.Tab", background=card_bg, foreground=fg_white, padding=[12, 6], font=("Segoe UI", 10, "bold"))
        self.style.map("TNotebook.Tab", background=[("selected", "#3b82f6")], foreground=[("selected", "#ffffff")])

        # Treeview styling for file explorer
        self.style.configure("Treeview", background="#181825", foreground="#cdd6f4", fieldbackground="#181825", rowheight=24, font=("Segoe UI", 9))
        self.style.map("Treeview", background=[("selected", "#313244")], foreground=[("selected", "#89b4fa")])

    def create_layout(self):
        # Header Bar
        header = ttk.Frame(self, padding=(16, 10))
        header.pack(fill=tk.X)

        title = ttk.Label(header, text="⚡ NoobEDA - Open-Source FPGA Studio", style="Title.TLabel")
        title.pack(side=tk.LEFT)

        status_btn = ttk.Button(header, text="🔍 Check Toolchain", style="TButton", command=self.show_toolchain_diagnostics)
        status_btn.pack(side=tk.RIGHT, pady=4)

        # Workspace Directory Picker Bar
        ws_bar = ttk.Frame(self, padding=(16, 2, 16, 8))
        ws_bar.pack(fill=tk.X)
        ttk.Label(ws_bar, text="📁 Active Workspace:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 6))
        ent_ws = ttk.Entry(ws_bar, textvariable=self.work_dir)
        ent_ws.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(ws_bar, text="Open Project Folder", width=18, command=self.browse_workspace).pack(side=tk.RIGHT, padx=(6, 0))
        ttk.Button(ws_bar, text="🔄 Rescan Files", width=14, command=self.rescan_workspace).pack(side=tk.RIGHT, padx=(6, 0))

        # Main Paned Window (Split into Top Half and Bottom Terminal)
        self.v_paned = ttk.PanedWindow(self, orient=tk.VERTICAL)
        self.v_paned.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        # Top Paned Window (Split into Top-Left File Explorer & Top-Right Operations)
        self.h_paned = ttk.PanedWindow(self.v_paned, orient=tk.HORIZONTAL)
        self.v_paned.add(self.h_paned, weight=3)

        # ======================================================================
        # TOP-LEFT: Project File Explorer (Clickable & Drag-and-Drop)
        # ======================================================================
        left_frame = ttk.Frame(self.h_paned, padding=8, style="Card.TFrame")
        self.h_paned.add(left_frame, weight=1)

        explorer_hdr = ttk.Frame(left_frame, style="Card.TFrame")
        explorer_hdr.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(explorer_hdr, text="📂 Project File Explorer", style="Header.TLabel").pack(side=tk.LEFT)
        ttk.Label(explorer_hdr, text="Drag to Top/TB or double-click to edit", font=("Segoe UI", 8, "italic"), foreground="#a6adc8").pack(side=tk.RIGHT)

        tree_scroll_y = ttk.Scrollbar(left_frame, orient=tk.VERTICAL)
        self.file_tree = ttk.Treeview(left_frame, selectmode="browse", yscrollcommand=tree_scroll_y.set)
        tree_scroll_y.config(command=self.file_tree.yview)

        self.file_tree.heading("#0", text="  Workspace Files & Entities", anchor=tk.W)
        self.file_tree.pack(fill=tk.BOTH, expand=True, side=tk.TOP)
        tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y, before=self.file_tree)

        # File Tree Event Bindings (Open in editor + Drag-and-Drop)
        self.file_tree.bind("<Double-Button-1>", self.on_file_double_click)
        self.file_tree.bind("<ButtonPress-1>", self.on_drag_start)
        self.file_tree.bind("<B1-Motion>", self.on_drag_motion)
        self.file_tree.bind("<ButtonRelease-1>", self.on_drag_end)

        # Context Menu for Right-Click
        self.tree_menu = tk.Menu(self, tearoff=0, bg="#1e1e2e", fg="#cdd6f4")
        self.tree_menu.add_command(label="⬆ Set as Top HDL File", command=self.set_selected_as_top)
        self.tree_menu.add_command(label="🧪 Set as Testbench File", command=self.set_selected_as_tb)
        self.tree_menu.add_separator()
        self.tree_menu.add_command(label="✏️ Open in Text Editor", command=self.open_selected_in_editor)
        self.file_tree.bind("<Button-3>", self.show_tree_context_menu)

        # Quick Actions Below Explorer
        btn_bar = ttk.Frame(left_frame, style="Card.TFrame")
        btn_bar.pack(fill=tk.X, pady=(6, 0))
        ttk.Button(btn_bar, text="⬆ Set Top", width=10, command=self.set_selected_as_top).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(btn_bar, text="🧪 Set TB", width=10, command=self.set_selected_as_tb).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(btn_bar, text="✏️ Edit", width=8, command=self.open_selected_in_editor).pack(side=tk.RIGHT)

        # ======================================================================
        # TOP-RIGHT: Operations (Phases 1-5 with 3x Drop Zones & Decision Tree)
        # ======================================================================
        right_frame = ttk.Frame(self.h_paned, style="Card.TFrame")
        self.h_paned.add(right_frame, weight=3)

        self.notebook = ttk.Notebook(right_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1: Operations
        tab_ops = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab_ops, text="  Operations (5 Phases)  ")
        self.build_operations_tab(tab_ops)

        # Tab 2: Decision Tree Guide
        tab_tree = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab_tree, text="  Decision Tree & Rules  ")
        self.build_tree_tab(tab_tree)

        # ======================================================================
        # BOTTOM: Interactive Terminal & Execution Console
        # ======================================================================
        term_frame = ttk.Frame(self.v_paned, padding=8, style="Card.TFrame")
        self.v_paned.add(term_frame, weight=2)

        term_hdr = ttk.Frame(term_frame, style="Card.TFrame")
        term_hdr.pack(fill=tk.X, pady=(0, 4))

        lbl_term = ttk.Label(term_hdr, text="💻 Interactive Terminal & Execution Console", style="Header.TLabel")
        lbl_term.pack(side=tk.LEFT)

        btn_abort = ttk.Button(term_hdr, text="⏹ Abort", width=9, style="Warning.TButton", command=self.abort_current_task)
        btn_abort.pack(side=tk.RIGHT, padx=(4, 0))

        btn_clear = ttk.Button(term_hdr, text="🧹 Clear", width=8, command=self.clear_console)
        btn_clear.pack(side=tk.RIGHT, padx=(4, 0))

        btn_copy = ttk.Button(term_hdr, text="📋 Copy", width=8, command=self.copy_console)
        btn_copy.pack(side=tk.RIGHT, padx=(4, 0))

        # Terminal Output Box
        self.console = tk.Text(term_frame, bg="#0d0f18", fg="#a6e3a1", font=("Consolas", 10), insertbackground="#ffffff", relief="flat")
        self.console.pack(fill=tk.BOTH, expand=True, side=tk.TOP)

        term_scroll = ttk.Scrollbar(self.console, orient=tk.VERTICAL, command=self.console.yview)
        term_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.console.config(yscrollcommand=term_scroll.set)

        # Terminal Command Prompt Bar
        term_input_bar = ttk.Frame(term_frame, style="Card.TFrame")
        term_input_bar.pack(fill=tk.X, pady=(6, 0), side=tk.BOTTOM)

        self.lbl_prompt = ttk.Label(term_input_bar, text="noobeda:~$ ", font=("Consolas", 10, "bold"), foreground="#89b4fa")
        self.lbl_prompt.pack(side=tk.LEFT, padx=(2, 6))

        self.term_entry = ttk.Entry(term_input_bar, font=("Consolas", 10))
        self.term_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.term_entry.bind("<Return>", self.on_terminal_enter)
        self.term_entry.bind("<Up>", self.on_terminal_history_up)
        self.term_entry.bind("<Down>", self.on_terminal_history_down)

        btn_run = ttk.Button(term_input_bar, text="▶ Run", width=7, style="Primary.TButton", command=self.on_terminal_enter)
        btn_run.pack(side=tk.RIGHT, padx=(6, 0))

    def build_operations_tab(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)
        parent.columnconfigure(2, weight=1)

        # ================= Phase 1 & 2 =================
        p12 = ttk.Frame(parent, padding=10, style="Card.TFrame")
        p12.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)

        ttk.Label(p12, text="Phase 1 & 2: Setup & Elaboration", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 6))

        # 3X SIZED DROP BOX for Top HDL File
        self.drop_top_frame = tk.Frame(p12, bg="#11111b", bd=2, relief="groove", padx=8, pady=8)
        self.drop_top_frame.pack(fill=tk.X, pady=(2, 6))
        
        self.lbl_drop_top_title = tk.Label(self.drop_top_frame, text="📂 DROP TOP HDL FILE HERE", font=("Segoe UI", 9, "bold"), bg="#11111b", fg="#89b4fa")
        self.lbl_drop_top_title.pack(anchor=tk.W)
        self.lbl_drop_top_file = tk.Label(self.drop_top_frame, text="No file selected (Drag from left or Browse)", font=("Segoe UI", 8), bg="#11111b", fg="#a6adc8")
        self.lbl_drop_top_file.pack(anchor=tk.W, pady=(2, 0))
        self.lbl_drop_top_ent = tk.Label(self.drop_top_frame, text="Entity: -", font=("Segoe UI", 8, "bold"), bg="#11111b", fg="#a6e3a1")
        self.lbl_drop_top_ent.pack(anchor=tk.W, pady=(2, 0))

        ttk.Label(p12, text="Detected Modules (or select):", style="Card.TLabel").pack(anchor=tk.W)
        self.combo_hdl = ttk.Combobox(p12, state="readonly", values=["(Open a project folder to list files)"])
        self.combo_hdl.current(0)
        self.combo_hdl.pack(fill=tk.X, pady=(2, 6))
        self.combo_hdl.bind("<<ComboboxSelected>>", self.on_hdl_selected)

        ttk.Label(p12, text="Top Entity / Module Name:", style="Card.TLabel").pack(anchor=tk.W)
        ent_top = ttk.Entry(p12, textvariable=self.top_module)
        ent_top.pack(fill=tk.X, pady=(2, 6))

        # Actions
        btn_elab = ttk.Button(p12, text="▶ Run Analysis & Elaboration", style="Primary.TButton", command=self.run_elaboration)
        btn_elab.pack(fill=tk.X, pady=(4, 4))

        btn_latch = ttk.Button(p12, text="🔍 Check Inferred Latches / Warnings", style="TButton", command=self.check_latches)
        btn_latch.pack(fill=tk.X)

        # ================= Phase 3 (Simulation) =================
        p3 = ttk.Frame(parent, padding=10, style="Card.TFrame")
        p3.grid(row=0, column=1, sticky="nsew", padx=4, pady=4)

        ttk.Label(p3, text="Phase 3: Logic Simulation", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 6))

        # 3X SIZED DROP BOX for Testbench File
        self.drop_tb_frame = tk.Frame(p3, bg="#11111b", bd=2, relief="groove", padx=8, pady=8)
        self.drop_tb_frame.pack(fill=tk.X, pady=(2, 6))
        
        self.lbl_drop_tb_title = tk.Label(self.drop_tb_frame, text="🧪 DROP TESTBENCH FILE HERE", font=("Segoe UI", 9, "bold"), bg="#11111b", fg="#a6e3a1")
        self.lbl_drop_tb_title.pack(anchor=tk.W)
        self.lbl_drop_tb_file = tk.Label(self.drop_tb_frame, text="No testbench selected (Drag from left or Browse)", font=("Segoe UI", 8), bg="#11111b", fg="#a6adc8")
        self.lbl_drop_tb_file.pack(anchor=tk.W, pady=(2, 0))
        self.lbl_drop_tb_ent = tk.Label(self.drop_tb_frame, text="Testbench Entity: -", font=("Segoe UI", 8, "bold"), bg="#11111b", fg="#a6e3a1")
        self.lbl_drop_tb_ent.pack(anchor=tk.W, pady=(2, 0))

        ttk.Label(p3, text="Detected Testbenches (or select):", style="Card.TLabel").pack(anchor=tk.W)
        self.combo_tb = ttk.Combobox(p3, state="readonly", values=["(Open a project folder to list testbenches)"])
        self.combo_tb.current(0)
        self.combo_tb.pack(fill=tk.X, pady=(2, 6))
        self.combo_tb.bind("<<ComboboxSelected>>", self.on_tb_selected)

        ttk.Label(p3, text="Engines: GHDL (VHDL) & Icarus (Verilog)", style="Card.TLabel", font=("Segoe UI", 9, "italic")).pack(anchor=tk.W, pady=(2, 6))

        btn_sim = ttk.Button(p3, text="⚡ Compile & Run Simulation", style="Success.TButton", command=self.run_simulation)
        btn_sim.pack(fill=tk.X, pady=(4, 4))

        btn_wave = ttk.Button(p3, text="📈 Launch Waveform (GTKWave)", style="TButton", command=self.launch_gtkwave)
        btn_wave.pack(fill=tk.X, pady=(0, 4))

        btn_vsc_wave = ttk.Button(p3, text="📊 Open Waveform in Editor", style="TButton", command=self.open_vsc_wave)
        btn_vsc_wave.pack(fill=tk.X)

        # ================= Phase 4 & 5 =================
        p45 = ttk.Frame(parent, padding=10, style="Card.TFrame")
        p45.grid(row=0, column=2, sticky="nsew", padx=4, pady=4)

        ttk.Label(p45, text="Phase 4 & 5: Synthesis & Target", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 6))

        btn_schem = ttk.Button(p45, text="🎨 Generate Logic Schematic (SVG)", style="Primary.TButton", command=self.generate_schematic)
        btn_schem.pack(fill=tk.X, pady=(0, 6))

        btn_view_schem = ttk.Button(p45, text="🌐 Open Schematic in Browser", style="TButton", command=self.open_schematic)
        btn_view_schem.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(p45, text="Target Cable / Interface:", style="Card.TLabel").pack(anchor=tk.W)
        cbl_combo = ttk.Combobox(p45, textvariable=self.cable_mode, values=["USB-Blaster (JTAG)", "FTDI (JTAG)", "Auto-Detect"], state="readonly")
        cbl_combo.pack(fill=tk.X, pady=(2, 8))

        btn_detect = ttk.Button(p45, text="🔌 Scan Hardware / JTAG Chain", style="Warning.TButton", command=self.scan_hardware)
        btn_detect.pack(fill=tk.X)

    def build_tree_tab(self, parent):
        paned = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(paned, padding=8, style="Card.TFrame")
        paned.add(left, weight=1)

        ttk.Label(left, text="Interactive Decision Guide", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 6))
        
        scroll = ttk.Scrollbar(left)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.guide_tree = ttk.Treeview(left, selectmode="browse", yscrollcommand=scroll.set)
        self.guide_tree.pack(fill=tk.BOTH, expand=True)
        scroll.config(command=self.guide_tree.yview)

        self.guide_tree.heading("#0", text="Design Steps & Diagnostics")

        p1 = self.guide_tree.insert("", "end", text="Phase 1: Project Setup", open=True)
        self.guide_tree.insert(p1, "end", text="Workspace & Top Entity Configuration")
        self.guide_tree.insert(p1, "end", text="Managing Multi-File Designs")

        p2 = self.guide_tree.insert("", "end", text="Phase 2: Elaboration & Syntax", open=True)
        self.guide_tree.insert(p2, "end", text="Fast Analysis & Syntax Check")
        self.guide_tree.insert(p2, "end", text="Inferred Latch Prevention Rule")

        p3 = self.guide_tree.insert("", "end", text="Phase 3: Functional Simulation", open=True)
        self.guide_tree.insert(p3, "end", text="Running Testbenches with Assertions")
        self.guide_tree.insert(p3, "end", text="VCD Waveform & Bus Radix Inspection")

        p4 = self.guide_tree.insert("", "end", text="Phase 4: Synthesis & Constraints", open=True)
        self.guide_tree.insert(p4, "end", text="Logic Schematic Netlist Generation")
        self.guide_tree.insert(p4, "end", text="Unused Pin Protection (Tri-State Pull-Up)")

        p5 = self.guide_tree.insert("", "end", text="Phase 5: Hardware Programming", open=True)
        self.guide_tree.insert(p5, "end", text="JTAG Boundary Scan Detection")
        self.guide_tree.insert(p5, "end", text="Hardware Pitfalls (Active-Low IO & Displays)")

        self.guide_tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        right = ttk.Frame(paned, padding=10, style="Card.TFrame")
        paned.add(right, weight=2)

        ttk.Label(right, text="Diagnostic Advice & Best Practices", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 6))

        self.detail_text = tk.Text(right, bg="#11111b", fg="#cdd6f4", font=("Segoe UI", 10), wrap="word", relief="flat")
        self.detail_text.pack(fill=tk.BOTH, expand=True)

        self.show_default_rule()

    def show_default_rule(self):
        info = (
            "📌 NOOBEDA - CORE PHILOSOPHY & WORKFLOW\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "1. ALWAYS ELABORATE BEFORE COMPILING:\n"
            "   Don't wait minutes for a full vendor synthesis tool. Use 'Run Analysis & Elaboration' "
            "to catch typos, syntax bugs, and port mismatches in < 2 seconds.\n\n"
            "2. PREVENT UNINTENDED INFERRED LATCHES:\n"
            "   In combinational blocks (always @(*) in Verilog or process(all) in VHDL), "
            "ensure every output signal is explicitly assigned in every branch (always include an 'else' or 'default').\n\n"
            "3. SIMULATE BEFORE PUTTING ON SILICON:\n"
            "   Use your testbench with GTKWave or WaveTrace to verify edge cases before downloading to the FPGA board.\n\n"
            "4. PROTECT UNUSED PINS:\n"
            "   Always configure unused pins as 'input tri-stated with weak pull-up' to avoid short-circuiting.\n\n"
            "Select any item in the left tree to inspect detailed step-by-step guidance."
        )
        self.detail_text.delete("1.0", tk.END)
        self.detail_text.insert(tk.END, info)

    def on_tree_select(self, event):
        selected = self.guide_tree.selection()
        if not selected:
            return
        item_text = self.guide_tree.item(selected[0], "text")
        
        explanations = {
            "Workspace & Top Entity Configuration":
                "🎯 WORKSPACE SETUP\n"
                "• Set your project directory via 'Open Project Folder'.\n"
                "• Drag or select your top-level HDL entity into the Drop Box.\n"
                "• The top entity name is automatically inferred from the file declaration.",
            "Managing Multi-File Designs":
                "📚 MULTI-FILE ARCHITECTURES\n"
                "• All VHDL (.vhd) or Verilog (.v) files in the active workspace are automatically indexed.\n"
                "• GHDL and Yosys analyze all dependent entity files in the workspace automatically.",
            "Fast Analysis & Syntax Check":
                "⚡ FAST ELABORATION\n"
                "• Parses HDL AST, checks hierarchy, binds submodule ports.\n"
                "• Catches 95% of compilation errors instantly without synthesis overhead.",
            "Inferred Latch Prevention Rule":
                "⚠️ INFERRED LATCHES\n"
                "• Occurs when an output retains its state implicitly across cycles in combinational logic.\n"
                "• Click '🔍 Check Inferred Latches' to test your code structure.",
            "Running Testbenches with Assertions":
                "🔬 AUTOMATED TESTBENCHES\n"
                "• Run functional simulations with automated assertion checks.\n"
                "• Generates clean VCD waveforms for visual verification.",
            "VCD Waveform & Bus Radix Inspection":
                "📈 TIMING & WAVEFORMS\n"
                "• Click 'Launch Waveform' to open GTKWave, or 'Open Waveform in Editor' for in-IDE viewing.\n"
                "• Change bus radix to Hexadecimal, Signed, or Unsigned Decimal to verify calculations.",
            "Logic Schematic Netlist Generation":
                "🎨 VISUAL RTL SCHEMATICS\n"
                "• Translates your code into an interactive SVG schematic via netlistsvg.\n"
                "• Allows visual inspection of multiplexers, adders, registers, and interconnects.",
            "Unused Pin Protection (Tri-State Pull-Up)":
                "🛡️ HARDWARE PROTECTION\n"
                "• Prevent unassigned pins from driving GND if externally tied to VCC on the PCB.\n"
                "• Always configure unused pins as tri-stated inputs.",
            "JTAG Boundary Scan Detection":
                "🔌 HARDWARE DETECTION\n"
                "• Click 'Scan Hardware' to run openFPGALoader --detect.\n"
                "• Verifies USB-Blaster, FTDI, or other JTAG adapters connected to your system.",
            "Hardware Pitfalls (Active-Low IO & Displays)":
                "⚠️ COMMON HARDWARE PITFALLS\n"
                "• Pushbuttons on many boards are ACTIVE-LOW (0 when pressed, 1 when released).\n"
                "• 7-Segment displays are often COMMON ANODE (0 lights up the LED segment)."
        }
        
        msg = explanations.get(item_text, f"Selected: {item_text}\n\nReview the Operations tab to execute this stage.")
        self.detail_text.delete("1.0", tk.END)
        self.detail_text.insert(tk.END, msg)

    # --- Actions & Drag-and-Drop ---
    def log(self, text):
        self.console.insert(tk.END, text + "\n")
        self.console.see(tk.END)

    def clear_console(self):
        """Clears the console text widget."""
        self.console.delete("1.0", tk.END)

    def copy_console(self):
        """Copies execution log contents to system clipboard."""
        text = self.console.get("1.0", tk.END).strip()
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            messagebox.showinfo("Clipboard", "Execution log copied to clipboard!")
        else:
            messagebox.showinfo("Clipboard", "Console is currently empty.")

    def abort_current_task(self):
        """Terminates any active background EDA compilation or simulation process."""
        if self.current_process:
            try:
                self.current_process.kill()
                self.current_process = None
                self.log("🛑 OPERATION ABORTED BY USER.\n")
            except Exception as e:
                self.log(f"Error aborting task: {e}")
        else:
            self.log("ℹ No active background process to abort.")

    def on_terminal_enter(self, event=None):
        """Runs interactive shell command from terminal prompt in current workspace."""
        cmd = self.term_entry.get().strip()
        if not cmd:
            return
        self.term_entry.delete(0, tk.END)
        self._cmd_history.append(cmd)
        self._history_idx = len(self._cmd_history)
        self.log(f"\nnoobeda:$ {cmd}")
        cwd = self.work_dir.get() if (self.work_dir.get() and os.path.isdir(self.work_dir.get())) else None
        self.run_cmd_async(cmd, cwd=cwd)

    def on_terminal_history_up(self, event=None):
        if self._cmd_history and self._history_idx > 0:
            self._history_idx -= 1
            self.term_entry.delete(0, tk.END)
            self.term_entry.insert(0, self._cmd_history[self._history_idx])

    def on_terminal_history_down(self, event=None):
        if self._cmd_history and self._history_idx < len(self._cmd_history) - 1:
            self._history_idx += 1
            self.term_entry.delete(0, tk.END)
            self.term_entry.insert(0, self._cmd_history[self._history_idx])
        else:
            self._history_idx = len(self._cmd_history)
            self.term_entry.delete(0, tk.END)

    def show_toolchain_diagnostics(self):
        """Displays interactive modal inspecting paths and versions of all EDA engines."""
        diag_win = tk.Toplevel(self)
        diag_win.title("Toolchain Diagnostics & Health Inspector")
        diag_win.geometry("640x440")
        diag_win.configure(bg="#181825")
        diag_win.transient(self)
        diag_win.grab_set()

        hdr = ttk.Label(diag_win, text="🛠️ Installed EDA Toolchain Engines", style="Title.TLabel", font=("Segoe UI", 12, "bold"))
        hdr.pack(anchor=tk.W, padx=16, pady=(16, 8))

        content_box = tk.Text(diag_win, bg="#0d0f18", fg="#cdd6f4", font=("Consolas", 10), relief="flat", padx=10, pady=10)
        content_box.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 16))

        tools_to_check = [
            ("GHDL (VHDL Simulator & Synth)", GHDL_BIN, ["--version"]),
            ("Yosys (Logic Synthesis)", YOSYS_BIN, ["-V"]),
            ("Icarus Verilog", IVERILOG_BIN, ["-V"]),
            ("VVP (Verilog Engine)", VVP_BIN, ["-V"]),
            ("GTKWave (Waveform Viewer)", GTKWAVE_BIN, ["--version"]),
            ("netlistsvg (Schematic Generator)", NETLISTSVG_BIN, ["--version"]),
            ("openFPGALoader (JTAG Flasher)", OPENFPGA_BIN, ["--version"]),
        ]

        def run_checks():
            report = []
            for name, binary, args in tools_to_check:
                resolved = shutil.which(binary)
                if not resolved and sys.platform.startswith("win"):
                    for ext in [".cmd", ".exe", ".bat"]:
                        resolved = shutil.which(f"{binary}{ext}")
                        if resolved:
                            break

                if resolved:
                    try:
                        p = subprocess.run([resolved] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=3)
                        ver_line = (p.stdout or p.stderr).strip().splitlines()
                        ver = ver_line[0] if ver_line else "Available"
                    except Exception:
                        ver = "Detected (in PATH)"
                    report.append(f"✅ {name}\n   Path: {resolved}\n   Version: {ver}\n")
                else:
                    report.append(f"❌ {name}\n   Status: NOT FOUND in PATH\n   Tip: Check installation or add to PATH\n")

            content_box.insert(tk.END, "\n".join(report))
            content_box.config(state="disabled")

        threading.Thread(target=run_checks, daemon=True).start()

    def browse_workspace(self):
        initial = self.work_dir.get() if self.work_dir.get() and os.path.isdir(self.work_dir.get()) else None
        d = filedialog.askdirectory(initialdir=initial)
        if d:
            self.work_dir.set(d)
            self.lbl_prompt.config(text=f"{os.path.basename(d) or 'workspace'}:~$ ")
            self.log(f"📁 Switched active workspace to: {d}")
            self.rescan_workspace()

    def rescan_workspace(self):
        """Scans workspace directory dynamically for all HDL files and populates file tree & dropdowns."""
        cwd = self.work_dir.get()
        if not cwd or not os.path.exists(cwd):
            self.combo_hdl["values"] = ["(Open a project folder to list files)"]
            self.combo_hdl.current(0)
            self.combo_tb["values"] = ["(Open a project folder to list testbenches)"]
            self.combo_tb.current(0)
            self.file_tree.delete(*self.file_tree.get_children())
            return

        design_items = []
        tb_items = []
        self._design_map.clear()
        self._tb_map.clear()
        self.file_tree.delete(*self.file_tree.get_children())

        # Populate File Tree
        node_map = {}
        for root, dirs, files in os.walk(cwd):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ["work", "_build", "__pycache__"]]
            rel_dir = os.path.relpath(root, cwd)
            parent_node = "" if rel_dir == "." else node_map.get(os.path.dirname(rel_dir), "")

            if rel_dir != ".":
                dir_id = self.file_tree.insert(parent_node, "end", text=f"📁 {os.path.basename(root)}", open=True)
                node_map[rel_dir] = dir_id
            else:
                dir_id = ""

            for f in sorted(files):
                full_p = os.path.join(root, f)
                rel_p = os.path.relpath(full_p, cwd)
                lower = f.lower()

                # Choose icon
                if lower.endswith((".vhd", ".vhdl")):
                    icon = "🧪" if any(kw in lower for kw in ["tb", "test", "bench"]) else "📦"
                elif lower.endswith((".v", ".sv")):
                    icon = "🧪" if any(kw in lower for kw in ["tb", "test", "bench"]) else "⚡"
                elif lower.endswith((".qsf", ".pcf", ".xdc", ".sdc")):
                    icon = "⚙️"
                elif lower.endswith((".svg", ".png", ".jpg")):
                    icon = "🎨"
                elif lower.endswith((".vcd", ".vvp")):
                    icon = "📈"
                else:
                    icon = "📄"

                item_id = self.file_tree.insert(dir_id, "end", text=f"{icon} {f}", values=(full_p,))

                # HDL extraction for dropdowns
                if lower.endswith((".vhd", ".vhdl", ".v", ".sv")):
                    entities = extract_hdl_entities(full_p)
                    if not entities:
                        entities = [os.path.splitext(f)[0]]

                    for ent in entities:
                        if any(kw in lower for kw in ["tb", "test", "bench", "sim"]):
                            display = f"{rel_p}  [Entity: {ent}]"
                            tb_items.append(display)
                            self._tb_map[display] = (full_p, ent)
                        else:
                            display = f"{rel_p}  [Entity: {ent}]"
                            design_items.append(display)
                            self._design_map[display] = (full_p, ent)

        if design_items:
            self.combo_hdl["values"] = design_items
            self.combo_hdl.set("Select a design file...")
            self.log(f"🔎 Discovered {len(design_items)} design module(s) in workspace.")
        else:
            self.combo_hdl["values"] = ["(No design HDL files found)"]
            self.combo_hdl.current(0)

        if tb_items:
            self.combo_tb["values"] = tb_items
            self.combo_tb.set("Select a testbench file...")
            self.log(f"🔬 Discovered {len(tb_items)} testbench module(s) in workspace.")
        else:
            self.combo_tb["values"] = ["(No testbench files found)"]
            self.combo_tb.current(0)

    # --- Drag-and-Drop & File Interactions ---
    def on_drag_start(self, event):
        item = self.file_tree.identify_row(event.y)
        if item:
            vals = self.file_tree.item(item, "values")
            if vals and os.path.isfile(vals[0]):
                self._dragged_file = vals[0]
            else:
                self._dragged_file = None

    def on_drag_motion(self, event):
        if not self._dragged_file:
            return
        # Highlight drop zone if mouse hovers over it
        x, y = event.x_root, event.y_root
        target = self.winfo_containing(x, y)

        if target and (target == self.drop_top_frame or target in self.drop_top_frame.winfo_children()):
            self.drop_top_frame.config(bg="#2d3748")
            self.drop_tb_frame.config(bg="#11111b")
        elif target and (target == self.drop_tb_frame or target in self.drop_tb_frame.winfo_children()):
            self.drop_tb_frame.config(bg="#2d3748")
            self.drop_top_frame.config(bg="#11111b")
        else:
            self.drop_top_frame.config(bg="#11111b")
            self.drop_tb_frame.config(bg="#11111b")

    def on_drag_end(self, event):
        if not self._dragged_file:
            return
        x, y = event.x_root, event.y_root
        target = self.winfo_containing(x, y)

        self.drop_top_frame.config(bg="#11111b")
        self.drop_tb_frame.config(bg="#11111b")

        if target and (target == self.drop_top_frame or target in self.drop_top_frame.winfo_children()):
            self.set_top_hdl_from_file(self._dragged_file)
        elif target and (target == self.drop_tb_frame or target in self.drop_tb_frame.winfo_children()):
            self.set_tb_from_file(self._dragged_file)

        self._dragged_file = None

    def on_file_double_click(self, event):
        item = self.file_tree.identify_row(event.y)
        if item:
            vals = self.file_tree.item(item, "values")
            if vals and os.path.isfile(vals[0]):
                self.open_file_in_editor(vals[0])

    def show_tree_context_menu(self, event):
        item = self.file_tree.identify_row(event.y)
        if item:
            self.file_tree.selection_set(item)
            self.tree_menu.post(event.x_root, event.y_root)

    def set_selected_as_top(self):
        sel = self.file_tree.selection()
        if sel:
            vals = self.file_tree.item(sel[0], "values")
            if vals and os.path.isfile(vals[0]):
                self.set_top_hdl_from_file(vals[0])

    def set_selected_as_tb(self):
        sel = self.file_tree.selection()
        if sel:
            vals = self.file_tree.item(sel[0], "values")
            if vals and os.path.isfile(vals[0]):
                self.set_tb_from_file(vals[0])

    def open_selected_in_editor(self):
        sel = self.file_tree.selection()
        if sel:
            vals = self.file_tree.item(sel[0], "values")
            if vals and os.path.isfile(vals[0]):
                self.open_file_in_editor(vals[0])

    def set_top_hdl_from_file(self, filepath):
        self.hdl_file.set(filepath)
        entities = extract_hdl_entities(filepath)
        top = entities[0] if entities else os.path.splitext(os.path.basename(filepath))[0]
        self.top_module.set(top)
        
        # Update Drop Box UI
        self.lbl_drop_top_file.config(text=f"📄 {os.path.basename(filepath)}", fg="#ffffff")
        self.lbl_drop_top_ent.config(text=f"Entity: {top}", fg="#a6e3a1")
        self.drop_top_frame.config(bd=2, highlightbackground="#3b82f6", highlightcolor="#3b82f6")
        self.log(f"✔ Assigned Top HDL: {os.path.basename(filepath)} (Entity: {top})")

    def set_tb_from_file(self, filepath):
        self.tb_file.set(filepath)
        entities = extract_hdl_entities(filepath)
        tb_ent = entities[0] if entities else os.path.splitext(os.path.basename(filepath))[0]
        
        # Update Drop Box UI
        self.lbl_drop_tb_file.config(text=f"🧪 {os.path.basename(filepath)}", fg="#ffffff")
        self.lbl_drop_tb_ent.config(text=f"Testbench Entity: {tb_ent}", fg="#a6e3a1")
        self.drop_tb_frame.config(bd=2, highlightbackground="#10b981", highlightcolor="#10b981")
        self.log(f"✔ Assigned Testbench: {os.path.basename(filepath)} (Entity: {tb_ent})")

    def open_file_in_editor(self, filepath):
        """Cross-platform opener for source files in VS Code or default system editor."""
        if not filepath or not os.path.exists(filepath):
            return
        self.log(f"✏️ Opening in editor: {os.path.basename(filepath)}")
        if shutil.which("code"):
            subprocess.Popen(f'code "{filepath}"', shell=True)
        elif sys.platform.startswith("win"):
            os.startfile(filepath)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", filepath])
        else:
            subprocess.Popen(["xdg-open", filepath])

    def on_hdl_selected(self, event=None):
        selected = self.combo_hdl.get()
        if selected in self._design_map:
            path, entity = self._design_map[selected]
            self.set_top_hdl_from_file(path)

    def on_tb_selected(self, event=None):
        selected = self.combo_tb.get()
        if selected in self._tb_map:
            path, ent = self._tb_map[selected]
            self.set_tb_from_file(path)

    def browse_hdl(self):
        init_d = self.work_dir.get() if self.work_dir.get() and os.path.isdir(self.work_dir.get()) else None
        f = filedialog.askopenfilename(initialdir=init_d, filetypes=[("VHDL / Verilog", "*.vhd;*.vhdl;*.v;*.sv"), ("All Files", "*.*")])
        if f:
            self.set_top_hdl_from_file(f)
            if not self.work_dir.get():
                self.work_dir.set(os.path.dirname(f))
                self.rescan_workspace()

    def browse_tb(self):
        init_d = self.work_dir.get() if self.work_dir.get() and os.path.isdir(self.work_dir.get()) else None
        f = filedialog.askopenfilename(initialdir=init_d, filetypes=[("Testbench Files", "*.vhd;*.vhdl;*.v;*.sv"), ("All Files", "*.*")])
        if f:
            self.set_tb_from_file(f)
            if not self.work_dir.get():
                self.work_dir.set(os.path.dirname(f))
                self.rescan_workspace()

    def run_cmd_async(self, cmd, cwd=None, on_success=None):
        def worker():
            self.log(f"⚡ RUNNING: {cmd}")
            try:
                proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=cwd)
                self.current_process = proc
                for line in proc.stdout:
                    self.log(line.rstrip())
                proc.wait()
                self.current_process = None
                if proc.returncode == 0:
                    self.log("✅ COMPLETED SUCCESSFULLY.\n")
                    if on_success:
                        self.after(0, on_success)
                elif proc.returncode in (-15, -9, 15, 9):
                    self.log("⚠️ Task was aborted.\n")
                else:
                    self.log(f"❌ FAILED WITH EXIT CODE {proc.returncode}\n")
            except Exception as e:
                self.current_process = None
                self.log(f"❌ ERROR: {e}\n")

        t = threading.Thread(target=worker, daemon=True)
        t.start()

    def run_elaboration(self):
        hdl = self.hdl_file.get()
        if not hdl or not os.path.exists(hdl):
            messagebox.showerror("Error", "Please select or drop a valid HDL file first.")
            return

        cwd = os.path.dirname(hdl)
        base = os.path.basename(hdl)
        self.log(f"--- [Phase 2] Analyzing & Elaborating {base} ---")
        
        if base.lower().endswith((".vhd", ".vhdl")):
            all_vhdl = [f for f in os.listdir(cwd) if f.lower().endswith((".vhd", ".vhdl")) and not any(kw in f.lower() for kw in ["tb", "test"])]
            files_str = " ".join(f'"{f}"' for f in all_vhdl)
            top = self.top_module.get() or os.path.splitext(base)[0]
            cmd = f'"{GHDL_BIN}" -a --std=08 {files_str} && "{GHDL_BIN}" -e --std=08 {top}'
        else:
            cmd = f'"{IVERILOG_BIN}" -t null -Wall "{base}"'
            
        self.run_cmd_async(cmd, cwd=cwd)

    def check_latches(self):
        hdl = self.hdl_file.get()
        if not hdl or not os.path.exists(hdl):
            messagebox.showerror("Error", "Please select or drop a valid HDL file first.")
            return
        
        cwd = os.path.dirname(hdl)
        base = os.path.basename(hdl)
        top = self.top_module.get() or os.path.splitext(base)[0]
        self.log(f"--- Checking for Inferred Latches in {top} ---")
        
        if base.lower().endswith((".vhd", ".vhdl")):
            cmd = f'"{GHDL_BIN}" -a --std=08 "{base}"'
        else:
            yosys_script = f"read_verilog {base}; proc; opt"
            cmd = f'"{YOSYS_BIN}" -p "{yosys_script}"'
            
        self.run_cmd_async(cmd, cwd=cwd)

    def run_simulation(self):
        tb = self.tb_file.get()
        if not tb or not os.path.exists(tb):
            messagebox.showerror("Error", "Please select or drop a testbench file first.")
            return

        cwd = os.path.dirname(tb)
        tb_base = os.path.basename(tb)
        tb_entities = extract_hdl_entities(tb)
        tb_top = tb_entities[0] if tb_entities else os.path.splitext(tb_base)[0]
        self.log(f"--- [Phase 3] Running Simulation for {tb_top} ---")
        
        if tb_base.lower().endswith((".vhd", ".vhdl")):
            all_vhdl = [f for f in os.listdir(cwd) if f.lower().endswith((".vhd", ".vhdl"))]
            files_str = " ".join(f'"{f}"' for f in all_vhdl)
            cmd = (
                f'"{GHDL_BIN}" -a --std=08 {files_str} && '
                f'"{GHDL_BIN}" -e --std=08 {tb_top} && '
                f'"{GHDL_BIN}" -r --std=08 {tb_top} --vcd=simulation.vcd'
            )
        else:
            hdl = self.hdl_file.get()
            hdl_base = os.path.basename(hdl) if hdl else ""
            out_vvp = "sim_output.vvp"
            cmd = f'"{IVERILOG_BIN}" -o "{out_vvp}" "{hdl_base}" "{tb_base}" && "{VVP_BIN}" "{out_vvp}"'
        
        self.run_cmd_async(cmd, cwd=cwd, on_success=lambda: messagebox.showinfo("Simulation", "Simulation completed! Click 'Launch Waveform' to inspect."))

    def launch_gtkwave(self):
        cwd = self.work_dir.get()
        vcd_files = [f for f in os.listdir(cwd) if f.endswith(".vcd")] if cwd and os.path.exists(cwd) else []
        vcd_arg = f'"{os.path.join(cwd, vcd_files[0])}"' if vcd_files else ""

        self.log(f"--- Launching GTKWave GUI ({vcd_arg or 'No VCD found'}) ---")
        cmd = f'"{GTKWAVE_BIN}" {vcd_arg}'
        try:
            subprocess.Popen(cmd, shell=True, cwd=os.path.dirname(GTKWAVE_BIN) if os.path.isabs(GTKWAVE_BIN) else None)
            self.log("Launched GTKWave.")
        except Exception as e:
            self.log(f"Failed to launch GTKWave: {e}")

    def open_vsc_wave(self):
        cwd = self.work_dir.get()
        vcd_files = [f for f in os.listdir(cwd) if f.endswith(".vcd")] if cwd and os.path.exists(cwd) else []
        if vcd_files:
            vcd_path = os.path.join(cwd, vcd_files[0])
            self.open_file_in_editor(vcd_path)
        else:
            messagebox.showinfo("Waveform", "No .vcd file found in current workspace. Run simulation first.")

    def generate_schematic(self):
        hdl = self.hdl_file.get()
        if not hdl or not os.path.exists(hdl):
            messagebox.showerror("Error", "Please select or drop a valid HDL file first.")
            return

        if not shutil.which(NETLISTSVG_BIN):
            messagebox.showerror("netlistsvg Missing", "netlistsvg is required to render electronic schematics.\nPlease install it via: npm install -g netlistsvg")
            return

        cwd = os.path.dirname(hdl)
        base = os.path.basename(hdl)
        top = self.top_module.get() or os.path.splitext(base)[0]
        self.log(f"--- [Phase 4] Generating Electronic Schematic for {top} (netlistsvg) ---")

        json_out = os.path.join(cwd, "netlist.json")
        svg_out = os.path.join(cwd, "schematic.svg")

        def worker():
            try:
                # Step 1: Synthesize to Verilog (if VHDL)
                if base.lower().endswith((".vhd", ".vhdl")):
                    synth_v = os.path.join(cwd, "_noobeda_synth.v")
                    all_vhdl = [f for f in os.listdir(cwd) if f.lower().endswith((".vhd", ".vhdl")) and not any(kw in f.lower() for kw in ["tb", "test"])]
                    self.log(f"⚡ [1/3] Synthesizing VHDL via GHDL ({len(all_vhdl)} files)...")
                    ghdl_args = [GHDL_BIN, "--synth", "--std=08", "--out=verilog"] + all_vhdl + ["-e", top]
                    with open(synth_v, "w", encoding="utf-8") as f_out:
                        p_ghdl = subprocess.run(ghdl_args, cwd=cwd, stdout=f_out, stderr=subprocess.PIPE, text=True)
                    if p_ghdl.returncode != 0:
                        self.log(f"❌ GHDL Synthesis Error:\n{p_ghdl.stderr}")
                        return
                    yosys_target = synth_v
                else:
                    yosys_target = base

                # Step 2: Yosys elaboration and netlist generation
                self.log("⚡ [2/3] Elaborating gate-level netlist via Yosys...")
                yosys_cmd = f'read_verilog "{yosys_target}"; proc; opt; write_json "{json_out}"'
                p_yosys = subprocess.run([YOSYS_BIN, "-p", yosys_cmd], cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                if p_yosys.returncode != 0:
                    self.log(f"❌ Yosys Synthesis Error:\n{p_yosys.stdout}")
                    return

                # Step 3: Sanitize JSON for netlistsvg (handling tri-states / inouts)
                sanitize_netlist_json(json_out)

                # Step 4: Netlistsvg rendering
                self.log("⚡ [3/3] Rendering SVG schematic via netlistsvg...")
                p_svg = subprocess.run(f'"{NETLISTSVG_BIN}" "{json_out}" -o "{svg_out}"', cwd=cwd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                if p_svg.returncode != 0:
                    self.log(f"❌ netlistsvg Error:\n{p_svg.stdout}")
                    return

                self.log("✅ SCHEMATIC GENERATED SUCCESSFULLY.\n")
                self.after(0, self.open_schematic)
            except Exception as e:
                self.log(f"❌ ERROR: {e}\n")

        t = threading.Thread(target=worker, daemon=True)
        t.start()

    def open_schematic(self):
        cwd = self.work_dir.get()
        svg_file = os.path.join(cwd, "schematic.svg") if cwd else ""
        if not (svg_file and os.path.exists(svg_file)) and cwd:
            svg_file = os.path.join(cwd, "alu_schematic.svg")
            
        if svg_file and os.path.exists(svg_file):
            self.log(f"Opening schematic diagram: {svg_file}")
            if sys.platform.startswith("win"):
                os.startfile(svg_file)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", svg_file])
            else:
                subprocess.Popen(["xdg-open", svg_file])
        else:
            messagebox.showwarning("Schematic", "No SVG schematic found. Click 'Generate Logic Schematic' first.")

    def scan_hardware(self):
        self.log("--- [Phase 5] Scanning for Connected Hardware (JTAG Chain) ---")
        cmd = f'"{OPENFPGA_BIN}" --detect'
        self.run_cmd_async(cmd)

if __name__ == "__main__":
    app = NoobEDAApp()
    app.mainloop()
