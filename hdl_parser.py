import os
import re

def strip_comments(code: str, is_vhdl: bool = False) -> str:
    """Strips comments from HDL code while preserving string literals."""
    if is_vhdl:
        # VHDL line comments start with --
        return re.sub(r'--[^\r\n]*', '', code)
    else:
        # Verilog comments: /* ... */ block comments and // line comments
        def replacer(match):
            s = match.group(0)
            if s.startswith('/'):
                return " "
            return s
        pattern = r'(/\*.*?\*/|//[^\r\n]*|"(?:\\.|[^"\\])*")'
        return re.sub(pattern, replacer, code, flags=re.DOTALL)

def extract_hdl_entities(filepath):
    """Parses HDL source file to find declared entity (VHDL) or module (Verilog) names."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            raw_content = f.read()
    except Exception:
        return []

    lower_ext = os.path.splitext(filepath)[1].lower()
    is_vhdl = lower_ext in [".vhd", ".vhdl"]
    content = strip_comments(raw_content, is_vhdl=is_vhdl)

    if is_vhdl:
        matches = re.findall(r"(?i)\bentity\s+([a-zA-Z0-9_]+)\s+is\b", content)
        return matches
    elif lower_ext in [".v", ".sv"]:
        matches = re.findall(r"(?i)\bmodule\s+([a-zA-Z0-9_]+)\b", content)
        return matches
    return []

def extract_hdl_ports(filepath, target_entity=None):
    """
    Extracts port declarations (name, direction, type/width) from an HDL file.
    Handles:
    - ANSI and non-ANSI Verilog module headers
    - Parameterized modules #(parameter N=8)
    - Multi-name declarations: input wire [7:0] a, b
    - Bus ranges and data types
    - VHDL entity ports with generics
    """
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            raw_code = f.read()
    except Exception:
        return []

    lower_ext = os.path.splitext(filepath)[1].lower()
    is_vhdl = lower_ext in [".vhd", ".vhdl"]
    code = strip_comments(raw_code, is_vhdl=is_vhdl)
    ports = []

    if is_vhdl:
        # VHDL: match entity ... is ... port ( ... ); end
        ent_name = re.escape(target_entity) if target_entity else r'[a-zA-Z0-9_]+'
        ent_pat = rf"(?i)\bentity\s+{ent_name}\s+is\b.*?\bport\s*\((.*?)\)\s*;\s*(?:end\b)"
        m = re.search(ent_pat, code, re.DOTALL)
        if m:
            port_text = m.group(1)
            for stmt in port_text.split(";"):
                stmt = stmt.strip()
                if ":" in stmt:
                    p_names, rest = stmt.split(":", 1)
                    rest = rest.strip()
                    m_dir = re.search(r"^(inout|in|out|buffer)\b", rest, re.IGNORECASE)
                    direction = m_dir.group(1).lower() if m_dir else "in"
                    p_type = rest[len(direction):].strip()
                    for single_name in p_names.split(","):
                        single_name = single_name.strip()
                        if single_name:
                            ports.append({"name": single_name, "dir": direction, "type": p_type})
    elif lower_ext in [".v", ".sv"]:
        mod_name = re.escape(target_entity) if target_entity else r'[a-zA-Z0-9_]+'
        # Match module name, optional parameter block #( ... ), followed by port list ( ... );
        # or non-ANSI: module name ( ... ); followed by body declarations
        mod_header_pat = rf"(?i)\bmodule\s+{mod_name}\s*(?:#\s*\([^;]*?\)\s*)?\s*\((.*?)\)\s*;"
        m = re.search(mod_header_pat, code, re.DOTALL)

        if m:
            port_text = m.group(1).strip()
            # Check if this is ANSI (contains input/output/inout) or non-ANSI (just identifier list)
            has_ansi_direction = bool(re.search(r"\b(input|output|inout)\b", port_text, re.IGNORECASE))

            if has_ansi_direction:
                # Parse ANSI port list, accounting for multi-name declarations:
                # e.g., "input wire [7:0] a, b, output reg [3:0] y, z"
                curr_dir = "in"
                curr_type = "wire"
                curr_width = "1-bit"

                tokens = [t.strip() for t in port_text.split(",") if t.strip()]
                for token in tokens:
                    # Check if token starts with a direction
                    dir_match = re.match(
                        r"^(input|output|inout)\b\s*(?:(wire|reg|logic)\b)?\s*(\[[^\]]+\])?\s*([a-zA-Z0-9_]+)$",
                        token,
                        re.IGNORECASE
                    )
                    if dir_match:
                        curr_dir = dir_match.group(1).lower()
                        curr_type = dir_match.group(2) or "wire"
                        curr_width = dir_match.group(3) or "1-bit"
                        name = dir_match.group(4)
                        ports.append({"name": name, "dir": curr_dir, "type": curr_width})
                    else:
                        # Multi-name follow-up token inheriting previous direction and width
                        sub_dir_match = re.search(r"\b(input|output|inout)\b", token, re.IGNORECASE)
                        if sub_dir_match:
                            m_v = re.search(r"(input|output|inout)\s*(?:wire|reg|logic)?\s*(\[[^\]]+\])?\s*([a-zA-Z0-9_]+)", token, re.IGNORECASE)
                            if m_v:
                                curr_dir = m_v.group(1).lower()
                                curr_width = m_v.group(2) or "1-bit"
                                name = m_v.group(3)
                                ports.append({"name": name, "dir": curr_dir, "type": curr_width})
                        else:
                            ident_match = re.search(r"^([a-zA-Z0-9_]+)$", token)
                            if ident_match:
                                ports.append({"name": ident_match.group(1), "dir": curr_dir, "type": curr_width})
            else:
                # Non-ANSI port list: parse declarations in module body
                mod_body_pat = rf"(?i)\bmodule\s+{mod_name}\b.*?\bendmodule\b"
                mod_body_m = re.search(mod_body_pat, code, re.DOTALL)
                body_code = mod_body_m.group(0) if mod_body_m else code

                decl_pat = r"\b(input|output|inout)\b\s*(?:wire|reg|logic)?\s*(\[[^\]]+\])?\s*([^;]+);"
                for dm in re.finditer(decl_pat, body_code, re.IGNORECASE):
                    direction = dm.group(1).lower()
                    width = dm.group(2) or "1-bit"
                    names_part = dm.group(3)
                    for n in names_part.split(","):
                        clean_n = n.strip()
                        if clean_n and re.match(r"^[a-zA-Z0-9_]+$", clean_n):
                            ports.append({"name": clean_n, "dir": direction, "type": width})

    return ports

def is_testbench_file(filepath, content=None):
    """
    Detects whether a file is a testbench.
    Uses:
    1. Pattern check on filename (tb_*, *_tb, *_test, *_testbench).
    2. Content check: zero external ports AND contains an initial block (Verilog)
       or entity with zero ports (VHDL).
    Does NOT use loose substring matching (avoiding false positives like 'simple_counter.v').
    """
    base = os.path.basename(filepath)
    name, ext = os.path.splitext(base)
    lower_name = name.lower()

    # 1. Exact pattern matching on filename
    tb_patterns = [
        r"^tb_.*",
        r".*_tb$",
        r".*_test$",
        r".*_testbench$",
        r"^test_.*"
    ]
    if any(re.match(pat, lower_name) for pat in tb_patterns):
        return True

    # 2. Content inspection
    if content is None:
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            return False

    is_vhdl = ext.lower() in [".vhd", ".vhdl"]
    clean_code = strip_comments(content, is_vhdl=is_vhdl)

    if is_vhdl:
        ent_match = re.search(r"(?i)\bentity\s+([a-zA-Z0-9_]+)\s+is\b(.*?)\bend\b", clean_code, re.DOTALL)
        if ent_match:
            ent_body = ent_match.group(2)
            has_ports = bool(re.search(r"\bport\s*\(", ent_body, re.IGNORECASE))
            if not has_ports and re.search(r"\barchitecture\b", clean_code, re.IGNORECASE):
                return True
    else:
        mod_match = re.search(r"(?i)\bmodule\s+([a-zA-Z0-9_]+)\s*(?:\([^)]*\))?\s*;", clean_code)
        if mod_match:
            ports = extract_hdl_ports(filepath)
            has_initial = bool(re.search(r"\binitial\b", clean_code))
            if len(ports) == 0 and has_initial:
                return True

    return False

def get_top_module(filepath):
    """
    Picks the top module in a file or design.
    Method:
    1. Finds all declared modules/entities in the file.
    2. Checks which module is instantiated by others.
    3. The module that is NOT instantiated by any other module is the top module.
    4. If ambiguous (e.g. none instantiated), falls back to the LAST module declared.
    """
    entities = extract_hdl_entities(filepath)
    if not entities:
        return os.path.splitext(os.path.basename(filepath))[0]
    if len(entities) == 1:
        return entities[0]

    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            raw_content = f.read()
    except Exception:
        return entities[-1]

    lower_ext = os.path.splitext(filepath)[1].lower()
    clean_code = strip_comments(raw_content, is_vhdl=(lower_ext in [".vhd", ".vhdl"]))

    instantiated = set()
    for ent in entities:
        for other in entities:
            if other == ent:
                continue
            inst_pat = rf"\b{re.escape(other)}\b\s*(?:#\s*\([^;]*?\)\s*)?[a-zA-Z0-9_]+\s*\("
            if re.search(inst_pat, clean_code):
                instantiated.add(other)

    candidates = [e for e in entities if e not in instantiated]
    if len(candidates) == 1:
        return candidates[0]
    elif candidates:
        return candidates[-1]

    return entities[-1]
