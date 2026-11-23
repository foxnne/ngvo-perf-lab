"""suki_post.py - numpy port of the ACTIVE colour chain of "Suki's ENB Preset NLVA" (Skyrim LE, ENB DX9).

Source files (constants are copied from them, .fx.ini values override the .fx defaults):
    ref/nlva/insane/enbseries/enbeffect.fx + enbeffect.fx.ini   (PS_D6EC7DD1, POSTPROCESS==2, E_CC_PALETTE lookup)
    ref/nlva/insane/enbseries/Headers/Kabloom.fxh                (kaBloom, blend mode 6)
    ref/nlva/insane/enbseries/enbpalette.bmp                     (256x16 strip = 16^3 LUT)
    ref/nlva/insane/enbseries/effect.txt + effect.txt.ini        (optional: the per-pixel colour passes that run AFTER enbeffect.fx)

Colour space: everything here is in the shader's own space. Skyrim LE lights and blends in non-linear (display-like, "gamma")
space into an HDR target; enbeffect.fx reads that HDR value (texs0, SRGBTexture=FALSE), never linearises it, and writes with
SRGBWRITEENABLE=FALSE. So `rgb` in = HDR scene colour as LE renders it (0..~several, gamma-ish), out = display code values 0..1.

Order of operations in the pixel shader (and here):
    1. "eye adaptation" luminance compression (prod80)              color *= compLuma            [pre-bloom]
    2. kaBloom (Kermles), blend mode 6 "screen add"                  color += f(bloomTex)         [nearly a no-op with these values]
    3. ENB bloom                                                     color += bloomTex*EBloomAmount
    4. POSTPROCESS==2: adaptation divide, brightness, intensity contrast (pow on vector length),
       colour saturation (pow on the normalised colour, NOT renormalised), Reinhard-like tone curve with white point
    5. palette: saturate, 16^3 LUT, trilinear (kingeric1992 lookup; `#ifdef E_CC_PALETTE` is set by the ENB core because
       enbseries.ini has [COLORCORRECTION] UsePaletteTexture=true)
    6. EENE night-eye block: "---- EENE Enable ----=false" in the ini -> skipped entirely (its CC/vignette/sharpen/blur never run)
    (after the shader) ENB core [COLORCORRECTION] Brightness=1.1 / GammaCurve=1.1  -> optional, formula is NOT in the files (see core_cc)
    (after that)       effect.txt passes                                           -> optional per-pixel subset (see effect_txt)

Not ported (need neighbouring pixels / textures / time): the bloom texture itself (pass your own blurred image as `bloom`),
effect.txt LumaSharpen / horizontal blur / sharpening / colour shift (1.34 px vertical R/B split) / grain / dither / letterbox,
the ENB noise texture in the "kinematic blackness" mix (replaced by its mean 0.5), the EENE night-eye path (disabled anyway).

usage:  from suki_post import suki_post ;  out = suki_post(rgb, mode='day', adaptation=0.3)
        python suki_post.py     -> self-test (grey ramp + a few colours)
"""
import os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PALETTE_PATH = os.path.join(HERE, '..', 'ref', 'nlva', 'insane', 'enbseries', 'enbpalette.bmp')

# ---------------------------------------------------------------------------------------------------------------------
# constants: enbeffect.fx.ini  (name in comments = UIName / variable)
# ---------------------------------------------------------------------------------------------------------------------
V2 = {  # POSTPROCESS==2 block                 Day     Night   Interior
    'EBrightnessV2':                dict(day=0.5,   night=0.5,   interior=0.5),
    'EAdaptationMinV2':             dict(day=0.05,  night=0.04,  interior=0.07),
    'EAdaptationMaxV2':             dict(day=0.1,   night=0.02,  interior=0.06),
    'EToneMappingCurveV2':          dict(day=1.4,   night=1.5,   interior=3.1),
    'EIntensityContrastV2':         dict(day=0.94,  night=0.85,  interior=0.82),
    'EToneMappingOversaturationV2': dict(day=310.0, night=160.0, interior=340.0),
    'EColorSaturationV2':           dict(day=1.38,  night=1.17,  interior=1.1),
}
EYE = dict(  # "EYE ADAPTATION BY prod80" block; E = exterior, I = interior (blended by EInteriorFactor only)
    minAdaptE=0.05, maxAdaptE=0.1, minAdaptI=0.3, maxAdaptI=0.13,   # NB interior min > max -> clamp() always returns 0.13
    middleGrayE=3.0, middleGrayI=0.73, maxLumaE=12.0, maxLumaI=5.0)
KA = dict(  # Kabloom.fxh parameters
    InBlack=0.33, InWhite=0.48, InGamma=0.38, OutBlack=0.47, OutWhite=0.79,
    BloomBrightness=-0.83, BloomSaturation=0.31, BloomContrast=1.41, BloomSensitivity=0.31, BloomIntensity=-1.27,
    RGBBalance=(0.89, 0.902, 0.914), RGBWeights=(0.851, 0.863, 0.875), BlendMode=6, BlendAmount=3.0, BlendOpacity=100.0)
# enbseries.ini [BLOOM] Amount* is what the core passes as EBloomAmount; the per-weather files override it (0.5-0.9).
# Defaults below are the "!_ClearWeather__tundra.ini" values (Day 0.6, Night 0.5, Interior 0.5).
EBLOOM = dict(day=0.6, night=0.5, interior=0.5)
# enbseries.ini [ADAPTATION]: ForceMinMaxValues=true, AdaptationMin=0.12, AdaptationMax=0.7 (range of the adaptation texture)
ADAPT_RANGE = (0.12, 0.7)
# enbseries.ini [COLORCORRECTION] (applied by the ENB core, formula not in the files)
CORE_BRIGHTNESS, CORE_GAMMACURVE = 1.1, 1.1
# effect.txt.ini (only the per-pixel colour passes)
FX = dict(
    k_brightness=dict(ext_day=1.1, ext_night=1.15, int_day=1.0, int_night=1.0),
    noise_mix_curve=0.01, noise_mix_multiplier=0.27, enable_k_blackness=True,
    contrast=dict(ext_day=0.25, ext_night=0.1, int_day=0.55, int_night=0.2),
    vibrance=dict(day=-0.13, night=-0.13, interior=-0.13),
    vignette_amount=dict(day=0.2, night=0.1, interior=0.2), vignette_curve=1.5, vignette_radius=1.5)

_LUMA_ENB = np.array([0.2125, 0.7154, 0.0721])          # grayValue() in enbeffect.fx
_LUMA_FX = np.array([0.212656, 0.715158, 0.072186])     # effect.txt contrast / vibrance

_FACTORS = {'day': (1.0, 0.0), 'night': (0.0, 0.0), 'interior': (1.0, 1.0)}   # (ENightDayFactor, EInteriorFactor)


def _lerp(a, b, t):
    return a + (b - a) * t


def _dni(p, nd, interior):
    """the shader's lerp(Interior, lerp(Night, Day, hnd), pi) with pi = 1 - EInteriorFactor"""
    return _lerp(p['interior'], _lerp(p['night'], p['day'], nd), 1.0 - interior)


def _pow(x, e):
    return np.power(np.maximum(x, 0.0), e)


# ---------------------------------------------------------------------------------------------------------------------
# palette (kingeric1992 3D LUT lookup in enbeffect.fx): strip x = floor(b*15)*16 + r*15, y = g*15, lerp to next blue tile
# ---------------------------------------------------------------------------------------------------------------------
_CUBE = None


def _cube():
    global _CUBE
    if _CUBE is None:
        from PIL import Image
        a = np.asarray(Image.open(PALETTE_PATH).convert('RGB')).astype(np.float64) / 255.0   # (16 rows = g, 256 cols, 3)
        assert a.shape == (16, 256, 3), a.shape
        _CUBE = a.reshape(16, 16, 16, 3)                                                    # [g, b, r]
    return _CUBE


def palette_lookup(c):
    """color = saturate(color); trilinear 16^3 lookup. Equivalent to the two bilinear tex2Dlod taps + lerp on blue."""
    cube = _cube()
    c = np.clip(np.asarray(c, dtype=np.float64), 0.0, 1.0) * 15.0
    i0 = np.clip(np.floor(c).astype(int), 0, 14)
    f = c - i0
    out = 0.0
    for dr in (0, 1):
        for dg in (0, 1):
            for db in (0, 1):
                w = (f[..., 0] if dr else 1 - f[..., 0]) * (f[..., 1] if dg else 1 - f[..., 1]) * (f[..., 2] if db else 1 - f[..., 2])
                out = out + w[..., None] * cube[i0[..., 1] + dg, i0[..., 2] + db, i0[..., 0] + dr]
    return out


# ---------------------------------------------------------------------------------------------------------------------
# 1. prod80 "eye adaptation" (runs BEFORE bloom)
# ---------------------------------------------------------------------------------------------------------------------
def eye_adapt(color, adaptation, interior=0.0):
    """EyeAdapt = clamp(luma(adaptTex), minAdapt, maxAdapt); scaledLuma = pixelLuma*middleGray/EyeAdapt;
    compLuma = scaledLuma*(1+scaledLuma/maxLuma^2)/(1+scaledLuma); color *= compLuma.
    NB the colour is multiplied by the compressed luminance itself (not by compLuma/pixelLuma), so for dark pixels
    out ~ color * pixelLuma * middleGray/EyeAdapt: a quadratic toe (shadow crush), and ~x1.0-1.2 for bright pixels."""
    minA = _lerp(EYE['minAdaptE'], EYE['minAdaptI'], interior)
    maxA = _lerp(EYE['maxAdaptE'], EYE['maxAdaptI'], interior)
    mid = _lerp(EYE['middleGrayE'], EYE['middleGrayI'], interior)
    maxL = _lerp(EYE['maxLumaE'], EYE['maxLumaI'], interior)
    ea = np.minimum(np.maximum(adaptation, minA), maxA)          # HLSL clamp(x,a,b) = min(max(x,a),b)
    pl = color @ _LUMA_ENB
    s = pl * mid / ea
    comp = (s * (1.0 + s / (maxL * maxL))) / (1.0 + s)
    return color * comp[..., None]


# ---------------------------------------------------------------------------------------------------------------------
# 2. kaBloom (Kabloom.fxh), BlendMode 6
# ---------------------------------------------------------------------------------------------------------------------
def _sum_to(w, s):
    w = np.asarray(w, dtype=np.float64)
    return w / (w.sum() / s) if np.any(w) else np.full(3, s / 3.0)


def kabloom_term(bloom):
    """returns the value kaBloom ADDS to color (blend mode 6: color += 1-(1-sat(k))*(1-sat(k*BlendAmount)))."""
    k = np.clip(np.asarray(bloom, dtype=np.float64), 0.0, 1.0)
    # levelsAdjust
    k = _pow(np.maximum(k - KA['InBlack'], 0.0) / max(KA['InWhite'] - KA['InBlack'], 1e-4), KA['InGamma']) \
        * max(KA['OutWhite'] - KA['OutBlack'], 1e-4) + KA['OutBlack']
    k = k * _sum_to(KA['RGBBalance'], 3.0)                       # colour balance
    k = k * 2.0 ** KA['BloomBrightness']                         # input intensity
    c = max(0.0, KA['BloomContrast'])                            # adjustContrast
    k = np.maximum(0.0, _pow(k, c) / (_pow(np.clip(k, 0, 1), c) + _pow(1.0 - np.clip(k, 0, 1), c)))
    grey = k @ np.full(3, 0.3333)                                # adjustSaturation (saturation < 1 branch -> plain lerp)
    sat = KA['BloomSaturation']
    if sat < 1.0:
        k = grey[..., None] + (k - grey[..., None]) * sat
    else:
        cs = k.max(-1) - k.min(-1); vib = sat - 1.0
        k = grey[..., None] + (k - grey[..., None]) * (1.0 + vib * (1.0 - np.sign(vib) * cs))[..., None]
    lw = _sum_to(KA['RGBWeights'], 1.0)                          # cLuma weights
    cl = np.sqrt(_pow(k, 2.0) @ lw)
    k = np.maximum(0.0, _pow(k, np.maximum(0.0, 1.0 / np.maximum(1e-4, KA['BloomSensitivity'] * cl))[..., None]))
    k = k * 2.0 ** KA['BloomIntensity']                          # output intensity
    return 1.0 - (1.0 - np.clip(k, 0, 1)) * (1.0 - np.clip(k * KA['BlendAmount'], 0, 1))


# ---------------------------------------------------------------------------------------------------------------------
# 4. POSTPROCESS == 2
# ---------------------------------------------------------------------------------------------------------------------
def postprocess2(color, adaptation, nd=1.0, interior=0.0):
    p = {k: _dni(v, nd, interior) for k, v in V2.items()}
    ga = np.minimum(np.maximum(adaptation, 0.0), 50.0)
    color = color / (ga * p['EAdaptationMaxV2'] + p['EAdaptationMinV2'])
    color = color * p['EBrightnessV2']
    color = color + 0.000001
    n = np.linalg.norm(color, axis=-1, keepdims=True)
    xncol = color / n                                            # normalize(color)
    scl = color / xncol                                          # = length, per channel
    scl = _pow(scl, p['EIntensityContrastV2'])
    xncol = _pow(xncol, p['EColorSaturationV2'])                 # not renormalised: grey (0.577) -> 0.577^sat
    color = scl * xncol
    lumamax = p['EToneMappingOversaturationV2']
    return (color * (1.0 + color / lumamax)) / (color + p['EToneMappingCurveV2'])


# ---------------------------------------------------------------------------------------------------------------------
# optional: effect.txt per-pixel passes (PostProcess = kinematic filter, PostProcess6 = contrast, PostProcess7 = vibrance,
#           PostProcess8 = vignette if uv given). Runs on the 8-bit-ish LDR image after enbeffect.fx / core CC.
# ---------------------------------------------------------------------------------------------------------------------
def effect_txt_colour(color, nd=1.0, interior=0.0, uv=None):
    is_int = interior > 0.0                                      # shader uses `if (EInteriorFactor)`
    kb = FX['k_brightness']; ct = FX['contrast']
    k_brightness = _lerp(kb['int_night'], kb['int_day'], nd) if is_int else _lerp(kb['ext_night'], kb['ext_day'], nd)
    contrast = _lerp(ct['int_night'], ct['int_day'], nd) if is_int else _lerp(ct['ext_night'], ct['ext_day'], nd)
    # kinematic filter: scale, clamp, "blackness" mix (noise texture replaced by its mean 0.5 -> additive 0.5*0.0075)
    o = np.clip(color * k_brightness, 0.000005, 15.25)
    if FX['enable_k_blackness']:
        mix = _pow(np.clip(FX['noise_mix_multiplier'] * (o.sum(-1) * 2.133), 0, 1), FX['noise_mix_curve'])[..., None]
        o = _lerp(o * -0.45 + 0.5 * 0.0075, o, mix)
    o = np.clip(o, 0.0, 1.0)                                     # 8-bit render target between techniques
    # contrast (SweetFX curves formula on luma, chroma kept)
    luma = (o @ _LUMA_FX)[..., None]; chroma = o - luma
    x = luma - 0.5; x = x / (np.abs(x) * 1.25 + 0.375) + 0.5
    o = np.clip(_lerp(luma, x, contrast) + chroma, 0.0, 1.0)
    # vibrance (negative = desaturate the less saturated colours more)
    vib = _lerp(_lerp(FX['vibrance']['night'], FX['vibrance']['day'], nd), FX['vibrance']['interior'], interior)
    luma = (o @ _LUMA_FX)[..., None]; cs = (o.max(-1) - o.min(-1))[..., None]
    o = np.clip(_lerp(luma, o, 1.0 + vib * (1.0 - np.sign(vib) * cs)), 0.0, 1.0)
    if uv is not None:                                           # vignette to black
        va = _lerp(_lerp(FX['vignette_amount']['night'], FX['vignette_amount']['day'], nd), FX['vignette_amount']['interior'], interior)
        q = (np.asarray(uv) - 0.5) * FX['vignette_radius']
        v = _pow(np.clip((q * q).sum(-1), 0, 1), FX['vignette_curve'])[..., None]
        o = o * (1.0 - v * va)
    return o


# ---------------------------------------------------------------------------------------------------------------------
# main entry
# ---------------------------------------------------------------------------------------------------------------------
def suki_post(rgb, mode='day', adaptation=0.3, bloom=None, bloom_amount=None, night_day=None, interior=None,
              eye_adaptation=True, kabloom=True, palette=True, core_cc=None, effect_txt=False, uv=None):
    """Active enbeffect.fx colour chain of the preset.

    rgb         float array (..., 3): HDR scene colour as Skyrim LE renders it (non-linear / display-like space).
    mode        'day' | 'night' | 'interior' -> (ENightDayFactor, EInteriorFactor) = (1,0) | (0,0) | (1,1);
                override with night_day / interior (0..1 floats) for blends, e.g. interior at night: mode='interior', night_day=0.
                V2 parameters blend as lerp(Interior, lerp(Night, Day, ENightDayFactor), 1-EInteriorFactor).
    adaptation  value of ENB's adaptation texture (texs4, max channel == luma for grey). enbseries.ini forces it into
                [0.12, 0.7]. Used twice: clamp()ed to [0.05,0.1] ext / ->0.13 int in step 1, and as
                /(adaptation*AdaptMax+AdaptMin) in step 4 (day: 0.062..0.12, i.e. gain x8.1..x4.2 after the x0.5 brightness).
    bloom       optional float array like rgb: the enbbloom.fx output (texs3). None = no bloom (0).
    bloom_amount EBloomAmount; default per mode from the tundra weather file (0.6 / 0.5 / 0.5).
    core_cc     None (default) or 'brightness' or 'brightness_gamma': ENB core [COLORCORRECTION] Brightness=1.1 / GammaCurve=1.1.
                The formula lives in the closed-source d3d9.dll; 'brightness' = c*1.1, 'brightness_gamma' = (c*1.1)^(1/1.1) are GUESSES.
    effect_txt  also apply the per-pixel effect.txt passes (x1.1 brightness day, contrast, vibrance -0.13; vignette if uv given).
    returns     display code values (0..1 after the palette; pre-palette values are unclamped if palette=False).
    """
    nd, it = _FACTORS[mode]
    if night_day is not None: nd = float(night_day)
    if interior is not None: it = float(interior)
    color = np.asarray(rgb, dtype=np.float64)
    if eye_adaptation:
        color = eye_adapt(color, adaptation, it)
    if kabloom and KA['BlendMode']:
        color = color + kabloom_term(np.zeros_like(color) if bloom is None else bloom)
    if bloom is not None:
        amt = _dni(EBLOOM, nd, it) if bloom_amount is None else bloom_amount
        color = color + np.asarray(bloom, dtype=np.float64) * amt
    color = postprocess2(color, adaptation, nd, it)
    if palette:
        color = palette_lookup(color)
    if core_cc == 'brightness':
        color = np.clip(color * CORE_BRIGHTNESS, 0, 1)
    elif core_cc == 'brightness_gamma':
        color = _pow(np.clip(color * CORE_BRIGHTNESS, 0, 1), 1.0 / CORE_GAMMACURVE)
    if effect_txt:
        color = effect_txt_colour(color, nd, it, uv)
    return color


# ---------------------------------------------------------------------------------------------------------------------
# self-test
# ---------------------------------------------------------------------------------------------------------------------
if __name__ == '__main__':
    np.set_printoptions(precision=3, suppress=True, linewidth=200)
    ramp = np.array([0.0, 0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0, 1.5, 2.0, 4.0, 8.0])
    grey = ramp[:, None].repeat(3, 1)
    print('kaBloom additive term: bloom=0 ->', kabloom_term(np.zeros(3)), ' bloom>=1.0 ->', kabloom_term(np.ones(3)))
    print('palette neutral axis  in :', np.round(np.linspace(0, 1, 11), 2).tolist())
    print('                      out:', np.round(palette_lookup(np.linspace(0, 1, 11)[:, None].repeat(3, 1)), 3).tolist())
    print('\ngrey ramp (scene value, LE non-linear HDR) :', ramp.tolist())
    for mode in ('day', 'night', 'interior'):
        for a in (0.12, 0.3, 0.7):
            o = suki_post(grey, mode, a)
            print('  %-8s adapt=%.2f  enbeffect out (G): %s' % (mode, a, np.round(o[:, 1], 3).tolist()))
        o = suki_post(grey, mode, 0.3, palette=False)
        print('  %-8s adapt=0.30  before palette    : %s' % (mode, np.round(o[:, 1], 3).tolist()))
        o = suki_post(grey, mode, 0.3, core_cc='brightness', effect_txt=True)
        print('  %-8s adapt=0.30  +core x1.1 +fx.txt: %s' % (mode, np.round(o[:, 1], 3).tolist()))
        o = suki_post(grey, mode, 0.3)
        print('  %-8s adapt=0.30  R-G, B-G tint     : %s %s' % (mode, np.round(o[:, 0] - o[:, 1], 3).tolist(), np.round(o[:, 2] - o[:, 1], 3).tolist()))
    cols = [('red', [.6, .2, .2]), ('green', [.25, .5, .2]), ('blue', [.2, .3, .6]), ('skin', [.75, .55, .45]), ('straw', [.7, .62, .42]),
            ('grass', [.30, .42, .18]), ('sky', [.35, .55, .85]), ('cool shadow', [.06, .08, .11]), ('fire', [1.8, .9, .3])]

    def sat(c):
        c = np.asarray(c, dtype=float); return (c.max() - c.min()) / max(c.max(), 1e-6)
    print('\ncolours (scene in -> out), adaptation 0.3; s = HSV saturation in -> out')
    for nm, c in cols:
        c = np.array(c)
        d, n, i = (suki_post(c, m, 0.3) for m in ('day', 'night', 'interior'))
        p = suki_post(c, 'day', 0.3, palette=False)
        f = suki_post(c, 'day', 0.3, core_cc='brightness', effect_txt=True)
        print('  %-12s %s -> day %s (s %.2f->%.2f; pre-palette %s; +fx %s)  night %s  interior %s' % (nm, c, np.round(d, 3), sat(c), sat(d), np.round(p, 3), np.round(f, 3), np.round(n, 3), np.round(i, 3)))
    # isolated effect of the V2 saturation pow (day 1.38) on chroma, at constant vector length
    c = np.array([.75, .55, .45]); n = c / np.linalg.norm(c); m = n ** 1.38
    print('\nV2 saturation pow 1.38 on skin %s: channel ratios R/G %.3f->%.3f, B/G %.3f->%.3f; grey gain %.3f' % (c, c[0] / c[1], m[0] / m[1], c[2] / c[1], m[2] / m[1], 0.57735 ** 1.38 / 0.57735))
