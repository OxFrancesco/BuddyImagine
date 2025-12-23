"""Tests for payment handlers."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.types import (
    Message,
    User,
    Chat,
    CallbackQuery,
    PreCheckoutQuery,
    SuccessfulPayment,
)


class TestCreditPackages:
    def test_credit_packages_defined(self):
        from imagine.handlers_payments import CREDIT_PACKAGES
        
        assert len(CREDIT_PACKAGES) > 0
        for pkg in CREDIT_PACKAGES:
            assert "id" in pkg
            assert "name" in pkg
            assert "credits" in pkg
            assert "price_cents" in pkg
            assert pkg["credits"] > 0
            assert pkg["price_cents"] > 0


class TestPreCheckoutHandler:
    @pytest.mark.asyncio
    async def test_pre_checkout_valid_payload(self):
        from imagine.handlers_payments import pre_checkout_handler
        
        mock_query = MagicMock(spec=PreCheckoutQuery)
        mock_query.invoice_payload = "123456:credits_100:100"
        mock_query.answer = AsyncMock()
        
        await pre_checkout_handler(mock_query)
        
        mock_query.answer.assert_called_once_with(ok=True)

    @pytest.mark.asyncio
    async def test_pre_checkout_invalid_payload_format(self):
        from imagine.handlers_payments import pre_checkout_handler
        
        mock_query = MagicMock(spec=PreCheckoutQuery)
        mock_query.invoice_payload = "invalid_payload"
        mock_query.answer = AsyncMock()
        
        await pre_checkout_handler(mock_query)
        
        mock_query.answer.assert_called_once()
        call_args = mock_query.answer.call_args
        assert call_args.kwargs["ok"] is False
        assert "Invalid payment data" in call_args.kwargs["error_message"]

    @pytest.mark.asyncio
    async def test_pre_checkout_nonexistent_package(self):
        from imagine.handlers_payments import pre_checkout_handler
        
        mock_query = MagicMock(spec=PreCheckoutQuery)
        mock_query.invoice_payload = "123456:nonexistent_package:100"
        mock_query.answer = AsyncMock()
        
        await pre_checkout_handler(mock_query)
        
        mock_query.answer.assert_called_once()
        call_args = mock_query.answer.call_args
        assert call_args.kwargs["ok"] is False
        assert "no longer available" in call_args.kwargs["error_message"]

    @pytest.mark.asyncio
    async def test_pre_checkout_mismatched_credits(self):
        from imagine.handlers_payments import pre_checkout_handler
        
        mock_query = MagicMock(spec=PreCheckoutQuery)
        # credits_100 package has 100 credits, but payload says 999
        mock_query.invoice_payload = "123456:credits_100:999"
        mock_query.answer = AsyncMock()
        
        await pre_checkout_handler(mock_query)
        
        mock_query.answer.assert_called_once()
        call_args = mock_query.answer.call_args
        assert call_args.kwargs["ok"] is False
        assert "changed" in call_args.kwargs["error_message"]


class TestSuccessfulPaymentHandler:
    @pytest.mark.asyncio
    async def test_successful_payment_adds_credits(self):
        from imagine.handlers_payments import successful_payment_handler
        
        mock_user = MagicMock(spec=User)
        mock_user.id = 123456
        
        mock_payment = MagicMock(spec=SuccessfulPayment)
        mock_payment.invoice_payload = "123456:credits_100:100"
        mock_payment.total_amount = 899
        mock_payment.currency = "USD"
        mock_payment.telegram_payment_charge_id = "mock_tg_charge_for_test"
        mock_payment.provider_payment_charge_id = "mock_provider_charge_for_test"
        
        mock_message = MagicMock(spec=Message)
        mock_message.successful_payment = mock_payment
        mock_message.from_user = mock_user
        mock_message.answer = AsyncMock()
        
        mock_convex = MagicMock()
        mock_convex.add_credits_with_log.return_value = {"success": True, "current_credits": 110.0}
        mock_convex.record_payment.return_value = "mock_payment_record_id"
        
        with patch("imagine.handlers_payments.convex_service", mock_convex):
            await successful_payment_handler(mock_message)
        
        # Verify credits were added
        mock_convex.add_credits_with_log.assert_called_once()
        call_args = mock_convex.add_credits_with_log.call_args
        assert call_args.kwargs["telegram_id"] == 123456
        assert call_args.kwargs["amount"] == 100.0
        assert call_args.kwargs["log_type"] == "purchase"
        
        # Verify payment was recorded
        mock_convex.record_payment.assert_called_once()
        
        # Verify success message was sent
        mock_message.answer.assert_called_once()
        answer_text = mock_message.answer.call_args[0][0]
        assert "Payment Successful" in answer_text
        assert "100" in answer_text  # credits added


class TestPaymentTokenRetrieval:
    def test_get_payment_returns_env_value(self):
        from imagine.handlers_payments import get_payment_token
        
        # Using obviously fake test value
        fake_value = "FAKE_TEST_VALUE_NOT_REAL"
        with patch.dict("os.environ", {"TELEGRAM_PAYMENT_TOKEN": fake_value}):
            result = get_payment_token()
            assert result == fake_value

    def test_get_payment_returns_none_when_not_set(self):
        from imagine.handlers_payments import get_payment_token
        
        with patch.dict("os.environ", {}, clear=True):
            result = get_payment_token()
            assert result is None
