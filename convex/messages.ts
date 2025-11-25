import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

const MAX_MESSAGES_PER_USER = 20;

export const saveMessage = mutation({
    args: {
        telegram_id: v.number(),
        role: v.string(),
        content: v.string(),
    },
    handler: async (ctx, args) => {
        return await ctx.db.insert("messages", {
            telegram_id: args.telegram_id,
            role: args.role,
            content: args.content,
            created_at: Date.now(),
        });
    },
});

export const getMessages = query({
    args: {
        telegram_id: v.number(),
        limit: v.optional(v.number()),
    },
    handler: async (ctx, args) => {
        const limit = args.limit ?? MAX_MESSAGES_PER_USER;
        const messages = await ctx.db
            .query("messages")
            .withIndex("by_telegram_id", (q) => q.eq("telegram_id", args.telegram_id))
            .order("desc")
            .take(limit);

        // Return in chronological order (oldest first)
        return messages.reverse();
    },
});

export const clearMessages = mutation({
    args: { telegram_id: v.number() },
    handler: async (ctx, args) => {
        const messages = await ctx.db
            .query("messages")
            .withIndex("by_telegram_id", (q) => q.eq("telegram_id", args.telegram_id))
            .collect();

        for (const msg of messages) {
            await ctx.db.delete(msg._id);
        }

        return { deleted: messages.length };
    },
});
