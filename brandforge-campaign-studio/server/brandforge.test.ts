import { describe, expect, it } from "vitest";
import { assetFallback, calculateCampaignEconomics, createManimPlan, makeNarrationPrompt, makeTtsPrompt, normalizeSocialPack, strategyFallback } from "./brandforge";

const kit = {
  name: "Detail Reserve",
  palette: ["#111827", "#F8F5EE", "#C9A86A", "#344054", "#FFFFFF"],
  fonts: { heading: "Cormorant Garamond", body: "DM Sans" },
  voice: "Confident and composed",
  tagline: "A higher standard of done.",
  offer: "Signature mobile detailing with priority scheduling.",
};

describe("BrandForge generation contracts", () => {
  it("builds exactly three differentiated strategy directions", () => {
    const options = strategyFallback({ niche: "mobile auto detailing", market: "DFW" });
    expect(options).toHaveLength(3);
    expect(options.map((option) => option.id)).toEqual([1, 2, 3]);
    expect(options[0].brand.palette).toHaveLength(5);
  });

  it("returns renderer-ready website and logo payloads", () => {
    expect(assetFallback("website", kit, 1).pages[0].sections[0].layout_id).toBe("cinema-split");
    expect(assetFallback("logo", kit, 2).concepts).toHaveLength(3);
  });

  it("returns previewable website and three-email payloads", () => {
    const website = assetFallback("website", kit, 3);
    const email = assetFallback("email", kit, 2);
    expect(website.pages[0].sections).toHaveLength(3);
    expect(email.templates).toHaveLength(3);
    expect(email.templates.map((template) => template.name)).toEqual(["Welcome", "Promo", "Re-engage"]);
  });

  it("models campaign economics with traceable operational inputs", () => {
    const economics = calculateCampaignEconomics({ monthlyBudget: 3500, averageOrderValue: 500, grossMarginPct: 50, leadToBookingPct: 25, costPerLead: 50 });
    expect(economics.estimatedLeads).toBe(70);
    expect(economics.estimatedBookings).toBe(17.5);
    expect(economics.estimatedRevenue).toBe(8750);
    expect(economics.grossProfit).toBe(4375);
    expect(economics.contributionAfterMarketing).toBe(875);
  });

  it("produces a portable ManimCE economics script and compliant TTS direction", () => {
    const economics = calculateCampaignEconomics({ monthlyBudget: 1000, averageOrderValue: 250, grossMarginPct: 50, leadToBookingPct: 20, costPerLead: 25 });
    const animation = createManimPlan(kit, economics);
    expect(animation.framework).toBe("ManimCE");
    expect(animation.script).toContain("from manim import *");
    expect(animation.script).toContain("class CampaignEconomics");
    expect(makeNarrationPrompt(kit, "A short clean message for a social launch.")).toContain(":");
  });

  it("normalizes video delivery and required TikTok discovery tags", () => {
    expect(makeNarrationPrompt(kit, "A short narration", "Confident, measured, and concise")).toContain("measured pace");
    const normalized = normalizeSocialPack({ posts: [{ platform: "TikTok", format: "Reel", hook: "Hook", caption: "Caption", hashtags: ["#Local"], cta: "Act" }, { platform: "Instagram", format: "Reel", hook: "Hook", caption: "Caption", hashtags: ["#Local"], cta: "Act" }, { platform: "Facebook", format: "Post", hook: "Hook", caption: "Caption", hashtags: ["#Local"], cta: "Act" }] });
    expect(normalized.posts[0]?.hashtags).toEqual(["#fyp", "#foryoupage", "#viral", "#Local"]);
  });

  it("separates TTS direction from spoken copy with a colon", () => {
    const prompt = makeTtsPrompt(kit);
    expect(prompt).toContain(":");
    expect(prompt).toContain(kit.tagline);
    expect(prompt.split(":")[1].trim().split(/\s+/)).toHaveLength(17);
  });
});
