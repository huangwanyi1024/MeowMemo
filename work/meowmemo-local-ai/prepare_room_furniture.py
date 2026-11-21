"""Prepare existing Peach Milk furniture; trim disconnected sheet fragments without changing original packs."""
from pathlib import Path
from PIL import Image,ImageFilter
p=Path(__file__).resolve().parents[2]/'outputs/meowmemo-prototype';out=p/'assets/alternate-room';out.mkdir(exist_ok=True)
names={'sofa':'sofa','desk':'desk','tree':'cat_tree','tv':'tv_stand','table':'coffee_table','window':'window','rug':'rug','plant':'plant','wall_shelf':'bookshelf'}
metrics={}
for kind,name in names.items():
 im=Image.open(p.parents[1]/'MeowMemo_Peach_Milk_Assets/furniture'/f'{name}.png').convert('RGBA');a=im.getchannel('A');w,h=im.size;pix=a.load();seen=set();components=[]
 for y in range(h):
  for x in range(w):
   if pix[x,y]<32 or (x,y)in seen:continue
   q=[(x,y)];seen.add((x,y));part=[]
   while q:
    xx,yy=q.pop();part.append((xx,yy))
    for nx,ny in [(xx-1,yy),(xx+1,yy),(xx,yy-1),(xx,yy+1)]:
     if 0<=nx<w and 0<=ny<h and pix[nx,ny]>=32 and (nx,ny)not in seen:seen.add((nx,ny));q.append((nx,ny))
   components.append(part)
 mask=Image.new('L',im.size);mp=mask.load()
 for xy in max(components,key=len):mp[xy]=255
 mask=mask.filter(ImageFilter.MaxFilter(3));im.putalpha(Image.eval(a,lambda v:v));im.putalpha(Image.composite(a,Image.new('L',im.size),mask));im=im.crop(im.getbbox());pad=Image.new('RGBA',(im.width+4,im.height+4));pad.paste(im,(2,2));pad.save(out/f'{kind}.png');metrics[kind]=pad.size
