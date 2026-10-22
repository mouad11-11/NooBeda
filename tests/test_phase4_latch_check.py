import pytest
import os
import subprocess
import shutil
from netlist import parse_yosys_latch_output

def get_toolchain_env():
    env = os.environ.copy()
    candidate_paths = [
        r"C:\tools\oss-cad-suite\bin",
        r"C:\tools\oss-cad-suite\lib",
        r"C:\tools\ghdl\bin"
    ]
    existing = [p for p in candidate_paths if os.path.exists(p)]
    if existing:
        env["PATH"] = ";".join(existing) + ";" + env.get("PATH", "")
    return env

def test_parse_yosys_latch_output_unit():
    raw_sample = """
3. Executing PROC_DLATCH pass (find and create latches).
Latch inferred for signal `\\bad_module.\\q' from process `\\bad_module.$proc$bad.v:5$1': $auto$proc_dlatch.cc:427:proc_dlatch$27
Latch inferred for signal `\\bad_module.\\state' from process `\\bad_module.$proc$bad.v:18$2': $auto$proc_dlatch.cc:427:proc_dlatch$28
4. Executing OPT pass (optimize).
"""
    latches = parse_yosys_latch_output(raw_sample)
    assert len(latches) == 2
    assert latches[0]["module"] == "bad_module"
    assert latches[0]["signal"] == "q"
    assert latches[0]["line"] == "5"

    assert latches[1]["module"] == "bad_module"
    assert latches[1]["signal"] == "state"
    assert latches[1]["line"] == "18"

    clean_sample = """
3. Executing PROC_DLATCH pass (find and create latches).
4. Executing OPT pass (optimize).
"""
    clean_latches = parse_yosys_latch_output(clean_sample)
    assert len(clean_latches) == 0

def test_ghdl_latch_output_parsing():
    ghdl_err = 'C:\\temp\\bad_latch.vhd:9:9:error: latch infered for net "q" (use --latches)\n        q  : out std_logic;\n'
    latches = parse_yosys_latch_output(ghdl_err)
    assert len(latches) == 1
    assert latches[0]["signal"] == "q"
    assert latches[0]["line"] == "9"

def test_verilog_latch_detection_real_yosys(tmp_path):
    env = get_toolchain_env()
    yosys = shutil.which("yosys", path=env["PATH"]) or (r"C:\tools\oss-cad-suite\bin\yosys.exe" if os.path.exists(r"C:\tools\oss-cad-suite\bin\yosys.exe") else None)
    if not yosys:
        pytest.skip("Yosys binary not found in environment")

    # 1. Deliberately bad Verilog (missing else)
    bad_v = tmp_path / "bad_latch.v"
    bad_v.write_text("""
module bad_latch(input wire en, input wire d, output reg q);
    always @(*) begin
        if (en)
            q = d;
    end
endmodule
""", encoding="utf-8")

    proc = subprocess.run(
        [yosys, "-p", f'read_verilog "{bad_v}"; proc; opt'],
        capture_output=True,
        text=True,
        env=env,
        cwd=tmp_path
    )
    latches = parse_yosys_latch_output(proc.stdout)
    assert len(latches) >= 1
    assert any(l["signal"] == "q" for l in latches)

    # 2. Clean combinational design
    clean_v = tmp_path / "clean_comb.v"
    clean_v.write_text("""
module clean_comb(input wire sel, input wire a, input wire b, output reg y);
    always @(*) begin
        if (sel)
            y = a;
        else
            y = b;
    end
endmodule
""", encoding="utf-8")

    proc_clean = subprocess.run(
        [yosys, "-p", f'read_verilog "{clean_v}"; proc; opt'],
        capture_output=True,
        text=True,
        env=env,
        cwd=tmp_path
    )
    clean_latches = parse_yosys_latch_output(proc_clean.stdout)
    assert len(clean_latches) == 0

def test_vhdl_latch_detection_ghdl_yosys(tmp_path):
    env = get_toolchain_env()
    ghdl = shutil.which("ghdl", path=env["PATH"]) or (r"C:\tools\oss-cad-suite\bin\ghdl.exe" if os.path.exists(r"C:\tools\oss-cad-suite\bin\ghdl.exe") else None)
    if not ghdl:
        pytest.skip("GHDL binary not found in environment")

    bad_vhd = tmp_path / "bad_latch.vhd"
    bad_vhd.write_text("""
library ieee;
use ieee.std_logic_1164.all;

entity bad_latch_vhdl is
    port (
        en : in std_logic;
        d  : in std_logic;
        q  : out std_logic
    );
end entity;

architecture rtl of bad_latch_vhdl is
begin
    process(en, d)
    begin
        if en = '1' then
            q <= d;
        end if;
    end process;
end architecture;
""", encoding="utf-8")

    ghdl_res = subprocess.run(
        [ghdl, "--synth", "--std=08", "--out=verilog", str(bad_vhd), "-e", "bad_latch_vhdl"],
        capture_output=True,
        text=True,
        env=env,
        cwd=tmp_path
    )
    # GHDL synthesizes or flags error: latch infered for net "q"
    output = ghdl_res.stdout + "\n" + ghdl_res.stderr
    latches = parse_yosys_latch_output(output)
    assert len(latches) >= 1
    assert any("q" in l["signal"] for l in latches)

    # Clean VHDL design
    clean_vhd = tmp_path / "clean_comb.vhd"
    clean_vhd.write_text("""
library ieee;
use ieee.std_logic_1164.all;

entity clean_comb_vhdl is
    port (
        sel : in std_logic;
        a   : in std_logic;
        b   : in std_logic;
        y   : out std_logic
    );
end entity;

architecture rtl of clean_comb_vhdl is
begin
    process(sel, a, b)
    begin
        if sel = '1' then
            y <= a;
        else
            y <= b;
        end if;
    end process;
end architecture;
""", encoding="utf-8")

    ghdl_clean = subprocess.run(
        [ghdl, "--synth", "--std=08", "--out=verilog", str(clean_vhd), "-e", "clean_comb_vhdl"],
        capture_output=True,
        text=True,
        env=env,
        cwd=tmp_path
    )
    clean_output = ghdl_clean.stdout + "\n" + ghdl_clean.stderr
    clean_latches = parse_yosys_latch_output(clean_output)
    assert len(clean_latches) == 0
