"""Optional live local-Qwen regression check. Fictional profiles only; no paid calls."""
import json
import re
from pathlib import Path
import requests

base = 'http://127.0.0.1:8765'
common = dict(catId='tabby', catName='Nori', participantNames=['Miso', 'Nori'],
              context='unknown', contextSource='owner', personality='goofy', ownerStyle='everyday',
              ownerDescription='A graduate student who studies late.',
              previousText='Shh! Let me sneak some fish for the quiet study session.')
cases = [
    ('shared-fish-en', dict(language='en', memoryTitle='Two cuties sit together',
        memoryNote='For the first time, both cats sat peacefully together, waiting for dried fish treats.',
        memoryTags=['Together', 'FirstTime', 'FishTreats'])),
    ('shared-fish-zh', dict(language='zh', memoryTitle='第一次和平共处',
        memoryNote='这两只第一次和平坐在一起，等待小鱼干。', memoryTags=['一起', '第一次', '小鱼干'])),
    ('note-without-fish', dict(language='en', memoryTitle='Two cutties sit together',
        memoryNote='The first time they get along very well.', memoryTags=['Together'])),
    ('window-not-food', dict(language='en', catName='Miso', participantNames=['Miso'], context='other',
        memoryTitle='Window watch', memoryNote='She watched two birds through the closed window.', memoryTags=['Birds', 'Window'])),
    ('tags-only', dict(language='en', memoryTags=['Together', 'FirstTime', 'FishTreats'])),
]
results = []
for name, extra in cases:
    payload = {**common, **extra}
    response = requests.post(base+'/api/captions', json=payload, timeout=100)
    row = {'case': name, 'status': response.status_code}
    if response.ok:
        data = response.json(); text = data['text']; row['text'] = text
        assert data['context'] == payload['context']
        assert data['personalization']['memoryTags'] == payload['memoryTags']
        assert data['localOnly'] and data['source'] == 'ai-copy'
        assert 'caption-v2-story-first' in data['generatorVersion']
        assert not re.search(r'\b(study|homework|thesis|lecture|assignment)\b|学习|作业|论文', text, re.I)
        if name in ('note-without-fish', 'window-not-food'):
            assert not re.search(r'\b(fish|treat|bowl|snack)\b', text, re.I)
    else:
        row['code'] = response.json().get('code')
    print(json.dumps(row, ensure_ascii=False), flush=True)
    results.append(row)
Path(__file__).with_name('artifacts').joinpath('caption-grounding-v2-checks.json').write_text(
    json.dumps({'scope': 'Five fictional regression cases; not a formal accuracy evaluation. Early experiments still showed small-model factual drift.',
                'model': 'qwen3.5:4b', 'results': results}, ensure_ascii=False, indent=2))
assert all(row['status'] == 200 for row in results), 'Some cases were rejected or failed; inspect the recorded results.'
print('PASS: five live local cases, tags/cast payload and provenance, unknown preservation, no unrelated study topic.')
