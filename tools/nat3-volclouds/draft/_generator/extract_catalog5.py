r"""Pass 5 catalogue extractor: ONE source, the main checkout as it is now (read-only; nothing is written into it).

The checkout's own generator is first run into a scratch directory:

    python -I -B <checkout>\cmake\generate_scene_settings_catalog.py --source-dir <checkout> --out-dir <scratch>\cat-main
    python -I extract_catalog5.py <scratch>\cat-main

Source: C:\Users\foxnn\dev\skyrim-community-shaders (branch foxnne/llf-shadowless-spots at the time of pass 5).
Policy = blacklist + whitelists of src\CSEditor\SceneManager\SceneSettingsPolicy.h of that checkout; every policy entry also
gets its line number ("policyLines") so the notes can cite the exact blocking line.
Writes scene-catalog-pass5.json beside this file (same shape as scene-catalog-pass4.json, read by build_pass3.Validator).
"""
import collections
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import extract_catalog4 as x4  # noqa: E402  (regexes, read_rows, read_policy, head)

SRC = r'C:\Users\foxnn\dev\skyrim-community-shaders'
POLICY_FILE = os.path.join('src', 'CSEditor', 'SceneManager', 'SceneSettingsPolicy.h')
# features pass 5 writes or had to check for drivability (pass 4's list + PostProcessing for the exposure question)
x4.FEATURES = x4.FEATURES + ('PostProcessing',)


def policy_lines():
    """{list name: {'/'.join(entry): line number}} from SceneSettingsPolicy.h."""
    out, current = collections.OrderedDict(), None
    with open(os.path.join(SRC, POLICY_FILE), encoding='utf-8') as f:
        for no, line in enumerate(f, 1):
            m = re.search(r'(kSettingBlacklist|kLocationFeatureWhitelist|kTimeOfDayFeatureWhitelist)\s*=\s*\{', line)
            if m:
                current = out.setdefault(m.group(1), collections.OrderedDict())
                continue
            if current is None:
                continue
            code = line.split('//')[0]
            if code.strip() == '};':
                current = None
                continue
            names = re.findall(r'"([^"]*)"', code)
            if names:
                current['/'.join(names)] = no
    return out


def main():
    rows = x4.read_rows(sys.argv[1])
    policy = x4.read_policy(SRC)
    out = {'source': 'offline generator run of the main checkout %s (%s)' % (SRC, x4.head(SRC)),
           'heads': {'main': x4.head(SRC)}, 'policy': policy, 'policyFile': POLICY_FILE.replace(os.sep, '/'),
           'policyLines': policy_lines(), 'rows': rows}
    with open(os.path.join(HERE, 'scene-catalog-pass5.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(out, f, indent=0)
    print(len(rows), 'rows:', dict(collections.Counter(r['feature'] for r in rows)))
    print('policy:', ', '.join('%s %d' % (k, len(v)) for k, v in policy.items()))
    print('source:', out['source'])


if __name__ == '__main__':
    main()
