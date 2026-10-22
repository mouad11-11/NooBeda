import os
import re

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

def extract_hdl_ports(filepath, target_entity=None):
    """Extracts port declarations (name, direction, type/width) from an HDL file."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            code = f.read()
    except Exception:
        return []

    ports = []
    lower_ext = os.path.splitext(filepath)[1].lower()

    if lower_ext in [".vhd", ".vhdl"]:
        ent_pat = rf"(?i)entity\s+{re.escape(target_entity) if target_entity else r'\w+'}\s+is.*?port\s*\((.*?)\);\s*end"
        m = re.search(ent_pat, code, re.DOTALL)
        if m:
            port_text = m.group(1)
            for line in port_text.split(";"):
                line = line.strip()
                if ":" in line:
                    p_names, rest = line.split(":", 1)
                    rest = rest.strip()
                    m_dir = re.search(r"^(inout|in|out|buffer)\b", rest, re.IGNORECASE)
                    direction = m_dir.group(1).lower() if m_dir else "in"
                    p_type = rest[len(direction):].strip()
                    for single_name in p_names.split(","):
                        single_name = single_name.strip()
                        if single_name:
                            ports.append({"name": single_name, "dir": direction, "type": p_type})
    elif lower_ext in [".v", ".sv"]:
        mod_pat = rf"(?i)module\s+{re.escape(target_entity) if target_entity else r'\w+'}\s*\((.*?)\);"
        m = re.search(mod_pat, code, re.DOTALL)
        if m:
            port_text = m.group(1)
            for item in port_text.split(","):
                item = item.strip()
                m_v = re.search(r"(input|output|inout)\s*(?:wire|reg)?\s*(\[[^\]]+\])?\s*([a-zA-Z0-9_]+)", item)
                if m_v:
                    direction = m_v.group(1).lower()
                    width = m_v.group(2) or "1-bit"
                    name = m_v.group(3)
                    ports.append({"name": name, "dir": direction, "type": width})
    return ports

def is_testbench_file(filepath):
    """Current legacy testbench detection based on filename keywords."""
    lower = os.path.basename(filepath).lower()
    return any(kw in lower for kw in ["tb", "test", "bench", "sim"])

def get_top_module(filepath):
    """Current legacy top module detection: simply picks the first module/entity declared."""
    entities = extract_hdl_entities(filepath)
    if entities:
        return entities[0]
    return os.path.splitext(os.path.basename(filepath))[0]
