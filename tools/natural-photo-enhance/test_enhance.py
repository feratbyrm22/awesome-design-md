#!/usr/bin/env python3
"""Checks for the properties that keep a result from reading as retouched.

Run with:  python test_enhance.py
"""

import sys

import cv2
import numpy as np

import enhance as E


def synthetic_portrait(h=1200, w=700, seed=7):
    """A flat, warm-cast frame with a blotchy skin region and sensor noise."""
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)

    img = np.repeat((0.22 + 0.10 * (1 - y / h))[..., None], 3, axis=2).astype(np.float32)
    face = ((x - w * 0.5) / (w * 0.19)) ** 2 + ((y - h * 0.24) / (h * 0.14)) ** 2 < 1
    shirt = (np.abs(x - w * 0.5) < w * 0.33) & (y > h * 0.40) & (y < h * 0.80)
    img[face] = np.array([0.68, 0.50, 0.41], np.float32)
    img[shirt] = np.array([0.16, 0.32, 0.30], np.float32)

    blotch = cv2.GaussianBlur(rng.standard_normal((h, w)).astype(np.float32), (0, 0), 22)
    pores = cv2.GaussianBlur(rng.standard_normal((h, w)).astype(np.float32), (0, 0), 0.8)
    img += (face.astype(np.float32) * (blotch * 0.055 + pores * 0.036))[..., None]

    img *= np.array([1.07, 1.0, 0.93], np.float32)   # warm cast
    img = 0.12 + img * 0.78                          # flat contrast
    img += rng.standard_normal(img.shape).astype(np.float32) * 0.012
    return np.clip(img, 0, 1).astype(np.float32), face, ~(face | shirt)


CHECKS = []


def check(fn):
    CHECKS.append(fn)
    return fn


@check
def strength_zero_is_identity(img, face, bg):
    out, _ = E.enhance(img.copy(), E.PRESETS["natural"], strength=0.0)
    worst = float(np.abs(out - img).max())
    assert worst < 0.01, f"strength 0 changed pixels by {worst:.4f}"
    return f"max pixel drift {worst:.5f}"


@check
def skin_texture_survives(img, face, bg):
    """The high-frequency band on skin must not be wiped out."""
    mask = face.astype(np.float32)
    before = E.texture_energy(img, mask)
    worst = 1.0
    for name in E.PRESETS:
        out, m = E.enhance(img.copy(), E.PRESETS[name], strength=1.0)
        ratio = E.texture_energy(out, mask) / before
        assert ratio > 0.65, f"{name}: skin texture fell to {ratio:.2f} of the original"
        worst = min(worst, ratio)
        assert m["generative_steps"] == 0
    return f"worst retained texture {worst * 100:.0f}%"


@check
def retouch_does_real_work(img, face, bg):
    """The safety rails must not have turned the retouch into a no-op.

    Blotchy low-frequency shading has to come down measurably while the
    high-frequency band stays put — that ratio is the whole technique.
    """
    mask = face.astype(np.float32)

    def blotchiness(im):
        return float(cv2.GaussianBlur(E.luminance(im), (0, 0), 18)[face].std())

    p = E.PRESETS["natural"]
    skin = E.skin_mask(img, [])
    graded = E.stage_colour(
        E.stage_local_contrast(
            E.stage_tone(E.stage_white_balance(img, p, 1.0), p, 1.0), p, 1.0
        ), p, 1.0, skin,
    )
    retouched = E.stage_skin(graded, p, 1.0, skin)

    flattened = 1.0 - blotchiness(retouched) / blotchiness(graded)
    texture_lost = 1.0 - E.texture_energy(retouched, mask) / E.texture_energy(graded, mask)
    assert flattened > 0.08, f"skin stage barely changed the shading ({flattened:.1%})"
    assert texture_lost < 0.10, f"skin stage ate {texture_lost:.1%} of the texture"
    return f"shading flattened {flattened:.0%}, texture lost {texture_lost:.1%}"


@check
def mask_stays_on_the_skin(img, face, bg):
    """A skin mask that leaks onto the background smooths the whole photo."""
    skin = E.skin_mask(img, [])
    inside, outside = float(skin[face].mean()), float(skin[bg].mean())
    assert inside > 0.6, f"skin mask only covers {inside:.2f} of the face"
    assert outside < 0.15, f"skin mask leaks onto the background at {outside:.2f}"
    return f"face {inside:.2f}, background {outside:.2f}"


@check
def exposure_moves_toward_the_target_key(img, face, bg):
    """Regression guard: the adaptive gamma must lift dark frames and hold back
    bright ones. An inverted exponent darkens exactly the photos that need help.
    """
    p = E.PRESETS["natural"]
    dark = np.clip(img * 0.55, 0, 1).astype(np.float32)
    bright = np.clip(0.45 + img * 0.55, 0, 1).astype(np.float32)

    dark_out, _ = E.enhance(dark.copy(), p, 1.0)
    bright_out, _ = E.enhance(bright.copy(), p, 1.0)

    before_d, after_d = np.median(E.luminance(dark)), np.median(E.luminance(dark_out))
    before_b, after_b = np.median(E.luminance(bright)), np.median(E.luminance(bright_out))
    assert after_d > before_d, f"dark frame got darker: {before_d:.3f} -> {after_d:.3f}"
    assert after_b < before_b, f"bright frame got brighter: {before_b:.3f} -> {after_b:.3f}"
    return f"dark {before_d:.2f}->{after_d:.2f}, bright {before_b:.2f}->{after_b:.2f}"


@check
def skin_colour_stays_believable(img, face, bg):
    """Skin is the one subject a viewer can colour-check from memory."""
    def stats(im):
        lab = cv2.cvtColor(np.clip(im, 0, 1).astype(np.float32), cv2.COLOR_RGB2LAB)
        a, b = lab[..., 1][face], lab[..., 2][face]
        return float(np.hypot(a, b).mean()), float(np.degrees(np.arctan2(b.mean(), a.mean())))

    chroma_0, hue_0 = stats(img)
    worst_c, worst_h = 1.0, 0.0
    for name in E.PRESETS:
        if E.PRESETS[name].mono:
            continue
        out, _ = E.enhance(img.copy(), E.PRESETS[name], strength=1.0)
        chroma, hue = stats(out)
        gain, drift = chroma / chroma_0, abs(hue - hue_0)
        assert gain < 1.35, f"{name}: skin chroma ran to {gain:.2f}x — orange skin"
        assert drift < 6.0, f"{name}: skin hue drifted {drift:.1f} degrees"
        worst_c, worst_h = max(worst_c, gain), max(worst_h, drift)
    return f"worst chroma {worst_c:.2f}x, worst hue drift {worst_h:.1f} deg"


@check
def noise_is_not_erased(img, face, bg):
    """A denoised subject on a noisy frame is the loudest tell there is.

    Scored against the noise the grade is *expected* to produce — the input
    level times the tone curve's amplification — rather than the raw input
    level, which a lifted frame can never legitimately hold.
    """
    worst_low, worst_high = 10.0, 0.0
    for name in E.PRESETS:
        out, m = E.enhance(img.copy(), E.PRESETS[name], strength=1.0)
        ratio = m["output_noise_sigma"] / m["expected_noise_sigma"]
        assert 0.7 < ratio < 1.6, f"{name}: noise landed at {ratio:.2f}x expected"
        worst_low, worst_high = min(worst_low, ratio), max(worst_high, ratio)
    return f"{worst_low:.2f}-{worst_high:.2f}x the exposure-adjusted expectation"


@check
def guard_clamps_an_overdriven_edit(img, face, bg):
    """Absurd settings must be pulled back, not rendered."""
    reckless = E.Params(
        skin_smooth=1.0, dodge_burn=1.0, retouch_delta_e=1.5, texture_floor=0.9
    )
    out, m = E.enhance(img.copy(), reckless, strength=2.0)
    assert m["retouch_strength_kept"] < 1.0, "guard failed to engage"
    assert m["retouch_delta_e"] <= reckless.retouch_delta_e + 0.15
    assert m["retouch_texture_retained"] >= reckless.texture_floor - 0.02
    return (f"kept {m['retouch_strength_kept'] * 100:.0f}% of the retouch, "
            f"dE {m['retouch_delta_e']:.2f}, texture {m['retouch_texture_retained']:.2f}")


@check
def output_is_well_formed(img, face, bg):
    out, _ = E.enhance(img.copy(), E.PRESETS["studio"], strength=1.0)
    assert out.shape == img.shape and out.dtype == np.float32
    assert np.isfinite(out).all()
    assert out.min() >= 0.0 and out.max() <= 1.0
    return f"{out.shape}, range [{out.min():.3f}, {out.max():.3f}]"


@check
def mono_is_neutral(img, face, bg):
    out, _ = E.enhance(img.copy(), E.PRESETS["mono"], strength=1.0)
    spread = float(np.abs(out - out.mean(axis=2, keepdims=True)).max())
    assert spread < 0.02, f"mono output carries colour, spread {spread:.3f}"
    return f"max channel spread {spread:.4f}"


@check
def cast_is_neutralised(img, face, bg):
    """Measured on the near-neutral background, where a cast is actually visible."""
    out, _ = E.enhance(img.copy(), E.PRESETS["natural"], strength=1.0)

    def relative_cast(im):
        # normalised by overall level, so a brighter result is not scored as
        # a stronger cast than the dim frame it came from
        channels = im[bg].mean(0)
        return float(np.ptp(channels / channels.mean()))

    before, after = relative_cast(img), relative_cast(out)
    assert after < before * 0.6, f"cast only moved {before:.4f} -> {after:.4f}"
    return f"relative background cast {before:.4f} -> {after:.4f}"


def main():
    img, face, bg = synthetic_portrait()
    failures = 0
    for fn in CHECKS:
        try:
            detail = fn(img, face, bg)
            print(f"  ok   {fn.__name__}: {detail}")
        except AssertionError as exc:
            failures += 1
            print(f"  FAIL {fn.__name__}: {exc}")
    print(f"\n{len(CHECKS) - failures}/{len(CHECKS)} checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
