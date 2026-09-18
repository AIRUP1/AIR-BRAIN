# BrandForge Campaign Studio

A full-stack cinematic niche-marketing campaign studio.

## Application directory

The deployable project lives in `brandforge-campaign-studio/`.

## Delivered capabilities

- Live niche intake → three structured strategic directions through a Claude-capable model.
- Brand Kit locking and persistent projects, strategy options, assets, and asset version records.
- Structured deck, launch-site, email, POS, and self-contained SVG-logo generation with three selectable layout variants.
- Native visual generation routing, photo recognition/OCR, safe image upscaling, and brand-bound TTS prompt direction.

## Local development

```bash
cd brandforge-campaign-studio
pnpm install
pnpm dev
```

The managed runtime injects secure LLM, image, object-storage, and database credentials. A Vercel migration requires equivalent environment variables and a compatible server deployment configuration.
