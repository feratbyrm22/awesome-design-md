# Notes

## DESIGN.md format
- Starts with YAML front matter between `---` lines. Top-level keys seen in v2 files:
  `version` (currently `alpha`), `name`, `description`, `colors`, `typography`,
  `rounded`, `spacing`, `components`.
- `colors` is a flat map of semantic token → hex (e.g. `primary`, `ink`, `canvas`,
  `hairline`). `typography` maps a style name (e.g. `display-xl`) to `fontFamily`,
  `fontSize`, `fontWeight`, `lineHeight`, `letterSpacing`, optional `fontFeature`.
- Body sections (`##`) in v2 files: Overview, Colors, Typography, Layout,
  Elevation & Depth, Shapes, Components, Do's and Don'ts, Responsive Behavior,
  Iteration Guide. Check one file with `grep -n '^## '` before assuming.
- Spec: https://stitch.withgoogle.com/docs/design-md/specification/

## Naming
- Newer files use `<Brand>-Inspired-design-analysis` as `name`, and some brand
  names are deliberately misspelled (Stripi, Slacc, Supabaze, Sentri, Shopifi,
  Superhumon). This keeps them as "inspired" analyses rather than official brand
  material. Older files use `<Brand>-design-analysis`.
- Retro entries carry a year in the slug: `dell-1996`, `nintendo-2001`. They go
  under the README category "Retro Web · DESIGN.md Nostalgia".

## Adding or editing an entry
1. Create `design-md/<slug>/DESIGN.md` from live-site values.
2. Copy the README.md stub from any other entry and change the name and slug.
3. Add one line to the matching README category:
   `- [**Name**](https://getdesign.md/<slug>/design-md) - One-line summary.`
4. Bump the count badge (`DESIGN.md%20count-N`) to match `ls -d design-md/*/ | wc -l`.
5. Run the "Folders vs README links" command from CLAUDE.md; it should print nothing.

## Slack
- Commit da06867 removed the old slack folder and 3440bf2 removed its README link.
- beec066 re-added `design-md/slack/DESIGN.md` as v2 and e06a966 renamed it
  (`Slacc-Inspired`), but no stub or README line came back. Whether that was on
  purpose is unknown; tracked in todo.md.

## Why this doc layout
- CLAUDE.md is loaded into every session, so it holds a small map only.
  todo.md and notes.md are read on demand. English text uses about half the
  tokens of the same text in Turkish, so docs are in English and replies are
  in Turkish.
