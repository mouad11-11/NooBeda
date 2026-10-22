import os
import pytest
from hdl_parser import extract_hdl_ports, is_testbench_file, get_top_module

def test_multi_name_port_declaration_drops_b(tmp_path):
    """Bug 1: 'input wire [7:0] a, b' drops b in legacy regex parser."""
    src = tmp_path / "multi_port.v"
    src.write_text(
        "module multi_port (\n"
        "    input wire [7:0] a, b,\n"
        "    output wire [7:0] y\n"
        ");\n"
        "endmodule\n",
        encoding="utf-8"
    )
    ports = extract_hdl_ports(str(src), "multi_port")
    port_names = [p["name"] for p in ports]
    # Expected behavior: both a and b should be extracted.
    # In legacy parser, this fails because b is dropped.
    assert "b" in port_names, f"Port 'b' was dropped! Extracted ports: {port_names}"

def test_parameter_block_returns_no_ports(tmp_path):
    """Bug 2: #(parameter N=8) causes port extraction to return empty list."""
    src = tmp_path / "param_mod.v"
    src.write_text(
        "module param_mod #(\n"
        "    parameter N = 8\n"
        ") (\n"
        "    input wire clk,\n"
        "    output wire [N-1:0] data\n"
        ");\n"
        "endmodule\n",
        encoding="utf-8"
    )
    ports = extract_hdl_ports(str(src), "param_mod")
    port_names = [p["name"] for p in ports]
    # Expected behavior: clk and data should be found.
    # In legacy parser, this fails because regex captures #(parameter N=8) instead of the port list.
    assert len(ports) > 0, "No ports returned for parameterized module!"
    assert "clk" in port_names
    assert "data" in port_names

def test_simple_counter_classed_as_testbench():
    """Bug 3: 'simple_counter.v' is falsely classified as a testbench due to 'sim' substring."""
    filename = "simple_counter.v"
    # Expected behavior: simple_counter.v is a design source, NOT a testbench.
    # In legacy parser, this fails because 'sim' in 'simple_counter.v' triggers testbench classification.
    assert not is_testbench_file(filename), f"'{filename}' was incorrectly classified as a testbench!"

def test_first_module_picked_as_top(tmp_path):
    """Bug 4: The first module in the file is picked as top instead of the true top module."""
    src = tmp_path / "counter_with_submodule.v"
    src.write_text(
        "module clock_divider (\n"
        "    input wire clk_in,\n"
        "    output wire clk_out\n"
        ");\n"
        "endmodule\n\n"
        "module top_counter (\n"
        "    input wire sys_clk,\n"
        "    output wire [3:0] count\n"
        ");\n"
        "    wire slow_clk;\n"
        "    clock_divider u_div (.clk_in(sys_clk), .clk_out(slow_clk));\n"
        "endmodule\n",
        encoding="utf-8"
    )
    top = get_top_module(str(src))
    # Expected behavior: 'top_counter' should be detected as the top module.
    # In legacy parser, this fails because it blindly picks 'clock_divider' (the first module).
    assert top == "top_counter", f"Expected 'top_counter' as top module, but got '{top}'"
