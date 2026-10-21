# NoobEDA ⚡

> **The Zero-Bloat, Beginner-Friendly Cockpit for Open-Source FPGA & Digital Design**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8+-green.svg)](https://www.python.org/)
[![Platform: Windows | Linux | macOS](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)]()

Traditional vendor EDA software (Quartus, Vivado, ModelSim) takes **20–40 GB** of disk space, requires complicated license managers, and often abandons support for older hardware (such as Cyclone II boards).

**NoobEDA** is a lightweight, cross-platform graphical workbench that stitches the most powerful open-source hardware tools into a seamless, **1-click workflow**.

---

## 🚀 Features

- 📁 **Universal Workspace Adaptive**: Change folders anytime or run inside any project. Automatically detects VHDL (`.vhd`) and Verilog (`.v`, `.sv`) sources and testbenches.
- ⚡ **Instant Analysis & Elaboration**: Run fast syntax checks and submodule port bindings via GHDL or Icarus Verilog in < 2 seconds.
- 🔍 **Inferred Latch Detector**: Spot accidental asynchronous latches (missing `else` or default branches) before synthesis.
- 🧪 **1-Click Simulation → Waveforms**: Compile, simulate, and launch **GTKWave** or view interactive waveforms inside your editor via `.vcd`.
- 🎨 **RTL Vector Schematics**: Translates your behavioral HDL into interactive vector diagrams (`.svg`) via Yosys and Graphviz with zoom and wire tracing.
- 🔌 **Hardware JTAG Scanner**: Detect connected USB-Blaster, FTDI, or other programming cables using `openFPGALoader`.
- 🧠 **Embedded Decision Guide**: Diagnostic knowledge base covering active-low buttons, 7-segment displays, clock domains, and unused pin protection.

---

## 🛠️ Toolchain Under the Hood

NoobEDA acts as a graphical control deck over best-in-class open-source engines:

| Engine | Role in NoobEDA |
| :--- | :--- |
| **[GHDL](https://github.com/ghdl/ghdl)** | VHDL-2008 / VHDL-93 compilation, elaboration, and simulation |
| **[Icarus Verilog](https://github.com/steveicarus/iverilog)** | Verilog / SystemVerilog simulation and AST elaboration |
| **[GTKWave](https://gtkwave.sourceforge.net/)** | Full timing diagram and digital bus waveform inspection |
| **[Yosys](https://github.com/YosysHQ/yosys)** | RTL synthesis engine for gate mapping and structural extraction |
| **[Graphviz](https://graphviz.org/)** | Netlist rendering to clean SVG schematic diagrams |
| **[openFPGALoader](https://github.com/trabucayre/openFPGALoader)** | Universal JTAG boundary-scan and FPGA bitstream flasher |

---

## 📦 Installation & Getting Started

### 1. Prerequisites
NoobEDA requires **Python 3.8+** (with Tkinter, which is included by default with standard Python installers).

Install the open-source EDA engines:
* **All-in-One (Recommended for Windows/Linux/macOS)**:
  Download the ready-to-run [OSS CAD Suite](https://github.com/YosysHQ/oss-cad-suite-build/releases/latest) or install via your system package manager:
  ```bash
  # Debian / Ubuntu
  sudo apt install ghdl iverilog gtkwave yosys graphviz

  # Arch Linux
  sudo pacman -S ghdl iverilog gtkwave yosys graphviz

  # macOS (Homebrew)
  brew install ghdl icarus-verilog gtkwave yosys graphviz
  ```

### 2. Clone and Run
```bash
git clone https://github.com/mouad11-11/NooBeda.git
cd NooBeda
python noobeda.py
```

---

## 🧭 The 5-Phase Workflow in NoobEDA

```mermaid
flowchart LR
    P1["1. Project Setup<br/>(Auto-detect)"] --> P2["2. Elaboration<br/>(GHDL / Icarus)"]
    P2 --> P3["3. Simulation<br/>(VCD Waveforms)"]
    P3 --> P4["4. Synthesis<br/>(Yosys Schematic)"]
    P4 --> P5["5. Hardware<br/>(JTAG Detect)"]
```

1. **Setup**: Select your working directory and designated top module.
2. **Elaborate**: Catch 95% of typos, missing semicolons, and port mismatches in seconds without running full synthesis.
3. **Simulate**: Run your testbench and view signal transitions in GTKWave with proper Hex/Decimal bus formatting.
4. **Schematic**: Generate vector SVGs to visually inspect your ALU arithmetic blocks, multiplexers, and state registers.
5. **Hardware**: Verify cable connectivity before programming silicon.

---

## 📄 License
This project is open-source under the [MIT License](LICENSE).
