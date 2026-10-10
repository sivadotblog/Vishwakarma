---
paths:
  - "apps/web/**"
---

# Web conventions

- Content pages are Markdown/MDX in `apps/web/src/content/docs/`; reach for a custom `.astro` component only when Starlight's built-ins can't do it.
- Every page needs `title` and `description` frontmatter.
- TypeScript is `astro/tsconfigs/strict`; no `any` without a comment saying why.
- Keep the site static (no SSR adapter) unless an issue explicitly requires it.
