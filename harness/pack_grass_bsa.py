"""Pack the active loose grass cache (grass/*.cgid) into one uncompressed SSE BSA with libbsarch (MO2's copy).
usage: python pack_grass_bsa.py   -> mods/foxnne - Grass Cache BSA/foxnne - Grass Cache.bsa"""
import ctypes as C, os, sys, time
I = 'C:/Modlists/NGVO 8.0 Beta'
mods = [l.strip()[1:] for l in open(I + '/profiles/foxnne-nsfw/modlist.txt', encoding='utf-8-sig') if l.startswith('+foxnne - Grass Cache 20')]
SRC = os.path.join(I, 'mods', mods[0], 'Grass'); OUT = os.path.join(I, 'mods', 'foxnne - Grass Cache BSA', 'foxnne - Grass Cache.bsa')
BS = chr(92); GR = 'grass' + BS
L = C.WinDLL(I + '/dlls/libbsarch.dll')


class R(C.Structure):
    _fields_ = [('code', C.c_int8), ('text', C.c_wchar * 1024)]


def ck(r, what):
    if r.code != 0: sys.exit('%s failed: %s' % (what, r.text))


L.bsa_create.restype = C.c_void_p; L.bsa_entry_list_create.restype = C.c_void_p
for n, a in (('bsa_entry_list_add', [C.c_void_p, C.c_wchar_p]), ('bsa_create_archive', [C.c_void_p, C.c_wchar_p, C.c_int, C.c_void_p]),
             ('bsa_add_file_from_disk', [C.c_void_p, C.c_wchar_p, C.c_wchar_p]), ('bsa_save', [C.c_void_p]), ('bsa_free', [C.c_void_p]), ('bsa_entry_list_free', [C.c_void_p])):
    f = getattr(L, n); f.argtypes = a; f.restype = R
L.bsa_compress_set.argtypes = [C.c_void_p, C.c_bool]; L.bsa_share_data_set.argtypes = [C.c_void_p, C.c_bool]
files = sorted(f for f in os.listdir(SRC) if f.lower().endswith('.cgid')); print('source', mods[0], len(files), 'files', flush=True)
b = L.bsa_create(); el = L.bsa_entry_list_create()
for f in files: ck(L.bsa_entry_list_add(el, GR + f), 'list add')
L.bsa_compress_set(b, False); L.bsa_share_data_set(b, False)
if os.path.exists(OUT): os.remove(OUT)
ck(L.bsa_create_archive(b, OUT.replace('/', BS), 4, el), 'create')      # 4 = baSSE
t = time.time()
for i, f in enumerate(files): ck(L.bsa_add_file_from_disk(b, GR + f, os.path.join(SRC, f).replace('/', BS)), 'add ' + f)
ck(L.bsa_save(b), 'save'); L.bsa_free(b); L.bsa_entry_list_free(el)
print('wrote %s, %.0f MB in %.0f s (loose total %.0f MB)' % (OUT, os.path.getsize(OUT) / 1e6, time.time() - t, sum(os.path.getsize(os.path.join(SRC, f)) for f in files) / 1e6))
