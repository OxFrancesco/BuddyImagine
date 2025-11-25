import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

export default defineSchema({
    users: defineTable({
        telegram_id: v.number(),
        username: v.optional(v.string()),
        first_name: v.string(),
        last_name: v.optional(v.string()),
        credits: v.float64(),
        default_model: v.optional(v.string()),
        created_at: v.number(),
        // User settings for credit system
        save_uncompressed_to_r2: v.optional(v.boolean()), // +10% cost, saves full quality to R2
        telegram_quality: v.optional(v.string()), // "compressed" | "uncompressed" (default: uncompressed)
        notify_low_credits: v.optional(v.boolean()),
        low_credit_threshold: v.optional(v.float64()), // default: 10
    }).index("by_telegram_id", ["telegram_id"]),

    messages: defineTable({
        telegram_id: v.number(),
        role: v.string(), // "user" or "assistant"
        content: v.string(),
        created_at: v.number(),
    }).index("by_telegram_id", ["telegram_id"]),

    credit_logs: defineTable({
        telegram_id: v.number(),
        amount: v.float64(), // positive=add, negative=deduct
        balance_after: v.float64(),
        type: v.string(), // "purchase" | "generation" | "refund" | "admin" | "subscription"
        description: v.string(),
        model_used: v.optional(v.string()),
        r2_filename: v.optional(v.string()),
        created_at: v.number(),
    })
        .index("by_telegram_id", ["telegram_id"])
        .index("by_type", ["type"]),
});
