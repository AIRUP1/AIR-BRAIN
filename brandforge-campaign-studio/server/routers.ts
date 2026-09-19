import { z } from "zod";
import { COOKIE_NAME } from "@shared/const";
import { getSessionCookieOptions } from "./_core/cookies";
import { systemRouter } from "./_core/systemRouter";
import { publicProcedure, router } from "./_core/trpc";
import * as db from "./db";
import { calculateCampaignEconomics, createCampaignVisual, createManimPlan, generateAsset, generateSocialPack, generateStrategy, generateVideoPlan, makeTtsPrompt, recognizePhoto, upscaleImage } from "./brandforge";
import { buildDeluxeCatalogPayload, buildQuoteReceipt, catalogItemsFromAsset, createPosTicket, deluxeReadiness } from "./pos";

const intakeSchema = z.object({ niche: z.string().min(2).max(240), market: z.string().min(2).max(240), budget: z.string().max(80).optional(), audience: z.string().max(320).optional(), tone: z.string().max(120).optional() });
const brandKitSchema = z.object({ name: z.string().min(2).max(160), palette: z.array(z.string()).min(3).max(6), fonts: z.object({ heading: z.string(), body: z.string() }), voice: z.string().min(2), tagline: z.string().min(2), offer: z.string().min(2) });
const imageDataSchema = z.string().startsWith("data:image/").max(4_500_000);
const economicsSchema = z.object({ monthlyBudget: z.number().min(0).max(10_000_000), averageOrderValue: z.number().min(0).max(10_000_000), grossMarginPct: z.number().min(0).max(100), leadToBookingPct: z.number().min(0).max(100), costPerLead: z.number().positive().max(1_000_000) });
const posPayloadSchema = z.object({}).catchall(z.unknown());
const posTicketLineSchema = z.object({ id: z.string().min(1).max(120), name: z.string().min(1).max(160), unitPriceCents: z.number().int().min(0).max(10_000_000), quantity: z.number().int().min(1).max(100) });

export const appRouter = router({
  system: systemRouter,
  auth: router({
    me: publicProcedure.query((opts) => opts.ctx.user),
    logout: publicProcedure.mutation(({ ctx }) => { const cookieOptions = getSessionCookieOptions(ctx.req); ctx.res.clearCookie(COOKIE_NAME, { ...cookieOptions, maxAge: -1 }); return { success: true } as const; }),
  }),
  studio: router({
    generateStrategy: publicProcedure.input(intakeSchema).mutation(async ({ input, ctx }) => {
      const generated = await generateStrategy(input); const projectId = await db.createProject({ ...input, userId: ctx.user?.id });
      if (projectId) await db.saveNicheOptions(projectId, generated.options as unknown as Array<Record<string, unknown>>);
      return { ...generated, projectId: projectId ?? 0 };
    }),
    lockBrandKit: publicProcedure.input(z.object({ projectId: z.number().int().nonnegative(), strategyOptionId: z.number().int().optional(), kit: brandKitSchema })).mutation(async ({ input }) => {
      const id = input.projectId ? await db.lockBrandKit({ projectId: input.projectId, strategyOptionId: input.strategyOptionId, ...input.kit }) : null; return { id: id ?? 0, kit: input.kit };
    }),
    generateAsset: publicProcedure.input(z.object({ brandKitId: z.number().int().nonnegative(), type: z.enum(["deck", "website", "email", "pos", "logo"]), variant: z.number().int().min(1).max(3), kit: brandKitSchema })).mutation(async ({ input }) => {
      const generated = await generateAsset(input.type, input.variant, input.kit); const id = input.brandKitId ? await db.saveAsset({ brandKitId: input.brandKitId, type: input.type, variant: input.variant, provider: generated.provider, payload: generated.payload }) : null; return { id: id ?? 0, ...generated };
    }),
    generateVisual: publicProcedure.input(z.object({ brandKitId: z.number().int().nonnegative(), provider: z.string().min(2).max(40), kit: brandKitSchema })).mutation(async ({ input }) => {
      const generated = await createCampaignVisual(input.kit, input.provider); const id = input.brandKitId ? await db.saveAsset({ brandKitId: input.brandKitId, type: "visual", variant: 1, provider: generated.provider, payload: { prompt: generated.prompt }, previewUrl: generated.url ?? undefined }) : null; return { id: id ?? 0, ...generated };
    }),
    recognizePhoto: publicProcedure.input(z.object({ dataUrl: imageDataSchema, filename: z.string().min(1).max(160) })).mutation(async ({ input }) => recognizePhoto(input.dataUrl, input.filename)),
    upscaleVisual: publicProcedure.input(z.object({ dataUrl: imageDataSchema })).mutation(async ({ input }) => ({ url: await upscaleImage(input.dataUrl) })),
    makeVoicePrompt: publicProcedure.input(brandKitSchema).query(({ input }) => ({ prompt: makeTtsPrompt(input) })),
    modelEconomics: publicProcedure.input(economicsSchema.extend({ brandKitId: z.number().int().nonnegative() })).mutation(async ({ input }) => {
      const { brandKitId, ...economicsInput } = input; const model = calculateCampaignEconomics(economicsInput);
      const id = brandKitId ? await db.saveAsset({ brandKitId, type: "finance", variant: 1, provider: "deterministic model", payload: model }) : null;
      return { id: id ?? 0, ...model };
    }),
    createVideoPlan: publicProcedure.input(z.object({ brandKitId: z.number().int().nonnegative(), kit: brandKitSchema, objective: z.string().min(5).max(320) })).mutation(async ({ input }) => {
      const generated = await generateVideoPlan(input.kit, input.objective); const id = input.brandKitId ? await db.saveAsset({ brandKitId: input.brandKitId, type: "video", variant: 1, provider: generated.provider, payload: generated.plan }) : null; return { id: id ?? 0, ...generated };
    }),
    createManimPlan: publicProcedure.input(z.object({ brandKitId: z.number().int().nonnegative(), kit: brandKitSchema, economics: economicsSchema })).mutation(async ({ input }) => {
      const plan = createManimPlan(input.kit, calculateCampaignEconomics(input.economics)); const id = input.brandKitId ? await db.saveAsset({ brandKitId: input.brandKitId, type: "animation", variant: 1, provider: "ManimCE", payload: plan }) : null; return { id: id ?? 0, plan };
    }),
    createSocialPack: publicProcedure.input(z.object({ brandKitId: z.number().int().nonnegative(), kit: brandKitSchema, objective: z.string().min(5).max(320) })).mutation(async ({ input }) => {
      const generated = await generateSocialPack(input.kit, input.objective); const id = input.brandKitId ? await db.saveAsset({ brandKitId: input.brandKitId, type: "social", variant: 1, provider: generated.provider, payload: generated.pack }) : null; return { id: id ?? 0, ...generated };
    }),
    pos: router({
      catalog: publicProcedure.input(z.object({ payload: posPayloadSchema })).query(({ input }) => ({ items: catalogItemsFromAsset(input.payload) })),
      createTicket: publicProcedure.input(z.object({ brandKitId: z.number().int().nonnegative(), lines: z.array(posTicketLineSchema).min(1).max(80), taxRateBps: z.number().int().min(0).max(2_000), tipRateBps: z.number().int().min(0).max(5_000) })).mutation(async ({ input }) => {
        const ticket = createPosTicket(input);
        const id = input.brandKitId ? await db.savePosTicket({ brandKitId: input.brandKitId, ...ticket, payload: ticket as unknown as Record<string, unknown> }) : null;
        return { id: id ?? 0, ...ticket };
      }),
      listTickets: publicProcedure.input(z.object({ brandKitId: z.number().int().positive() })).query(({ input }) => db.listPosTickets(input.brandKitId)),
      buildReceipt: publicProcedure.input(z.object({ brandName: z.string().min(2).max(160), locationName: z.string().min(2).max(160), receiptFooter: z.string().min(2).max(320), ticket: z.object({ ticketNumber: z.string(), currency: z.literal("USD"), lines: z.array(posTicketLineSchema.extend({ lineTotalCents: z.number().int().min(0) })), subtotalCents: z.number().int().min(0), taxRateBps: z.number().int().min(0), taxCents: z.number().int().min(0), tipRateBps: z.number().int().min(0), tipCents: z.number().int().min(0), totalCents: z.number().int().min(0), status: z.literal("quote"), paymentBoundary: z.string() }) })).mutation(({ input }) => ({ receipt: buildQuoteReceipt(input) })),
      deluxeReadiness: publicProcedure.query(() => deluxeReadiness()),
      buildDeluxeCatalog: publicProcedure.input(z.object({ brandName: z.string().min(2).max(160), catalog: posPayloadSchema, taxRateBps: z.number().int().min(0).max(2_000), locationName: z.string().min(2).max(160), receiptFooter: z.string().min(2).max(320) })).mutation(({ input }) => ({ payload: buildDeluxeCatalogPayload(input) })),
    }),
    listAssets: publicProcedure.input(z.object({ brandKitId: z.number().int().positive() })).query(({ input }) => db.listBrandAssets(input.brandKitId)),
  }),
});
export type AppRouter = typeof appRouter;
