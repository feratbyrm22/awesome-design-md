#!/usr/bin/env python3
"""Natural photo enhancement — retouching that does not read as AI.

The pipeline is deliberately non-generative: no upscaler, no face restoration
model, no inpainting. Every stage is a bounded, local operation on the pixels
that are already there, so facial geometry, pore structure and lens character
survive untouched. That is what keeps the result from looking synthetic.

Stages, in order:

    1.  white balance     neutralise a colour cast using near-neutral pixels
    2.  tone              black/white point + adaptive gamma toward a target key
    3.  local contrast    mild CLAHE on L*, blended back at partial strength
    4.  colour            vibrance (weak colours boosted, skin protected)
    5.  skin              frequency separation: blotches smoothed, texture kept
    6.  dodge & burn      flattens large-scale shading, keeps small-scale detail
    7.  eyes              optional, only with a known face box
    8.  depth             very light periphery falloff for subject separation
    9.  sharpen           unsharp mask gated by an edge mask, halo-clamped
    10. grain             luminance grain re-injected at the measured level
    11. realism guard     whole result dialled back to a Delta-E budget

Usage:

    python enhance.py photo.jpg
    python enhance.py photo.jpg --preset studio --strength 0.8
    python enhance.py photo.jpg --all -o out/
    python enhance.py photo.jpg --face 300,200,480,480 --report report.json
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
from dataclasses import dataclass, replace, asdict

import cv2
import numpy as np
from PIL import Image, ImageOps


# --------------------------------------------------------------------------
# parameters
# --------------------------------------------------------------------------


@dataclass
class Params:
    """All knobs, in "at strength 1.0" units. Everything is deliberately small."""

    # white balance
    wb: float = 0.75          # how far toward neutral to move the cast
    wb_max_gain: float = 0.12  # hard cap on any single channel gain

    # tone
    black_point: float = 0.6   # percentile used as the new black
    white_point: float = 99.6  # percentile used as the new white
    target_key: float = 0.46   # target median luminance
    gamma_limit: float = 0.35  # max deviation of the gamma exponent from 1.0
    shadow_lift: float = 0.10

    # local contrast
    clahe_clip: float = 1.3
    clahe_blend: float = 0.35

    # colour
    vibrance: float = 0.18
    skin_saturation_guard: float = 0.6  # 1.0 = skin fully excluded from vibrance
    warmth: float = 0.0                 # >0 warmer, <0 cooler, in a*/b* units

    # skin colour rails — orange, oversaturated skin is the most visible tell
    skin_chroma_gain: float = 1.20      # max growth of mean skin chroma
    skin_chroma_ceiling: float = 38.0   # absolute mean C* ceiling for skin
    skin_hue_tolerance: float = 4.0     # max mean hue drift, degrees

    # skin
    skin_smooth: float = 0.55   # blend of the smoothed low frequency band
    skin_radius: float = 0.012  # bilateral radius as a fraction of the long edge
    dodge_burn: float = 0.22    # how much large-scale skin shading is flattened

    # eyes (needs a face box)
    eye_boost: float = 0.30

    # depth
    depth: float = 0.10        # periphery darkening / clarity falloff

    # sharpening
    sharpen: float = 0.55
    sharpen_radius: float = 0.0009  # fraction of the long edge
    sharpen_clamp: float = 0.13     # halo ceiling, in signal units

    # grain
    grain: float = 0.95        # fraction of the measured original noise re-added
    grain_floor: float = 0.004  # never leave the image cleaner than this
    noise_texture_floor: float = 0.90  # detail the noise-settling pass must keep

    # realism guard — applied to the retouching only, never to the grade
    retouch_delta_e: float = 4.0  # mean Delta-E76 the local stages may move skin
    texture_floor: float = 0.72   # min fraction of skin micro-texture retained

    # monochrome
    mono: bool = False
    mono_mix: tuple = (0.30, 0.62, 0.08)  # R, G, B weights for the B&W mix


PRESETS = {
    # everyday, believable, the default
    "natural": Params(),
    # cleaner light and a touch more sculpting, as if shot with a softbox
    "studio": Params(
        target_key=0.50,
        clahe_clip=1.6,
        clahe_blend=0.45,
        skin_smooth=0.62,
        dodge_burn=0.30,
        vibrance=0.14,
        depth=0.16,
        sharpen=0.60,
    ),
    # daylight look: cooler shadows, more colour, less smoothing
    "outdoor": Params(
        warmth=-0.6,
        vibrance=0.26,
        clahe_clip=1.5,
        skin_smooth=0.42,
        dodge_burn=0.16,
        grain=1.0,
    ),
    # editorial black and white; grain matters most here
    "mono": Params(
        mono=True,
        clahe_clip=1.8,
        clahe_blend=0.5,
        skin_smooth=0.45,
        dodge_burn=0.28,
        sharpen=0.65,
        grain=1.25,
        depth=0.18,
    ),
}


# --------------------------------------------------------------------------
# io
# --------------------------------------------------------------------------


def load_image(path: str):
    """Return (float32 RGB in [0,1], exif bytes or None, icc profile or None)."""
    with Image.open(path) as im:
        exif = im.info.get("exif")
        icc = im.info.get("icc_profile")
        im = ImageOps.exif_transpose(im).convert("RGB")
        arr = np.asarray(im, dtype=np.float32) / 255.0
    if exif is not None:
        # orientation is already baked into the pixels; leaving the tag in place
        # would rotate the image a second time in any viewer that honours it
        exif = _strip_orientation(exif)
    return arr, exif, icc


def _strip_orientation(exif_bytes: bytes):
    try:
        exif = Image.Exif()
        exif.load(exif_bytes)
        exif.pop(0x0112, None)
        return exif.tobytes()
    except Exception:
        return None


def save_image(path: str, rgb: np.ndarray, exif=None, icc=None, quality: int = 95):
    out = np.clip(rgb * 255.0 + 0.5, 0, 255).astype(np.uint8)
    im = Image.fromarray(out, mode="RGB")
    kwargs = {}
    ext = os.path.splitext(path)[1].lower()
    if ext in (".jpg", ".jpeg"):
        kwargs = dict(quality=quality, subsampling=0, optimize=True)
    if exif:
        kwargs["exif"] = exif
    if icc:
        kwargs["icc_profile"] = icc
    im.save(path, **kwargs)


# --------------------------------------------------------------------------
# analysis
# --------------------------------------------------------------------------


def luminance(rgb: np.ndarray) -> np.ndarray:
    return rgb @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)


def estimate_noise(rgb: np.ndarray) -> float:
    """Immerkaer's fast noise sigma estimate, on the luminance channel."""
    gray = luminance(rgb)
    kernel = np.array([[1, -2, 1], [-2, 4, -2], [1, -2, 1]], dtype=np.float32)
    conv = cv2.filter2D(gray, -1, kernel, borderType=cv2.BORDER_REPLICATE)
    h, w = gray.shape
    return float(np.sqrt(np.pi / 2.0) * np.abs(conv).sum() / (6.0 * (w - 2) * (h - 2)))


def skin_mask(rgb: np.ndarray, faces=None) -> np.ndarray:
    """Feathered [0,1] mask of skin, from YCrCb chroma plus optional face boxes."""
    bgr8 = cv2.cvtColor((np.clip(rgb, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2BGR)
    ycrcb = cv2.cvtColor(bgr8, cv2.COLOR_BGR2YCrCb)
    y, cr, cb = cv2.split(ycrcb)

    mask = ((cr >= 133) & (cr <= 180) & (cb >= 77) & (cb <= 127) & (y >= 40) & (y <= 245))
    mask = (mask.astype(np.uint8)) * 255

    # drop specks, close pores-sized holes, then feather hard
    k = max(3, int(round(min(rgb.shape[:2]) * 0.006)) | 1)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = mask.astype(np.float32) / 255.0
    mask = cv2.GaussianBlur(mask, (0, 0), max(2.0, min(rgb.shape[:2]) * 0.008))

    if faces:
        # weight toward the face so hands, arms and skin-coloured walls get less
        weight = np.full(mask.shape, 0.45, dtype=np.float32)
        for (x, y0, w, h) in faces:
            ellipse = np.zeros(mask.shape, dtype=np.float32)
            cv2.ellipse(
                ellipse,
                (int(x + w / 2), int(y0 + h / 2)),
                (int(w * 0.62), int(h * 0.72)),
                0, 0, 360, 1.0, -1,
            )
            ellipse = cv2.GaussianBlur(ellipse, (0, 0), max(2.0, w * 0.10))
            weight = np.maximum(weight, ellipse)
        mask = mask * weight

    return np.clip(mask, 0.0, 1.0)


def detect_faces(rgb: np.ndarray):
    """Best-effort Haar face detection. Returns [] when no cascade is installed."""
    path = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
    if not os.path.isfile(path):
        return []
    cascade = cv2.CascadeClassifier(path)
    if cascade.empty():
        return []
    gray = (np.clip(luminance(rgb), 0, 1) * 255).astype(np.uint8)
    scale = 900.0 / max(gray.shape)
    if scale < 1.0:
        small = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    else:
        scale, small = 1.0, gray
    found = cascade.detectMultiScale(small, 1.15, 5, minSize=(60, 60))
    return [tuple(int(v / scale) for v in box) for box in found]


def radial_falloff(shape, power: float = 2.2) -> np.ndarray:
    """0 at the centre, 1 at the corners, elliptical to match the frame."""
    h, w = shape
    yy = (np.linspace(-1.0, 1.0, h, dtype=np.float32)) ** 2
    xx = (np.linspace(-1.0, 1.0, w, dtype=np.float32)) ** 2
    r = np.sqrt(yy[:, None] + xx[None, :]) / float(np.sqrt(2.0))
    return (np.clip(r, 0.0, 1.0) ** power).astype(np.float32)


def _blur_sigma(shape, fraction: float, minimum: float = 1.0) -> float:
    return max(minimum, max(shape[:2]) * fraction)


# --------------------------------------------------------------------------
# stages
# --------------------------------------------------------------------------


def stage_white_balance(rgb: np.ndarray, p: Params, s: float) -> np.ndarray:
    """Grey-world, but only over pixels that are plausibly neutral already."""
    lum = luminance(rgb)
    mx = rgb.max(axis=2)
    mn = rgb.min(axis=2)
    sat = (mx - mn) / np.maximum(mx, 1e-4)
    sel = (sat < 0.22) & (lum > 0.12) & (lum < 0.95)
    if sel.sum() < lum.size * 0.002:
        return rgb

    means = np.array([rgb[..., c][sel].mean() for c in range(3)], dtype=np.float32)
    means = np.maximum(means, 1e-4)
    gains = means.mean() / means
    gains = 1.0 + (gains - 1.0) * (p.wb * s)
    gains = np.clip(gains, 1.0 - p.wb_max_gain, 1.0 + p.wb_max_gain)
    return np.clip(rgb * gains[None, None, :], 0.0, 1.0)


def fit_tone_curve(lum: np.ndarray, p: Params, s: float):
    """Fit the tone curve to this frame and return it as a plain function.

    Fitting and applying are separate so the same curve can be sampled — its
    slope is what tells the grain stage how much the exposure multiplied the
    noise, which no before/after average can recover once it has been applied.
    """
    lo = float(np.percentile(lum, p.black_point))
    hi = float(np.percentile(lum, p.white_point))
    stretch = hi - lo > 0.05
    if stretch:
        # both endpoints interpolate from identity (0, 1) at s = 0 toward a
        # partial pull to the measured percentiles at s = 1 — never all the way
        lo = lo * 0.85 * s
        hi = 1.0 - 0.55 * s * (1.0 - hi)

    stretched = np.clip((lum - lo) / max(hi - lo, 1e-3), 0.0, 1.0) if stretch else lum
    median = float(np.median(stretched))
    gamma = 1.0
    if 0.02 < median < 0.98:
        gamma = np.log(max(p.target_key, 1e-3)) / np.log(median)
        gamma = float(np.clip(gamma, 1.0 - p.gamma_limit, 1.0 + p.gamma_limit))
        gamma = 1.0 + (gamma - 1.0) * s
    lift = p.shadow_lift * s

    def curve(x):
        out = np.clip((x - lo) / max(hi - lo, 1e-3), 0.0, 1.0) if stretch else x
        if gamma != 1.0:
            # median ** gamma == target, so the exponent is applied directly:
            # inverting it would darken exactly the frames that need lifting
            out = np.power(np.clip(out, 0.0, 1.0), gamma)
        if lift > 0:
            # lift only the bottom of the range, rolling off before mid grey
            mask = np.clip(1.0 - out / 0.45, 0.0, 1.0) ** 2
            out = out + lift * mask * (1.0 - out)
        return np.clip(out, 0.0, 1.0)

    return curve


def tone_noise_gain(lum: np.ndarray, curve, bins: int = 128) -> float:
    """Mean slope of the tone curve, weighted by how many pixels sit on it.

    Noise is amplified by the local slope where it lives, not by the change in
    average brightness: a curve can lift the shadows hard and leave the median
    where it was. Weighting the slope by the luminance histogram gives the
    factor the frame's grain was actually multiplied by.
    """
    edges = np.linspace(0.0, 1.0, bins + 1, dtype=np.float32)
    mapped = curve(edges)
    slopes = np.diff(mapped) / np.diff(edges)
    counts, _ = np.histogram(lum, bins=edges)
    if counts.sum() == 0:
        return 1.0
    return float(np.clip((slopes * counts).sum() / counts.sum(), 0.25, 6.0))


def stage_tone(rgb: np.ndarray, p: Params, s: float) -> np.ndarray:
    """Apply the tone curve as a per-pixel gain on luminance, ratios preserved.

    Running the curve on R, G and B independently is the obvious implementation
    and the wrong one: subtracting a black point from each channel changes the
    ratios between them, which inflates saturation as contrast rises and drags
    any residual colour cast back out of the shadows. Scaling all three channels
    by one luminance-derived factor moves the tonality and nothing else.
    """
    lum = luminance(rgb)
    mapped = fit_tone_curve(lum, p, s)(lum)
    gain = np.clip(mapped / np.maximum(lum, 1e-4), 0.0, 8.0)
    return np.clip(rgb * gain[..., None], 0.0, 1.0)


def stage_local_contrast(rgb: np.ndarray, p: Params, s: float) -> np.ndarray:
    """CLAHE on the structural band only.

    Run over the raw channel, CLAHE stretches the histogram inside every flat
    tile, and in a flat tile the only thing to stretch is the grain — a wall or
    a patch of sky comes back several times noisier. Splitting the grain off
    first lets the equalisation shape tonality while the noise passes through
    at exactly the level it came in at.
    """
    if p.clahe_blend <= 0 or s <= 0:
        return rgb
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
    L = lab[..., 0]

    structure = cv2.GaussianBlur(L, (0, 0), 1.5)
    grain = L - structure

    clahe = cv2.createCLAHE(clipLimit=p.clahe_clip, tileGridSize=(8, 8))
    equalised = clahe.apply((np.clip(structure / 100.0, 0, 1) * 65535).astype(np.uint16))
    equalised = equalised.astype(np.float32) / 65535.0 * 100.0

    blend = p.clahe_blend * s
    lab[..., 0] = structure * (1.0 - blend) + equalised * blend + grain
    return np.clip(cv2.cvtColor(lab, cv2.COLOR_LAB2RGB), 0.0, 1.0)


def stage_colour(rgb: np.ndarray, p: Params, s: float, skin: np.ndarray) -> np.ndarray:
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
    a, b = lab[..., 1], lab[..., 2]

    chroma = np.sqrt(a * a + b * b)
    # vibrance: strongest where chroma is low, nothing where it is already loud
    boost = p.vibrance * s * np.clip(1.0 - chroma / 60.0, 0.0, 1.0)
    # ...but near-neutrals are held out entirely. Boosting them would amplify
    # whatever cast survived the white balance, tinting the greys back again
    neutral = np.clip((chroma - 2.0) / 6.0, 0.0, 1.0)
    boost *= neutral * neutral * (3.0 - 2.0 * neutral)
    boost *= 1.0 - p.skin_saturation_guard * skin
    lab[..., 1] = a * (1.0 + boost)
    lab[..., 2] = b * (1.0 + boost)

    if p.warmth:
        lab[..., 2] = lab[..., 2] + p.warmth * s
        lab[..., 1] = lab[..., 1] + p.warmth * 0.35 * s

    return np.clip(cv2.cvtColor(lab, cv2.COLOR_LAB2RGB), 0.0, 1.0)


def _skin_ab(lab: np.ndarray, skin: np.ndarray):
    """Weighted mean a*/b* of the skin region."""
    total = float(skin.sum())
    if total <= 1e-6:
        return 0.0, 0.0
    a = float((lab[..., 1] * skin).sum() / total)
    b = float((lab[..., 2] * skin).sum() / total)
    return a, b


def stage_skin_colour(rgb, p: Params, s: float, skin: np.ndarray, reference) -> np.ndarray:
    """Hold skin inside the chroma and hue band that real skin occupies.

    Contrast and vibrance both multiply chroma, and skin is the one subject
    where a viewer knows the right answer by heart. This pulls the skin region
    back if the grade pushed it orange, and leaves everything else alone.
    Hue is compared against the white-balanced frame, not the raw file, so
    removing a colour cast still counts as a correction rather than a drift.
    """
    if s <= 0 or float(skin.mean()) < 0.005:
        return rgb

    lab = cv2.cvtColor(np.clip(rgb, 0, 1).astype(np.float32), cv2.COLOR_RGB2LAB)
    ref = cv2.cvtColor(np.clip(reference, 0, 1).astype(np.float32), cv2.COLOR_RGB2LAB)

    a, b = _skin_ab(lab, skin)
    ra, rb = _skin_ab(ref, skin)
    chroma = float(np.hypot(a, b))
    ref_chroma = float(np.hypot(ra, rb))
    if chroma < 1e-3:
        return rgb

    ceiling = min(ref_chroma * p.skin_chroma_gain, p.skin_chroma_ceiling)
    if chroma > ceiling:
        # scale a*/b* toward neutral, but only by as much as the skin mask says
        pull = 1.0 - (ceiling / chroma)
        factor = 1.0 - skin * pull
        lab[..., 1] *= factor
        lab[..., 2] *= factor

    if ref_chroma > 1e-3:
        drift = np.degrees(np.arctan2(b, a) - np.arctan2(rb, ra))
        drift = (drift + 180.0) % 360.0 - 180.0
        excess = abs(drift) - p.skin_hue_tolerance
        if excess > 0:
            theta = np.radians(-np.sign(drift) * excess) * skin
            cos_t, sin_t = np.cos(theta), np.sin(theta)
            a_ch, b_ch = lab[..., 1].copy(), lab[..., 2].copy()
            lab[..., 1] = a_ch * cos_t - b_ch * sin_t
            lab[..., 2] = a_ch * sin_t + b_ch * cos_t

    return np.clip(cv2.cvtColor(lab, cv2.COLOR_LAB2RGB), 0.0, 1.0)


def _low_frequency(rgb: np.ndarray, radius_px: float) -> np.ndarray:
    """Edge-preserving low band. Computed small, then lifted back up."""
    h, w = rgb.shape[:2]
    scale = min(1.0, 1100.0 / max(h, w))
    small = cv2.resize(rgb, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) \
        if scale < 1.0 else rgb
    d = int(max(5, round(radius_px * scale) | 1))
    low = cv2.bilateralFilter(small, d, 0.08, d * 1.5)
    low = cv2.bilateralFilter(low, d, 0.08, d * 1.5)
    if scale < 1.0:
        low = cv2.resize(low, (w, h), interpolation=cv2.INTER_LINEAR)
    return low


def stage_skin(rgb: np.ndarray, p: Params, s: float, skin: np.ndarray) -> np.ndarray:
    """Frequency separation. The high band is never touched — that is the point.

    Blotchy colour and uneven shading live in the low band; pores, stubble and
    fine hair live in the high band. Smoothing only the low band removes the
    mottling that reads as "tired" while leaving the texture that reads as real.
    """
    if s <= 0 or (p.skin_smooth <= 0 and p.dodge_burn <= 0):
        return rgb

    radius = _blur_sigma(rgb.shape, p.skin_radius, 5.0)
    low = _low_frequency(rgb, radius)
    high = rgb - low

    result_low = low
    if p.skin_smooth > 0:
        softer = cv2.GaussianBlur(low, (0, 0), radius * 0.55)
        alpha = np.clip(p.skin_smooth * s, 0.0, 0.75) * skin[..., None]
        result_low = low * (1.0 - alpha) + softer * alpha

    if p.dodge_burn > 0:
        # pull large-scale luminance toward its own local average: this is the
        # manual dodge-and-burn a retoucher does, at a scale far above pores
        lum = luminance(result_low)
        base = cv2.GaussianBlur(lum, (0, 0), radius * 4.0)
        target = cv2.GaussianBlur(base, (0, 0), radius * 12.0)
        delta = (target - base) * (p.dodge_burn * s) * skin
        delta = np.clip(delta, -0.10, 0.10)
        result_low = result_low + delta[..., None]

    return np.clip(result_low + high, 0.0, 1.0)


def stage_eyes(rgb: np.ndarray, p: Params, s: float, faces) -> np.ndarray:
    """Local clarity in the eye region only, and only when a face box is known."""
    if not faces or p.eye_boost <= 0 or s <= 0:
        return rgb
    path = os.path.join(cv2.data.haarcascades, "haarcascade_eye.xml")
    if not os.path.isfile(path):
        return rgb
    cascade = cv2.CascadeClassifier(path)
    if cascade.empty():
        return rgb

    gray = (np.clip(luminance(rgb), 0, 1) * 255).astype(np.uint8)
    mask = np.zeros(rgb.shape[:2], dtype=np.float32)
    hit = False
    for (fx, fy, fw, fh) in faces:
        roi = gray[fy:fy + int(fh * 0.6), fx:fx + fw]
        if roi.size == 0:
            continue
        for (ex, ey, ew, eh) in cascade.detectMultiScale(roi, 1.1, 6):
            cv2.circle(
                mask,
                (fx + ex + ew // 2, fy + ey + eh // 2),
                int(max(ew, eh) * 0.42),
                1.0, -1,
            )
            hit = True
    if not hit:
        return rgb

    mask = cv2.GaussianBlur(mask, (0, 0), max(2.0, rgb.shape[1] * 0.004))
    sharp = unsharp(rgb, _blur_sigma(rgb.shape, 0.0012, 1.0), 0.9, 0.20)
    amount = np.clip(p.eye_boost * s, 0.0, 0.5) * mask[..., None]
    return np.clip(rgb * (1.0 - amount) + sharp * amount, 0.0, 1.0)


def stage_depth(rgb: np.ndarray, p: Params, s: float) -> np.ndarray:
    """A whisper of periphery falloff. Enough to seat the subject, not a vignette."""
    if p.depth <= 0 or s <= 0:
        return rgb
    r = radial_falloff(rgb.shape[:2])
    amount = p.depth * s
    darken = 1.0 - amount * 0.55 * r
    out = rgb * darken[..., None]
    # very slight desaturation at the edges, the way fast glass falls off
    lab = cv2.cvtColor(np.clip(out, 0, 1).astype(np.float32), cv2.COLOR_RGB2LAB)
    fade = 1.0 - amount * 0.35 * r
    lab[..., 1] *= fade
    lab[..., 2] *= fade
    return np.clip(cv2.cvtColor(lab, cv2.COLOR_LAB2RGB), 0.0, 1.0)


def unsharp(rgb: np.ndarray, sigma: float, amount: float, clamp: float) -> np.ndarray:
    blurred = cv2.GaussianBlur(rgb, (0, 0), sigma)
    detail = np.clip(rgb - blurred, -clamp, clamp)
    return rgb + amount * detail


def stage_sharpen(rgb: np.ndarray, p: Params, s: float, noise: float) -> np.ndarray:
    """Unsharp masking gated by an edge mask, so flat areas keep their noise."""
    if p.sharpen <= 0 or s <= 0:
        return rgb
    sigma = _blur_sigma(rgb.shape, p.sharpen_radius, 0.8)
    sharp = unsharp(rgb, sigma, p.sharpen * s, p.sharpen_clamp)

    lum = luminance(rgb)
    gx = cv2.Sobel(lum, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(lum, cv2.CV_32F, 0, 1, ksize=3)
    grad = cv2.GaussianBlur(np.sqrt(gx * gx + gy * gy), (0, 0), sigma * 1.5)

    lo = max(noise * 2.5, 0.008)
    hi = max(noise * 8.0, 0.045)
    edge = np.clip((grad - lo) / max(hi - lo, 1e-4), 0.0, 1.0)
    edge = edge * edge * (3.0 - 2.0 * edge)  # smoothstep, no visible mask seam

    return np.clip(rgb * (1.0 - edge[..., None]) + sharp * edge[..., None], 0.0, 1.0)


def _settle_noise(rgb: np.ndarray, target: float, residual: float,
                  texture_floor: float) -> np.ndarray:
    """Ease noise back toward the target — but never at the cost of texture.

    Brightening, CLAHE and sharpening all multiply whatever noise was in the
    file, and that much is honest: a lifted photo really is grainier. What is
    not honest is scrubbing the grain out, because the detail goes with it.
    So this removes only the excess that fits inside the texture budget and
    accepts the rest; a slightly grainy frame reads as a photograph, a smooth
    one reads as a render.
    """
    denoised = cv2.bilateralFilter(rgb, 5, max(residual * 3.0, 0.01), 3.0)
    reachable = residual - estimate_noise(denoised)
    if reachable <= 1e-6:
        return rgb

    wanted = float(np.clip((residual - target) / reachable, 0.0, 1.0))
    whole = np.ones(rgb.shape[:2], dtype=np.float32)
    before = texture_energy(rgb, whole)
    if before <= 1e-6:
        return rgb

    def keeps_texture(alpha: float) -> bool:
        blend = rgb * (1.0 - alpha) + denoised * alpha
        return texture_energy(blend, whole) / before >= texture_floor

    if keeps_texture(wanted):
        alpha = wanted
    else:
        lo, hi = 0.0, wanted
        for _ in range(6):
            mid = (lo + hi) / 2.0
            lo, hi = (mid, hi) if keeps_texture(mid) else (lo, mid)
        alpha = lo

    return rgb * (1.0 - alpha) + denoised * alpha


def stage_grain(rgb: np.ndarray, p: Params, s: float, noise: float,
                exposure_gain: float = 1.0) -> np.ndarray:
    """Put the sensor noise back.

    Every smoothing stage above removes noise, and a uniformly noiseless face on
    a noisy background is the single loudest tell of machine retouching. This
    re-adds luminance-only grain at the level measured on the input, slightly
    correlated so it looks like a sensor rather than per-pixel static.

    Only the *deficit* is added, in quadrature against whatever noise survived
    the pipeline, so the output lands at the input's noise level instead of
    overshooting it — an unnaturally grainy frame is as much of a tell as an
    unnaturally clean one.

    The target scales with the exposure the grade applied: lifting a dark frame
    multiplies its noise along with everything else, so holding the output to
    the *unlifted* measurement would mean scrubbing away real detail to hit a
    number that was never the right one.
    """
    target = max(noise * exposure_gain * p.grain * s, p.grain_floor * s)
    if target <= 0:
        return rgb

    residual = estimate_noise(rgb)
    if residual > target * 1.10:
        rgb = _settle_noise(rgb, target, residual, p.noise_texture_floor)
        residual = estimate_noise(rgb)

    sigma = float(np.sqrt(max(target * target - residual * residual, 0.0)))
    if sigma <= 1e-5:
        return rgb

    rng = np.random.default_rng(1729)
    noise_field = rng.standard_normal(rgb.shape[:2]).astype(np.float32)
    noise_field = cv2.GaussianBlur(noise_field, (0, 0), 0.6)
    noise_field /= max(float(noise_field.std()), 1e-6)

    lum = luminance(rgb)
    # grain is most visible in the mid-tones and shadows, least in the highlights
    weight = np.clip(1.0 - np.abs(2.0 * lum - 1.0) ** 1.5, 0.15, 1.0)
    # renormalise so the modulation redistributes the grain instead of muting it
    weight = weight / max(float(np.sqrt((weight ** 2).mean())), 1e-6)
    return np.clip(rgb + (noise_field * weight * sigma)[..., None], 0.0, 1.0)


def stage_mono(rgb: np.ndarray, p: Params) -> np.ndarray:
    if not p.mono:
        return rgb
    w = np.array(p.mono_mix, dtype=np.float32)
    gray = np.clip(rgb @ (w / w.sum()), 0.0, 1.0)
    return np.repeat(gray[..., None], 3, axis=2)


# --------------------------------------------------------------------------
# realism guard
# --------------------------------------------------------------------------


def delta_e(a: np.ndarray, b: np.ndarray, weight: np.ndarray | None = None) -> float:
    """Mean CIE76 colour difference, optionally weighted by a mask."""
    la = cv2.cvtColor(np.clip(a, 0, 1).astype(np.float32), cv2.COLOR_RGB2LAB)
    lb = cv2.cvtColor(np.clip(b, 0, 1).astype(np.float32), cv2.COLOR_RGB2LAB)
    d = np.sqrt(((la - lb) ** 2).sum(axis=2))
    if weight is None:
        return float(d.mean())
    total = float(weight.sum())
    return float((d * weight).sum() / total) if total > 1e-6 else 0.0


def texture_energy(rgb: np.ndarray, weight: np.ndarray) -> float:
    """RMS of the micro-detail band, over the weighted region.

    This is the number that separates a retouch from a synthetic face: pores and
    stubble are high-frequency energy, and every generative or heavy-handed
    smoothing pass destroys them.
    """
    lum = luminance(rgb)
    hf = lum - cv2.GaussianBlur(lum, (0, 0), 1.2)
    total = float(weight.sum())
    if total <= 1e-6:
        return 0.0
    return float(np.sqrt(((hf * hf) * weight).sum() / total))


def _shrink(*arrays, max_dim: int = 900):
    """Downscale the guard's inputs — the alpha it solves for is resolution free."""
    h, w = arrays[0].shape[:2]
    scale = min(1.0, max_dim / max(h, w))
    if scale >= 1.0:
        return arrays
    return tuple(
        cv2.resize(a, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        for a in arrays
    )


def fit_guard(base, edited, weight, de_budget: float, texture_floor: float):
    """Find the strongest retouch that still passes as un-retouched.

    Constraints are checked against `base` (the graded but un-retouched frame),
    not the raw file, so an honest exposure or white balance correction is never
    counted against the budget. Blending back toward `base` moves both metrics
    monotonically, so a short bisection finds the best admissible blend.
    """
    sb, se, sw = _shrink(base, edited, weight)
    reference_texture = texture_energy(sb, sw)

    def admissible(alpha: float):
        blend = sb * (1.0 - alpha) + se * alpha
        de = delta_e(sb, blend, sw)
        tex = texture_energy(blend, sw)
        ratio = tex / reference_texture if reference_texture > 1e-6 else 1.0
        return (de <= de_budget and ratio >= texture_floor), de, ratio

    ok, de, ratio = admissible(1.0)
    if ok:
        return edited, 1.0, de, ratio

    lo, hi = 0.0, 1.0
    for _ in range(8):
        mid = (lo + hi) / 2.0
        ok, _, _ = admissible(mid)
        lo, hi = (mid, hi) if ok else (lo, mid)
    _, de, ratio = admissible(lo)
    blended = np.clip(base * (1.0 - lo) + edited * lo, 0.0, 1.0)
    return blended, lo, de, ratio


# --------------------------------------------------------------------------
# pipeline
# --------------------------------------------------------------------------


def enhance(rgb: np.ndarray, p: Params, strength: float = 1.0, faces=None):
    """Run the full pipeline. Returns (result, metrics dict)."""
    original = rgb.copy()
    s = float(strength)

    noise = estimate_noise(rgb)
    if faces is None:
        faces = detect_faces(rgb)
    skin = skin_mask(rgb, faces)

    # a photograph the camera could have produced: nothing here is suspicious,
    # so none of it is charged against the realism budget
    balanced = stage_white_balance(rgb, p, s)
    balanced_lum = luminance(balanced)
    exposure_gain = tone_noise_gain(balanced_lum, fit_tone_curve(balanced_lum, p, s))
    graded = stage_tone(balanced, p, s)
    graded = stage_local_contrast(graded, p, s)
    graded = stage_colour(graded, p, s, skin)
    graded = stage_skin_colour(graded, p, s, skin, balanced)

    # everything a viewer would call "retouching" — bounded below
    retouched = stage_skin(graded, p, s, skin)
    retouched = stage_eyes(retouched, p, s, faces)

    weight = skin if float(skin.mean()) > 0.01 else np.ones(skin.shape, np.float32)
    retouched, alpha, local_de, texture_ratio = fit_guard(
        graded, retouched, weight, p.retouch_delta_e, p.texture_floor
    )

    out = stage_depth(retouched, p, s)
    out = stage_sharpen(out, p, s, noise)
    out = stage_mono(out, p)
    out = stage_grain(out, p, s, noise, exposure_gain)

    # measured end to end, on the file that actually gets written — a ratio taken
    # mid-pipeline would miss whatever the closing stages cost
    reference_texture = texture_energy(original, weight)
    final_texture = (texture_energy(out, weight) / reference_texture
                     if reference_texture > 1e-6 else 1.0)

    metrics = {
        "input_noise_sigma": round(noise, 5),
        "output_noise_sigma": round(estimate_noise(out), 5),
        "exposure_noise_gain": round(exposure_gain, 3),
        "expected_noise_sigma": round(noise * exposure_gain, 5),
        "faces_detected": len(faces),
        "skin_coverage": round(float(skin.mean()), 4),
        "retouch_delta_e": round(local_de, 3),
        "retouch_delta_e_budget": p.retouch_delta_e,
        "retouch_strength_kept": round(alpha, 3),
        "retouch_texture_retained": round(texture_ratio, 3),
        "skin_texture_retained": round(final_texture, 3),
        "texture_floor": p.texture_floor,
        "grade_delta_e_vs_original": round(delta_e(original, out), 3),
        "generative_steps": 0,
    }
    return out, metrics


# --------------------------------------------------------------------------
# cli
# --------------------------------------------------------------------------


def parse_face(value: str):
    parts = [int(v) for v in value.replace(" ", "").split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("expected x,y,w,h")
    return tuple(parts)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Natural, non-generative photo enhancement.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("image", help="input photo")
    ap.add_argument("-o", "--output", help="output file, or a directory with --all")
    ap.add_argument("-p", "--preset", default="natural", choices=sorted(PRESETS))
    ap.add_argument("--all", action="store_true", help="render every preset")
    ap.add_argument("--strength", type=float, default=1.0,
                    help="global multiplier, 0 = untouched")
    ap.add_argument("--unmirror", action="store_true",
                    help="flip horizontally, for mirror selfies (fixes reversed text)")
    ap.add_argument("--face", type=parse_face, action="append",
                    help="face box x,y,w,h; repeatable, skips detection")
    ap.add_argument("--budget", type=float,
                    help="override the retouch Delta-E budget (lower = subtler)")
    ap.add_argument("--texture-floor", type=float,
                    help="min fraction of skin micro-texture to retain, 0..1")
    ap.add_argument("--quality", type=int, default=95, help="JPEG quality")
    ap.add_argument("--report", help="write metrics to this JSON file")
    args = ap.parse_args(argv)

    if not os.path.isfile(args.image):
        print(f"no such file: {args.image}", file=sys.stderr)
        return 1
    if not 0.0 <= args.strength <= 2.0:
        print("--strength must be between 0 and 2", file=sys.stderr)
        return 1

    rgb, exif, icc = load_image(args.image)
    if args.unmirror:
        # a phone mirror-selfie is left-right reversed: text reads backwards and
        # the face is the one nobody else ever sees
        rgb = np.ascontiguousarray(rgb[:, ::-1])
    stem, ext = os.path.splitext(os.path.basename(args.image))
    ext = ext if ext.lower() in (".jpg", ".jpeg", ".png") else ".jpg"

    presets = sorted(PRESETS) if args.all else [args.preset]
    if args.all:
        outdir = args.output or "."
        os.makedirs(outdir, exist_ok=True)
    else:
        outdir = None

    faces = args.face if args.face else None
    report = {"source": args.image, "strength": args.strength, "results": {}}

    for name in presets:
        params = PRESETS[name]
        if args.budget is not None:
            params = replace(params, retouch_delta_e=args.budget)
        if args.texture_floor is not None:
            params = replace(params, texture_floor=args.texture_floor)

        result, metrics = enhance(rgb.copy(), params, args.strength, faces)

        if outdir is not None:
            path = os.path.join(outdir, f"{stem}--{name}{ext}")
        else:
            path = args.output or f"{stem}--{name}{ext}"
        save_image(path, result, exif, icc, args.quality)

        metrics["output"] = path
        metrics["params"] = asdict(params)
        report["results"][name] = metrics
        print(
            f"{name:8s} -> {path}\n"
            f"           retouch dE {metrics['retouch_delta_e']:.2f}"
            f"/{metrics['retouch_delta_e_budget']:.1f}"
            f" (kept {metrics['retouch_strength_kept'] * 100:.0f}%)   "
            f"skin texture {metrics['retouch_texture_retained'] * 100:.0f}%"
            f" (floor {metrics['texture_floor'] * 100:.0f}%)   "
            f"noise {metrics['output_noise_sigma']:.4f}"
            f" vs {metrics['expected_noise_sigma']:.4f} expected   "
            f"faces {metrics['faces_detected']}"
        )

    if args.report:
        with open(args.report, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)
        print(f"report   -> {args.report}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
