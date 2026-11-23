"""Queue job: replace Better Facial Animations 6.1.2 with 7.0.0, same installer choices (game and MO2 closed)."""
import os, re, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench
if bench.running() or bench.mo2_running(): sys.exit('game or Mod Organizer open')
src = sys.argv[2]; dst = 'C:/Modlists/NGVO 8.0 Beta/mods/Better Facial Animations'; bak = 'C:/Modlists/backups/better-facial-animations-6.1.2-' + time.strftime('%Y%m%d')
keep_ini = open(dst + '/SKSE/Plugins/BetterFacialAnimations.ini', 'rb').read()
if not os.path.isdir(bak): shutil.move(dst + '/SKSE', bak + '/SKSE')
else: shutil.rmtree(dst + '/SKSE')
shutil.copytree(src + '/SKSE', dst + '/SKSE')
inst = dst + '/SKSE/Plugins/BetterFacialAnimations/Installer'; os.makedirs(inst, exist_ok=True)
choice = {'GraphicsRoute': 'independent', 'Startup': 'gpu0', 'EmotionDevice': 'gpu0', 'FaceModel': 'quality', 'EmotionModel': 'performance', 'VanillaEmotions': 'on',
          'ActiveOnly': 'off', 'PlayerAnimation': 'on', 'PrepareEarly': 'on', 'Tongue': 'on', 'Gaze': 'on', 'Logging': 'on', 'FaceGraphFusion': 'off',
          'EmotionGraphFusion': 'off', 'Khajiit': 'on', 'Argonian': 'on'}
for k, v in choice.items(): shutil.copy2(f'{src}/options/{k}-{v}.ini', f'{inst}/{k}.ini')
open(dst + '/SKSE/Plugins/BetterFacialAnimations.ini', 'wb').write(keep_ini)
m = dst + '/meta.ini'; t = open(m, encoding='utf-8', errors='replace').read()
t = re.sub(r'(?m)^version=.*$', 'version=7.0.0.0', t); t = re.sub(r'(?m)^installationFile=.*$', 'installationFile=Better Facial Animations 7.0.0 193598 7.0.0 2026-11-16T23-09Z izKcFkz0K.7z', t)
open(m, 'w', encoding='utf-8').write(t); print('installed 7.0.0; backup', bak, sorted(os.listdir(inst)))
