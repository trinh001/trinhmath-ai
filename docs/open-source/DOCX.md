# docx review

## Identity

- Official repository: https://github.com/dolanmiu/docx
- Local review clone: `external/docx`
- Reviewed commit: `fda088d1da3772474bec9c40feb210cebb304f97` (2026-09-19)
- License: MIT (`external/docx/LICENSE`)
- Reviewed package version: 9.7.1
- Stated capability: declarative JavaScript/TypeScript generation and
  modification of `.docx` files for Node.js and browsers.

## Principal dependencies

The published package currently depends on `hash.js`, `jszip`, `nanoid`, `xml`
and `xml-js`; the repository's development toolchain is much larger but is not
needed by consumers. It targets Node 10+ according to its metadata.

## TrinhMath fit and recommendation

This is a reasonable future replacement or companion for Word export when
TrinhMath has a deliberate TypeScript/Node export boundary. It may help create
teacher-reviewed worksheets and preserve a clean document-generation layer.

Use the published npm package in a new, isolated export service/app only after
the target layout, font embedding, Vietnamese typography, formula/OMML strategy
and test fixtures are agreed. Do not copy repository source into the current
Python app and do not build this into the existing PDF export path now.

## Risks and controls

- **Equation fidelity:** `.docx` equation and MathML/OMML requirements must be
  tested with Word and LibreOffice; visual preview alone is insufficient.
- **Untrusted content:** sanitize file names and never allow generated archives
  to overwrite source documents.
- **Release bypass:** export must select only variants that already pass the
  existing release validator; it must not serialize drafts into student output.
- **Dependency updates:** pin the npm version and review lockfile changes.

## Status

Future export-library candidate only; no JavaScript runtime, package or export
code was added.
