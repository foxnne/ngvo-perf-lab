"""Put sky, shadow-light and exposure in the saved CS settings back to the baseline copy (the game re-saves live test values into
SettingsUser.json). Other keys are kept. fix() returns the list of keys it had to restore."""
import copy, json
D = 'C:/Modlists/NGVO 8.0 Beta/mods/CS Settings/SKSE/Plugins/CommunityShaders/'


def fix():
    A = json.load(open(D + 'SettingsUser.json')); B = json.load(open(D + 'SettingsUser.user-best-20261122.json')); C = copy.deepcopy(A)
    for k in ('Physical Sky', 'Image Based Lighting'):
        if k in B: C[k] = copy.deepcopy(B[k])
        else: C.pop(k, None)
    C['Post Processing']['Histogram Auto Exposure']['settings']['ExposureCompensation'] = B['Post Processing']['Histogram Auto Exposure']['settings']['ExposureCompensation']
    ch = [k for k in ('Physical Sky', 'Image Based Lighting', 'Post Processing') if A.get(k) != C.get(k)]
    if ch: json.dump(C, open(D + 'SettingsUser.json', 'w'), indent=1)
    return ch


if __name__ == '__main__': print('restored:', fix() or 'nothing')
