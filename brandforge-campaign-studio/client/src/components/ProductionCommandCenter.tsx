import { useState } from "react";
import { BarChart3, Check, Clapperboard, Copy, Download, FileCode2, Film, Layers3, Loader2, Mic2, Radio, Share2, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { trpc } from "@/lib/trpc";

type Kit = { name: string; palette: string[]; fonts: { heading: string; body: string }; voice: string; tagline: string; offer: string };
type Economics = { monthlyBudget: number; averageOrderValue: number; grossMarginPct: number; leadToBookingPct: number; costPerLead: number; estimatedLeads: number; estimatedBookings: number; estimatedRevenue: number; grossProfit: number; contributionAfterMarketing: number; blendedRoas: number; breakEvenBookings: number; assumptions: string[]; disclaimer: string };
type VideoPlan = { title: string; objective: string; durationSeconds: number; aspectRatio: "9:16" | "16:9"; visualStyle: string; narrator: { voice: string; language: string; pacing: string; ttsPrompt: string }; clips: Array<{ number: number; durationSeconds: number; purpose: string; scene: string; action: string; transitionDescription: string; camera: string; narration: string }>; referenceImages: string[] };
type ManimPlan = { title: string; framework: "ManimCE"; durationSeconds: number; scenes: Array<{ title: string; durationSeconds: number; purpose: string; visual: string }>; script: string };
type SocialPack = { posts: Array<{ platform: "TikTok" | "Instagram" | "Facebook"; format: string; hook: string; caption: string; hashtags: string[]; cta: string }> };

function money(value: number) { return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(value); }
function download(filename: string, content: string, mime = "application/json") { const blob = new Blob([content], { type: mime }); const url = URL.createObjectURL(blob); const link = document.createElement("a"); link.href = url; link.download = filename; link.click(); URL.revokeObjectURL(url); }

export default function ProductionCommandCenter({ kit, brandKitId }: { kit: Kit; brandKitId: number }) {
  const [objective, setObjective] = useState("Drive qualified local bookings with a visual proof-led launch.");
  const [inputs, setInputs] = useState({ monthlyBudget: 3500, averageOrderValue: 549, grossMarginPct: 55, leadToBookingPct: 35, costPerLead: 42 });
  const [economics, setEconomics] = useState<Economics | null>(null);
  const [video, setVideo] = useState<VideoPlan | null>(null);
  const [manim, setManim] = useState<ManimPlan | null>(null);
  const [social, setSocial] = useState<SocialPack | null>(null);

  const economicsModel = trpc.studio.modelEconomics.useMutation({ onSuccess: (data) => { setEconomics(data as Economics); toast.success("Campaign economics updated from your planning assumptions."); }, onError: () => toast.error("Check the campaign economics inputs and retry.") });
  const videoPlan = trpc.studio.createVideoPlan.useMutation({ onSuccess: (data) => { setVideo(data.plan as VideoPlan); toast.success(`Video production brief created with ${data.provider}.`); }, onError: () => toast.error("Video brief generation needs another attempt.") });
  const manimPlan = trpc.studio.createManimPlan.useMutation({ onSuccess: (data) => { setManim(data.plan as ManimPlan); toast.success("ManimCE explainer script is ready to download."); }, onError: () => toast.error("Animation brief generation needs another attempt.") });
  const socialPack = trpc.studio.createSocialPack.useMutation({ onSuccess: (data) => { setSocial(data.pack as SocialPack); toast.success(`Three platform packs created with ${data.provider}.`); }, onError: () => toast.error("Social pack generation needs another attempt.") });
  const updateInput = (key: keyof typeof inputs, value: string) => setInputs((current) => ({ ...current, [key]: Number(value) || 0 }));
  const ready = brandKitId > 0;

  return <section className="production-command section-card">
    <div className="section-kicker compact"><span>06</span><div><small>CONNECTED PRODUCTION / ECONOMICS, MOTION, DISTRIBUTION</small><h2>Make the campaign move.</h2></div><div className="line" /><p>Plan spend, direct the video, explain the numbers, and prepare channel-native social outputs from one locked Brand Kit.</p></div>
    <div className="command-objective"><div><Radio size={17} /><span>CAMPAIGN OBJECTIVE</span></div><input aria-label="Campaign objective" value={objective} onChange={(event) => setObjective(event.target.value)} /><b><span /> LOCKED TO {kit.name.toUpperCase()}</b></div>

    <div className="command-grid">
      <article className="command-card finance-card"><div className="command-card-head"><div><span>01 / FINANCIAL ANALYSIS</span><h3>Campaign economics</h3></div><BarChart3 size={21} /></div><p>Model a marketing scenario using explicit operational assumptions—no market data or investment recommendations.</p><div className="assumption-grid">
        <label><span>MONTHLY SPEND</span><input type="number" value={inputs.monthlyBudget} onChange={(event) => updateInput("monthlyBudget", event.target.value)} /></label>
        <label><span>AVG. ORDER VALUE</span><input type="number" value={inputs.averageOrderValue} onChange={(event) => updateInput("averageOrderValue", event.target.value)} /></label>
        <label><span>GROSS MARGIN %</span><input type="number" value={inputs.grossMarginPct} onChange={(event) => updateInput("grossMarginPct", event.target.value)} /></label>
        <label><span>LEAD → BOOK %</span><input type="number" value={inputs.leadToBookingPct} onChange={(event) => updateInput("leadToBookingPct", event.target.value)} /></label>
        <label className="wide"><span>COST PER LEAD</span><input type="number" value={inputs.costPerLead} onChange={(event) => updateInput("costPerLead", event.target.value)} /></label>
      </div><button className="command-action" onClick={() => economicsModel.mutate({ brandKitId, ...inputs })} disabled={!ready || economicsModel.isPending}>{economicsModel.isPending ? <Loader2 className="spin" size={15} /> : <Sparkles size={15} />}{economicsModel.isPending ? "Modeling..." : "Model campaign economics"}</button>
      {economics && <div className="economics-result"><div className="metric-run"><span><b>{money(economics.estimatedRevenue)}</b>REVENUE</span><span><b>{economics.blendedRoas.toFixed(2)}x</b>BLENDED ROAS</span><span><b>{economics.estimatedBookings.toFixed(1)}</b>BOOKINGS</span></div><div className="contribution-line"><span>Contribution after marketing</span><b className={economics.contributionAfterMarketing >= 0 ? "positive" : "negative"}>{money(economics.contributionAfterMarketing)}</b></div><small>{economics.disclaimer}</small></div>}
      </article>

      <article className="command-card video-card"><div className="command-card-head"><div><span>02 / AI VIDEO GENERATOR</span><h3>Director’s brief</h3></div><Clapperboard size={21} /></div><p>Creates an executable short-form plan with clip-level motion, narration, references, and a compliant TTS direction.</p><div className="video-window"><div className="video-grid" /><div className="video-orb"><i /></div><span>REFERENCE-READY<br />NO RENDER YET</span><b>9:16</b></div><button className="command-action" onClick={() => videoPlan.mutate({ brandKitId, kit, objective })} disabled={!ready || videoPlan.isPending}>{videoPlan.isPending ? <Loader2 className="spin" size={15} /> : <Film size={15} />}{videoPlan.isPending ? "Planning clips..." : "Create video brief"}</button>
      {video && <div className="video-result"><div className="result-title"><span>{video.aspectRatio} / {video.durationSeconds} SEC</span><b>{video.title}</b></div><div className="clip-track">{video.clips.map((clip) => <span key={clip.number} style={{ flex: clip.durationSeconds }}><i>0{clip.number}</i>{clip.purpose}<em>{clip.durationSeconds}s</em></span>)}</div><div className="narration-prompt"><Mic2 size={14} /><p>{video.narrator.ttsPrompt}</p><button onClick={() => { navigator.clipboard?.writeText(video.narrator.ttsPrompt); toast.success("TTS direction copied."); }} aria-label="Copy video TTS direction"><Copy size={13} /></button></div><button className="export-brief" onClick={() => download(`${kit.name.toLowerCase().replace(/\s+/g, "-")}-video-brief.json`, JSON.stringify(video, null, 2))}><Download size={13} /> Export video brief</button></div>}
      </article>

      <article className="command-card manim-card"><div className="command-card-head"><div><span>03 / MANIM ANIMATOR</span><h3>Explain the signal</h3></div><Layers3 size={21} /></div><p>Transforms the campaign model into a reproducible Python animation script for a compact economics explainer.</p><div className="manim-stage"><div className="manim-axis axis-one" /><div className="manim-axis axis-two" /><div className="manim-bars"><i /><i /><i /><i /></div><span>MANIMCE / VECTOR MOTION</span></div><button className="command-action" onClick={() => economics && manimPlan.mutate({ brandKitId, kit, economics })} disabled={!ready || !economics || manimPlan.isPending}>{manimPlan.isPending ? <Loader2 className="spin" size={15} /> : <FileCode2 size={15} />}{manimPlan.isPending ? "Writing scene..." : economics ? "Create ManimCE script" : "Model economics first"}</button>
      {manim && <div className="manim-result"><div><Check size={14} /><span>{manim.framework} / {manim.durationSeconds} SEC EXPLAINER</span></div><p>{manim.scenes.map((scene) => scene.title).join(" → ")}</p><button className="export-brief" onClick={() => download(`${kit.name.toLowerCase().replace(/\s+/g, "-")}-campaign-economics.py`, manim.script, "text/x-python")}> <Download size={13} /> Download Python script</button></div>}
      </article>

      <article className="command-card social-card"><div className="command-card-head"><div><span>04 / SOCIAL TRAFFIC BOOSTER</span><h3>Distribution pack</h3></div><Share2 size={21} /></div><p>Creates three channel-native organic posts. Discovery tags are suggested, not presented as live trend data.</p><div className="social-signal"><span>TIKTOK</span><span>INSTAGRAM</span><span>FACEBOOK</span><div><i /><i /><i /></div></div><button className="command-action" onClick={() => socialPack.mutate({ brandKitId, kit, objective })} disabled={!ready || socialPack.isPending}>{socialPack.isPending ? <Loader2 className="spin" size={15} /> : <Share2 size={15} />}{socialPack.isPending ? "Building pack..." : "Create social distribution pack"}</button>
      {social && <div className="social-result">{social.posts.map((post) => <article key={post.platform}><div><span>{post.platform}</span><b>{post.format}</b></div><h4>{post.hook}</h4><p>{post.caption}</p><div className="social-tags">{post.hashtags.slice(0, 4).map((tag) => <span key={tag}>{tag}</span>)}</div><button onClick={() => { navigator.clipboard?.writeText(`${post.caption}\n\n${post.hashtags.join(" ")}`); toast.success(`${post.platform} copy copied.`); }}><Copy size={12} /> Copy post</button></article>)}</div>}
      </article>
    </div>
    <div className="production-note"><Check size={15} /><p><b>Production boundary.</b> The studio produces plans, scripts, prompts, and exportable payloads. Rendering video, speech, or Manim output is intentionally a separate approved production action so each final format and visual reference can be reviewed first.</p></div>
  </section>;
}
