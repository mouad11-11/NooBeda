import os
import pytest
from hdl_parser import extract_hdl_entities, extract_hdl_ports, is_testbench_file, get_top_module

def test_vhdl_generics_and_comments(tmp_path):
    """Test VHDL entity with generics, comments, and multi-name ports."""
    src = tmp_path / "alu_vhdl.vhd"
    src.write_text(
        "-- This is a comment\n"
        "library ieee;\n"
        "use ieee.std_logic_1164.all;\n\n"
        "entity alu_vhdl is\n"
        "    generic (\n"
        "        DATA_WIDTH : integer := 8; -- Generic width\n"
        "        ADDR_WIDTH : integer := 4\n"
        "    );\n"
        "    port (\n"
        "        clk, rst_n : in std_logic; -- Control signals\n"
        "        data_in    : in std_logic_vector(DATA_WIDTH-1 downto 0);\n"
        "        data_out   : out std_logic_vector(DATA_WIDTH-1 downto 0)\n"
        "    );\n"
        "end entity alu_vhdl;\n",
        encoding="utf-8"
    )
    entities = extract_hdl_entities(str(src))
    assert entities == ["alu_vhdl"]

    ports = extract_hdl_ports(str(src), "alu_vhdl")
    port_dict = {p["name"]: p for p in ports}

    assert "clk" in port_dict and port_dict["clk"]["dir"] == "in"
    assert "rst_n" in port_dict and port_dict["rst_n"]["dir"] == "in"
    assert "data_in" in port_dict and port_dict["data_in"]["dir"] == "in"
    assert "data_out" in port_dict and port_dict["data_out"]["dir"] == "out"

def test_multi_module_top_detection(tmp_path):
    """Test 3 modules in a single file with hierarchical instantiation."""
    src = tmp_path / "soc_top.v"
    src.write_text(
        "module alu (input [7:0] a, b, output [7:0] y);\n"
        "    assign y = a + b;\n"
        "endmodule\n\n"
        "module reg_file (input clk, input [7:0] d, output [7:0] q);\n"
        "endmodule\n\n"
        "module soc_top (input clk, input [7:0] in_data, output [7:0] out_data);\n"
        "    wire [7:0] alu_res;\n"
        "    alu u_alu (.a(in_data), .b(8'h01), .y(alu_res));\n"
        "    reg_file u_rf (.clk(clk), .d(alu_res), .q(out_data));\n"
        "endmodule\n",
        encoding="utf-8"
    )
    entities = extract_hdl_entities(str(src))
    assert entities == ["alu", "reg_file", "soc_top"]

    top = get_top_module(str(src))
    assert top == "soc_top"

def test_non_ansi_verilog_ports(tmp_path):
    """Test non-ANSI Verilog module with body port declarations."""
    src = tmp_path / "legacy_module.v"
    src.write_text(
        "module legacy_module (clk, reset, data_in, data_out);\n"
        "    input clk, reset;\n"
        "    input [7:0] data_in;\n"
        "    output [7:0] data_out;\n"
        "    // Internal logic\n"
        "endmodule\n",
        encoding="utf-8"
    )
    ports = extract_hdl_ports(str(src), "legacy_module")
    port_names = [p["name"] for p in ports]
    assert "clk" in port_names
    assert "reset" in port_names
    assert "data_in" in port_names
    assert "data_out" in port_names
