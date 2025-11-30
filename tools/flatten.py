#!/usr/bin/env python3
import re
import sys
import os

# Check command line
if len(sys.argv) < 2:
    print("Usage: python3 flatten_html.py <input_html_file> [configure_js_file]")
    sys.exit(1)

html_file = sys.argv[1]

# Optional override for configure.js
js_file = sys.argv[2] if len(sys.argv) > 2 else "configure.js"

# Determine output filename
base, ext = os.path.splitext(html_file)
output_file = f"{base}_flattened{ext}"

# Read configure.js
with open(js_file, "r", encoding="utf-8") as f:
    js_text = f.read()

# Extract all constants from configure.js
secrets = dict(re.findall(r'const (\w+) = ["\'](.*?)["\'];', js_text))

# Read HTML
with open(html_file, "r", encoding="utf-8") as f:
    html_text = f.read()

# Pattern to match <script> blocks
script_pattern = re.compile(r'(<script[^>]*>)(.*?)(</script>)', re.DOTALL)

# Keep track of which constants we have already replaced
processed_consts = {}

def replace_consts_in_script(script_content, script_index):
    """
    Replace any const that exists in configure.js within this script block.
    Warn if a duplicate const is found.
    Adds a comment marker to indicate the block has been flattened.
    """
    lines = script_content.splitlines()
    new_lines = []
    replaced_any = False

    for line_num, line in enumerate(lines, 1):
        replaced_line = line
        stripped = line.strip()
        for name, value in secrets.items():
            # Only replace if line defines a const
            pattern = rf'const {name}\s*=\s*.*?;'
            if re.fullmatch(pattern, stripped):
                replaced_line = f'const {name} = "{value}"; // from configure.js'
                replaced_any = True

                if name in processed_consts:
                    prev_block, prev_line = processed_consts[name]
                    print(f"⚠️ WARNING: Duplicate const '{name}' found in script block {script_index} line {line_num} "
                          f"(previously replaced in script block {prev_block} line {prev_line})")
                # Record the latest replacement
                processed_consts[name] = (script_index, line_num)

        new_lines.append(replaced_line)

    # If we replaced any consts, prepend a comment marker
    if replaced_any:
        new_lines.insert(0, f"<!-- Flattened constants from {js_file} in script block {script_index} -->")

    return "\n".join(new_lines)

# Process all script blocks
def process_all_scripts(html):
    def repl(match):
        start, content, end = match.groups()
        script_index = repl.script_counter
        repl.script_counter += 1
        new_content = replace_consts_in_script(content, script_index)
        return start + new_content + end
    repl.script_counter = 1
    return script_pattern.sub(repl, html)

# Apply processing
html_text = process_all_scripts(html_text)

# Write output
with open(output_file, "w", encoding="utf-8") as f:
    f.write(html_text)

print(f"✅ Updated HTML written to: {output_file}")

# Warn about any constants in configure.js not found in the HTML
missing_consts = set(secrets.keys()) - set(processed_consts.keys())
for name in missing_consts:
    print(f"⚠️ WARNING: Constant '{name}' from {js_file} was NOT found in any <script> block of HTML.")
