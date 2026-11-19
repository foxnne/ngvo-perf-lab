"""Extracts the PhysicalSky and ExponentialHeightFog rows of the fork's compiled scene catalog.

    python -I extract_catalog.py [path-to-SceneSettingsCatalog.generated.cpp]

Reads the generated .cpp read-only, writes scene-catalog-pass2.json beside this file.
Default source: the newest of build/*/generated/SceneSettingsCatalog.generated.cpp in the fork.
"""
import glob
import json
import os
import re
import sys

FORK = r'C:\Users\foxnn\dev\skyrim-community-shaders'
HERE = os.path.dirname(os.path.abspath(__file__))
FEATURES = ('PhysicalSky', 'ExponentialHeightFog')

STR = r'"((?:[^"\\]|\\.)*)"'
HEAD = re.compile(r'^\s*\{\s*' + STR + r',\s*' + STR + r',\s*' + STR + r',\s*' + STR + r',')
TAIL = re.compile(r'ValueType::(\w+),\s*(.*?),\s*SceneSettingsCatalog::EditorSemantic::(\w+),\s*' + STR +
                  r',\s*([-\d.eE+]+),\s*([-\d.eE+]+),\s*([-\d.eE+]+),\s*SceneSettingsCatalog::NumericTransform::\w+,\s*(true|false),\s*(true|false)')


def main():
    if len(sys.argv) > 1:
        src = sys.argv[1]
    else:
        cands = glob.glob(os.path.join(FORK, 'build', '*', 'generated', 'SceneSettingsCatalog.generated.cpp'))
        src = max(cands, key=os.path.getmtime)
    rows = []
    with open(src, encoding='utf-8') as f:
        for line in f:
            h = HEAD.match(line)
            if not h or h.group(1) not in FEATURES:
                continue
            t = TAIL.search(line)
            if not t:
                continue
            flags = '|'.join(x[:5] for x in re.findall(r'SettingFlag::(\w+)', t.group(2)))
            rows.append({'feature': h.group(1), 'path': h.group(3), 'key': h.group(4), 'vtype': t.group(1), 'flags': flags,
                         'sem': t.group(3), 'widget': t.group(4), 'mn': t.group(5), 'mx': t.group(6),
                         'bounds': t.group(8), 'clamp': t.group(9)})
    out = {'source': src, 'sourceModified': os.path.getmtime(src), 'rows': rows}
    path = os.path.join(HERE, 'scene-catalog-pass2.json')
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(out, f, indent=0)
    print(len(rows), 'rows from', src, '->', path)


if __name__ == '__main__':
    main()
