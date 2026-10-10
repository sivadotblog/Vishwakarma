# Factory run log: issue #5

## Summary

Rebrand the Astro Starlight documentation site in apps/web to Vishwakarma by updating configuration, landing page content, and sidebar navigation.

Reviewer verdict: approve.

## Classification

- type: feature
- priority: medium
- complexity: small
- affected_area: apps/web

## Analysis

### Problem

The Astro Starlight docs site in apps/web contains default template branding ('My Docs', 'Welcome to Starlight', Houston mascot image, and links to astro.build/starlight.astro.build). It needs to be rebranded to Vishwakarma (the autonomous software factory in this repo) by updating configuration, landing page content, sidebar navigation, and guide file paths while maintaining base path compatibility under /Vishwakarma.

### Approach

Update Starlight config in apps/web/astro.config.mjs (title, social link, sidebar slug/label, and header comment removal), move example.md to getting-started.md via git mv, delete the Houston graphic asset, rewrite the index.mdx landing page with Vishwakarma copy and cards, and update description frontmatter in reference/example.md to remove template branding.

### Plan

1. Run make setup-web to ensure Node dependencies in apps/web/node_modules are installed.
2. Use git mv apps/web/src/content/docs/guides/example.md apps/web/src/content/docs/guides/getting-started.md to relocate the guide page.
3. Use git rm apps/web/src/assets/houston.webp to remove the Houston mascot image asset.
4. Update apps/web/astro.config.mjs: set title: 'Vishwakarma', GitHub social href: 'https://github.com/sivadotblog/Vishwakarma', sidebar guide entry label: 'Getting started' and slug: 'guides/getting-started', and remove top comment containing 'astro.build'.
5. Update apps/web/src/content/docs/guides/getting-started.md frontmatter: set title: Getting started and description: Getting started with Vishwakarma autonomous software factory.
6. Update apps/web/src/content/docs/reference/example.md frontmatter description to replace 'Starlight' with 'Vishwakarma'.
7. Update apps/web/src/content/docs/index.mdx: update frontmatter (title: Vishwakarma, description, tagline), remove hero image, keep single primary action pointing to guides/getting-started/, and replace 'Next steps' CardGrid with Vishwakarma summary copy and three feature cards ('How work arrives', 'What you get back', 'Human in the loop').
8. Run npm run format -w web to apply Prettier formatting.
9. Run make check-web to run lint, typecheck (astro check), and build.
10. Verify build outputs (apps/web/dist/guides/getting-started/index.html exists and contains /Vishwakarma/guides/getting-started/) and run grep verification for zero legacy branding matches.

### Acceptance criteria

- [ ] Site title in apps/web/astro.config.mjs is "Vishwakarma", and the GitHub social icon links to https://github.com/sivadotblog/Vishwakarma.
- [x] grep -rniE "astro\.build|withastro|houston|Welcome to Starlight|Starlight docs" apps/web/src apps/web/astro.config.mjs returns nothing.
- [ ] Home page (apps/web/src/content/docs/index.mdx) has no hero image, one "Get started" action linking to guides/getting-started/, and Vishwakarma content in place of "Next steps".
- [ ] apps/web/src/content/docs/guides/getting-started.md exists with frontmatter title "Getting started"; apps/web/src/content/docs/guides/example.md no longer exists; sidebar config points to slug guides/getting-started.
- [ ] In build output (make check-web), apps/web/dist/guides/getting-started/index.html exists and contains the sidebar link /Vishwakarma/guides/getting-started/.
- [ ] make check-web passes completely (Prettier, astro check, build).

## Implementation

Branch `factory/issue-5-rebrand-docs` (base `main`).

### Change summary

- `apps/web/astro.config.mjs`: Updated title to 'Vishwakarma', social GitHub link to 'https://github.com/sivadotblog/Vishwakarma', sidebar guide entry to 'Getting started' ('guides/getting-started'), and removed astro.build reference comment.
- `apps/web/src/assets/houston.webp`: Deleted Houston mascot image as part of removing Astro branding assets.
- `apps/web/src/content/docs/guides/getting-started.md`: Renamed example.md to getting-started.md via git mv and updated frontmatter title to 'Getting started' and description for Vishwakarma.
- `apps/web/src/content/docs/index.mdx`: Updated frontmatter title, description, tagline, and action link ('guides/getting-started/'), removed mascot hero image reference and Starlight docs link, and replaced 'Next steps' CardGrid with Vishwakarma overview content.
- `apps/web/src/content/docs/reference/example.md`: Updated frontmatter description from 'Starlight docs site' to 'Vishwakarma docs site'.

### Verification

- `make setup-web`: npm ci installed 371 packages successfully.
- `grep -rniE "astro\.build|withastro|houston|Welcome to Starlight|Starlight docs" apps/web/src apps/web/astro.config.mjs`: Returned no matches (exit code 1).
- `make check-web`: Prettier formatting check passed, astro check reported 0 errors / 0 warnings, astro build generated static site successfully.
- `test -f apps/web/dist/guides/getting-started/index.html && grep -o '/Vishwakarma/guides/getting-started/' apps/web/dist/guides/getting-started/index.html`: Confirmed output file exists and sidebar link includes /Vishwakarma/guides/getting-started/.
- `make check`: Ruff lint & format, MyPy strict typecheck, Pytest (114 tests passed), and web checks all passed cleanly.

### Deviations

- None

## Review

Verdict: **approve**

The implementation rebrands the Astro Starlight documentation site to Vishwakarma completely and cleanly. All starter links to Astro/Starlight and Houston mascot assets were removed, the guide was renamed to `getting-started.md` with updated sidebar navigation, and all verification checks (`make check-web` and `make check`) passed without issues.

### Criteria results

- pass: Site title is "Vishwakarma"; the GitHub icon links to https://github.com/sivadotblog/Vishwakarma. (`apps/web/astro.config.mjs` defines `title: 'Vishwakarma'` and social link `href: 'https://github.com/sivadotblog/Vishwakarma'`.)
- pass: grep -rniE "astro\.build|withastro|houston|Welcome to Starlight|Starlight docs" apps/web/src apps/web/astro.config.mjs returns nothing. (Executed regex search across `apps/web/src` and `apps/web/astro.config.mjs`; returned zero matches (exit code 1).)
- pass: Home page has no hero image, one Get started action linking to guides/getting-started/, and Vishwakarma content in place of "Next steps". (`apps/web/src/content/docs/index.mdx` has no hero `image:`, single hero action linking to `guides/getting-started/`, and Vishwakarma feature cards replacing "Next steps".)
- pass: guides/getting-started.md exists with title "Getting started"; guides/example.md no longer exists; the sidebar points at the new slug. (File `apps/web/src/content/docs/guides/getting-started.md` exists with frontmatter `title: Getting started`, `example.md` is removed, and `apps/web/astro.config.mjs` sidebar points to `slug: 'guides/getting-started'`.)
- pass: In the build output, apps/web/dist/guides/getting-started/index.html exists and the sidebar link in it is /Vishwakarma/guides/getting-started/. (`apps/web/dist/guides/getting-started/index.html` was generated during build and contains sidebar link `<a href="/Vishwakarma/guides/getting-started/">`.)
- pass: make check-web passes (Prettier, astro check, build). (`make check-web` ran successfully (Prettier formatting check passed, `astro check` returned 0 errors/warnings, and `astro build` completed). `make check` also passed across the monorepo.)
