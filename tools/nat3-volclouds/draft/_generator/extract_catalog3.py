"""Pass 3 copy of extract_catalog.py. Extracts the scene catalog rows of the features pass 3 writes
(PhysicalSky, ExponentialHeightFog, ImageBasedLighting, GroundFog) and the scene policy lists.

    python -I extract_catalog3.py [path-to-SceneSettingsCatalog.generated.cpp]

Reads the fork read-only, writes scene-catalog-pass3.json beside this file.
Default source: the newest of build/*/generated/SceneSettingsCatalog.generated.cpp in the fork.
"""
import glob
import json
import os
import re
import sys

FORK = r'C:\Users\foxnn\dev\skyrim-community-shaders'
HERE = os.path.dirname(os.path.abspath(__file__))
FEATURES = ('PhysicalSky', 'ExponentialHeightFog', 'ImageBasedLighting', 'GroundFog')

STR = r'"((?:[^"\\]|\\.)*)"'
HEAD = re.compile(r'^\s*\{\s*' + STR + r',\s*' + STR + r',\s*' + STR + r',\s*' + STR + r',')
TAIL = re.compile(r'ValueType::(\w+),\s*(.*?),\s*SceneSettingsCatalog::EditorSemantic::(\w+),\s*' + STR +
                  r',\s*([-\d.eE+]+),\s*([-\d.eE+]+),\s*([-\d.eE+]+),\s*SceneSettingsCatalog::NumericTransform::\w+,\s*(true|false),\s*(true|false)')
POLICY_LISTS = ('kSettingBlacklist', 'kLocationFeatureWhitelist', 'kTimeOfDayFeatureWhitelist')


def read_policy():
    """Blacklist and the feature whitelists of SceneSettingsPolicy.h. Weather scenes use the time-of-day whitelist
    (SceneSettingsContextRules.cpp: SceneContextType::Weather -> SceneType::TimeOfDay)."""
    path = os.path.join(FORK, 'src', 'CSEditor', 'SceneManager', 'SceneSettingsPolicy.h')
    with open(path, encoding='utf-8') as f:
        text = f.read()
    policy = {}
    for name in POLICY_LISTS:
        body = re.search(name + r'\s*=\s*\{(.*?)\n\t\};', text, re.S).group(1)
        body = re.sub(r'//[^\n]*', '', body)
        policy[name] = [re.findall(r'"([^"]*)"', m) for m in re.findall(r'\{([^{}]*)\}', body)]
    return path, policy


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
    policy_path, policy = read_policy()
    out = {'source': src, 'sourceModified': os.path.getmtime(src), 'policySource': policy_path, 'policy': policy, 'rows': rows}
    path = os.path.join(HERE, 'scene-catalog-pass3.json')
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(out, f, indent=0)
    print(len(rows), 'rows from', src, '->', path)
    print('policy:', ', '.join('%s %d' % (k, len(v)) for k, v in policy.items()))


if __name__ == '__main__':
    main()
