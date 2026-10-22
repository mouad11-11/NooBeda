import os
import shutil
import subprocess
import pytest
from hdl_parser import discover_sources
from noobeda import configure_toolchain_environment

configure_toolchain_environment()

def test_recursive_discovery_skips_build(tmp_path):
    """Verify discover_sources finds files recursively and ignores build/work dirs."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "alu.v").write_text("module alu; endmodule", encoding="utf-8")

    sub_dir = src_dir / "pkg"
    sub_dir.mkdir()
    (sub_dir / "defs.sv").write_text("package defs; endpackage", encoding="utf-8")

    build_dir = tmp_path / "_build"
    build_dir.mkdir()
    (build_dir / "cached.v").write_text("module cached; endmodule", encoding="utf-8")

    discovered = discover_sources(str(tmp_path), extensions=(".v", ".sv"))
    disc_basenames = [os.path.basename(p) for p in discovered]

    assert "alu.v" in disc_basenames
    assert "defs.sv" in disc_basenames
    assert "cached.v" not in disc_basenames, "_build directory was not skipped!"

def test_two_module_verilog_build_flow(tmp_path):
    """Test 2-module Verilog/SV project builds and elaborates with Yosys hierarchy."""
    yosys_bin = shutil.which("yosys")
    iverilog_bin = shutil.which("iverilog")
    vvp_bin = shutil.which("vvp")

    if not (yosys_bin and iverilog_bin and vvp_bin):
        pytest.skip("OSS CAD Suite toolchain not installed in PATH")

    build_dir = tmp_path / "_build"
    build_dir.mkdir()

    sub = tmp_path / "adder.v"
    sub.write_text(
        "module adder (input [7:0] a, b, output [7:0] sum);\n"
        "    assign sum = a + b;\n"
        "endmodule\n",
        encoding="utf-8"
    )

    top = tmp_path / "calc.sv"
    top.write_text(
        "module calc (input logic [7:0] x, y, output logic [7:0] out);\n"
        "    adder u1 (.a(x), .b(y), .sum(out));\n"
        "endmodule\n",
        encoding="utf-8"
    )

    tb = tmp_path / "tb_calc.v"
    tb.write_text(
        "module tb_calc;\n"
        "    reg [7:0] x, y;\n"
        "    wire [7:0] out;\n"
        "    calc dut (.x(x), .y(y), .out(out));\n"
        "    initial begin\n"
        "        $dumpfile(\"" + str(build_dir / "simulation.vcd").replace("\\", "/") + "\");\n"
        "        $dumpvars(0, tb_calc);\n"
        "        x = 5; y = 10; #10;\n"
        "        $finish;\n"
        "    end\n"
        "endmodule\n",
        encoding="utf-8"
    )

    all_v = discover_sources(str(tmp_path), extensions=(".v", ".sv"))
    vvp_out = str(build_dir / "sim.vvp")

    # 1. Compile simulation with -g2012 for SystemVerilog
    p_comp = subprocess.run([iverilog_bin, "-g2012", "-o", vvp_out] + all_v, cwd=str(tmp_path), capture_output=True, text=True)
    assert p_comp.returncode == 0, f"Compilation failed: {p_comp.stderr}"

    # 2. Run simulation
    p_sim = subprocess.run([vvp_bin, vvp_out], cwd=str(tmp_path), capture_output=True, text=True)
    assert p_sim.returncode == 0, f"Simulation failed: {p_sim.stderr}"
    assert (build_dir / "simulation.vcd").exists(), "VCD file not generated in _build!"

    # 3. Yosys synthesis with hierarchy -check -top calc and -sv flag
    json_out = str(build_dir / "netlist.json")
    yosys_cmds = f'read_verilog "{sub}"; read_verilog -sv "{top}"; hierarchy -check -top calc; proc; opt; write_json "{json_out}"'
    p_synth = subprocess.run([yosys_bin, "-p", yosys_cmds], cwd=str(tmp_path), capture_output=True, text=True)
    assert p_synth.returncode == 0, f"Yosys synthesis failed: {p_synth.stdout}"
    assert (build_dir / "netlist.json").exists(), "netlist.json not generated in _build!"

def test_three_file_vhdl_project_automatic_order(tmp_path):
    """Test 3-file VHDL project (package, entity, testbench) with ghdl -i and ghdl -m."""
    ghdl_bin = shutil.which("ghdl")
    if not ghdl_bin:
        pytest.skip("GHDL binary not in PATH")

    build_dir = tmp_path / "_build"
    build_dir.mkdir()

    # File 1: Package
    pkg = tmp_path / "pkg.vhd"
    pkg.write_text(
        "library ieee;\n"
        "use ieee.std_logic_1164.all;\n"
        "package my_pkg is\n"
        "    constant WIDTH : integer := 4;\n"
        "end package my_pkg;\n",
        encoding="utf-8"
    )

    # File 2: Entity using package
    ent = tmp_path / "core.vhd"
    ent.write_text(
        "library ieee;\n"
        "use ieee.std_logic_1164.all;\n"
        "use work.my_pkg.all;\n"
        "entity core is\n"
        "    port (clk : in std_logic; d : in std_logic_vector(WIDTH-1 downto 0); q : out std_logic_vector(WIDTH-1 downto 0));\n"
        "end entity core;\n"
        "architecture rtl of core is\n"
        "begin\n"
        "    process(clk) begin\n"
        "        if rising_edge(clk) then\n"
        "            q <= d;\n"
        "        end if;\n"
        "    end process;\n"
        "end architecture;\n",
        encoding="utf-8"
    )

    # File 3: Testbench
    tb = tmp_path / "tb_core.vhd"
    tb.write_text(
        "library ieee;\n"
        "use ieee.std_logic_1164.all;\n"
        "use work.my_pkg.all;\n"
        "entity tb_core is\n"
        "end entity;\n"
        "architecture sim of tb_core is\n"
        "    signal clk : std_logic := '0';\n"
        "    signal d, q : std_logic_vector(WIDTH-1 downto 0) := (others => '0');\n"
        "begin\n"
        "    uut: entity work.core port map(clk => clk, d => d, q => q);\n"
        "    clk <= not clk after 5 ns;\n"
        "    process begin\n"
        "        d <= \"0001\"; wait for 20 ns;\n"
        "        std.env.finish;\n"
        "    end process;\n"
        "end architecture;\n",
        encoding="utf-8"
    )

    all_vhd = discover_sources(str(tmp_path), extensions=(".vhd", ".vhdl"))

    # Pass in intentionally reverse order to prove ghdl -i / ghdl -m solves dependency graph automatically!
    reverse_vhd = list(reversed(all_vhd))

    # 1. ghdl -i imports into workdir
    p_import = subprocess.run([ghdl_bin, "-i", f"--workdir={build_dir}", "--std=08"] + reverse_vhd, cwd=str(tmp_path), capture_output=True, text=True)
    assert p_import.returncode == 0, f"ghdl -i failed: {p_import.stderr}"

    # 2. ghdl -m compiles and resolves order
    p_make = subprocess.run([ghdl_bin, "-m", f"--workdir={build_dir}", "--std=08", "tb_core"], cwd=str(tmp_path), capture_output=True, text=True)
    assert p_make.returncode == 0, f"ghdl -m failed: {p_make.stderr}"

    # 3. ghdl -r simulates
    vcd_out = str(build_dir / "simulation.vcd")
    p_run = subprocess.run([ghdl_bin, "-r", f"--workdir={build_dir}", "--std=08", "tb_core", f"--vcd={vcd_out}"], cwd=str(tmp_path), capture_output=True, text=True)
    assert p_run.returncode == 0, f"ghdl -r failed: {p_run.stderr}"
    assert (build_dir / "simulation.vcd").exists(), "VHDL VCD not generated in _build!"
