"""Rebuild portable HTML; original media and bundled illustration bytes stay intact."""
from pathlib import Path
import base64
import json
import mimetypes
import re

root = Path(__file__).resolve().parent
assets = {}
for path in sorted((root / 'assets').rglob('*')):
    if path.is_file() and path.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp', '.ttf'}:
        assets[path.relative_to(root).as_posix()] = 'data:' + mimetypes.guess_type(path.name)[0] + ';base64,' + base64.b64encode(path.read_bytes()).decode('ascii')
names = ['demo-data.js', 'scene.js', 'captions.js', 'shop.js', 'rooms.js', 'home-v3.js', 'app.js']
script = '\n'.join((root / name).read_text() for name in names)
for key in assets:
    # JS values, then image paths within template literals; keep each image once.
    script = script.replace("'" + key + "'", 'ASSETS[' + json.dumps(key) + ']')
    script = script.replace('src="' + key + '"', 'src="${ASSETS[' + json.dumps(key) + ']}"')
script = 'const ASSETS = ' + json.dumps(assets) + ';\n' + script
css = (root / 'styles.css').read_text()
for key, value in assets.items():
    css = css.replace(key, value)
html = re.sub(r'<link rel="stylesheet" href="styles\.css(?:\?[^"]*)?">', lambda _: '<style>\n' + css + '\n</style>', (root / 'index.html').read_text())
tags = '\n'.join(re.search(r'  <script src="' + re.escape(name) + r'(?:\?[^"\n]*)?" defer></script>', html).group(0) for name in names)
assert tags in html, 'Source script list changed; update standalone builder.'
html = html.replace(tags, '  <script>\n' + script + '\n</script>')
destination = root / 'meowmemo.html'
destination.write_text(html)
print(f'Saved {destination} ({destination.stat().st_size / 1024 / 1024:.1f} MB)')
