import { ChangeEvent, useMemo, useState } from "react";
import { toast } from "sonner";
import {
  Aperture, ArrowUpRight, AudioLines, Box, Check, ChevronRight, Clapperboard, Copy,
  Download, Eye, FileText, ImageUp, Layers3, Loader2, Menu, Mic2, MousePointer2,
  Palette, ScanText, Sparkles, WandSparkles, Zap,
} from "lucide-react";
import { trpc } from "@/lib/trpc";
import AssetPreview from "@/components/AssetPreview";

type Option = {
  id: number; positioning: string; target_customer: string; core_offer: string;
  campaign: { name: string; big_idea: string; channels: string[]; "30_day_plan": string[] };
  strategy: { pricing_angle: string; acquisition: string[]; retention: string[]; kpis: string[] };
  brand: { name_ideas: string[]; tagline: string; voice: string; palette: string[]; fonts: { heading: string; body: string }; logo_direction: string };
};
type Kit = { name: string; palette: string[]; fonts: { heading: string; body: string }; voice: string; tagline: string; offer: string };
type Asset = { type: string; variant: number; provider: string; payload: Record<string, unknown> };
type PhotoResult = { previewUrl: string; analysis: { summary: string; scene: string; objects: string[]; people: string[]; mood: string; visual_quality: string; extracted_text: string[]; marketing_opportunities: string[]; suggested_asset: string }; provider: string };

const initialKit: Kit = {
  name: "DFW Detail Reserve",
  palette: ["#111827", "#F8F5EE", "#C9A86A", "#344054", "#FFFFFF"],
  fonts: { heading: "Cormorant Garamond", body: "DM Sans" },
  voice: "Confident, composed, exacting, quietly luxurious.",
  tagline: "A higher standard of done.",
  offer: "Signature mobile detailing with priority scheduling and a satisfaction-backed finish.",
};
const assetLabels = [
  { type: "deck", name: "Pitch deck", icon: Layers3, export: "Print-ready deck" },
  { type: "website", name: "Launch site", icon: Box, export: "Vercel-ready sections" },
  { type: "email", name: "Email flow", icon: FileText, export: "HTML / MJML blocks" },
  { type: "pos", name: "POS menu", icon: Menu, export: "Screen JSON" },
  { type: "logo", name: "Logo system", icon: Aperture, export: "SVG marks" },
];

function downloadFile(filename: string, content: string, mime = "application/json") {
  const blob = new Blob([content], { type: mime }); const url = URL.createObjectURL(blob); const link = document.createElement("a"); link.href = url; link.download = filename; link.click(); URL.revokeObjectURL(url);
}

export default function Home() {
  const [niche, setNiche] = useState("Mobile auto detailing");
  const [market, setMarket] = useState("DFW, Texas");
  const [budget, setBudget] = useState("$3,500/mo");
  const [audience, setAudience] = useState("Busy professionals and households with two or more vehicles");
  const [tone, setTone] = useState("Premium");
  const [options, setOptions] = useState<Option[]>([]);
  const [selected, setSelected] = useState<number>(2);
  const [projectId, setProjectId] = useState(0);
  const [brandKitId, setBrandKitId] = useState(0);
  const [kit, setKit] = useState<Kit>(initialKit);
  const [stage, setStage] = useState("01");
  const [assets, setAssets] = useState<Asset[]>([]);
  const [assetVariant, setAssetVariant] = useState(1);
  const [visualUrl, setVisualUrl] = useState<string | null>(null);
  const [visualProvider, setVisualProvider] = useState("Nano Banana");
  const [photo, setPhoto] = useState<PhotoResult | null>(null);
  const [photoData, setPhotoData] = useState<string | null>(null);
  const [ttsPrompt, setTtsPrompt] = useState("");
  const [previewAsset, setPreviewAsset] = useState<Asset | null>(null);

  const strategy = trpc.studio.generateStrategy.useMutation({
    onSuccess: (data) => { setOptions(data.options as Option[]); setProjectId(data.projectId); setSelected(2); setStage("02"); toast.success(`Three ${data.model} strategy directions are ready.`); },
    onError: () => toast.error("Strategy generation needs another attempt."),
  });
  const lockKit = trpc.studio.lockBrandKit.useMutation({
    onSuccess: (data) => { setBrandKitId(data.id); setStage("03"); toast.success("Brand Kit locked. Every asset now inherits this system."); },
    onError: () => { setBrandKitId(0); toast.success("Brand Kit locked in this session."); },
  });
  const assetGen = trpc.studio.generateAsset.useMutation({
    onSuccess: (data, input) => { setAssets((previous) => [{ type: input.type, variant: input.variant, provider: data.provider, payload: data.payload as Record<string, unknown> }, ...previous.filter((item) => item.type !== input.type)]); setStage("04"); toast.success(`${input.type} variant ${input.variant} is rendered.`); },
    onError: () => toast.error("Asset generation needs another attempt."),
  });
  const visualGen = trpc.studio.generateVisual.useMutation({
    onSuccess: (data) => { setVisualUrl(data.url); toast.success(data.url ? `Visual made with ${data.provider}.` : "Visual prompt prepared; choose another available model."); },
    onError: () => toast.error("Visual production needs another attempt."),
  });
  const recognition = trpc.studio.recognizePhoto.useMutation({
    onSuccess: (data) => { setPhoto(data as PhotoResult); toast.success(`Photo intelligence complete with ${data.provider}.`); },
    onError: () => toast.error("Photo analysis needs a smaller image or another attempt."),
  });
  const upscale = trpc.studio.upscaleVisual.useMutation({
    onSuccess: (data) => { if (data.url) setVisualUrl(data.url); toast.success(data.url ? "High-resolution version is ready." : "Upscale did not return a usable image."); },
    onError: () => toast.error("Upscaling needs another attempt."),
  });
  const voice = trpc.studio.makeVoicePrompt.useQuery(kit, { enabled: false });

  const selectedOption = useMemo(() => options.find((item) => item.id === selected), [options, selected]);
  const chooseOption = (option: Option) => {
    setSelected(option.id);
    setKit({ name: option.brand.name_ideas[0] || initialKit.name, palette: option.brand.palette, fonts: option.brand.fonts, voice: option.brand.voice, tagline: option.brand.tagline, offer: option.core_offer });
  };
  const generateAsset = (type: "deck" | "website" | "email" | "pos" | "logo") => assetGen.mutate({ brandKitId, type, variant: assetVariant, kit });
  const recognizeFile = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]; if (!file) return;
    if (!file.type.startsWith("image/")) { toast.error("Choose an image file."); return; }
    if (file.size > 3_000_000) { toast.error("Use an image under 3 MB for live recognition."); return; }
    const reader = new FileReader(); reader.onload = () => { const dataUrl = String(reader.result); setPhotoData(dataUrl); recognition.mutate({ dataUrl, filename: file.name }); }; reader.readAsDataURL(file);
  };
  const getVoicePrompt = async () => { const answer = await voice.refetch(); if (answer.data?.prompt) { setTtsPrompt(answer.data.prompt); navigator.clipboard?.writeText(answer.data.prompt); toast.success("TTS-ready direction copied."); } };

  return (
    <main className="studio-shell">
      <div className="ambient ambient-one" /><div className="ambient ambient-two" /><div className="grain" />
      <aside className="left-rail">
        <div className="brand-mark"><span className="brand-dot" /><span>BRAND<br />FORGE</span></div>
        <div className="rail-rule" />
        {[{ id: "01", name: "INTAKE", icon: MousePointer2 }, { id: "02", name: "STRATEGY", icon: Zap }, { id: "03", name: "BRAND", icon: Palette }, { id: "04", name: "ASSETS", icon: Layers3 }, { id: "05", name: "EXPORT", icon: ArrowUpRight }].map((item) => (
          <button key={item.id} className={`rail-item ${stage === item.id ? "is-active" : ""}`} onClick={() => setStage(item.id)}><item.icon size={16} /><span>{item.id}</span><b>{item.name}</b></button>
        ))}
        <div className="rail-bottom"><span className="live-dot" />PRODUCTION MODE</div>
      </aside>

      <section className="studio-content">
        <header className="topbar">
          <div className="crumb"><span>PROJECTS</span><ChevronRight size={14} /><strong>{niche || "New Project"}</strong><span className="draft-pill">DRAFT</span></div>
          <div className="topbar-actions"><span className="depth"><span /> 3D CANVAS ACTIVE</span><button className="orb-button" onClick={() => window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" })}><Sparkles size={16} /> Build universe</button></div>
        </header>

        <section className="hero-grid">
          <div className="hero-copy">
            <div className="eyebrow"><span /> THE NICHE ENGINE</div>
            <h1>From one market<br />to a full <em>campaign universe.</em></h1>
            <p>Lock a strategic direction, then fan it into real production systems. Every asset carries one brand voice from first brief to final export.</p>
            <div className="hero-proof"><div><strong>03</strong><span>distinct<br />directions</span></div><div><strong>05</strong><span>asset<br />engines</span></div><div><strong>∞</strong><span>versioned<br />iterations</span></div></div>
          </div>
          <div className="hero-object">
            <div className="object-ui object-ui-top"><span>BRAND SYSTEM</span><b>{kit.name}</b><i /></div>
            <div className="orbital orbital-a" /><div className="orbital orbital-b" />
            <div className="glass-orb"><div className="orb-core" /><div className="orb-shine" /></div>
            <div className="object-ui object-ui-bottom"><span>ACTIVE SIGNAL</span><b>{selectedOption?.campaign.name || "Niche input"}</b><i /></div>
            <div className="coordinates">32° 46' 51.2" N&nbsp;&nbsp;&nbsp; // &nbsp;&nbsp;&nbsp;96° 48' 19.2" W</div>
          </div>
        </section>

        <section className="intake-section section-card" id="intake">
          <div className="section-kicker"><span>01</span><div><small>INPUT / CONSTRAINTS</small><h2>Shape the brief.</h2></div><p>Your niche becomes a production-grade source of truth.</p></div>
          <div className="intake-grid">
            <label className="field field-wide"><span>YOUR NICHE <i>*</i></span><input value={niche} onChange={(event) => setNiche(event.target.value)} placeholder="e.g. Mobile auto detailing" /></label>
            <label className="field"><span>PRIMARY MARKET <i>*</i></span><input value={market} onChange={(event) => setMarket(event.target.value)} placeholder="e.g. DFW, Texas" /></label>
            <label className="field"><span>MONTHLY BUDGET</span><input value={budget} onChange={(event) => setBudget(event.target.value)} placeholder="e.g. $3,500/mo" /></label>
            <label className="field field-wide"><span>IDEAL CUSTOMER</span><input value={audience} onChange={(event) => setAudience(event.target.value)} placeholder="Who should it move?" /></label>
            <div className="tone-field"><span>BRAND TEMPERATURE</span><div className="tone-pills">{["Premium", "Neighborly", "Disruptive"].map((name) => <button key={name} className={tone === name ? "selected" : ""} onClick={() => setTone(name)}>{name}</button>)}</div></div>
          </div>
          <button className="primary-action" onClick={() => strategy.mutate({ niche, market, budget, audience, tone })} disabled={strategy.isPending || niche.length < 2 || market.length < 2}>{strategy.isPending ? <Loader2 className="spin" size={17} /> : <WandSparkles size={17} />} {strategy.isPending ? "Mapping the market..." : "Generate 3 strategy directions"}<ArrowUpRight size={16} /></button>
        </section>

        <section className="direction-section">
          <div className="section-kicker compact"><span>02</span><div><small>STRATEGY ENGINE / THREE ROUTES</small><h2>Choose the energy.</h2></div><div className="line" /><p>{options.length ? "Select one direction or keep refining." : "Generate your brief to reveal distinct strategic routes."}</p></div>
          {options.length === 0 ? <div className="empty-state"><Zap size={20} /><span>Premium, value, and disruptor positions will render here.</span></div> : <div className="direction-grid">{options.map((option, index) => (
            <button key={option.id} className={`direction-card option-card option-${option.id} ${selected === option.id ? "chosen" : ""}`} onClick={() => chooseOption(option)}>
              <div className="card-index"><span>0{index + 1}</span>{selected === option.id && <span className="select-check"><Check size={13} /></span>}</div>
              <small>{index === 0 ? "PREMIUM" : index === 1 ? "VALUE" : "DISRUPTOR"}</small><h3>{option.campaign.name}</h3><p>{option.positioning}</p>
              <div className="card-stats"><span>{option.campaign.channels[0]}</span><span>{option.strategy.pricing_angle.slice(0, 26)}...</span></div><div className="card-arrow"><ArrowUpRight size={16} /></div>
            </button>
          ))}</div>}
        </section>

        <section className="brand-lock section-card">
          <div className="section-kicker compact"><span>03</span><div><small>BRAND KIT / SINGLE SOURCE OF TRUTH</small><h2>Lock the system.</h2></div><div className="line" /><p>Downstream assets stay on one voice, palette, offer, and visual rule.</p></div>
          <div className="kit-workbench">
            <div className="kit-main"><div className="kit-topline"><span>BRAND KIT / v1.0</span><span className={brandKitId ? "locked" : ""}>{brandKitId ? "LOCKED" : "EDITABLE"}</span></div><h3>{kit.name}</h3><p>{kit.tagline}</p><div className="color-row">{kit.palette.map((color, index) => <span key={`${color}-${index}`} style={{ background: color }} title={color} />)}</div><div className="kit-details"><span><b>Voice</b>{kit.voice}</span><span><b>Type</b>{kit.fonts.heading} / {kit.fonts.body}</span></div></div>
            <div className="kit-offer"><small>CORE OFFER</small><p>{kit.offer}</p><small>LOGO DIRECTION</small><p className="muted">{selectedOption?.brand.logo_direction || "Choose a strategy direction to sync logo direction."}</p></div>
            <button className="lock-button" onClick={() => lockKit.mutate({ projectId, strategyOptionId: selectedOption?.id, kit })} disabled={lockKit.isPending || !options.length}>{lockKit.isPending ? <Loader2 className="spin" size={17} /> : brandKitId ? <Check size={17} /> : <Palette size={17} />}{brandKitId ? "Brand Kit locked" : "Lock Brand Kit"}</button>
          </div>
        </section>

        <section className="production-section">
          <div className="section-kicker compact"><span>04</span><div><small>PARALLEL PRODUCTION / TEMPLATE FAMILY</small><h2>Fan out with intent.</h2></div><div className="line" /><p>Each engine creates a variant through the locked system.</p></div>
          <div className="variant-strip"><span>LAYOUT VARIANT</span>{[1, 2, 3].map((variant) => <button key={variant} className={assetVariant === variant ? "active" : ""} onClick={() => setAssetVariant(variant)}>0{variant} / {variant === 1 ? "CINEMA SPLIT" : variant === 2 ? "SIGNAL STACK" : "PROOF GRID"}</button>)}</div>
          <div className="asset-grid">{assetLabels.map((asset, index) => {
            const generated = assets.find((item) => item.type === asset.type); const Icon = asset.icon;
            return <div className="asset-card" key={asset.type}><div className="asset-card-head"><span>0{index + 1}</span><Icon size={18} /></div><h3>{asset.name}</h3><p>{asset.export}</p><div className="asset-card-bottom">{generated ? <><span className="ready"><Check size={13} /> READY</span><div className="asset-ready-actions">{(asset.type === "website" || asset.type === "email") && <button className="preview-link" onClick={() => setPreviewAsset(generated)}><Eye size={14} /> Preview</button>}<button onClick={() => downloadFile(`${kit.name.toLowerCase().replace(/\s+/g, "-")}-${asset.type}.json`, JSON.stringify(generated.payload, null, 2))}><Download size={15} /> Export</button></div></> : <button className="generate-link" onClick={() => generateAsset(asset.type as "deck" | "website" | "email" | "pos" | "logo")} disabled={assetGen.isPending || !brandKitId}><Sparkles size={14} /> Generate <ArrowUpRight size={14} /></button>}</div></div>;
          })}</div>
        </section>

        <section className="visual-lab section-card">
          <div className="section-kicker compact"><span>05</span><div><small>VISUAL LAB / GENERATE, RECOGNIZE, ENHANCE</small><h2>Make the image work harder.</h2></div><div className="line" /><p>Choose an available image model at run time; outputs are stored against the brand kit.</p></div>
          <div className="visual-layout">
            <div className={`visual-stage ${visualUrl ? "has-visual" : ""}`}>{visualUrl ? <img src={visualUrl} alt="Generated campaign visual" /> : <><div className="stage-axis axis-x" /><div className="stage-axis axis-y" /><div className="stage-shape shape-a" /><div className="stage-shape shape-b" /><div className="stage-label">CAMPAIGN<br />KEY VISUAL</div></>}<div className="stage-overlay"><span>16:9 / CINEMATIC</span><span>{visualUrl ? "ASSET READY" : "AWAITING SIGNAL"}</span></div></div>
            <div className="visual-control"><small>IMAGE PROVIDER ROUTING</small><div className="provider-list">{["Nano Banana", "Gemini", "DALL·E", "Midjourney bridge", "Canva handoff"].map((provider) => <button key={provider} className={visualProvider === provider ? "provider-selected" : ""} onClick={() => setVisualProvider(provider)}><span>{provider.includes("handoff") || provider.includes("bridge") ? <Clapperboard size={15} /> : <ImageUp size={15} />}</span>{provider}<i /></button>)}</div><button className="primary-action slim" onClick={() => visualGen.mutate({ brandKitId, provider: visualProvider, kit })} disabled={visualGen.isPending || !brandKitId}>{visualGen.isPending ? <Loader2 className="spin" size={16} /> : <Sparkles size={16} />}{visualGen.isPending ? "Composing visual..." : "Generate campaign visual"}</button><p className="provider-note">Midjourney and Canva are production handoffs. Available native image models are resolved automatically; unconnected providers never receive your brand data.</p></div>
          </div>
          <div className="recognition-panel"><div className="recognition-copy"><div className="scan-icon"><ScanText size={19} /></div><div><small>PHOTO INTELLIGENCE</small><h3>Recognize visual proof + extract visible text.</h3><p>Upload a reference image to detect scene elements, readable copy, quality signals, and marketing use cases. Files remain in project storage.</p></div></div><div className="recognition-actions"><label className="upload-action"><input type="file" accept="image/*" onChange={recognizeFile} /><ImageUp size={16} />{recognition.isPending ? "Analyzing photo..." : "Analyze a photo"}</label>{photoData && <button className="outline-action" onClick={() => upscale.mutate({ dataUrl: photoData })} disabled={upscale.isPending}>{upscale.isPending ? <Loader2 className="spin" size={15} /> : <Eye size={15} />} Upscale</button>}</div></div>
          {photo && <div className="photo-result"><img src={photo.previewUrl} alt="Uploaded visual reference" /><div className="photo-insight"><div className="result-meta"><span>VISION / {photo.provider.toUpperCase()}</span><span>{photo.analysis.visual_quality}</span></div><h3>{photo.analysis.scene}</h3><p>{photo.analysis.summary}</p><div className="tag-row">{photo.analysis.objects.slice(0, 5).map((item) => <span key={item}>{item}</span>)}{photo.analysis.people.length > 0 && <span>{photo.analysis.people.length} people described</span>}</div></div><div className="ocr-box"><small>VISIBLE TEXT / OCR</small>{photo.analysis.extracted_text.length ? <p>{photo.analysis.extracted_text.join(" · ")}</p> : <p className="muted">No confidently legible text identified.</p>}<small>BEST NEXT ASSET</small><b>{photo.analysis.suggested_asset}</b></div></div>}
        </section>

        <section className="voice-section"><div className="voice-art"><div className="voice-wave wave-one" /><div className="voice-wave wave-two" /><div className="voice-wave wave-three" /><Mic2 size={29} /></div><div><small>VOICE / TTS PROMPTER</small><h2>Direct the delivery, not just the words.</h2><p>BrandForge creates a ready-to-speak direction that separates voice performance from the spoken script.</p></div><button className="outline-action dark" onClick={getVoicePrompt} disabled={voice.isFetching}><AudioLines size={16} /> {voice.isFetching ? "Writing direction..." : "Generate TTS direction"}</button></section>
        {ttsPrompt && <section className="tts-result"><span>READY TO COPY</span><p>{ttsPrompt}</p><button onClick={() => { navigator.clipboard?.writeText(ttsPrompt); toast.success("Copied."); }}><Copy size={15} /> Copy</button></section>}

        <footer className="export-footer"><div><span>05</span><small>EXPORT LAYER</small><h2>Production, without the drift.</h2></div><p>Deck and email payloads export as structured content. Logos export as self-contained SVG. Site blocks are ready to implement or hand off to deployment.</p><button onClick={() => { assets.length ? downloadFile(`${kit.name.toLowerCase().replace(/\s+/g, "-")}-production-package.json`, JSON.stringify({ brandKit: kit, assets }, null, 2)) : toast.message("Generate an asset first."); }}><Download size={16} /> Download production package</button></footer>
      </section>
      {previewAsset && <AssetPreview asset={previewAsset} kit={kit} onClose={() => setPreviewAsset(null)} />}
    </main>
  );
}
