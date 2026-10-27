"""Live local-only creative batch check; fictional story, no browser data changes."""
import json
from pathlib import Path
import requests
common=dict(count=5,catId='tabby',catName='灰太狼',participantNames=['虎皮','灰太狼'],
 participantDetails=['虎皮：姐姐，粘人爱撒娇，爱讨饭。','灰太狼：妹妹，呆萌，嗓门大，不喜欢拥抱。'],
 memoryTitle='第一次和平共处',memoryNote='两只猫第一次和平坐在一起等待小鱼干。',
 memoryTags=['一起','小鱼干','第一次'],context='food',language='zh',ownerStyle='everyday',
 ownerDescription='A grad student who studies late. Do not use this as a current activity.')
results=[]
for name,extra in [('goofy-sister',dict(personality='goofy',catDescription='妹妹，呆萌，不喜欢被抱。')),
 ('clingy-sister',dict(catId='orange',catName='虎皮',personality='clingy',catDescription='姐姐，粘人，爱撒娇，每天讨饭。')),
 ('academic-metaphor',dict(personality='bossy',ownerStyle='academic',catDescription='呆萌，嗓门大。')),
 ('window-en',dict(catId='orange',catName='Miso',participantNames=['Miso'],participantDetails=[],personality='polite',
   language='en',context='other',memoryTitle='Window watch',memoryNote='I watched two birds through a closed window.',memoryTags=['Birds']))]:
 r=requests.post('http://127.0.0.1:8765/api/captions',json={**common,**extra},timeout=190)
 row={'case':name,'status':r.status_code,'result':r.json()};results.append(row)
 print(json.dumps(row,ensure_ascii=False),flush=True)
 assert r.ok
 result=r.json();assert len(result['options'])==5 and len(set(o['text'] for o in result['options']))==5
 assert result['localOnly'] and result['context']==extra.get('context',common['context'])
Path(__file__).with_name('artifacts').joinpath('caption-choices-v3-checks.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
