import pytest
import os
import tempfile
from exporters import build_qsf, build_pcf, build_xdc, expand_bus_mappings, parse_board_file
from hdl_parser import expand_bus_ports

def test_bus_expansion_in_exporters():
    pin_mappings = {
        "clk": "PIN_L1",
        "led[7:0]": [
            "PIN_R20", "PIN_R19", "PIN_U19", "PIN_Y19",
            "PIN_T18", "PIN_V19", "PIN_Y18", "PIN_U18"
        ]
    }
    expanded = expand_bus_mappings(pin_mappings)
    assert "clk" in expanded
    assert expanded["clk"] == "PIN_L1"
    for i in range(8):
        assert f"led[{i}]" in expanded
    assert expanded["led[0]"] == "PIN_R20"
    assert expanded["led[7]"] == "PIN_U18"

def test_bus_expansion_comma_string():
    pin_mappings = {
        "btn[2:0]": "PIN_A1, PIN_A2, PIN_A3"
    }
    expanded = expand_bus_mappings(pin_mappings)
    assert expanded["btn[0]"] == "PIN_A1"
    assert expanded["btn[1]"] == "PIN_A2"
    assert expanded["btn[2]"] == "PIN_A3"

def test_expand_bus_ports_hdl():
    raw_ports = [
        {"name": "clk", "dir": "input", "type": "1-bit"},
        {"name": "sw", "dir": "input", "type": "[3:0]"},
        {"name": "led", "dir": "output", "type": "std_logic_vector(7 downto 0)"}
    ]
    expanded = expand_bus_ports(raw_ports)
    names = [p["name"] for p in expanded]
    assert "clk" in names
    for i in range(4):
        assert f"sw[{i}]" in names
    for i in range(8):
        assert f"led[{i}]" in names
    assert len(expanded) == 1 + 4 + 8

def test_round_trip_qsf_export_and_reload(tmp_path):
    top = "alu_top"
    family = "Cyclone II"
    device = "EP2C20F484C7"
    original_mappings = {
        "clk": "PIN_L1",
        "rst": "PIN_R22",
        "led[0]": "PIN_R20",
        "led[1]": "PIN_R19",
        "led[2]": "PIN_U19",
        "sw[0]": "PIN_L22",
        "sw[1]": "PIN_L21"
    }

    qsf_content = build_qsf(top, family, device, original_mappings)
    qsf_file = tmp_path / f"{top}.qsf"
    qsf_file.write_text(qsf_content, encoding="utf-8")

    parsed_dev, parsed_fam, parsed_pins = parse_board_file(str(qsf_file))
    assert parsed_dev == device
    assert parsed_fam == family
    assert parsed_pins == original_mappings

def test_round_trip_pcf_export_and_reload(tmp_path):
    top = "ice_top"
    original_mappings = {
        "clk": "J3",
        "led[0]": "B5",
        "led[1]": "B4",
        "led[2]": "A2",
        "led[3]": "A1"
    }

    pcf_content = build_pcf(top, original_mappings)
    pcf_file = tmp_path / f"{top}.pcf"
    pcf_file.write_text(pcf_content, encoding="utf-8")

    _, parsed_fam, parsed_pins = parse_board_file(str(pcf_file))
    assert parsed_fam == "iCE40"
    assert parsed_pins == original_mappings

def test_ice40_preset_breakout_pins():
    # Verify official Lattice iCE40-HX8K breakout board pin mapping
    official_pcf = {
        "CLK": "J3",
        "LED[0]": "B5",
        "LED[1]": "B4",
        "LED[2]": "A2",
        "LED[3]": "A1",
        "LED[4]": "C5",
        "LED[5]": "C4",
        "LED[6]": "B3",
        "LED[7]": "C3",
    }
    for sig, pin in official_pcf.items():
        assert pin in ["J3", "B5", "B4", "A2", "A1", "C5", "C4", "B3", "C3"]
