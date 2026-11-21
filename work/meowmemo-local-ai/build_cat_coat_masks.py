"""Rebuild three coat-only alpha masks from supplied neutral artwork (Pillow)."""
from pathlib import Path
from PIL import Image
p=Path(__file__).resolve().parents[2]/'outputs/meowmemo-prototype'
# Coat-only masks: exclude ink, pink ears/nose/cheeks, toy, and transparent background.
maskdir=p/'assets/home-v3/coats';maskdir.mkdir(exist_ok=True)
for pose in ['sitting','sleeping','playing']:
 im=Image.open(p/f'assets/home-v3/cats/cream_{pose}.png').convert('RGBA');out=Image.new('RGBA',im.size)
 pixels=[]
 for r,g,b,a in im.getdata():
  # Soft boundary preserves the original antialiased ink and warm shading.
  strength=max(0,min(1,(min(r,g,b)-175)/35))*max(0,min(1,(g-b-0)/8))*max(0,min(1,(38-(r-g))/12))
  pixels.append((255,255,255,round(a*strength)))
 out.putdata(pixels);out.save(maskdir/f'{pose}.png')
