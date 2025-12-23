"""Payment handlers for Telegram native payments."""

import os
import logging
from typing import Optional
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    PreCheckoutQuery,
    LabeledPrice,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from imagine.services.convex import ConvexService

logger = logging.getLogger(__name__)

router = Router()

# Initialize Convex service
convex_service: Optional[ConvexService] = None
try:
    convex_service = ConvexService()
except ValueError:
    logger.warning("ConvexService not initialized for payments. CONVEX_URL not set.")

from typing import TypedDict


class CreditPackage(TypedDict):
    id: str
    name: str
    credits: int
    price_cents: int
    description: str


# Credit packages available for purchase
CREDIT_PACKAGES: list[CreditPackage] = [
    {"id": "credits_50", "name": "50 Credits", "credits": 50, "price_cents": 499, "description": "Good for ~10-25 generations"},
    {"id": "credits_100", "name": "100 Credits", "credits": 100, "price_cents": 899, "description": "Good for ~20-50 generations"},
    {"id": "credits_250", "name": "250 Credits", "credits": 250, "price_cents": 1999, "description": "Good for ~50-125 generations"},
    {"id": "credits_500", "name": "500 Credits", "credits": 500, "price_cents": 3499, "description": "Good for ~100-250 generations"},
]


def get_payment_token() -> str | None:
    """Get the Telegram payment provider token."""
    return os.getenv("TELEGRAM_PAYMENT_TOKEN")


@router.message(Command("buy"))
async def cmd_buy(message: Message):
    """Show available credit packages for purchase."""
    if not message.from_user:
        return

    payment_token = get_payment_token()
    if not payment_token:
        await message.answer(
            "💳 **Payments not configured**\n\n"
            "Payment system is not available yet. Please contact the administrator.",
            parse_mode="Markdown"
        )
        return

    # Build inline keyboard with package options
    keyboard = []
    for pkg in CREDIT_PACKAGES:
        price_display = f"${pkg['price_cents'] / 100:.2f}"
        keyboard.append([
            InlineKeyboardButton(
                text=f"💎 {pkg['name']} - {price_display}",
                callback_data=f"buy:{pkg['id']}"
            )
        ])

    # Get current balance if available
    balance_text = ""
    if convex_service:
        current_balance = convex_service.get_credits(message.from_user.id)
        balance_text = f"\n\n💰 **Your current balance**: {current_balance:.2f} credits"

    pkg_lines = "\n".join([
        f"• **{pkg['name']}** - ${pkg['price_cents'] / 100:.2f}\n  _{pkg['description']}_"
        for pkg in CREDIT_PACKAGES
    ])
    await message.answer(
        "💎 **Buy Credits**\n\n"
        "Select a credit package to purchase:\n\n"
        + pkg_lines
        + balance_text
        + "\n\n_Payments are processed securely via Telegram._",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="Markdown"
    )


@router.callback_query(F.data.startswith("buy:"))
async def process_buy_callback(callback: CallbackQuery):
    """Handle credit package selection and send invoice."""
    if not callback.data or not callback.message:
        return

    package_id = callback.data.split(":")[1]
    
    # Find the selected package
    package = next((p for p in CREDIT_PACKAGES if p["id"] == package_id), None)
    if not package:
        await callback.answer("Package not found", show_alert=True)
        return

    payment_token = get_payment_token()
    if not payment_token:
        await callback.answer("Payment system unavailable", show_alert=True)
        return

    # Create invoice payload with user and package info
    payload = f"{callback.from_user.id}:{package_id}:{package['credits']}"

    try:
        await callback.message.answer_invoice(
            title=f"BuddyImagine - {package['name']}",
            description=f"Purchase {package['credits']} credits for AI image generation. {package['description']}.",
            payload=payload,
            provider_token=payment_token,
            currency="USD",
            prices=[
                LabeledPrice(label=package['name'], amount=package['price_cents'])
            ],
            start_parameter=f"buy_{package_id}",
            photo_url="https://buddytools.org/logo.png",
            photo_width=512,
            photo_height=512,
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Failed to send invoice: {e}")
        await callback.answer("Failed to create invoice. Please try again.", show_alert=True)


@router.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    """
    Handle pre-checkout query - validate the order before payment.
    Must respond within 10 seconds.
    """
    try:
        # Parse payload to validate
        payload_parts = pre_checkout_query.invoice_payload.split(":")
        if len(payload_parts) != 3:
            await pre_checkout_query.answer(
                ok=False,
                error_message="Invalid payment data. Please try again."
            )
            return

        user_id, package_id, credits = payload_parts
        
        # Validate package exists
        package = next((p for p in CREDIT_PACKAGES if p["id"] == package_id), None)
        if not package:
            await pre_checkout_query.answer(
                ok=False,
                error_message="Selected package is no longer available."
            )
            return

        # Validate credits match
        if str(package['credits']) != credits:
            await pre_checkout_query.answer(
                ok=False,
                error_message="Package details have changed. Please try again."
            )
            return

        # All validations passed
        await pre_checkout_query.answer(ok=True)
        logger.info(f"Pre-checkout approved for user {user_id}, package {package_id}")

    except Exception as e:
        logger.error(f"Pre-checkout error: {e}")
        await pre_checkout_query.answer(
            ok=False,
            error_message="An error occurred. Please try again."
        )


@router.message(F.successful_payment)
async def successful_payment_handler(message: Message):
    """Handle successful payment - add credits to user account."""
    if not message.successful_payment or not message.from_user:
        return

    payment = message.successful_payment
    
    try:
        # Parse payload
        payload_parts = payment.invoice_payload.split(":")
        if len(payload_parts) != 3:
            logger.error(f"Invalid payment payload: {payment.invoice_payload}")
            await message.answer("❌ Payment received but credits could not be added. Please contact support.")
            return

        user_id_str, package_id, credits_str = payload_parts
        credits_amount = float(credits_str)

        # Find package for description
        package = next((p for p in CREDIT_PACKAGES if p["id"] == package_id), None)
        package_name = package['name'] if package else f"{credits_amount} Credits"

        if not convex_service:
            logger.error("ConvexService not available for payment processing")
            await message.answer(
                "✅ Payment received!\n\n"
                f"💳 Amount: ${payment.total_amount / 100:.2f} {payment.currency}\n"
                f"📦 Package: {package_name}\n\n"
                "⚠️ Credits will be added shortly. Please contact support if not received within 24 hours."
            )
            return

        # Add credits to user account
        result = convex_service.add_credits_with_log(
            telegram_id=message.from_user.id,
            amount=credits_amount,
            log_type="purchase",
            description=f"Purchased {package_name} - Telegram Payment ID: {payment.telegram_payment_charge_id[:20]}..."
        )

        if result and result.get("success"):
            new_balance = result.get("current_credits", 0)
            
            # Record payment in payments table
            try:
                convex_service.record_payment(
                    telegram_id=message.from_user.id,
                    amount_cents=payment.total_amount,
                    currency=payment.currency,
                    credits_added=credits_amount,
                    package_id=package_id,
                    telegram_payment_charge_id=payment.telegram_payment_charge_id,
                    provider_payment_charge_id=payment.provider_payment_charge_id,
                )
            except Exception as record_err:
                logger.error(f"Failed to record payment: {record_err}")

            await message.answer(
                "🎉 **Payment Successful!**\n\n"
                f"💳 Amount: ${payment.total_amount / 100:.2f} {payment.currency}\n"
                f"💎 Credits added: {credits_amount:.0f}\n"
                f"💰 New balance: {new_balance:.2f} credits\n\n"
                "Thank you for your purchase! Start generating images with /imagine",
                parse_mode="Markdown"
            )
            logger.info(
                f"Payment successful: user={message.from_user.id}, "
                f"credits={credits_amount}, charge_id={payment.telegram_payment_charge_id}"
            )
        else:
            logger.error(f"Failed to add credits: {result}")
            await message.answer(
                "✅ Payment received but there was an issue adding credits.\n"
                "Please contact support with your payment ID:\n"
                f"`{payment.telegram_payment_charge_id}`",
                parse_mode="Markdown"
            )

    except Exception as e:
        logger.error(f"Payment processing error: {e}")
        await message.answer(
            "✅ Payment received but there was an error.\n"
            "Please contact support with your payment ID:\n"
            f"`{payment.telegram_payment_charge_id}`",
            parse_mode="Markdown"
        )


@router.message(Command("payments"))
async def cmd_payments(message: Message):
    """Show payment history."""
    if not message.from_user:
        return

    if not convex_service:
        await message.answer("Service unavailable.")
        return

    payments = convex_service.get_payment_history(message.from_user.id, limit=10)
    
    if not payments:
        await message.answer(
            "📜 **Payment History**\n\n"
            "No payments found.\n\n"
            "Use /buy to purchase credits.",
            parse_mode="Markdown"
        )
        return

    response = "📜 **Payment History** (last 10):\n\n"
    for p in payments:
        response += (
            f"• ${p['amount_cents'] / 100:.2f} {p['currency']} → "
            f"+{p['credits_added']:.0f} credits\n"
        )

    response += "\n_Use /credits to see your current balance._"
    await message.answer(response, parse_mode="Markdown")
