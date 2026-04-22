"""Read empty_legs.json and re-embed the flights array into index.html."""
import json, re, sys

with open("empty_legs.json") as f:
    flights = json.load(f)["flights"]

with open("index.html") as f:
    html = f.read()

replacement = "const FLIGHTS = " + json.dumps(flights, separators=(",", ":")) + ";"

html, n = re.subn(r"const FLIGHTS = \[.*?\];", replacement, html, flags=re.DOTALL)

if n != 1:
    print("ERROR: could not find FLIGHTS constant in index.html", file=sys.stderr)
    sys.exit(1)

with open("index.html", "w") as f:
    f.write(html)

print(f"Injected {len(flights)} flights into index.html")
