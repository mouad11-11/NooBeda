# NoobEDA User Manual & Guidebook 📖

Welcome to **NoobEDA** — the fast, zero-bloat, open-source digital design studio and FPGA workbench. This manual provides a step-by-step guide to using every feature of the cockpit.

---

## 📑 Table of Contents

1. [Interface Overview](#1-interface-overview)
2. [Quickstart (30-Second Tutorial)](#2-quickstart-30-second-tutorial)
3. [Core Workflows](#3-core-workflows)
   - [Phase 1: Project & Workspace Setup](#phase-1-project--workspace-setup)
   - [Phase 2: Analysis & Elaboration](#phase-2-analysis--elaboration)
   - [Phase 3: Testbench Simulation & Waveforms](#phase-3-testbench-simulation--waveforms)
   - [Phase 4: Gate-Level RTL Schematics](#phase-4-gate-level-rtl-schematics)
   - [Phase 5: JTAG & Hardware Boundary Scan](#phase-5-jtag--hardware-boundary-scan)
4. [Pin & Chip Planner](#4-pin--chip-planner)
5. [In-App Schematic Vector Canvas](#5-in-app-schematic-vector-canvas)
6. [Interactive Terminal](#6-interactive-terminal)
7. [Hardware Decision Tree & Diagnostics](#7-hardware-decision-tree--diagnostics)
8. [Multi-File Verilog & VHDL Projects](#8-multi-file-verilog--vhdl-projects)
9. [Toolchain Setup & Troubleshooting](#9-toolchain-setup--troubleshooting)

---

## 1. Interface Overview

NoobEDA is organized into a clean **3-Pane Cockpit**:

```
+-----------------------------------+---------------------------------------------------+
|  📁 PROJECT EXPLORER (Left)        |  🎛️ STUDIO TABS (Right)                           |
|                                   |  [ Operations | Decision Tree | Schematic | Pins ]|
|  • Workspace files & subfolders   |  -----------------------------------------------  |
|  • File type badges (VHD, V, VCD) |  • 3x Sized Drag-and-Drop Drop Zones              |
|  • Double-click to open in editor |  • 1-Click Action Buttons for each Phase          |
|  • Drag-and-drop to Top / TB      |  • Toolchain status indicators                    |
+-----------------------------------+---------------------------------------------------+
|  💻 LIVE INTERACTIVE TERMINAL (Bottom)                                                |
|  • Real-time console log streaming with status icons (✅ / ❌ / ⚡)                    |
|  • Command execution input with command history (↑ / ↓ arrows)                       |
|  • [▶ Run]  [⏹ Abort Process]  [🧹 Clear Console]  [📋 Copy Log]                     |
+---------------------------------------------------------------------------------------+
```

### 1.1 Left Pane: Project Explorer
- **Auto-Populates**: Whenever you open or switch workspaces, all files are dynamically listed.
- **File Type Icons**:
  - 📜 `.vhd`, `.vhdl` — VHDL Source
  - ⚡ `.v`, `.sv` — Verilog / SystemVerilog Source
  - 📊 `.vcd` — Waveform Trace Dump
  - 🎨 `.svg` — Vector Schematic Diagram
  - ⚙️ `.qsf`, `.pcf`, `.xdc` — Hardware Constraints
- **Double-Click**: Instantly opens any file in VS Code or your operating system's default code editor.
- **Drag-and-Drop**: Drag any HDL file directly from the explorer tree into the **Top Design** or **Testbench** drop zones.

### 1.2 Right Pane: Studio Notebook
Contains 4 specialized workspace tabs:
1. **Operations**: The main mission control for design elaboration, latch checks, simulation, and synthesis.
2. **Hardware Decision Tree**: Interactive checklist and diagnostic guide for FPGA safety rules.
3. **Schematic View**: High-resolution embedded vector canvas powered by PyMuPDF with real-time drag-to-pan and mouse-wheel zoom.
4. **Pin & Chip Planner**: Visual FPGA pad assignment grid with fuzzy auto-mapping and multi-vendor constraint exporters.

### 1.3 Bottom Pane: Integrated Terminal
- Direct execution channel for underlying EDA tools (`ghdl`, `iverilog`, `vvp`, `yosys`, `netlistsvg`, `openFPGALoader`).
- Allows typing custom shell commands or batch scripts directly within your workspace directory.

---

## 2. Quickstart (30-Second Tutorial)

1. Launch NoobEDA:
   ```bash
   python noobeda.py
   ```
2. Click **📁 Browse Workspace** (or drop a folder into the application).
3. Drag your top-level HDL file into the **Target Top-Level HDL File** box.
4. Drag your testbench file into the **Target Simulation Testbench** box.
5. Click **⚡ Analyze & Elaborate** to verify syntax.
6. Click **▶️ Run Simulation** and then **📈 Launch GTKWave Waveform** to inspect timing!

---

## 3. Core Workflows

### Phase 1: Project & Workspace Setup
- Click **📁 Browse Workspace** or enter a folder path. NoobEDA automatically scans for HDL files and testbenches.
- If your file contains multiple modules or entities, use the **Top Module / Entity Name** input to specify the designated top. If left blank, NoobEDA automatically parses the file AST to identify your primary entity.

### Phase 2: Analysis & Elaboration
- **Analyze & Elaborate (`GHDL -a -e` / `iverilog -Wall`)**:
  - Parses language semantics, checks bus-width consistency, and validates entity port mappings.
  - Automatically compiles all dependent HDL files in the project workspace.
  - Catches syntax errors, undefined signals, and type mismatches in less than 2 seconds.
- **Check Inferred Latches**:
  - Leverages Yosys RTL passes (`proc; opt`) or GHDL analysis to verify whether all conditional branches (`if`/`case`) have complete assignments.
  - Protects against unwanted hardware latches that consume clock routing and introduce timing race conditions.

### Phase 3: Testbench Simulation & Waveforms
- Click **▶️ Run Simulation**:
  - Compiles both your design sources and testbench into an executable simulation model.
  - Generates a standard Value Change Dump (`simulation.vcd`).
- Click **📈 Launch GTKWave Waveform**:
  - Opens the native GTKWave GUI with the generated `.vcd` preloaded.
- Click **⚡ Open in Editor Waveform**:
  - If you use VS Code with waveform extensions (such as *WaveTrace* or *Wavelyzer*), this opens the `.vcd` directly inside your editor.

### Phase 4: Gate-Level RTL Schematics
- Click **🎨 Generate Logic Schematic**:
  - Synthesizes the design through **Yosys** to infer logic gates, adders, multiplexers, and flip-flops.
  - Validates and sanitizes signal connections and tri-state buses.
  - Renders an IEEE-standard vector schematic using **netlistsvg**.
  - Automatically loads the diagram into the in-app **Schematic View** tab!

### Phase 5: JTAG & Hardware Boundary Scan
- Select your programming cable (e.g., `USB-Blaster (JTAG)`, `FTDI`, `Digilent JTAG-SMT2`).
- Click **🔍 Scan JTAG Chain**:
  - Uses `openFPGALoader --detect` to probe the physical JTAG boundary scan chain.
  - Reports connected FPGA device IDs and verifies cable communication.

---

## 4. Pin & Chip Planner

The **Pin & Chip Planner** tab bridges RTL design ports with physical silicon package pins.

```
+---------------------------------------------------------------------------------------+
| Target Board / FPGA Preset: [ Terasic DE1 (Cyclone II EP2C20F484C7) ▼ ] [ 📁 Load Custom ] |
| Status: Device: EP2C20F484C7 | 46 Pins Available                                       |
+---------------------------------------------------------------------------------------+
| [⚡ Scan Ports from Top HDL]  [🎯 Auto-Map by Name]  [🧹 Clear All]                   |
| Assign Selected to: [ PIN_L1 (CLOCK_50) ▼ ] [ Assign ]                                |
+---------------------------------------------------------------------------------------+
| Top HDL Port   | Direction | Data Type / Bus Width | Physical FPGA Pin | Peripheral   |
|----------------+-----------+-----------------------+-------------------+--------------|
| clk            | input     | std_logic             | PIN_L1            | CLOCK_50     |
| rst_n          | input     | std_logic             | PIN_R22           | KEY[0]       |
| data_out[7:0]  | output    | std_logic_vector(7:0) | PIN_R20           | LEDR[0]      |
+---------------------------------------------------------------------------------------+
| Export Hardware Constraints: [ 💾 Export .QSF ]  [ 💾 Export .PCF ]  [ 💾 Export .XDC ] |
+---------------------------------------------------------------------------------------+
```

### Steps to Assign Pins:
1. **Select a Target Board**:
   - Choose from built-in presets (**Terasic DE1**, **Terasic DE10-Lite**, **Lattice iCE40 Breakout**), or click **📁 Load Custom File** to load your own pinout definition (`.csv`, `.json`, `.qsf`, or `.xdc`).
2. **Scan Ports**:
   - Click **⚡ Scan Ports from Top HDL**. NoobEDA inspects the entity port block and populates the table with signal names, directions, and bit-widths.
3. **Auto-Map**:
   - Click **🎯 Auto-Map by Name**. NoobEDA intelligently matches signals (e.g., `clk` ➔ `CLOCK_50`, `rst` ➔ `KEY[0]`, `led` ➔ `LEDR[x]`).
4. **Manual Assignment**:
   - Click on any port row in the table, pick the desired physical pin from the dropdown, and click **Assign**.
5. **Export Constraints**:
   - **💾 Export .QSF**: For Intel / Altera Quartus Prime (`set_location_assignment`).
   - **💾 Export .PCF**: For Lattice / nextpnr / Project Trellis / IceStorm (`set_io`).
   - **💾 Export .XDC**: For AMD / Xilinx Vivado (`set_property PACKAGE_PIN`).

---

## 5. In-App Schematic Vector Canvas

The **Schematic View** tab embeds a high-DPI vector rendering engine directly into the application window:

- **Vector Rendering**: Powered by `PyMuPDF` and `Pillow`, rendering SVG schematics without pixelation or blurriness at any zoom level.
- **Interactive Drag-to-Pan**: Click and drag anywhere on the canvas to pan across large, complex netlists.
- **Mouse-Wheel Zoom**: Scroll the mouse wheel up to zoom in, and scroll down to zoom out (focus stays centered).
- **Zoom Toolbar Controls**:
  - `[🔍+ Zoom In]`
  - `[🔍- Zoom Out]`
  - `[🔄 100% Reset]`
  - `[🌐 Open External SVG]` (opens in your default web browser or vector editor)

---

## 6. Interactive Terminal

The bottom terminal pane gives you complete visibility and control over background EDA runs:

- **Live Streaming Output**: See synthesis logs, compiler warnings, and simulation outputs as they occur.
- **Command Input**: Enter arbitrary commands into the prompt bar.
- **History Navigation**: Use the **Up Arrow (↑)** and **Down Arrow (↓)** keys to cycle through previous terminal commands.
- **Process Abort (`⏹ Abort`)**: Instantly terminates any stuck simulation or long-running synthesis process safely without crashing NoobEDA.
- **Clipboard Export (`📋 Copy`)**: One click copies the entire log buffer for debugging or sharing.

---

## 7. Hardware Decision Tree & Diagnostics

The **Hardware Decision Tree** tab acts as an embedded senior digital designer, preventing common hardware bugs before you flash an FPGA:

| Diagnostic Topic | Rule & Best Practice |
| :--- | :--- |
| **Pushbuttons & Keys** | Most FPGA evaluation boards (DE1, DE10, Nexys) wire buttons as **Active-Low** (`'0'` = pressed, `'1'` = released). Invert signals at top-level entity if needed. |
| **7-Segment Displays** | Most development boards use **Active-Low Common Anode** displays (`'0'` turns segment ON, `'1'` turns segment OFF). |
| **Unused FPGA Pins** | Always configure unused pins as **"As input tri-stated with weak pull-up"** to prevent accidental short-circuits. |
| **Clock Domains** | Never drive registers with logic-generated clocks. Always use hardware PLLs or global clock routing networks (`BUFG` / `GLOBAL`). |
| **Asynchronous Resets** | Ensure asynchronous resets are de-asserted synchronously to avoid metastability. |

---

## 8. Multi-File Verilog & VHDL Projects

NoobEDA is built to handle modular projects with ease:

### How Multi-File Projects Work:
- **Automatic Discovery**: When you elaborate, simulate, or synthesize, NoobEDA inspects your workspace directory and automatically discovers all project sources (`.v`, `.sv`, `.vhd`, `.vhdl`).
- **Testbench Separation**: Design compilation excludes files marked with `_tb` or `test` to prevent module conflicts during synthesis.
- **Entity Binding**: Top-level entity ports and submodules are automatically resolved by the underlying compiler without needing manual Makefiles.

---

## 9. Toolchain Setup & Troubleshooting

### Recommended All-in-One Package:
The simplest way to equip your system with all required open-source engines is the **OSS CAD Suite**:
1. Download the archive for Windows, Linux, or macOS from the [YosysHQ Releases](https://github.com/YosysHQ/oss-cad-suite-build/releases/latest).
2. Extract the folder to your preferred directory (e.g., `C:\tools\oss-cad-suite` or `~/tools/oss-cad-suite`).
3. Add the `bin` directory to your system `PATH`.
4. Install `netlistsvg` for schematic generation:
   ```bash
   npm install -g netlistsvg
   ```

### Troubleshooting Checklist:

- **"netlistsvg is required to render electronic schematics"**:
  Make sure Node.js is installed (`node -v`) and run `npm install -g netlistsvg`.
- **"Waveform not opening"**:
  Ensure GTKWave is installed and present in your system `PATH`. Alternatively, click **⚡ Open in Editor Waveform** to use a VS Code extension.
- **"GHDL or Icarus Verilog missing"**:
  Check the **Operations** tab toolchain status badges. If a badge is red, verify that your compiler binary is on your environment `PATH`.
- **"JTAG cable not detected"**:
  Verify the USB cable is securely connected and that WinUSB or libusb drivers are bound (on Windows, use [Zadig](https://zadig.akeo.ie/) to configure the driver for USB-Blaster or FTDI).

---

*Happy Hacking with NoobEDA!* 🚀
