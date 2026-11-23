"""Route B helper (pass 4): builds a MERGED COPY of the live SceneManager.json with the pass-4 weather entries added.

    python -I merge_user_layer4.py

Reads (read-only): the live SceneSettings/SceneManager.json and ../alt-user-overrides-pass4/SceneManager.weather.pass4.json
Writes:            ../alt-user-overrides-pass4/SceneManager.merged.json   (nothing under C:/Modlists is touched)

The merged file is a snapshot of the live file at the moment this runs: re-run it right before installing, with the
game closed, and copy it over the live file by hand (after a backup). Existing entries are kept; an entry with the same
feature / path / setting / period as a pass-4 entry is replaced by the pass-4 one.
"""
import json
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DRAFT = os.path.dirname(HERE)
LIVE = 'C:/Modlists/NGVO 8.0 Beta/mods/CS Settings/SKSE/Plugins/CommunityShaders/SceneSettings/SceneManager.json'
OUT_DIR = os.path.join(DRAFT, 'alt-user-overrides-pass4')


def key(e):
    return (e.get('feature'), tuple(e.get('path', [])), e.get('setting'), e.get('period'))


def main():
    with open(LIVE, encoding='utf-8') as f:
        live = json.load(f)
    with open(os.path.join(OUT_DIR, 'SceneManager.weather.pass4.json'), encoding='utf-8') as f:
        add = json.load(f)
    weather = live.setdefault('weather', {})
    created = replaced = added = 0
    for formkey, block in add.items():
        if formkey not in weather:
            weather[formkey] = {'entries': []}
            created += 1
        new_keys = {key(e) for e in block['entries']}
        kept = [e for e in weather[formkey].get('entries', []) if key(e) not in new_keys]
        replaced += len(weather[formkey].get('entries', [])) - len(kept)
        weather[formkey]['entries'] = kept + block['entries']
        added += len(block['entries'])
    out = os.path.join(OUT_DIR, 'SceneManager.merged.json')
    with open(out, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(live, f, separators=(',', ':'))
    print('weathers in pass 4:', len(add), '| new weather keys:', created, '| entries added:', added, '| existing entries replaced:', replaced)
    print('written:', out, '(%d bytes; live file is %d bytes, modified %s)' % (
        os.path.getsize(out), os.path.getsize(LIVE), time.strftime('%Y-%m-%d %H:%M', time.localtime(os.path.getmtime(LIVE)))))


if __name__ == '__main__':
    main()
