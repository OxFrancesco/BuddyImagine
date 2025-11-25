import { query } from "./_generated/server";
import { v } from "convex/values";

export const getCreditHistory = query({
    args: {
        telegram_id: v.number(),
        limit: v.optional(v.number()),
    },
    handler: async (ctx, args) => {
        const limit = args.limit ?? 50;
        const logs = await ctx.db
            .query("credit_logs")
            .withIndex("by_telegram_id", (q) => q.eq("telegram_id", args.telegram_id))
            .order("desc")
            .take(limit);

        return logs;
    },
});

export const getCreditSummary = query({
    args: { telegram_id: v.number() },
    handler: async (ctx, args) => {
        const user = await ctx.db
            .query("users")
            .withIndex("by_telegram_id", (q) => q.eq("telegram_id", args.telegram_id))
            .first();

        if (!user) {
            return null;
        }

        const logs = await ctx.db
            .query("credit_logs")
            .withIndex("by_telegram_id", (q) => q.eq("telegram_id", args.telegram_id))
            .collect();

        let totalSpent = 0;
        let totalAdded = 0;
        let generationCount = 0;

        for (const log of logs) {
            if (log.amount < 0) {
                totalSpent += Math.abs(log.amount);
                if (log.type === "generation") {
                    generationCount++;
                }
            } else {
                totalAdded += log.amount;
            }
        }

        return {
            current_balance: user.credits,
            total_spent: totalSpent,
            total_added: totalAdded,
            generation_count: generationCount,
        };
    },
});
