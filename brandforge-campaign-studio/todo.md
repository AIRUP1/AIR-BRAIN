# BrandForge Campaign Studio — Feature Tracker

## Completed Capabilities

- [x] Build niche intake, three-route strategy engine, and Brand Kit lock.
- [x] Generate deck, website, email, POS, logo, visual, and TTS prompt assets.
- [x] Add image recognition, OCR, upscale workflow, and interactive website/email preview modes.
- [x] Add campaign economics, AI-video briefs, ManimCE script exports, compliant TTS directions, and social distribution packs.
- [x] Add a POS Operations workspace that turns a generated POS Menu into a category-aware register catalog.
- [x] Add editable quote tickets with line quantities, tax, tip, immutable cents arithmetic, and receipt-context fields.
- [x] Add a database-backed POS quote ledger with ticket number, status, totals, and a non-sensitive JSON payload.
- [x] Add plain-text quote receipt export clearly marked as not a payment receipt.
- [x] Add a Deluxe-oriented merchant onboarding package for catalog, tax, location, and receipt mapping.
- [x] Add an Eliot by Deluxe activation panel that detects server-side credential readiness and documents hosted-payment versus Mobile POS SDK requirements.
- [x] Preserve a strict payment boundary: no card, EMV, wallet, or PCI-sensitive data is accepted or stored in BrandForge.
- [x] Validate POS catalog conversion, quote calculations, quote persistence, receipt export, non-sensitive Deluxe mapping, TypeScript, unit tests, production build, and live browser workflow.

## Intentionally Deferred Merchant Activation

- [x] Deferred by project owner: do not add `DELUXE_CLIENT_ID`, `DELUXE_CLIENT_SECRET`, or `DELUXE_PARTNER_TOKEN` to the current release.
- [x] Deferred by project owner: do not request or infer the merchant’s approved Deluxe payment product.
- [x] Deferred by project owner: do not build a bearer-token, transaction, or webhook flow without the merchant-specific Deluxe API contract.
- [x] Deferred by project owner: do not connect a sandbox or simulate a merchant-authorized payment test.

The application remains useful without merchant credentials: it produces catalogs, quotes, quote receipts, an operational ledger, and a non-sensitive Deluxe onboarding package. Live payment capture stays intentionally unavailable until a merchant-provisioned Deluxe integration is authorized.
