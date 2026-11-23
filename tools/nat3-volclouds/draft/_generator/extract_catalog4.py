r"""Pass 4 catalogue extractor. Neither source worktree has a build tree, so the compiled scene catalogue is first
regenerated offline with each worktree's own generator into a scratch directory (nothing is written into a worktree):

    python <worktree>\cmake\generate_scene_settings_catalog.py --source-dir <worktree> --out-dir <scratch>\cat-<tag>
    python -I extract_catalog4.py <scratch>\cat-lightning <scratch>\cat-groundfog3

Sources (read-only):
    C:\Users\foxnn\dev\cs-wt-lightning   branch foxnne/lightning-fix   (heavy-sky + lightning)  -> every feature but GroundFog
    C:\Users\foxnn\dev\cs-wt-groundfog3  branch foxnne/ground-fog-near (Ground Fog phase 3)     -> GroundFog rows
Policy (blacklist + whitelists of SceneSettingsPolicy.h) = union of both worktrees (what the merged build will hold).
Writes scene-catalog-pass4.json beside this file. Rows of the other worktree are kept under "crossCheck".
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WT = {'lightning': r'C:\Users\foxnn\dev\cs-wt-lightning', 'groundfog3': r'C:\Users\foxnn\dev\cs-wt-groundfog3'}
# features pass 4 writes or had to check for drivability
FEATURES = ('PhysicalSky', 'ExponentialHeightFog', 'ImageBasedLighting', 'GroundFog', 'SkySync', 'Effects11',
            'VolumetricLighting', 'ViewAtmosphere', 'Skylighting')
PRIMARY = {'GroundFog': 'groundfog3'}   # every other feature: lightning

STR = r'"((?:[^"\\]|\\.)*)"'
HEAD = re.compile(r'^\s*\{\s*' + STR + r',\s*' + STR + r',\s*' + STR + r',\s*' + STR + r',')
TAIL = re.compile(r'ValueType::(\w+),\s*(.*?),\s*SceneSettingsCatalog::EditorSemantic::(\w+),\s*' + STR +
                  r',\s*([-\d.eE+]+),\s*([-\d.eE+]+),\s*([-\d.eE+]+),\s*SceneSettingsCatalog::NumericTransform::\w+,\s*(true|false),\s*(true|false)')
POLICY_LISTS = ('kSettingBlacklist', 'kLocationFeatureWhitelist', 'kTimeOfDayFeatureWhitelist')


def read_policy(root):
    path = os.path.join(root, 'src', 'CSEditor', 'SceneManager', 'SceneSettingsPolicy.h')
    with open(path, encoding='utf-8') as f:
        text = f.read()
    policy = {}
    for name in POLICY_LISTS:
        body = re.search(name + r'\s*=\s*\{(.*?)\n\t\};', text, re.S).group(1)
        body = re.sub(r'//[^\n]*', '', body)
        policy[name] = [re.findall(r'"([^"]*)"', m) for m in re.findall(r'\{([^{}]*)\}', body)]
    return policy


def read_rows(cat_dir):
    rows = []
    with open(os.path.join(cat_dir, 'SceneSettingsCatalog.generated.cpp'), encoding='utf-8') as f:
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
    return rows


def head(root):
    return subprocess.run(['git', '-C', root, 'log', '-1', '--format=%h %D %s'], capture_output=True, text=True).stdout.strip()


def main():
    dirs = {'lightning': sys.argv[1], 'groundfog3': sys.argv[2]}
    allrows = {tag: read_rows(d) for tag, d in dirs.items()}
    policies = {tag: read_policy(WT[tag]) for tag in WT}
    policy = {}
    for name in POLICY_LISTS:
        merged = []
        for tag in ('lightning', 'groundfog3'):
            for p in policies[tag][name]:
                if p not in merged:
                    merged.append(p)
        policy[name] = merged
    rows = [r for tag in allrows for r in allrows[tag] if PRIMARY.get(r['feature'], 'lightning') == tag]
    # cross-check: rows of the features both trees hold
    key = lambda r: (r['feature'], r['path'], r['key'])
    a = {key(r): r for r in allrows['lightning']}
    b = {key(r): r for r in allrows['groundfog3']}
    cross = {'onlyInLightning': sorted('/'.join(filter(None, k)) for k in a if k not in b),
             'onlyInGroundfog3': sorted('/'.join(filter(None, k)) for k in b if k not in a),
             'different': sorted('/'.join(filter(None, k)) + ': ' + json.dumps({x: (a[k][x], b[k][x]) for x in a[k] if a[k][x] != b[k][x]})
                                 for k in a if k in b and a[k] != b[k]),
             'policyOnlyInLightning': {n: [p for p in policies['lightning'][n] if p not in policies['groundfog3'][n]] for n in POLICY_LISTS},
             'policyOnlyInGroundfog3': {n: [p for p in policies['groundfog3'][n] if p not in policies['lightning'][n]] for n in POLICY_LISTS}}
    out = {'source': 'offline generator run of cs-wt-lightning (%s) + GroundFog rows of cs-wt-groundfog3 (%s)' % (head(WT['lightning']), head(WT['groundfog3'])),
           'heads': {tag: head(WT[tag]) for tag in WT}, 'policy': policy, 'crossCheck': cross, 'rows': rows}
    path = os.path.join(HERE, 'scene-catalog-pass4.json')
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(out, f, indent=0)
    import collections
    print(len(rows), 'rows:', dict(collections.Counter(r['feature'] for r in rows)))
    print('policy:', ', '.join('%s %d' % (k, len(v)) for k, v in policy.items()))
    for k, v in cross.items():
        print(k, ':', v if not isinstance(v, list) or len(v) < 80 else len(v))


if __name__ == '__main__':
    main()
