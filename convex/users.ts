import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

export const upsertUser = mutation({
    args: {
        telegram_id: v.number(),
        username: v.optional(v.string()),
        first_name: v.string(),
        last_name: v.optional(v.string()),
        default_model: v.optional(v.string()),
    },
    handler: async (ctx, args) => {
        const existing = await ctx.db
            .query("users")
            .withIndex("by_telegram_id", (q) => q.eq("telegram_id", args.telegram_id))
            .first();

        if (existing) {
            await ctx.db.patch(existing._id, {
                username: args.username,
                first_name: args.first_name,
                last_name: args.last_name,
                // Don't overwrite default_model if it's not provided in args (preserve user preference)
                ...(args.default_model !== undefined ? { default_model: args.default_model } : {}),
            });
            return existing._id;
        } else {
            // New users get limited initial credits (10) to prevent abuse
            // Admins can add more credits via addCreditsWithLog
            return await ctx.db.insert("users", {
                telegram_id: args.telegram_id,
                username: args.username,
                first_name: args.first_name,
                last_name: args.last_name,
                credits: 10.0, // Reduced from 100 to prevent multi-account abuse
                default_model: args.default_model,
                created_at: Date.now(),
            });
        }
    },
});

export const getUser = query({
    args: { telegram_id: v.number() },
    handler: async (ctx, args) => {
        return await ctx.db
            .query("users")
            .withIndex("by_telegram_id", (q) => q.eq("telegram_id", args.telegram_id))
            .first();
    },
});

export const setDefaultModel = mutation({
    args: { telegram_id: v.number(), model_id: v.string() },
    handler: async (ctx, args) => {
        const user = await ctx.db
            .query("users")
            .withIndex("by_telegram_id", (q) => q.eq("telegram_id", args.telegram_id))
            .first();

        if (!user) {
            throw new Error("User not found");
        }

        await ctx.db.patch(user._id, {
            default_model: args.model_id,
        });

        return { success: true, model_id: args.model_id };
    },
});

export const deductCredits = mutation({
    args: { telegram_id: v.number(), amount: v.float64() },
    handler: async (ctx, args) => {
        const user = await ctx.db
            .query("users")
            .withIndex("by_telegram_id", (q) => q.eq("telegram_id", args.telegram_id))
            .first();

        if (!user) {
            throw new Error("User not found");
        }

        if (user.credits < args.amount) {
            return { success: false, message: "Insufficient credits", current_credits: user.credits };
        }

        await ctx.db.patch(user._id, {
            credits: user.credits - args.amount,
        });

        return { success: true, current_credits: user.credits - args.amount };
    },
});

export const refundCredits = mutation({
    args: { telegram_id: v.number(), amount: v.float64() },
    handler: async (ctx, args) => {
        const user = await ctx.db
            .query("users")
            .withIndex("by_telegram_id", (q) => q.eq("telegram_id", args.telegram_id))
            .first();

        if (!user) {
            throw new Error("User not found");
        }

        await ctx.db.patch(user._id, {
            credits: user.credits + args.amount,
        });

        return { success: true, current_credits: user.credits + args.amount };
    },
});

export const getCredits = query({
    args: { telegram_id: v.number() },
    handler: async (ctx, args) => {
        const user = await ctx.db
            .query("users")
            .withIndex("by_telegram_id", (q) => q.eq("telegram_id", args.telegram_id))
            .first();

        return user ? user.credits : 0;
    },
});

export const updateUserSettings = mutation({
    args: {
        telegram_id: v.number(),
        save_uncompressed_to_r2: v.optional(v.boolean()),
        telegram_quality: v.optional(v.string()),
        notify_low_credits: v.optional(v.boolean()),
        low_credit_threshold: v.optional(v.float64()),
    },
    handler: async (ctx, args) => {
        const user = await ctx.db
            .query("users")
            .withIndex("by_telegram_id", (q) => q.eq("telegram_id", args.telegram_id))
            .first();

        if (!user) {
            throw new Error("User not found");
        }

        const updates: Record<string, boolean | string | number> = {};
        if (args.save_uncompressed_to_r2 !== undefined) {
            updates.save_uncompressed_to_r2 = args.save_uncompressed_to_r2;
        }
        if (args.telegram_quality !== undefined) {
            updates.telegram_quality = args.telegram_quality;
        }
        if (args.notify_low_credits !== undefined) {
            updates.notify_low_credits = args.notify_low_credits;
        }
        if (args.low_credit_threshold !== undefined) {
            updates.low_credit_threshold = args.low_credit_threshold;
        }

        await ctx.db.patch(user._id, updates);
        return { success: true };
    },
});

export const getUserSettings = query({
    args: { telegram_id: v.number() },
    handler: async (ctx, args) => {
        const user = await ctx.db
            .query("users")
            .withIndex("by_telegram_id", (q) => q.eq("telegram_id", args.telegram_id))
            .first();

        if (!user) {
            return null;
        }

        return {
            telegram_id: user.telegram_id,
            credits: user.credits,
            default_model: user.default_model ?? "fal-ai/fast-sdxl",
            save_uncompressed_to_r2: user.save_uncompressed_to_r2 ?? false,
            telegram_quality: user.telegram_quality ?? "uncompressed",
            notify_low_credits: user.notify_low_credits ?? true,
            low_credit_threshold: user.low_credit_threshold ?? 10,
            last_generated_image: user.last_generated_image,
        };
    },
});

export const setLastGeneratedImage = mutation({
    args: { telegram_id: v.number(), filename: v.string() },
    handler: async (ctx, args) => {
        const user = await ctx.db
            .query("users")
            .withIndex("by_telegram_id", (q) => q.eq("telegram_id", args.telegram_id))
            .first();

        if (!user) {
            throw new Error("User not found");
        }

        await ctx.db.patch(user._id, {
            last_generated_image: args.filename,
        });

        return { success: true };
    },
});

export const getLastGeneratedImage = query({
    args: { telegram_id: v.number() },
    handler: async (ctx, args) => {
        const user = await ctx.db
            .query("users")
            .withIndex("by_telegram_id", (q) => q.eq("telegram_id", args.telegram_id))
            .first();

        return user?.last_generated_image ?? null;
    },
});

export const deductCreditsWithLog = mutation({
    args: {
        telegram_id: v.number(),
        amount: v.float64(),
        type: v.string(),
        description: v.string(),
        model_used: v.optional(v.string()),
        r2_filename: v.optional(v.string()),
    },
    handler: async (ctx, args) => {
        const user = await ctx.db
            .query("users")
            .withIndex("by_telegram_id", (q) => q.eq("telegram_id", args.telegram_id))
            .first();

        if (!user) {
            throw new Error("User not found");
        }

        if (user.credits < args.amount) {
            return { success: false, message: "Insufficient credits", current_credits: user.credits };
        }

        const newBalance = user.credits - args.amount;

        await ctx.db.patch(user._id, { credits: newBalance });

        await ctx.db.insert("credit_logs", {
            telegram_id: args.telegram_id,
            amount: -args.amount,
            balance_after: newBalance,
            type: args.type,
            description: args.description,
            model_used: args.model_used,
            r2_filename: args.r2_filename,
            created_at: Date.now(),
        });

        return { success: true, current_credits: newBalance };
    },
});

export const addCreditsWithLog = mutation({
    args: {
        telegram_id: v.number(),
        amount: v.float64(),
        type: v.string(),
        description: v.string(),
    },
    handler: async (ctx, args) => {
        const user = await ctx.db
            .query("users")
            .withIndex("by_telegram_id", (q) => q.eq("telegram_id", args.telegram_id))
            .first();

        if (!user) {
            throw new Error("User not found");
        }

        const newBalance = user.credits + args.amount;

        await ctx.db.patch(user._id, { credits: newBalance });

        await ctx.db.insert("credit_logs", {
            telegram_id: args.telegram_id,
            amount: args.amount,
            balance_after: newBalance,
            type: args.type,
            description: args.description,
            created_at: Date.now(),
        });

        return { success: true, current_credits: newBalance };
    },
});
