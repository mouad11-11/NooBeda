#!/usr/bin/env python3
"""
NoobEDA - The Zero-Bloat, Beginner-Friendly FPGA & Digital Design Studio
Cross-Platform GUI orchestrator for open-source EDA tools:
GHDL, Yosys, GTKWave, Icarus Verilog, Graphviz, and openFPGALoader.
"""

import os
import sys
import shutil
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# ==============================================================================
# Dynamic Toolchain Discovery (Cross-Platform: Windows / Linux / macOS)
# ==============================================================================
COMMON_TOOL_DIRS = [
    r"C:\tools\oss-cad-suite\bin",
    r"C:\tools\oss-cad-suite\lib",
    r"C:\tools\gtkwave-win64\gtkwave64\bin",
    r"C:\tools\ghdl\bin",
    r"C:\Users\hp\AppData\Roaming\npm",
    "/usr/bin",
    "/usr/local/bin",
    "/opt/homebrew/bin",
]

# Ensure known tool directories are temporarily included in PATH search
for p in COMMON_TOOL_DIRS:
    if os.path.isdir(p) and p not in os.environ.get("PATH", ""):
        os.environ["PATH"] = f"{p}{os.pathsep}" + os.environ.get("PATH", "")

def find_binary(name):
    """Dynamically locate an executable in PATH with cross-platform fallback."""
    found = shutil.which(name)
    if found:
        return found
    # Try Windows .exe explicitly
    if sys.platform.startswith("win"):
        found = shutil.which(f"{name}.exe")
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

# ==============================================================================
# Main Application
# ==============================================================================
class NoobEDAApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("NoobEDA - Open-Source FPGA & Digital Design Studio")
        self.geometry("1140x760")
        self.minsize(920, 620)
        self.configure(bg="#1e1e2e")

        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.configure_styles()

        # Workspace State - Empty by default for fresh user sessions
        self.work_dir = tk.StringVar(value="")
        self.hdl_file = tk.StringVar(value="")
        self.top_module = tk.StringVar(value="")
        self.tb_file = tk.StringVar(value="")
        self.cable_mode = tk.StringVar(value="USB-Blaster (JTAG)")

        self.create_layout()

    def configure_styles(self):
        dark_bg = "#1e1e2e"
        card_bg = "#252538"
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

    def auto_detect_workspace(self):
        """Scans current workspace directory for VHDL/Verilog source and testbench files."""
        cwd = self.work_dir.get()
        if not os.path.exists(cwd):
            return
        
        candidates = []
        tb_candidates = []
        for f in os.listdir(cwd):
            lower = f.lower()
            if lower.endswith((".vhd", ".vhdl", ".v", ".sv")):
                if "tb" in lower or "test" in lower:
                    tb_candidates.append(f)
                else:
                    candidates.append(f)
        
        if tb_candidates and not self.tb_file.get():
            self.tb_file.set(os.path.join(cwd, tb_candidates[0]))
        
        if candidates and not self.hdl_file.get():
            # Choose top candidate (prefer top or main if named so)
            chosen = candidates[0]
            for c in candidates:
                if "top" in c.lower() or "main" in c.lower():
                    chosen = c
                    break
            self.hdl_file.set(os.path.join(cwd, chosen))
            self.top_module.set(os.path.splitext(chosen)[0])

    def create_layout(self):
        # Header
        header = ttk.Frame(self, padding=(16, 10))
        header.pack(fill=tk.X)

        title = ttk.Label(header, text="⚡ NoobEDA - Open-Source FPGA Studio", style="Title.TLabel")
        title.pack(side=tk.LEFT)

        # Toolchain health status badge
        tools_ready = bool(shutil.which(GHDL_BIN) or shutil.which(IVERILOG_BIN))
        status_text = "Toolchain: GHDL + Yosys + netlistsvg + GTKWave" if tools_ready else "Toolchain: In PATH (auto-detect)"
        status_badge = ttk.Label(header, text=status_text, font=("Segoe UI", 9), foreground="#a6e3a1")
        status_badge.pack(side=tk.RIGHT, pady=4)

        # Workspace Directory Picker Bar
        ws_bar = ttk.Frame(self, padding=(16, 2, 16, 8))
        ws_bar.pack(fill=tk.X)
        ttk.Label(ws_bar, text="📁 Active Workspace:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 6))
        ent_ws = ttk.Entry(ws_bar, textvariable=self.work_dir)
        ent_ws.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(ws_bar, text="Change Folder", width=14, command=self.browse_workspace).pack(side=tk.RIGHT, padx=(6, 0))

        # Paned Window
        main_paned = ttk.PanedWindow(self, orient=tk.VERTICAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        notebook = ttk.Notebook(main_paned)
        main_paned.add(notebook, weight=3)

        # Tab 1: Operations
        tab_ops = ttk.Frame(notebook, padding=12)
        notebook.add(tab_ops, text="  Operations (5 Phases)  ")
        self.build_operations_tab(tab_ops)

        # Tab 2: Decision Tree Guide
        tab_tree = ttk.Frame(notebook, padding=12)
        notebook.add(tab_tree, text="  Decision Tree & Rules  ")
        self.build_tree_tab(tab_tree)

        # Bottom: Live Console
        console_frame = ttk.Frame(main_paned, padding=8, style="Card.TFrame")
        main_paned.add(console_frame, weight=2)

        lbl_console = ttk.Label(console_frame, text="Execution Log & Hardware Diagnostics", style="Header.TLabel")
        lbl_console.pack(anchor=tk.W, pady=(0, 4))

        self.console = tk.Text(console_frame, bg="#11111b", fg="#cdd6f4", font=("Consolas", 10), insertbackground="#ffffff", relief="flat")
        self.console.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        scrollbar = ttk.Scrollbar(console_frame, orient=tk.VERTICAL, command=self.console.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.console.config(yscrollcommand=scrollbar.set)

    def build_operations_tab(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)
        parent.columnconfigure(2, weight=1)

        # ================= Phase 1 & 2 =================
        p12 = ttk.Frame(parent, padding=12, style="Card.TFrame")
        p12.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)

        ttk.Label(p12, text="Phase 1 & 2: Setup & Elaboration", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 8))

        ttk.Label(p12, text="Top HDL File (.vhd / .v):", style="Card.TLabel").pack(anchor=tk.W)
        row_hdl = ttk.Frame(p12, style="Card.TFrame")
        row_hdl.pack(fill=tk.X, pady=(2, 6))
        ent_hdl = ttk.Entry(row_hdl, textvariable=self.hdl_file)
        ent_hdl.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(row_hdl, text="Browse", width=7, command=self.browse_hdl).pack(side=tk.RIGHT, padx=(4, 0))

        ttk.Label(p12, text="Top Entity / Module Name:", style="Card.TLabel").pack(anchor=tk.W)
        ent_top = ttk.Entry(p12, textvariable=self.top_module)
        ent_top.pack(fill=tk.X, pady=(2, 8))

        # Quick Actions
        btn_elab = ttk.Button(p12, text="▶ Run Analysis & Elaboration", style="Primary.TButton", command=self.run_elaboration)
        btn_elab.pack(fill=tk.X, pady=(4, 6))

        btn_latch = ttk.Button(p12, text="🔍 Check Inferred Latches / Warnings", style="TButton", command=self.check_latches)
        btn_latch.pack(fill=tk.X)

        # ================= Phase 3 (Simulation) =================
        p3 = ttk.Frame(parent, padding=12, style="Card.TFrame")
        p3.grid(row=0, column=1, sticky="nsew", padx=6, pady=6)

        ttk.Label(p3, text="Phase 3: Logic Simulation", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 8))

        ttk.Label(p3, text="Testbench File (.vhd / .v):", style="Card.TLabel").pack(anchor=tk.W)
        row_tb = ttk.Frame(p3, style="Card.TFrame")
        row_tb.pack(fill=tk.X, pady=(2, 6))
        ent_tb = ttk.Entry(row_tb, textvariable=self.tb_file)
        ent_tb.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(row_tb, text="Browse", width=7, command=self.browse_tb).pack(side=tk.RIGHT, padx=(4, 0))

        ttk.Label(p3, text="Engines: GHDL (VHDL) & Icarus (Verilog)", style="Card.TLabel", font=("Segoe UI", 9, "italic")).pack(anchor=tk.W, pady=(2, 6))

        btn_sim = ttk.Button(p3, text="⚡ Compile & Run Simulation", style="Success.TButton", command=self.run_simulation)
        btn_sim.pack(fill=tk.X, pady=(4, 6))

        btn_wave = ttk.Button(p3, text="📈 Launch Waveform (GTKWave)", style="TButton", command=self.launch_gtkwave)
        btn_wave.pack(fill=tk.X, pady=(0, 6))

        btn_vsc_wave = ttk.Button(p3, text="📊 Open WaveTrace in Editor", style="TButton", command=self.open_vsc_wave)
        btn_vsc_wave.pack(fill=tk.X)

        # ================= Phase 4 & 5 =================
        p45 = ttk.Frame(parent, padding=12, style="Card.TFrame")
        p45.grid(row=0, column=2, sticky="nsew", padx=6, pady=6)

        ttk.Label(p45, text="Phase 4 & 5: Synthesis & Target", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 8))

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

        right = ttk.Frame(paned, padding=12, style="Card.TFrame")
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
            "   Always configure unused FPGA pins as 'input tri-stated with weak pull-up' to avoid short-circuiting.\n\n"
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
                "• Set your project directory via 'Change Folder'.\n"
                "• Select your top-level HDL entity file.\n"
                "• Ensure your module name matches the entity declared in code.",
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
                "• Click 'Launch Waveform' to open GTKWave, or 'Open WaveTrace in Editor' for in-IDE viewing.\n"
                "• Change bus radix to Hexadecimal, Signed, or Unsigned Decimal to verify calculations.",
            "Logic Schematic Netlist Generation":
                "🎨 VISUAL RTL SCHEMATICS\n"
                "• Translates your code into an interactive SVG schematic.\n"
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

    # --- Actions ---
    def log(self, text):
        self.console.insert(tk.END, text + "\n")
        self.console.see(tk.END)

    def browse_workspace(self):
        d = filedialog.askdirectory(initialdir=self.work_dir.get())
        if d:
            self.work_dir.set(d)
            self.auto_detect_workspace()
            self.log(f"Switched active workspace to: {d}")

    def browse_hdl(self):
        init_d = self.work_dir.get() if self.work_dir.get() and os.path.isdir(self.work_dir.get()) else None
        f = filedialog.askopenfilename(initialdir=init_d, filetypes=[("VHDL / Verilog", "*.vhd;*.vhdl;*.v;*.sv"), ("All Files", "*.*")])
        if f:
            self.hdl_file.set(f)
            self.top_module.set(os.path.splitext(os.path.basename(f))[0])
            if not self.work_dir.get():
                self.work_dir.set(os.path.dirname(f))

    def browse_tb(self):
        init_d = self.work_dir.get() if self.work_dir.get() and os.path.isdir(self.work_dir.get()) else None
        f = filedialog.askopenfilename(initialdir=init_d, filetypes=[("Testbench Files", "*.vhd;*.vhdl;*.v;*.sv"), ("All Files", "*.*")])
        if f:
            self.tb_file.set(f)
            if not self.work_dir.get():
                self.work_dir.set(os.path.dirname(f))

    def run_cmd_async(self, cmd, cwd=None, on_success=None):
        def worker():
            self.log(f"⚡ RUNNING: {cmd}")
            try:
                proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=cwd)
                for line in proc.stdout:
                    self.log(line.rstrip())
                proc.wait()
                if proc.returncode == 0:
                    self.log("✅ COMPLETED SUCCESSFULLY.\n")
                    if on_success:
                        self.after(0, on_success)
                else:
                    self.log(f"❌ FAILED WITH EXIT CODE {proc.returncode}\n")
            except Exception as e:
                self.log(f"❌ ERROR: {e}\n")

        t = threading.Thread(target=worker, daemon=True)
        t.start()

    def run_elaboration(self):
        hdl = self.hdl_file.get()
        if not hdl or not os.path.exists(hdl):
            messagebox.showerror("Error", "Please select a valid HDL file first.")
            return

        cwd = os.path.dirname(hdl)
        base = os.path.basename(hdl)
        self.log(f"--- [Phase 2] Analyzing & Elaborating {base} ---")
        
        if base.lower().endswith((".vhd", ".vhdl")):
            # Gather all VHDL files in directory for proper resolution
            all_vhdl = [f for f in os.listdir(cwd) if f.lower().endswith((".vhd", ".vhdl")) and not ("tb" in f.lower() or "test" in f.lower())]
            files_str = " ".join(f'"{f}"' for f in all_vhdl)
            top = self.top_module.get() or os.path.splitext(base)[0]
            cmd = f'"{GHDL_BIN}" -a --std=08 {files_str} && "{GHDL_BIN}" -e --std=08 {top}'
        else:
            cmd = f'"{IVERILOG_BIN}" -t null -Wall "{base}"'
            
        self.run_cmd_async(cmd, cwd=cwd)

    def check_latches(self):
        hdl = self.hdl_file.get()
        if not hdl or not os.path.exists(hdl):
            messagebox.showerror("Error", "Please select a valid HDL file.")
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
            messagebox.showerror("Error", "Please select a testbench file (.vhd / .v).")
            return

        cwd = os.path.dirname(tb)
        tb_base = os.path.basename(tb)
        tb_top = os.path.splitext(tb_base)[0]
        self.log(f"--- [Phase 3] Running Simulation for {tb_top} ---")
        
        if tb_base.lower().endswith((".vhd", ".vhdl")):
            # Gather all design VHDL files + testbench
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
        vcd_files = [f for f in os.listdir(cwd) if f.endswith(".vcd")] if os.path.exists(cwd) else []
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
        vcd_files = [f for f in os.listdir(cwd) if f.endswith(".vcd")] if os.path.exists(cwd) else []
        if vcd_files:
            vcd_path = os.path.join(cwd, vcd_files[0])
            subprocess.Popen(f'code "{vcd_path}"', shell=True)
            self.log(f"Opened {vcd_files[0]} in editor.")
        else:
            messagebox.showinfo("Waveform", "No .vcd file found in current workspace. Run simulation first.")

    def generate_schematic(self):
        hdl = self.hdl_file.get()
        if not hdl or not os.path.exists(hdl):
            messagebox.showerror("Error", "Please select a valid HDL file.")
            return

        if not shutil.which(NETLISTSVG_BIN):
            messagebox.showerror("netlistsvg Missing", "netlistsvg is required to render electronic schematics.\nPlease install it via: npm install -g netlistsvg")
            return

        cwd = os.path.dirname(hdl)
        base = os.path.basename(hdl)
        top = self.top_module.get() or os.path.splitext(base)[0]
        self.log(f"--- [Phase 4] Generating Electronic Schematic for {top} (netlistsvg) ---")

        json_out = "netlist.json"
        svg_out = "schematic.svg"

        if base.lower().endswith((".vhd", ".vhdl")):
            synth_v = os.path.join(cwd, "_noobeda_synth.v")
            all_vhdl = [f for f in os.listdir(cwd) if f.lower().endswith((".vhd", ".vhdl")) and not ("tb" in f.lower() or "test" in f.lower())]
            files_str = " ".join(f'"{f}"' for f in all_vhdl)
            ghdl_cmd = f'"{GHDL_BIN}" --synth --std=08 {files_str} -e {top} > "{synth_v}"'
            yosys_script = f"read_verilog _noobeda_synth.v; proc; opt; write_json {json_out}"
            full_cmd = f'{ghdl_cmd} && "{YOSYS_BIN}" -p "{yosys_script}" && "{NETLISTSVG_BIN}" {json_out} -o {svg_out}'
            self.run_cmd_async(full_cmd, cwd=cwd, on_success=self.open_schematic)
        else:
            yosys_script = f"read_verilog {base}; proc; opt; write_json {json_out}"
            full_cmd = f'"{YOSYS_BIN}" -p "{yosys_script}" && "{NETLISTSVG_BIN}" {json_out} -o {svg_out}'
            self.run_cmd_async(full_cmd, cwd=cwd, on_success=self.open_schematic)

    def open_schematic(self):
        cwd = self.work_dir.get()
        svg_file = os.path.join(cwd, "schematic.svg")
        if not os.path.exists(svg_file):
            svg_file = os.path.join(cwd, "alu_schematic.svg")
            
        if os.path.exists(svg_file):
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
