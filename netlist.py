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
    
    # 2. Add stroke and fill to path elements (splitjoin elements get fill="#000")
    def path_repl(m):
        attrs = m.group(1)
        if 'splitjoin' in attrs.lower():
            return f'<path stroke="#000" fill="#000"{attrs}>'
        return f'<path stroke="#000" stroke-width="1.5" fill="none"{attrs}>'
    svg = re.sub(r'<path([^>]*)>', path_repl, svg)
    
    # 3. Add stroke to circle elements
    svg = re.sub(r'<circle\s+', '<circle stroke="#000" stroke-width="1.5" fill="none" ', svg)
    
    # 4. Add fill to text elements
    svg = re.sub(r'<text\s+', '<text fill="#000" stroke="none" font-family="monospace" font-weight="bold" ', svg)
    
    # 5. Add stroke to rect elements (splitjoin elements get fill="#000")
    def rect_repl(m):
        attrs = m.group(1)
        if 'splitjoin' in attrs.lower():
            return f'<rect stroke="#000" fill="#000"{attrs}>'
        return f'<rect stroke="#000" stroke-width="1.5" fill="none"{attrs}>'
    svg = re.sub(r'<rect([^>]*)>', rect_repl, svg)

    # 6. Add explicit style rule for splitjoinBody in SVG
    style_rule = """<style>
.splitjoinBody { fill: #000 !important; stroke: #000 !important; }
line { stroke: #000; stroke-width: 1.5; }
</style>"""
    if "<svg" in svg and "</svg>" in svg:
        svg = re.sub(r'(<svg[^>]*>)', r'\1' + style_rule, svg, count=1)
    
    return svg

def parse_yosys_latch_output(output_text: str):
    """
    Parses synthesis (Yosys or GHDL) output to find inferred latches.
    Returns a list of dicts: [{'module': ..., 'signal': ..., 'line': ..., 'raw': ...}]
    """
    latches = []
    yosys_pattern = r"Latch inferred for signal [`']\\?([a-zA-Z0-9_]+)\.\\?([a-zA-Z0-9_]+)['\"]"
    ghdl_pattern = r"latch infer+ed for net [\"']?([a-zA-Z0-9_]+)[\"']?"

    for line in output_text.splitlines():
        line_lower = line.lower()
        if "no latch inferred" in line_lower:
            continue
        if "latch inferred for signal" in line_lower:
            m = re.search(yosys_pattern, line, re.IGNORECASE)
            # Find line number (e.g., $proc$bad.v:5$1 or bad.v:5)
            line_m = re.search(r"\$([^\s:]+):([0-9]+)\$", line)
            if not line_m:
                line_m = re.search(r":([0-9]+)", line)
            
            line_num = line_m.group(2) if (line_m and len(line_m.groups()) >= 2) else (line_m.group(1) if line_m else "?")
            
            if m:
                latches.append({
                    "module": m.group(1),
                    "signal": m.group(2),
                    "line": line_num,
                    "raw": line.strip()
                })
            else:
                latches.append({
                    "module": "-",
                    "signal": line.strip(),
                    "line": line_num,
                    "raw": line.strip()
                })
        elif "latch infer" in line_lower:
            # GHDL format: e.g. "file.vhd:9:9:error: latch infered for net \"q\""
            m = re.search(ghdl_pattern, line, re.IGNORECASE)
            line_m = re.search(r":([0-9]+):[0-9]+:", line)
            line_num = line_m.group(1) if line_m else "?"
            sig = m.group(1) if m else line.strip()
            latches.append({
                "module": "VHDL",
                "signal": sig,
                "line": line_num,
                "raw": line.strip()
            })
    return latches
