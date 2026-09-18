import { describe, expect, it } from "vitest";
import { assetFallback, makeTtsPrompt, strategyFallback } from "./brandforge";

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

  it("separates TTS direction from spoken copy with a colon", () => {
    const prompt = makeTtsPrompt(kit);
    expect(prompt).toContain(":");
    expect(prompt).toContain(kit.tagline);
    expect(prompt.split(":")[1].trim().split(/\s+/)).toHaveLength(17);
  });
});
