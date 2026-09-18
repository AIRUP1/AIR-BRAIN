import { z } from "zod";
import { COOKIE_NAME } from "@shared/const";
import { getSessionCookieOptions } from "./_core/cookies";
import { systemRouter } from "./_core/systemRouter";
import { publicProcedure, router } from "./_core/trpc";
import * as db from "./db";
import { createCampaignVisual, generateAsset, generateStrategy, makeTtsPrompt, recognizePhoto, upscaleImage } from "./brandforge";

const intakeSchema = z.object({ niche: z.string().min(2).max(240), market: z.string().min(2).max(240), budget: z.string().max(80).optional(), audience: z.string().max(320).optional(), tone: z.string().max(120).optional() });
const brandKitSchema = z.object({ name: z.string().min(2).max(160), palette: z.array(z.string()).min(3).max(6), fonts: z.object({ heading: z.string(), body: z.string() }), voice: z.string().min(2), tagline: z.string().min(2), offer: z.string().min(2) });
const imageDataSchema = z.string().startsWith("data:image/").max(4_500_000);

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
    listAssets: publicProcedure.input(z.object({ brandKitId: z.number().int().positive() })).query(({ input }) => db.listBrandAssets(input.brandKitId)),
  }),
});
export type AppRouter = typeof appRouter;
