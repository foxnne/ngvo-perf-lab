"""Write the grass type table (markdown, csv, swatch sheet) from out/work/grass_types.json."""
import csv
import json
import os
from PIL import Image, ImageDraw
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
t = json.load(open(os.path.join(OUT, 'work', 'grass_types.json')))
rows = []
for k, v in t.items():
    if 'srgb' not in v:
        continue
    sh = v['shapes'][0]
    recs = v['records']
    per_inst = v['visible_area'] * v['mean_scale2']
    rows.append(dict(model=os.path.basename(k)[:-4], tamriel=v['tamriel'], all=v['instances'],
                     srgb=[int(round(x * 255)) for x in v['srgb']], linear=[round(x, 4) for x in v['linear']],
                     tex_linear=[round(x, 4) for x in v['linear_tex_only']], ao=round(v['ao'], 3),
                     blade_area=round(v['visible_area']), alpha_pass=round(v['visible_area'] / v['mesh_area'], 3),
                     height=round(v['bbox_hi'][2] - v['bbox_lo'][2]), width=round(max(v['bbox_hi'][0] - v['bbox_lo'][0], v['bbox_hi'][1] - v['bbox_lo'][1])),
                     weight=round(per_inst), total_area=per_inst * v['tamriel'],
                     vertex_colours=sh['vertex_colours'], vc_mean=sh['vc_mean_srgb'], complex=sh['complex'],
                     diffuse=sh['diffuse'], tex_size=sh['tex_size'], tex_source=sh['tex_source'], mesh_source=v['mesh_source'],
                     records=len(recs), edids=', '.join(sorted(set(r.get('edid') or '?' for r in recs)))[:120],
                     gras_flags=sorted(set(r.get('flags') for r in recs if r.get('flags') is not None)),
                     colour_range=sorted(set(round(r.get('colour_range'), 2) for r in recs if r.get('colour_range') is not None)),
                     density=sorted(set(r.get('density') for r in recs if r.get('density') is not None)),
                     colour_scale=round(v['mean_colour_scale'], 3), underwater=os.path.basename(k).startswith(('waterkelp', 'watercoral', 'rockgrasswater'))))
rows.sort(key=lambda r: -r['total_area'])
tot_area = sum(r['total_area'] for r in rows if not r['underwater'])
tot_inst = sum(r['tamriel'] for r in rows)
with open(os.path.join(OUT, 'grass_colour_table.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['model', 'tamriel_instances', 'instance_share', 'blade_area_share', 'srgb_r', 'srgb_g', 'srgb_b', 'lin_r', 'lin_g', 'lin_b',
                'vertex_ao', 'blade_area_units2', 'coverage_weight_per_instance', 'height', 'width', 'alpha_pass', 'vertex_colours', 'vertex_colour_mean_srgb',
                'complex_atlas', 'gras_records', 'gras_flags(1=vertex lighting,2=uniform scale,4=fit slope)', 'gras_colour_range', 'gras_density',
                'mean_instance_colour_scale', 'underwater_excluded', 'diffuse', 'tex_size', 'texture_source', 'mesh_source', 'editor_ids'])
    for r in rows:
        w.writerow([r['model'], r['tamriel'], '%.4f' % (r['tamriel'] / tot_inst), '%.4f' % (0 if r['underwater'] else r['total_area'] / tot_area), *r['srgb'], *r['linear'],
                    r['ao'], r['blade_area'], r['weight'], r['height'], r['width'], r['alpha_pass'], r['vertex_colours'], r['vc_mean'], r['complex'], r['records'],
                    r['gras_flags'], r['colour_range'], r['density'], r['colour_scale'], r['underwater'], r['diffuse'], r['tex_size'], r['tex_source'], r['mesh_source'], r['edids']])
with open(os.path.join(OUT, 'grass_colour_table.md'), 'w', encoding='utf-8') as f:
    f.write('# Grass type colours (Tamriel, %d instances in the cache, %d models)\n\n' % (tot_inst, len(rows)))
    f.write('Colour = diffuse texture x hue of the mesh vertex colour, alpha-tested, area-weighted over the mesh, averaged in linear light '
            '(what `RunGrass.hlsl` uses as albedo). `AO` = mean max-channel of the vertex colour (darkens ambient only, not in the colour). '
            '`weight` = alpha-passing blade area x mean scale^2 per instance (game units^2). `area share` = share of all land blade area in Tamriel. '
            'Sorted by area share. Underwater types are excluded from the map.\n\n')
    f.write('| model | instances | inst % | area % | sRGB | hex | linear | AO | weight | h x w | atlas | note |\n|---|---:|---:|---:|---|---|---|---:|---:|---|---|---|\n')
    for r in rows:
        f.write('| %s | %d | %.1f | %s | %d,%d,%d | #%02x%02x%02x | %.3f,%.3f,%.3f | %.2f | %d | %dx%d | %s | %s |\n' % (
            r['model'], r['tamriel'], 100 * r['tamriel'] / tot_inst, '-' if r['underwater'] else '%.1f' % (100 * r['total_area'] / tot_area), *r['srgb'], *r['srgb'], *r['linear'],
            r['ao'], r['weight'], r['height'], r['width'], 'complex' if r['complex'] else 'plain', 'underwater, excluded' if r['underwater'] else ''))
# swatches
top = rows[:48]
cw, chh = 330, 34
img = Image.new('RGB', (cw * 3, chh * 16 + 4), (24, 24, 24))
d = ImageDraw.Draw(img)
for i, r in enumerate(top):
    x, y = (i // 16) * cw, (i % 16) * chh
    d.rectangle([x + 4, y + 4, x + 64, y + chh - 2], fill=tuple(r['srgb']))
    b2 = tuple(int(round(255 * (min(1.0, c * 2.0) ** (1 / 2.2)))) for c in r['linear'])
    d.rectangle([x + 66, y + 4, x + 96, y + chh - 2], fill=b2)
    d.text((x + 102, y + 4), r['model'][:32], fill=(230, 230, 230))
    d.text((x + 102, y + 17), '%s  area %s%%' % ('%d,%d,%d' % tuple(r['srgb']), '-' if r['underwater'] else '%.1f' % (100 * r['total_area'] / tot_area)), fill=(160, 160, 160))
img.save(os.path.join(OUT, 'grass_colour_swatches.png'))
print('rows', len(rows))
fams = {}
for r in rows:
    if r['underwater']:
        continue
    fam = 'ComplexGrassDrJ11*' if r['model'].startswith('complexgrassdrj11') else r['model']
    fams[fam] = fams.get(fam, 0) + r['total_area']
for k, v in sorted(fams.items(), key=lambda kv: -kv[1])[:8]:
    print('  %-28s %.1f%% of land blade area' % (k, 100 * v / tot_area))
for r in rows[:22]:
    print('%-28s inst %4.1f%% area %5s%%  sRGB %-12s lin %-20s AO %.2f weight %5d %dx%d' % (r['model'], 100 * r['tamriel'] / tot_inst, '-' if r['underwater'] else '%.1f' % (100 * r['total_area'] / tot_area),
          '%d,%d,%d' % tuple(r['srgb']), '%.3f,%.3f,%.3f' % tuple(r['linear']), r['ao'], r['weight'], r['height'], r['width']))
import collections
print('vertex colours present:', collections.Counter(r['vertex_colours'] for r in rows), 'GRAS flags:', collections.Counter(str(r['gras_flags']) for r in rows), 'colour range:', collections.Counter(str(r['colour_range']) for r in rows).most_common(5))
print('non-grey vertex colour meshes:', [(r['model'], r['vc_mean']) for r in rows if r['vc_mean'] and max(r['vc_mean']) - min(r['vc_mean']) > 0.03][:12])
