import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

export const recordPayment = mutation({
    args: {
        telegram_id: v.number(),
        amount_cents: v.number(),
        currency: v.string(),
        credits_added: v.float64(),
        package_id: v.string(),
        telegram_payment_charge_id: v.string(),
        provider_payment_charge_id: v.string(),
    },
    handler: async (ctx, args) => {
        return await ctx.db.insert("payments", {
            telegram_id: args.telegram_id,
            amount_cents: args.amount_cents,
            currency: args.currency,
            credits_added: args.credits_added,
            package_id: args.package_id,
            telegram_payment_charge_id: args.telegram_payment_charge_id,
            provider_payment_charge_id: args.provider_payment_charge_id,
            status: "completed",
            created_at: Date.now(),
        });
    },
});

export const getPaymentHistory = query({
    args: {
        telegram_id: v.number(),
        limit: v.optional(v.number()),
    },
    handler: async (ctx, args) => {
        const limit = args.limit ?? 10;
        const payments = await ctx.db
            .query("payments")
            .withIndex("by_telegram_id", (q) => q.eq("telegram_id", args.telegram_id))
            .order("desc")
            .take(limit);
        return payments;
    },
});

export const getPaymentByChargeId = query({
    args: {
        telegram_payment_charge_id: v.string(),
    },
    handler: async (ctx, args) => {
        return await ctx.db
            .query("payments")
            .withIndex("by_charge_id", (q) => 
                q.eq("telegram_payment_charge_id", args.telegram_payment_charge_id)
            )
            .first();
    },
});

export const markPaymentRefunded = mutation({
    args: {
        telegram_payment_charge_id: v.string(),
    },
    handler: async (ctx, args) => {
        const payment = await ctx.db
            .query("payments")
            .withIndex("by_charge_id", (q) => 
                q.eq("telegram_payment_charge_id", args.telegram_payment_charge_id)
            )
            .first();

        if (!payment) {
            throw new Error("Payment not found");
        }

        await ctx.db.patch(payment._id, { status: "refunded" });
        return { success: true };
    },
});

export const getPaymentStats = query({
    args: {
        telegram_id: v.number(),
    },
    handler: async (ctx, args) => {
        const payments = await ctx.db
            .query("payments")
            .withIndex("by_telegram_id", (q) => q.eq("telegram_id", args.telegram_id))
            .filter((q) => q.eq(q.field("status"), "completed"))
            .collect();

        const totalSpent = payments.reduce((sum, p) => sum + p.amount_cents, 0);
        const totalCredits = payments.reduce((sum, p) => sum + p.credits_added, 0);

        return {
            total_payments: payments.length,
            total_spent_cents: totalSpent,
            total_credits_purchased: totalCredits,
        };
    },
});
