"""Read empty_legs.json and re-embed the flights array into index.html."""
import json, re, sys

with open("empty_legs.json") as f:
    data = json.load(f)

flights = data["flights"]
scraped_at = data.get("scraped_at", "")

with open("index.html") as f:
    html = f.read()

html, n = re.subn(
    r"const FLIGHTS = \[.*?\];",
    "const FLIGHTS = " + json.dumps(flights, separators=(",", ":")) + ";",
    html,
    flags=re.DOTALL,
)

if n != 1:
    print("ERROR: could not find FLIGHTS constant in index.html", file=sys.stderr)
    sys.exit(1)

if scraped_at:
    html, m = re.subn(
        r'const SCRAPED_AT = "[^"]*";',
        f'const SCRAPED_AT = "{scraped_at}";',
        html,
    )
    if m == 0:
        print(f"WARNING: SCRAPED_AT constant not found in index.html; skipping", file=sys.stderr)

with open("index.html", "w") as f:
    f.write(html)

print(f"Injected {len(flights)} flights into index.html (scraped_at={scraped_at})")
