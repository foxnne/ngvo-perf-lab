"""Route B helper (pass 5): builds a MERGED COPY of the live SceneManager.json with the pass-5 weather entries added.

    python -I merge_user_layer5.py

Reads (read-only): the live SceneSettings/SceneManager.json and ../alt-user-overrides-pass5/SceneManager.weather.pass5.json
Writes:            ../alt-user-overrides-pass5/SceneManager.merged.json   (nothing under C:/Modlists is touched)

Same rules as merge_user_layer4.py: a snapshot of the live file at the moment this runs; existing entries are kept; an entry
with the same feature / path / setting / period as a pass-5 entry is replaced by the pass-5 one. NOT RUN by the generator.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # -I drops the script directory
import merge_user_layer4 as m4  # noqa: E402


def main():
    import json
    import time
    out_dir = os.path.join(m4.DRAFT, 'alt-user-overrides-pass5')
    with open(m4.LIVE, encoding='utf-8') as f:
        live = json.load(f)
    with open(os.path.join(out_dir, 'SceneManager.weather.pass5.json'), encoding='utf-8') as f:
        add = json.load(f)
    weather = live.setdefault('weather', {})
    created = replaced = added = 0
    for formkey, block in add.items():
        if formkey not in weather:
            weather[formkey] = {'entries': []}
            created += 1
        new_keys = {m4.key(e) for e in block['entries']}
        kept = [e for e in weather[formkey].get('entries', []) if m4.key(e) not in new_keys]
        replaced += len(weather[formkey].get('entries', [])) - len(kept)
        weather[formkey]['entries'] = kept + block['entries']
        added += len(block['entries'])
    out = os.path.join(out_dir, 'SceneManager.merged.json')
    with open(out, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(live, f, separators=(',', ':'))
    print('weathers in pass 5:', len(add), '| new weather keys:', created, '| entries added:', added, '| existing entries replaced:', replaced)
    print('written:', out, '(%d bytes; live file is %d bytes, modified %s)' % (
        os.path.getsize(out), os.path.getsize(m4.LIVE), time.strftime('%Y-%m-%d %H:%M', time.localtime(os.path.getmtime(m4.LIVE)))))


if __name__ == '__main__':
    main()
