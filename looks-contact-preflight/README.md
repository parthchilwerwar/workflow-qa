# Contact-path preflight

A zero-dependency Python check for a specific editorial failure: policy pages that send readers around a loop without a reachable contact email.

## Why this exists

On September 13, 2026, the public corrections flow on looksmaxxing.guide led from [Editorial Standards](https://looksmaxxing.guide/en/editorial-standards/) to [Terms](https://looksmaxxing.guide/en/legal/terms/), then [About](https://looksmaxxing.guide/en/about/), then back to Terms. The rendered main content of those three pages contained no email link or contact form. This observation is scoped to those pages, not a claim that no contact channel exists anywhere.

For an evidence-led publisher, readers need a working way to flag errors. A normal HTTP status checker misses this problem because all the pages load.

## Run in under a minute

Requires Python 3.10 or later. No pip install, API key, network or credentials.

From this folder:

```bash
python3 -m unittest -v

# Expected: JSON ok=false, exit 1 (the loop has no mailbox)
python3 contact_preflight.py fixtures/broken --page /en/editorial-standards/ --page /en/legal/terms/ --page /en/about/

# Expected: JSON ok=true, exit 0 (each route reaches the synthetic mailbox)
python3 contact_preflight.py fixtures/fixed --page /en/editorial-standards/ --page /en/legal/terms/ --page /en/about/
```

On Windows, use `py` or `python` instead of `python3`.

The fixtures are invented minimal HTML, not copied site pages. `editor@example.org` is a reserved example-domain address, not a real editorial contact.

## Use on a generated site

```bash
python3 contact_preflight.py ./dist --origin https://looksmaxxing.guide \
  --page /en/editorial-standards/ \
  --page /en/legal/terms/ \
  --page /en/about/
```

Pass every policy/contact route you want followed. `/en/about/` maps to `dist/en/about/index.html`; `.html` routes map directly. Root-relative, relative and same-origin absolute links are supported. Query strings and fragments on links do not change the route. Selected route arguments must be plain paths.

The checker reads only the selected UTF-8 files, builds a graph from their `<main>` anchors, and finds the shortest path to a plausible single-address `mailto:` link. It never follows a link over the network and never edits inputs. Each file is limited to 2 MB and each run to 100 selected routes. Symlinks cannot escape the build directory.

- **Exit 0:** each selected page can reach an email link through selected pages.
- **Exit 1:** at least one route needs review. The JSON includes visited routes; loops terminate safely.
- **Exit 2:** invalid arguments/input, missing files, unsupported markup or unsafe paths. Invalid CLI syntax uses argparse's stderr output; input errors use JSON.

## How to fix the observed flow

The site owner should confirm a real monitored corrections mailbox, define it once in shared site configuration, and render a visible contact link directly in the About contact section. Terms and Editorial Standards should point straight to that section or use the same shared contact component. Do not guess an address or ship the fixture address. Verify the mailbox separately before publishing.

Then run this check against the generated policy pages and add it to the site's build check. This prototype is a regression check, not a deployed fix to the production website.

## Deliberate limits

- A reachable `mailto:` is not proof of mailbox ownership, delivery, monitoring or response time.
- Web forms are reported for manual review; this script does not claim to submit or validate them.
- Footer/navigation, script, style, template, `hidden` and `aria-hidden=true` content is excluded. External CSS visibility and accessible link naming require a real browser check.
- Only selected pages participate. An unselected contact page can cause a review finding; add it explicitly with `--page`.
- Static generated HTML only: no JavaScript execution, obfuscated email decoding or arbitrary HTML5 error recovery. Missing `<main>` is an input error instead of silently accepting a footer email.
- No medical claims, health recommendations, user tracking, or site-content rewriting.

## Verification

The included tests exercise the real parser, graph traversal and CLI: cycles, relative links, external lookalike domains, hidden/footer addresses, void tags, invalid addresses, manual-review forms, missing main/files, traversal/symlink escapes and JSON exit codes. The broken/fixed CLI fixtures are both runnable locally.

This folder is standalone on an isolated branch. It does not depend on, alter or claim to validate the parent repository's separate QA case study.

Copyright 2026 The Flywheel Corporation. No open-source license is granted by this prototype.
