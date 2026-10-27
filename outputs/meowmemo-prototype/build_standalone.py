"""Rebuild the portable, single-file HTML with unchanged original photographs."""
from pathlib import Path
import base64
import json

root = Path(__file__).resolve().parent
assets = {}
for path in sorted((root / "assets").glob("*.jpg")):
    assets["assets/" + path.name] = "data:image/jpeg;base64," + base64.b64encode(path.read_bytes()).decode("ascii")
script = (root / "demo-data.js").read_text() + "\n" + (root / "scene.js").read_text() + "\n" + (root / "captions.js").read_text() + "\n" + (root / "shop.js").read_text() + "\n" + (root / "rooms.js").read_text() + "\n" + (root / "app.js").read_text()
for key in assets:
    script = script.replace("'" + key + "'", "ASSETS[" + json.dumps(key) + "]")
script = "const ASSETS = " + json.dumps(assets) + ";\n" + script
html = (root / "index.html").read_text()
html = html.replace('<link rel="stylesheet" href="styles.css">', "<style>\n" + (root / "styles.css").read_text() + "\n</style>")
html = html.replace('  <script src="demo-data.js" defer></script>\n  <script src="scene.js" defer></script>\n  <script src="captions.js" defer></script>\n  <script src="shop.js" defer></script>\n  <script src="rooms.js" defer></script>\n  <script src="app.js" defer></script>', "  <script>\n" + script + "\n</script>")
destination = root / "meowmemo.html"
destination.write_text(html)
print(f"Saved {destination} ({destination.stat().st_size / 1024 / 1024:.1f} MB)")
