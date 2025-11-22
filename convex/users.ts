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
            return await ctx.db.insert("users", {
                telegram_id: args.telegram_id,
                username: args.username,
                first_name: args.first_name,
                last_name: args.last_name,
                credits: 100.0, // Default credits
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
