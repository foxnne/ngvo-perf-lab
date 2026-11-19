"""Snapshot / describe the configuration state that affects rendering and performance.

usage: python state.py snapshot NAME     -> configs/NAME/ (copies of the small config files + manifest.json)
       python state.py manifest          -> prints the current manifest (hashes), for stamping benchmark results
"""
import hashlib, json, os, shutil, sys, time
ROOT = 'C:/Modlists/NGVO 8.0 Beta'
LAB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROFILE = ROOT + '/profiles/foxnne-nsfw'
CSDIR = ROOT + '/mods/CS Settings/SKSE/Plugins/CommunityShaders'
FILES = {
    'profile/modlist.txt': PROFILE + '/modlist.txt', 'profile/plugins.txt': PROFILE + '/plugins.txt', 'profile/loadorder.txt': PROFILE + '/loadorder.txt',
    'profile/skyrim.ini': PROFILE + '/skyrim.ini', 'profile/skyrimprefs.ini': PROFILE + '/skyrimprefs.ini', 'profile/skyrimcustom.ini': PROFILE + '/skyrimcustom.ini',
    'cs/SettingsUser.json': CSDIR + '/SettingsUser.json', 'cs/SceneManager.json': CSDIR + '/SceneSettings/SceneManager.json',
    'ini/SSEDisplayTweaks.ini': ROOT + '/mods/NGVO - MCM and INI Settings/SKSE/Plugins/SSEDisplayTweaks.ini',
    'ini/TextureDownscaler.ini': ROOT + '/mods/Texture Downscaler/SKSE/Plugins/TextureDownscaler.ini',
    'ini/SPS.ini': ROOT + '/mods/Skyrim Performance Solution (SPS) - AE SSE VR/SKSE/Plugins/SPS.ini',
    'ini/SkyrimPrecombines.ini': ROOT + '/mods/Faster Objects/SKSE/Plugins/SkyrimPrecombines.ini',
    'ini/FasterTextures.ini': ROOT + '/mods/Faster Textures/SKSE/Plugins/FasterTextures.ini',
    'ini/DynDOLOD_MCM_settings.ini': ROOT + '/mods/DynDOLOD - Settings Loader/MCM/Config/DynDOLOD/settings.ini',
}
BINARIES = {
    'CommunityShaders.dll': ROOT + '/mods/Bottled Shaders - foxnne/SKSE/Plugins/CommunityShaders.dll',
    'nvngx_dlss.dll': ROOT + '/mods/Bottled Shaders - foxnne/Shaders/Upscaling/Streamline/nvngx_dlss.dll',
    'nvngx_dlssnr.dll': ROOT + '/mods/Bottled Shaders - foxnne/Shaders/Upscaling/Streamline/nvngx_dlssnr.dll',
}


def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def manifest():
    m = {'time': time.strftime('%Y-%m-%d %H:%M:%S'), 'files': {}, 'binaries': {}}
    for k, p in {**FILES}.items():
        m['files'][k] = md5(p) if os.path.exists(p) else None
    for k, p in BINARIES.items():
        m['binaries'][k] = md5(p) if os.path.exists(p) else None
    ml = open(PROFILE + '/modlist.txt', 'rb').read().decode('utf-8', 'ignore').splitlines()
    m['mods_enabled'] = sum(1 for l in ml if l.startswith('+')); m['mods_total'] = sum(1 for l in ml if l[:1] in '+-')
    m['id'] = hashlib.md5(json.dumps([m['files'], m['binaries']], sort_keys=True).encode()).hexdigest()[:10]
    return m


if __name__ == '__main__':
    if sys.argv[1] == 'manifest':
        print(json.dumps(manifest(), indent=1))
    elif sys.argv[1] == 'snapshot':
        out = os.path.join(LAB, 'configs', sys.argv[2]); os.makedirs(out, exist_ok=True)
        for k, p in FILES.items():
            if os.path.exists(p):
                d = os.path.join(out, k); os.makedirs(os.path.dirname(d), exist_ok=True); shutil.copy2(p, d)
        json.dump(manifest(), open(os.path.join(out, 'manifest.json'), 'w'), indent=1)
        print('snapshot', out, manifest()['id'])
