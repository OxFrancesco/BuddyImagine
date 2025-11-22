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
    }).index("by_telegram_id", ["telegram_id"]),
});
