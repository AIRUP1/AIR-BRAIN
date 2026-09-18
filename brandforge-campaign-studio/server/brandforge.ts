import { invokeLLM, listLLMModels } from "./_core/llm";
import { generateImage, listImageModels } from "./_core/imageGeneration";
import { storagePut } from "./storage";

export type Intake = { niche: string; market: string; budget?: string; audience?: string; tone?: string };
export type BrandKitInput = { name: string; palette: string[]; fonts: { heading: string; body: string }; voice: string; tagline: string; offer: string };
export type StrategyOption = {
  id: number; positioning: string; target_customer: string; core_offer: string;
  campaign: { name: string; big_idea: string; channels: string[]; "30_day_plan": string[] };
  strategy: { pricing_angle: string; acquisition: string[]; retention: string[]; kpis: string[] };
  brand: { name_ideas: string[]; tagline: string; voice: string; palette: string[]; fonts: { heading: string; body: string }; logo_direction: string };
};
export type PhotoAnalysis = {
  summary: string; scene: string; objects: string[]; people: string[]; mood: string;
  visual_quality: string; extracted_text: string[]; marketing_opportunities: string[]; suggested_asset: string;
};

export const STRATEGY_SYSTEM_PROMPT = `You are a niche marketing strategist. Given a niche and market, return ONLY valid JSON:
{"options":[{"id":1,"positioning":"","target_customer":"","core_offer":"","campaign":{"name":"","big_idea":"","channels":[],"30_day_plan":[]},"strategy":{"pricing_angle":"","acquisition":[],"retention":[],"kpis":[]},"brand":{"name_ideas":[],"tagline":"","voice":"","palette":["#hex","#hex","#hex","#hex","#hex"],"fonts":{"heading":"","body":""},"logo_direction":""}}]}
Return exactly 3 options that differ meaningfully (premium / value / disruptor). No generic advice. Be specific to the niche and market.`;

const strategyJsonSchema = {
  type: "object", properties: { options: { type: "array", minItems: 3, maxItems: 3, items: { type: "object", properties: {
    id: { type: "integer" }, positioning: { type: "string" }, target_customer: { type: "string" }, core_offer: { type: "string" },
    campaign: { type: "object", properties: { name: { type: "string" }, big_idea: { type: "string" }, channels: { type: "array", items: { type: "string" } }, "30_day_plan": { type: "array", items: { type: "string" } } }, required: ["name", "big_idea", "channels", "30_day_plan"], additionalProperties: false },
    strategy: { type: "object", properties: { pricing_angle: { type: "string" }, acquisition: { type: "array", items: { type: "string" } }, retention: { type: "array", items: { type: "string" } }, kpis: { type: "array", items: { type: "string" } } }, required: ["pricing_angle", "acquisition", "retention", "kpis"], additionalProperties: false },
    brand: { type: "object", properties: { name_ideas: { type: "array", items: { type: "string" } }, tagline: { type: "string" }, voice: { type: "string" }, palette: { type: "array", items: { type: "string" }, minItems: 5, maxItems: 5 }, fonts: { type: "object", properties: { heading: { type: "string" }, body: { type: "string" } }, required: ["heading", "body"], additionalProperties: false }, logo_direction: { type: "string" } }, required: ["name_ideas", "tagline", "voice", "palette", "fonts", "logo_direction"], additionalProperties: false },
  }, required: ["id", "positioning", "target_customer", "core_offer", "campaign", "strategy", "brand"], additionalProperties: false } } }, required: ["options"], additionalProperties: false,
};
const photoAnalysisSchema = {
  type: "object", properties: {
    summary: { type: "string" }, scene: { type: "string" }, objects: { type: "array", items: { type: "string" } }, people: { type: "array", items: { type: "string" } }, mood: { type: "string" }, visual_quality: { type: "string" }, extracted_text: { type: "array", items: { type: "string" } }, marketing_opportunities: { type: "array", items: { type: "string" } }, suggested_asset: { type: "string" },
  }, required: ["summary", "scene", "objects", "people", "mood", "visual_quality", "extracted_text", "marketing_opportunities", "suggested_asset"], additionalProperties: false,
};
const assetSchemas: Record<string, Record<string, unknown>> = {
  deck: { type: "object", properties: { slides: { type: "array", items: { type: "object", properties: { layout_id: { type: "string" }, title: { type: "string" }, body: { type: "string" }, cta: { type: "string" } }, required: ["layout_id", "title", "body", "cta"], additionalProperties: false } } }, required: ["slides"], additionalProperties: false },
  website: { type: "object", properties: { pages: { type: "array", items: { type: "object", properties: { slug: { type: "string" }, sections: { type: "array", items: { type: "object", properties: { layout_id: { type: "string" }, type: { type: "string" }, headline: { type: "string" }, body: { type: "string" }, cta: { type: "string" } }, required: ["layout_id", "type", "headline", "body", "cta"], additionalProperties: false } } }, required: ["slug", "sections"], additionalProperties: false } } }, required: ["pages"], additionalProperties: false },
  email: { type: "object", properties: { templates: { type: "array", minItems: 3, maxItems: 3, items: { type: "object", properties: { name: { type: "string" }, subject: { type: "string" }, blocks: { type: "array", items: { type: "object", properties: { layout_id: { type: "string" }, type: { type: "string" }, copy: { type: "string" } }, required: ["layout_id", "type", "copy"], additionalProperties: false } } }, required: ["name", "subject", "blocks"], additionalProperties: false } } }, required: ["templates"], additionalProperties: false },
  pos: { type: "object", properties: { categories: { type: "array", items: { type: "object", properties: { name: { type: "string" }, layout_id: { type: "string" }, items: { type: "array", items: { type: "object", properties: { name: { type: "string" }, price: { type: "string" }, description: { type: "string" } }, required: ["name", "price", "description"], additionalProperties: false } } }, required: ["name", "layout_id", "items"], additionalProperties: false } }, receipt_layout: { type: "string" } }, required: ["categories", "receipt_layout"], additionalProperties: false },
  logo: { type: "object", properties: { concepts: { type: "array", items: { type: "object", properties: { type: { type: "string" }, svg: { type: "string" } }, required: ["type", "svg"], additionalProperties: false } } }, required: ["concepts"], additionalProperties: false },
};

function cleanJson(content: unknown) { return (typeof content === "string" ? content : "").replace(/^```json\s*/i, "").replace(/```$/i, "").trim(); }
async function selectTextModel(preferred: "claude" | "gemini" = "claude") {
  try { const { data } = await listLLMModels(); return data.find((model) => model.id.toLowerCase().includes(preferred))?.id ?? data.find((model) => model.id.toLowerCase().includes("claude"))?.id ?? data[0]?.id; } catch { return undefined; }
}
function safeName(text: string) { return text.replace(/[^a-z0-9]/gi, " ").split(" ").filter(Boolean).map((word) => word[0]?.toUpperCase() + word.slice(1).toLowerCase()).join(" "); }

export function strategyFallback(input: Intake): StrategyOption[] {
  const niche = input.niche || "Local service"; const market = input.market || "your market"; const root = safeName(niche.split(",")[0]) || "Local";
  return [
    { id: 1, positioning: `White-glove ${niche} built for busy households in ${market}.`, target_customer: "Time-poor, quality-first homeowners who value convenience and pristine results.", core_offer: "Signature service with priority scheduling, concierge communication, and a satisfaction-backed finish.", campaign: { name: "The Standard, Elevated", big_idea: `Turn the ${market} customer’s highest-friction task into a calm, high-standard ritual.`, channels: ["Google Search", "Premium neighborhood partnerships", "Before/after social"], "30_day_plan": ["Week 1: launch proof-led landing page", "Week 2: activate premium local partners", "Week 3: retarget high-intent visits", "Week 4: convert first jobs into memberships"] }, strategy: { pricing_angle: "Anchor with a premium signature tier, then make membership the sensible upgrade.", acquisition: ["Geo-targeted search around high-intent phrases", "Concierge referral offer with luxury apartments", "Short-form transformation reels"], retention: ["48-hour aftercare check-in", "Seasonal maintenance membership", "VIP priority calendar"], kpis: ["Qualified lead cost", "Signature-to-membership rate", "90-day repeat rate"] }, brand: { name_ideas: [`${root} Reserve`, `${root} Atelier`, `${root} Standard`], tagline: "A higher standard of done.", voice: "Confident, composed, exacting, quietly luxurious.", palette: ["#111827", "#F8F5EE", "#C9A86A", "#344054", "#FFFFFF"], fonts: { heading: "Cormorant Garamond", body: "DM Sans" }, logo_direction: "Editorial wordmark with a restrained monogram; generous spacing, one refined metallic accent." } },
    { id: 2, positioning: `The clear, reliable ${niche} choice for practical ${market} customers.`, target_customer: "Price-aware families and professionals who need an easy, trustworthy recurring solution.", core_offer: "Transparent menu pricing with fast booking, dependable arrival windows, and a value-packed maintenance plan.", campaign: { name: "More Done. Less Fuss.", big_idea: `Make ${niche} the easiest thing to cross off a ${market} customer’s list.`, channels: ["Google Business Profile", "Nextdoor", "SMS referral", "Local Facebook groups"], "30_day_plan": ["Week 1: publish price-first booking flow", "Week 2: collect first 20 reviews", "Week 3: launch neighbor referral credit", "Week 4: invite first-time buyers into maintenance plan"] }, strategy: { pricing_angle: "Show the starting price boldly; bundle extras into a visibly better-value package.", acquisition: ["Map-pack optimization with city modifiers", "Neighbor-to-neighbor referral credit", "Simple offer cards in community groups"], retention: ["Text reminders before seasonal needs", "Every-fourth-service credit", "Saved preferences for one-tap rebooking"], kpis: ["Booked job conversion", "Cost per booked job", "Recurring plan penetration"] }, brand: { name_ideas: [`${root} Ready`, `${root} Local`, `${root} Co.`], tagline: "The easy yes for your day.", voice: "Helpful, plainspoken, punctual, and friendly without hype.", palette: ["#132A13", "#F5F7F2", "#86B049", "#E8C547", "#FFFFFF"], fonts: { heading: "Archivo", body: "Inter" }, logo_direction: "Friendly geometric wordmark with a simple local-service symbol; strong readability on vehicles and mobile." } },
    { id: 3, positioning: `A bold, content-forward ${niche} brand designed to own attention in ${market}.`, target_customer: "Younger urban customers who respond to proof, speed, and visible transformation.", core_offer: "A high-impact transformation service with digital booking, shareable results, and a no-excuses service guarantee.", campaign: { name: "Reset the Ordinary", big_idea: `Make every ${niche} result in ${market} feel like a reveal worth sharing.`, channels: ["TikTok", "Instagram Reels", "Creator collaborations", "Paid social retargeting"], "30_day_plan": ["Week 1: launch visual identity and reveal format", "Week 2: seed creator transformations", "Week 3: run location-radiused paid social", "Week 4: release limited reset bundle"] }, strategy: { pricing_angle: "Lead with a magnetic hero package and time-boxed drop-style upgrades.", acquisition: ["Transformation-first short-form content", "Creator codes with local radius targeting", "Instant quote quiz with SMS conversion"], retention: ["Monthly reset drops", "Share-to-earn account credits", "Personalized refresh reminders"], kpis: ["Video-to-booking rate", "Cost per quote start", "Referral share rate"] }, brand: { name_ideas: [`${root} Reset`, `${root} Signal`, `${root} After`], tagline: "Make the after unforgettable.", voice: "Direct, kinetic, visually precise, and unapologetically modern.", palette: ["#160B31", "#F5F1FF", "#A3FF12", "#7C3AED", "#FF5C35"], fonts: { heading: "Space Grotesk", body: "Manrope" }, logo_direction: "High-contrast symbol that suggests motion or transformation; modular enough for social avatar and app icon." } },
  ];
}

export async function generateStrategy(input: Intake) {
  const model = await selectTextModel("claude");
  try {
    const response = await invokeLLM({ model, messages: [{ role: "system", content: STRATEGY_SYSTEM_PROMPT }, { role: "user", content: `Niche: ${input.niche}\nMarket: ${input.market}\nBudget: ${input.budget || "Not supplied"}\nAudience: ${input.audience || "Not supplied"}\nTone: ${input.tone || "Not supplied"}` }], response_format: { type: "json_schema", json_schema: { name: "niche_strategy_options", strict: true, schema: strategyJsonSchema } } });
    const parsed = JSON.parse(cleanJson(response.choices[0]?.message?.content));
    if (Array.isArray(parsed.options) && parsed.options.length === 3) return { options: parsed.options as StrategyOption[], model: model ?? "claude" };
    throw new Error("Unexpected strategy response");
  } catch { return { options: strategyFallback(input), model: "curated fallback" }; }
}

export function assetFallback(type: string, kit: BrandKitInput, variant: number) {
  const prefix = kit.name || "Brand"; const layouts = ["cinema-split", "signal-stack", "proof-grid"];
  if (type === "deck") return { slides: [{ layout_id: layouts[variant - 1], title: kit.tagline, body: `${kit.name} is built around ${kit.offer}.`, cta: "Open the campaign" }, { layout_id: "proof-grid", title: "The offer", body: kit.offer, cta: "Choose your service" }, { layout_id: "signal-stack", title: "Make the next move", body: `A ${kit.voice.toLowerCase()} invitation to book.`, cta: "Book now" }] };
  if (type === "website") return { pages: [{ slug: "/", sections: [{ layout_id: layouts[variant - 1], type: "hero", headline: kit.tagline, body: kit.offer, cta: "Get started" }, { layout_id: "proof-grid", type: "services", headline: "Built around what matters", body: kit.offer, cta: "View services" }, { layout_id: "signal-stack", type: "cta", headline: "Ready when you are.", body: kit.voice, cta: "Reserve your spot" }] }] };
  if (type === "email") return { templates: ["Welcome", "Promo", "Re-engage"].map((name) => ({ name, subject: `${prefix}: ${kit.tagline}`, blocks: [{ layout_id: layouts[variant - 1], type: "headline", copy: kit.tagline }, { layout_id: "proof-grid", type: "body", copy: kit.offer }, { layout_id: "signal-stack", type: "cta", copy: "Book your next service" }] })) };
  if (type === "pos") return { categories: [{ name: "Signature services", layout_id: layouts[variant - 1], items: [{ name: "The Essential", price: "$149", description: kit.offer }, { name: "The Complete", price: "$249", description: "The complete reset, built to last." }] }], receipt_layout: "minimal-brand-receipt" };
  return { concepts: ["wordmark", "icon", "combination"].map((type) => ({ type, svg: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 80"><rect width="240" height="80" rx="16" fill="${kit.palette[0] || "#111827"}"/><path d="M36 56 55 20l19 36-19-10z" fill="${kit.palette[2] || "#C9A86A"}"/><text x="88" y="49" fill="${kit.palette[1] || "#FFFFFF"}" font-family="Arial, sans-serif" font-size="21" font-weight="700">${prefix.replace(/[<&>]/g, "").slice(0, 12)}</text></svg>` })) };
}

export async function generateAsset(type: "deck" | "website" | "email" | "pos" | "logo", variant: number, kit: BrandKitInput) {
  const model = await selectTextModel("claude"); const layoutIds = ["cinema-split", "signal-stack", "proof-grid"];
  const system = `You generate content for a template engine. Use ONLY the Brand Kit provided.\nAsset type: ${type}\nVariant: ${variant}\nOutput ONLY JSON matching this schema: ${JSON.stringify(assetSchemas[type])}\nRules: copy in brand voice; real niche-specific services and prices; no lorem ipsum; every block must use an allowed layout ID from ${JSON.stringify(layoutIds)}.\nFor logo: return {"concepts":[{"type":"","svg":""}]} with valid, self-contained SVG using brand palette only.`;
  try {
    const response = await invokeLLM({ model, messages: [{ role: "system", content: system }, { role: "user", content: JSON.stringify({ brand_kit: kit }) }], response_format: { type: "json_schema", json_schema: { name: `${type}_asset`, strict: true, schema: assetSchemas[type] } } });
    return { payload: JSON.parse(cleanJson(response.choices[0]?.message?.content)), provider: model ?? "claude" };
  } catch { return { payload: assetFallback(type, kit, variant), provider: "curated fallback" }; }
}

export async function createCampaignVisual(kit: BrandKitInput, provider: string) {
  const prompt = `Create a cinematic brand campaign key visual for ${kit.name}. Subject: an abstract transformation moment that communicates ${kit.offer}. Composition: wide editorial 16:9 canvas, sculptural focal point on the right, large calm negative space on the left for website copy. Style: premium dimensional 3D material study, cinematic directional light, palette ${kit.palette.join(", ")}, sophisticated, no visible words. Constraints: no logos or readable text, no generic interface elements, strong visual depth.`;
  try {
    const available = await listImageModels();
    const match = available.models.find((item) => (item.id ?? "").toLowerCase().includes(provider.toLowerCase())) ?? available.models.find((item) => /nano|banana|gemini/i.test(item.id ?? "")) ?? available.models.find((item) => /gpt|dall/i.test(item.id ?? ""));
    const result = await generateImage({ prompt, ...(match?.model ? { model: match.model } : {}) });
    return { url: result.url ?? null, provider: match?.id ?? "native image generator", prompt };
  } catch { return { url: null, provider: "unavailable", prompt }; }
}

export async function upscaleImage(dataUrl: string) {
  const mimeType = /^data:([^;]+);base64,/.exec(dataUrl)?.[1] ?? "image/jpeg";
  const result = await generateImage({ prompt: "Restore and upscale this image to high resolution while preserving every detail exactly as in the original.", originalImages: [{ url: dataUrl, mimeType }] });
  return result.url ?? null;
}
function photoAnalysisFallback(): PhotoAnalysis { return { summary: "Reference stored for review. Run vision with an available multimodal model to complete scene and text extraction.", scene: "Image reference uploaded", objects: [], people: [], mood: "Unclassified", visual_quality: "Ready for enhancement review", extracted_text: [], marketing_opportunities: ["Use the reference to inform a brand-consistent hero or social visual."], suggested_asset: "Campaign visual" }; }
export async function recognizePhoto(dataUrl: string, filename: string) {
  const mimeType = /^data:([^;]+);base64,/.exec(dataUrl)?.[1] ?? "image/jpeg"; const raw = dataUrl.split(",")[1]; if (!raw) throw new Error("Image data could not be decoded");
  const stored = await storagePut(`references/${Date.now()}-${filename.replace(/[^a-zA-Z0-9._-]/g, "-")}`, Buffer.from(raw, "base64"), mimeType);
  const model = await selectTextModel("gemini");
  try {
    const response = await invokeLLM({ model, messages: [
      { role: "system", content: "You are a visual brand analyst. Inspect the supplied photo closely. Identify scene, objects, people only at a descriptive non-identifying level, visible text exactly as legible, quality signals, and specific ways this reference can become an ethical marketing asset. Never infer sensitive traits or private identity. Return only the requested JSON." },
      { role: "user", content: [{ type: "text", text: "Analyze this image for photo recognition and OCR." }, { type: "image_url", image_url: { url: dataUrl, detail: "high" } }] },
    ], response_format: { type: "json_schema", json_schema: { name: "photo_analysis", strict: true, schema: photoAnalysisSchema } } });
    return { previewUrl: stored.url, analysis: JSON.parse(cleanJson(response.choices[0]?.message?.content)) as PhotoAnalysis, provider: model ?? "gemini" };
  } catch { return { previewUrl: stored.url, analysis: photoAnalysisFallback(), provider: "vision fallback" }; }
}
export function makeTtsPrompt(kit: BrandKitInput) {
  const offer = kit.offer.split(/(?<=[.!?])\s+/)[0]?.trim() ?? kit.offer;
  const script = `${kit.name}. ${kit.tagline} ${offer} Reserve your moment today.`
    .split(/\s+/)
    .slice(0, 45)
    .join(" ");
  return `Speak in English with a confident, composed, warmly persuasive commercial delivery at a natural pace: ${script}`;
}
