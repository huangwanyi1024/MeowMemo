"""Recover 18 supplied sitting sprites from their intact reference sheet (Pillow only).

Rebuilds runtime copies only; original packs remain untouched.
"""
from PIL import Image,ImageFilter,ImageDraw
from pathlib import Path
root=Path(__file__).resolve().parents[2]
sheet=Image.open(root/'MeowMemo_Fur_Pattern_Assets/reference_sheet.png').convert('RGB')
out=root/'outputs/meowmemo-prototype/assets/home-v3/appearance';out.mkdir(exist_ok=True)
for row,color in enumerate(['orange','gray','cream']):
 for col,(pattern,fur) in enumerate([(p,f)for p in ['stripes','patches','solid']for f in ['short','long']]):
  cx=[285,500,740,950,1190,1400][col];cy=[232,450,670][row]
  im=sheet.crop((cx-112,cy-105,cx+113,cy+110));lum=im.convert('L');blur=lum.filter(ImageFilter.GaussianBlur(8))
  edge=Image.new('L',im.size);edge.putdata([255 if v<b-15 else 0 for v,b in zip(lum.getdata(),blur.getdata())]);edge=edge.filter(ImageFilter.MaxFilter(3))
  # Flood outside only; closed ink contours protect the full coat and tail.
  mask=edge.copy();ImageDraw.floodfill(mask,(0,0),128,thresh=0)
  mask=mask.point(lambda v:0 if v==128 else 255)
  # Keep only the cat component and drop unrelated contour fragments.
  w,h=mask.size;px=mask.load();seen=set();parts=[]
  for y in range(h):
   for x in range(w):
    if not px[x,y] or (x,y)in seen:continue
    q=[(x,y)];seen.add((x,y));part=[]
    while q:
     a,b=q.pop();part.append((a,b))
     for xx,yy in [(a-1,b),(a+1,b),(a,b-1),(a,b+1)]:
      if 0<=xx<w and 0<=yy<h and px[xx,yy] and (xx,yy)not in seen:seen.add((xx,yy));q.append((xx,yy))
    parts.append(part)
  largest=max(parts,key=len);mask=Image.new('L',im.size);mp=mask.load()
  for xy in largest:mp[xy]=255
  mask=mask.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(.45));im.putalpha(mask)
  box=mask.point(lambda v:255 if v>32 else 0).getbbox();assert box and box[0]>0 and box[1]>0 and box[2]<w and box[3]<h, 'Review crop bounds'
  im=im.crop(box);padded=Image.new('RGBA',(im.width+4,im.height+4));padded.paste(im,(2,2));padded.save(out/f'{color}_{pattern}_{fur}.png')
