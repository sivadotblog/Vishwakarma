---
name: starlight
description: Work on the Astro Starlight frontend in apps/web — add or edit docs pages, change the sidebar or site config, use Starlight components (Card, Tabs, Aside, Steps), override components, add assets, or add npm packages to the web app. Use for any change under apps/web.
---

# Starlight in this repo

`apps/web` is an Astro + Starlight site, the npm workspace named `web`. Run everything from the repo root with `-w web`.

## Layout

- `astro.config.mjs` — site title, `sidebar`, social links, Starlight options.
- `src/content/docs/**` — every `.md`/`.mdx` file is a page; its path is its URL slug (`guides/example.md` → `/guides/example/`).
- `src/content.config.ts` — content collection schema (`docsLoader` + `docsSchema`). Extend the schema here if pages need extra frontmatter.
- `src/assets/` — images referenced from content (optimized); `public/` — files served as-is.

## Common tasks

**New page:** create `src/content/docs/<section>/<slug>.md` with frontmatter `title:` (required) and `description:`. If the section's sidebar group uses `autogenerate`, you're done; otherwise add `{ label, slug: '<section>/<slug>' }` to that group in `astro.config.mjs`.

**Components:** use `.mdx` and import from `@astrojs/starlight/components`:

```mdx
import { Aside, Card, CardGrid, Steps, Tabs, TabItem } from '@astrojs/starlight/components';

<Aside type="caution">Heads up.</Aside>
```

**Override a built-in component:** add `components: { Footer: './src/components/Footer.astro' }` to the `starlight()` options — only when config options can't do it.

**Dependencies:** `npm install -w web <pkg>` (dev: add `-D`). Never edit `package-lock.json` by hand. Integrations: `npx -w web astro add <name>`.

## Dev server

Start it in the background so it doesn't block: `npx -w web astro dev --background`; manage with `astro dev status|logs|stop`.

## Docs

Before non-trivial work, check <https://starlight.astro.build> (guides, components, configuration reference) and <https://docs.astro.build> — Starlight changes fast, don't rely on memory for config keys.

## Verify

`make check` (runs `astro check` and a full build — broken links in the sidebar fail the build).
