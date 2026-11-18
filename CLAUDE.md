# CLAUDE.md

Project-level rules for any AI agent (Claude, or another coding agent reading this file) working in **awesome-design-md** — a curated collection of `DESIGN.md` files. Because this repo's entire purpose is design quality, the anti-slop rules below are non-negotiable defaults for anything generated here: new `DESIGN.md` entries, example UIs, README sections, or any visual/interface output.

## 1. Banned by default ("AI slop" patterns)

Never reach for these unless the user explicitly asks for them:

- Serif display headings + broken-white/cream background (`#FAF9F6`-ish) + orange/coral accent — this specific trio is the single most overused "AI generated design" tell. Banned outright.
- Colored accent stripes on the left or top edge of cards (`border-left: 4px solid ...`).
- Generic "corporate template" layouts: centered hero, 3-up feature cards, Inter/Roboto/Arial everywhere, no typographic point of view.
- Purple-to-blue gradients or glassmorphism (frosted glass panels) as a default aesthetic.
- Default dark-mode-via-pure-black (`#000`) or default light-mode-via-pure-white (`#FFF`) without an intentional tint.

## 2. Required method: explore before you build

For any new design direction (a new `DESIGN.md`, a mockup, a component system):

1. **Do not produce one final design first.** Present **5 genuinely different directions** — different type pairing, color palette, spacing rhythm, and layout architecture, not 5 palette swaps of the same layout.
2. For each direction, state in one or two lines:
   - The typeface pairing (e.g. "geometric sans-serif display + monospace body" or "brutalist display + clean grotesque") and why it fits the brief.
   - The color palette and the reasoning behind it (mood, contrast, brand fit) — not just hex codes.
3. Wait for the user to pick one, or a hybrid of two, before producing a full build-out.

## 3. Typographic and layout quality bar

- Build hierarchy with tracking (letter-spacing), line-height, and weight contrast — not font-size alone.
- Use negative space deliberately; don't fill every region just because it's empty.
- Target the feel of a real shipped product or an edited editorial page, not a template.

## 4. Project-specific identity (fill in if/when this repo adopts one)

If a maintainer sets fixed brand tokens for this repo's own site/README assets, record them here so agents stop re-deriving them each time, e.g.:

```
Base background: <hex>
Accent: <hex>
Display font: <name>
Mono/code font: <name>
```

(Currently unset — no fixed identity has been chosen yet. Until it is, follow the exploration method in §2 for anything new.)

## 5. When given a moodboard

If the user pastes a screenshot of a site/app/video they like instead of describing colors and fonts, treat that as the brief: extract the typographic spirit, spacing balance, and color atmosphere from the image, then still produce 5 distinct directions referencing it — don't just clone it 1:1.
