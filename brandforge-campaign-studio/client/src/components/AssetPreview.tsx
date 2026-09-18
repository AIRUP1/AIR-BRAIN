import { useEffect, useMemo, useState, type CSSProperties } from "react";
import { Check, ChevronDown, ExternalLink, Monitor, Smartphone, Tablet, X } from "lucide-react";
import { toast } from "sonner";

type BrandKit = {
  name: string;
  palette: string[];
  fonts: { heading: string; body: string };
  voice: string;
  tagline: string;
  offer: string;
};

type PreviewAsset = {
  type: string;
  variant: number;
  provider: string;
  payload: Record<string, unknown>;
};

type WebsiteSection = { layout_id: string; type: string; headline: string; body: string; cta: string };
type WebsitePage = { slug: string; sections: WebsiteSection[] };
type EmailBlock = { layout_id: string; type: string; copy: string };
type EmailTemplate = { name: string; subject: string; blocks: EmailBlock[] };
type Device = "desktop" | "tablet" | "mobile";

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null && !Array.isArray(value) ? value as Record<string, unknown> : null;
}

function text(value: unknown, fallback = ""): string {
  return typeof value === "string" && value.trim() ? value : fallback;
}

function websitePages(payload: Record<string, unknown>): WebsitePage[] {
  const pages = Array.isArray(payload.pages) ? payload.pages : [];
  return pages.map((page) => {
    const record = asRecord(page) ?? {};
    const sections = Array.isArray(record.sections) ? record.sections : [];
    return {
      slug: text(record.slug, "/"),
      sections: sections.map((section) => {
        const block = asRecord(section) ?? {};
        return {
          layout_id: text(block.layout_id, "cinema-split"),
          type: text(block.type, "content"),
          headline: text(block.headline, "A considered next step."),
          body: text(block.body, "Built to move the right customer from interest to action."),
          cta: text(block.cta, "Get started"),
        };
      }),
    };
  }).filter((page) => page.sections.length > 0);
}

function emailTemplates(payload: Record<string, unknown>): EmailTemplate[] {
  const templates = Array.isArray(payload.templates) ? payload.templates : [];
  return templates.map((template) => {
    const record = asRecord(template) ?? {};
    const blocks = Array.isArray(record.blocks) ? record.blocks : [];
    return {
      name: text(record.name, "Campaign email"),
      subject: text(record.subject, "A note from the brand"),
      blocks: blocks.map((block) => {
        const item = asRecord(block) ?? {};
        return { layout_id: text(item.layout_id, "cinema-split"), type: text(item.type, "body"), copy: text(item.copy, "") };
      }),
    };
  }).filter((template) => template.blocks.length > 0);
}

function WebsiteSectionPreview({ section, index }: { section: WebsiteSection; index: number }) {
  const kind = section.type.toLowerCase();
  const simulateAction = () => toast.message(`Preview interaction: ${section.cta}`);
  if (kind.includes("hero")) {
    return <section className={`site-block site-hero layout-${section.layout_id}`}><span className="preview-eyebrow">{index === 0 ? "THE NEW STANDARD" : "CAMPAIGN SIGNAL"}</span><h1>{section.headline}</h1><p>{section.body}</p><button onClick={simulateAction}>{section.cta} <ExternalLink size={13} /></button><div className="preview-orb"><i /><b /></div></section>;
  }
  if (/(service|pricing|offer|feature)/.test(kind)) {
    const details = section.body.split(/[.;·]/).map((item) => item.trim()).filter(Boolean).slice(0, 3);
    return <section className={`site-block site-services layout-${section.layout_id}`}><div><span className="preview-eyebrow">WHAT YOU GET</span><h2>{section.headline}</h2><p>{section.body}</p></div><div className="preview-service-grid">{(details.length ? details : [section.body, "Priority guidance", "A clear next step"]).map((detail, detailIndex) => <button key={`${detail}-${detailIndex}`} onClick={() => toast.message(`Preview detail ${detailIndex + 1}`)}><span>0{detailIndex + 1}</span><b>{detail}</b><ExternalLink size={13} /></button>)}</div><button className="preview-text-link" onClick={simulateAction}>{section.cta} <ExternalLink size={13} /></button></section>;
  }
  if (/(testimonial|proof|review)/.test(kind)) {
    return <section className="site-block site-proof"><span className="preview-eyebrow">CUSTOMER PROOF</span><blockquote>“{section.body}”</blockquote><div><b>{section.headline}</b><span>Verified customer story</span></div><button className="preview-text-link" onClick={simulateAction}>{section.cta} <ExternalLink size={13} /></button></section>;
  }
  return <section className={`site-block site-cta layout-${section.layout_id}`}><span className="preview-eyebrow">READY WHEN YOU ARE</span><h2>{section.headline}</h2><p>{section.body}</p><button onClick={simulateAction}>{section.cta} <ExternalLink size={13} /></button></section>;
}

function WebsitePreview({ asset, kit, device }: { asset: PreviewAsset; kit: BrandKit; device: Device }) {
  const pages = useMemo(() => websitePages(asset.payload), [asset.payload]);
  const [pageIndex, setPageIndex] = useState(0);
  const page = pages[Math.min(pageIndex, Math.max(pages.length - 1, 0))];
  const style = {
    "--preview-ink": kit.palette[0] || "#132A13",
    "--preview-paper": kit.palette[1] || "#F5F7F2",
    "--preview-accent": kit.palette[2] || "#86B049",
    "--preview-soft": kit.palette[3] || "#E8C547",
    "--preview-heading": kit.fonts.heading,
    "--preview-body": kit.fonts.body,
  } as CSSProperties;

  if (!page) return <div className="preview-empty">The website payload does not contain any previewable pages.</div>;
  return <div className="preview-content">
    <div className="preview-subbar"><span>PAGE</span><div className="preview-select-wrap"><select value={pageIndex} onChange={(event) => setPageIndex(Number(event.target.value))}>{pages.map((item, index) => <option value={index} key={`${item.slug}-${index}`}>{item.slug === "/" ? "Home /" : item.slug}</option>)}</select><ChevronDown size={13} /></div><span className="preview-live"><i /> LIVE CONTENT</span></div>
    <div className={`preview-device preview-device-${device}`}>
      <article className={`site-preview variant-${asset.variant}`} style={style}>
        <header className="site-preview-nav"><strong>{kit.name}</strong><nav><button onClick={() => toast.message("Preview navigation: Services")}>Services</button><button onClick={() => toast.message("Preview navigation: Why us")}>Why us</button><button onClick={() => toast.message("Preview navigation: Contact")}>Contact</button></nav><button className="site-nav-cta" onClick={() => toast.message("Preview navigation: Book now")}>Book now</button></header>
        {page.sections.map((section, index) => <WebsiteSectionPreview key={`${section.type}-${index}`} section={section} index={index} />)}
        <footer className="site-preview-footer"><strong>{kit.name}</strong><span>{kit.tagline}</span><span>© 2026</span></footer>
      </article>
    </div>
  </div>;
}

function EmailPreview({ asset, kit, device }: { asset: PreviewAsset; kit: BrandKit; device: Device }) {
  const templates = useMemo(() => emailTemplates(asset.payload), [asset.payload]);
  const [templateIndex, setTemplateIndex] = useState(0);
  const template = templates[Math.min(templateIndex, Math.max(templates.length - 1, 0))];
  const style = { "--email-ink": kit.palette[0] || "#132A13", "--email-paper": kit.palette[1] || "#F5F7F2", "--email-accent": kit.palette[2] || "#86B049", "--email-soft": kit.palette[3] || "#E8C547", "--preview-heading": kit.fonts.heading, "--preview-body": kit.fonts.body } as CSSProperties;

  if (!template) return <div className="preview-empty">The email payload does not contain any previewable templates.</div>;
  return <div className="preview-content">
    <div className="preview-subbar preview-template-bar"><span>EMAIL SEQUENCE</span><div className="template-tabs">{templates.map((item, index) => <button key={`${item.name}-${index}`} onClick={() => setTemplateIndex(index)} className={index === templateIndex ? "active" : ""}>{item.name}</button>)}</div><span className="preview-live"><i /> {device.toUpperCase()} VIEW</span></div>
    <div className={`preview-device preview-device-${device}`}>
      <article className="email-preview" style={style}>
        <div className="email-client-meta"><span>FROM</span><b>{kit.name}</b><span>TO</span><b>you@inbox.com</b></div>
        <div className="email-subject"><span>SUBJECT</span><h3>{template.subject}</h3></div>
        <div className="email-body"><header><strong>{kit.name}</strong><span>EST. {new Date().getFullYear()}</span></header>{template.blocks.map((block, index) => {
          const blockKind = block.type.toLowerCase();
          if (/(headline|hero|title)/.test(blockKind)) return <h1 key={`${block.type}-${index}`}>{block.copy}</h1>;
          if (/(cta|button)/.test(blockKind)) return <button key={`${block.type}-${index}`} onClick={() => toast.message(`Preview interaction: ${block.copy}`)}>{block.copy} <ExternalLink size={13} /></button>;
          return <p key={`${block.type}-${index}`}>{block.copy}</p>;
        })}<footer><span>{kit.tagline}</span><button onClick={() => toast.message("Preview interaction: Manage preferences")}>Manage preferences</button></footer></div>
      </article>
    </div>
  </div>;
}

export default function AssetPreview({ asset, kit, onClose }: { asset: PreviewAsset; kit: BrandKit; onClose: () => void }) {
  const [device, setDevice] = useState<Device>(asset.type === "email" ? "mobile" : "desktop");
  useEffect(() => { const onKeyDown = (event: KeyboardEvent) => { if (event.key === "Escape") onClose(); }; window.addEventListener("keydown", onKeyDown); return () => window.removeEventListener("keydown", onKeyDown); }, [onClose]);
  const title = asset.type === "website" ? "Launch site preview" : "Email flow preview";
  return <div className="preview-backdrop" onMouseDown={(event) => { if (event.currentTarget === event.target) onClose(); }}><section className="preview-modal" role="dialog" aria-modal="true" aria-labelledby="preview-title"><header className="preview-modal-header"><div><span>INTERACTIVE PREVIEW / VARIANT 0{asset.variant}</span><h2 id="preview-title">{title}</h2></div><div className="preview-header-actions"><div className="device-controls" aria-label="Preview device size"><button className={device === "desktop" ? "active" : ""} onClick={() => setDevice("desktop")} aria-label="Desktop preview"><Monitor size={16} /></button><button className={device === "tablet" ? "active" : ""} onClick={() => setDevice("tablet")} aria-label="Tablet preview"><Tablet size={16} /></button><button className={device === "mobile" ? "active" : ""} onClick={() => setDevice("mobile")} aria-label="Mobile preview"><Smartphone size={16} /></button></div><button className="preview-close" onClick={onClose} aria-label="Close preview"><X size={18} /></button></div></header><div className="preview-modal-body">{asset.type === "website" ? <WebsitePreview asset={asset} kit={kit} device={device} /> : <EmailPreview asset={asset} kit={kit} device={device} />}</div><footer className="preview-modal-footer"><span><Check size={14} /> Rendered from the generated {asset.type} payload</span><span>MODEL / {asset.provider}</span></footer></section></div>;
}
