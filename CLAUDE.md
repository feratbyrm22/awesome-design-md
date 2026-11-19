# awesome-design-md
Status: live — public fork of https://github.com/VoltAgent/awesome-design-md

## What it is
A curated list of DESIGN.md files (Google Stitch format). Each one describes the
visual language of a well-known website so AI agents can generate consistent UI.
Docs only: no build, no app code, no dependencies.

## Layout
- README.md — the public list. Entries sit under `## Collection`, grouped by
  category (`###` headings); each links to `https://getdesign.md/<slug>/design-md`.
- design-md/<slug>/DESIGN.md — the design system: YAML front matter, then `##` sections.
- design-md/<slug>/README.md — 5-line stub pointing to getdesign.md.
- CONTRIBUTING.md — contributor rules (open an issue first).
- .github/ISSUE_TEMPLATE/design-md-request.yml — request form.

## Commands
- Entry count: `ls -d design-md/*/ | wc -l`
- Badge count: `grep -o 'DESIGN.md%20count-[0-9]*' README.md`
- Folders vs README links:
  `diff <(grep -o 'getdesign.md/[^/]*/design-md' README.md | cut -d/ -f2 | sort) <(ls design-md | sort)`
- Missing stubs: `for d in design-md/*/; do [ -f "$d/README.md" ] || echo "$d"; done`
- Section outline of one file: `grep -n '^## ' design-md/<slug>/DESIGN.md`

## Critical traps
- Slug = folder name = getdesign.md URL segment. Keep all three identical
  (dots are valid: `linear.app`, `mistral.ai`).
- A new entry touches 3 places: the folder (DESIGN.md + README.md stub), one line
  in the right README category, and the count badge in README.md.
- Some front-matter names are altered on purpose (`Stripi`, `Slacc`, `Supabaze`…,
  the `*-Inspired-design-analysis` files). Do not "fix" them.
- DESIGN.md files run up to ~45 KB. Grep or read one section, not the whole file.
- Colors, fonts and sizes must come from the live site. Never invent tokens.
- Do not touch sponsor/banner blocks in README.md or `.github/FUNDING.yml` unless asked.
- Upstream does not accept new-DESIGN.md PRs; only fixes to existing files.

## Language
- Write everything in English: CLAUDE.md, todo.md, notes.md, comments, commit messages.
- Reply to the user in Turkish.

## Doc rules
- Budget: this file ≤ 8 KB. If an addition would exceed it, compress first or move
  detail to notes.md.
- Replace outdated lines in place. No dated "changed on…" notes; history is git log.
- No narratives here, only one-line rules. Stories go to notes.md or the commit message.
- No `@import`; reference other files by plain path.
- Write the command that shows a number, not the number.
- Every root-level doc (.md) must be listed in the index below.
- todo.md: delete finished items; do not tick them and leave them.

## Doc index (when to open)
- todo.md — open work and known inconsistencies; check before starting.
- notes.md — DESIGN.md format, entry workflow, past decisions; open when adding
  or editing an entry.
- CONTRIBUTING.md — open when preparing a PR to upstream.
