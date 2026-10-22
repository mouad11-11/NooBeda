import os
import re
import json

def sanitize_netlist_json(json_path):
    """Sanitizes Yosys JSON netlist to strictly satisfy netlistsvg schema (tri-states and inouts)."""
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        def sanitize_val(val):
            if isinstance(val, list):
                return [sanitize_val(x) for x in val]
            elif isinstance(val, dict):
                return {k: sanitize_val(v) for k, v in val.items()}
            elif val in ("z", "Z", "Z0", "Z1", "z0", "z1"):
                return "x"
            return val

        for mod in data.get("modules", {}).values():
            for port in mod.get("ports", {}).values():
                if port.get("direction") == "inout":
                    port["direction"] = "output"
            for cell in mod.get("cells", {}).values():
                if "connections" in cell:
                    cell["connections"] = sanitize_val(cell["connections"])

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        return True
    except Exception as e:
        print(f"Netlist sanitization notice: {e}")
        return False

def prepare_svg_for_rendering(svg_content):
    """Inlines CSS attributes into raw SVG elements so vector renderers display all wires and labels."""
    # 1. Add stroke to line elements (wires)
    svg = re.sub(r'<line\s+', '<line stroke="#000" stroke-width="1.5" ', svg_content)
    
    # 2. Add stroke and fill to path elements
    def path_repl(m):
        full = m.group(0)
        if 'splitjoinBody' in full:
            return '<path stroke="#000" fill="#000" '
        return '<path stroke="#000" stroke-width="1.5" fill="none" '
    svg = re.sub(r'<path\s+', path_repl, svg)
    
    # 3. Add stroke to circle elements
    svg = re.sub(r'<circle\s+', '<circle stroke="#000" stroke-width="1.5" fill="none" ', svg)
    
    # 4. Add fill to text elements
    svg = re.sub(r'<text\s+', '<text fill="#000" stroke="none" font-family="monospace" font-weight="bold" ', svg)
    
    # 5. Add stroke to rect elements
    def rect_repl(m):
        full = m.group(0)
        if 'splitjoinBody' in full:
            return '<rect stroke="#000" fill="#000" '
        return '<rect stroke="#000" stroke-width="1.5" fill="none" '
    svg = re.sub(r'<rect\s+', rect_repl, svg)
    
    return svg
