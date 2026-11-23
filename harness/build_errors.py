"""Distinct compiler errors from an MSBuild log. usage: python build_errors.py LOG [max]"""
import collections, re, sys
t = open(sys.argv[1], encoding='ascii', errors='replace').read().replace('\r', '')
t = re.sub(r'\n\s+(?=\S)', ' ', t)          # MSBuild wraps long lines with an indent
errs = collections.OrderedDict()
for m in re.finditer(r'([\w.-]+[.](?:cpp|h|hlsl|hlsli))[(](\d+)[^)]*[)]\s*:\s*(?:fatal )?error (\w+):\s*([^\[\n]*)', t):
    errs.setdefault((m.group(1), m.group(2), m.group(3)), m.group(4).strip()[:190])
lnk = sorted(set(re.findall(r'error (LNK\d+):\s*([^\[\n]{0,200})', t)))
print(len(errs), 'compile errors,', len(lnk), 'link errors')
for (f, l, c), msg in list(errs.items())[:int(sys.argv[2]) if len(sys.argv) > 2 else 50]: print('%s:%s %s %s' % (f, l, c, msg))
for c, msg in lnk[:20]: print(c, msg)
