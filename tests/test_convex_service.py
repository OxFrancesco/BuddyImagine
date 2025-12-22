import pytest
from unittest.mock import MagicMock, patch


class TestConvexService:
    @pytest.fixture
    def mock_convex_client(self):
        with patch("imagine.services.convex.ConvexClient") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client
            yield mock_client

    @pytest.fixture
    def convex_service(self, mock_convex_client):
        with patch.dict("os.environ", {"CONVEX_URL": "https://fake.convex.cloud"}):
            from imagine.services.convex import ConvexService
            service = ConvexService()
            return service

    def test_upsert_user(self, convex_service, mock_convex_client):
        mock_convex_client.mutation.return_value = "user_id_123"

        result = convex_service.upsert_user(
            telegram_id=12345,
            first_name="John",
            username="johndoe",
            last_name="Doe"
        )

        assert result == "user_id_123"
        mock_convex_client.mutation.assert_called_once_with(
            "users:upsertUser",
            {
                "telegram_id": 12345,
                "first_name": "John",
                "username": "johndoe",
                "last_name": "Doe"
            }
        )

    def test_upsert_user_minimal(self, convex_service, mock_convex_client):
        mock_convex_client.mutation.return_value = "user_id_123"

        result = convex_service.upsert_user(telegram_id=12345, first_name="John")

        mock_convex_client.mutation.assert_called_once_with(
            "users:upsertUser",
            {"telegram_id": 12345, "first_name": "John"}
        )

    def test_get_user(self, convex_service, mock_convex_client):
        mock_convex_client.query.return_value = {
            "telegram_id": 12345,
            "first_name": "John",
            "credits": 100.0
        }

        result = convex_service.get_user(12345)

        assert result["telegram_id"] == 12345
        mock_convex_client.query.assert_called_once_with(
            "users:getUser",
            {"telegram_id": 12345}
        )

    def test_set_default_model(self, convex_service, mock_convex_client):
        convex_service.set_default_model(12345, "fal-ai/flux/dev")

        mock_convex_client.mutation.assert_called_once_with(
            "users:setDefaultModel",
            {"telegram_id": 12345, "model_id": "fal-ai/flux/dev"}
        )

    def test_deduct_credits(self, convex_service, mock_convex_client):
        mock_convex_client.mutation.return_value = {"success": True, "current_credits": 95.0}

        result = convex_service.deduct_credits(12345, 5.0)

        assert result["success"] is True
        assert result["current_credits"] == 95.0
        mock_convex_client.mutation.assert_called_once_with(
            "users:deductCredits",
            {"telegram_id": 12345, "amount": 5.0}
        )

    def test_refund_credits(self, convex_service, mock_convex_client):
        convex_service.refund_credits(12345, 5.0)

        mock_convex_client.mutation.assert_called_once_with(
            "users:refundCredits",
            {"telegram_id": 12345, "amount": 5.0}
        )

    def test_get_credits(self, convex_service, mock_convex_client):
        mock_convex_client.query.return_value = 100.0

        result = convex_service.get_credits(12345)

        assert result == 100.0
        mock_convex_client.query.assert_called_once_with(
            "users:getCredits",
            {"telegram_id": 12345}
        )

    def test_save_message(self, convex_service, mock_convex_client):
        convex_service.save_message(12345, "user", "Hello!")

        mock_convex_client.mutation.assert_called_once_with(
            "messages:saveMessage",
            {"telegram_id": 12345, "role": "user", "content": "Hello!"}
        )

    def test_get_messages(self, convex_service, mock_convex_client):
        mock_convex_client.query.return_value = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]

        result = convex_service.get_messages(12345, limit=10)

        assert len(result) == 2
        mock_convex_client.query.assert_called_once_with(
            "messages:getMessages",
            {"telegram_id": 12345, "limit": 10}
        )

    def test_get_messages_empty(self, convex_service, mock_convex_client):
        mock_convex_client.query.return_value = None

        result = convex_service.get_messages(12345)

        assert result == []

    def test_clear_messages(self, convex_service, mock_convex_client):
        mock_convex_client.mutation.return_value = {"deleted": 5}

        result = convex_service.clear_messages(12345)

        assert result["deleted"] == 5
        mock_convex_client.mutation.assert_called_once_with(
            "messages:clearMessages",
            {"telegram_id": 12345}
        )

    def test_update_user_settings(self, convex_service, mock_convex_client):
        convex_service.update_user_settings(
            12345,
            save_uncompressed_to_r2=True,
            telegram_quality="compressed"
        )

        mock_convex_client.mutation.assert_called_once_with(
            "users:updateUserSettings",
            {
                "telegram_id": 12345,
                "save_uncompressed_to_r2": True,
                "telegram_quality": "compressed"
            }
        )

    def test_get_user_settings(self, convex_service, mock_convex_client):
        mock_convex_client.query.return_value = {
            "telegram_quality": "uncompressed",
            "save_uncompressed_to_r2": False
        }

        result = convex_service.get_user_settings(12345)

        assert result["telegram_quality"] == "uncompressed"
        mock_convex_client.query.assert_called_once_with(
            "users:getUserSettings",
            {"telegram_id": 12345}
        )

    def test_get_user_settings_none(self, convex_service, mock_convex_client):
        mock_convex_client.query.return_value = None

        result = convex_service.get_user_settings(12345)

        assert result is None

    def test_deduct_credits_with_log(self, convex_service, mock_convex_client):
        mock_convex_client.mutation.return_value = {"success": True, "current_credits": 90.0}

        result = convex_service.deduct_credits_with_log(
            telegram_id=12345,
            amount=10.0,
            log_type="generation",
            description="Test generation",
            model_used="fal-ai/flux/dev"
        )

        assert result["success"] is True
        mock_convex_client.mutation.assert_called_once_with(
            "users:deductCreditsWithLog",
            {
                "telegram_id": 12345,
                "amount": 10.0,
                "type": "generation",
                "description": "Test generation",
                "model_used": "fal-ai/flux/dev"
            }
        )

    def test_add_credits_with_log(self, convex_service, mock_convex_client):
        convex_service.add_credits_with_log(
            telegram_id=12345,
            amount=50.0,
            log_type="topup",
            description="Admin topup"
        )

        mock_convex_client.mutation.assert_called_once_with(
            "users:addCreditsWithLog",
            {
                "telegram_id": 12345,
                "amount": 50.0,
                "type": "topup",
                "description": "Admin topup"
            }
        )

    def test_get_credit_history(self, convex_service, mock_convex_client):
        mock_convex_client.query.return_value = [
            {"amount": -5.0, "type": "generation", "description": "Gen 1"},
            {"amount": 50.0, "type": "topup", "description": "Topup"}
        ]

        result = convex_service.get_credit_history(12345, limit=10)

        assert len(result) == 2
        mock_convex_client.query.assert_called_once_with(
            "creditLogs:getCreditHistory",
            {"telegram_id": 12345, "limit": 10}
        )

    def test_get_credit_summary(self, convex_service, mock_convex_client):
        mock_convex_client.query.return_value = {
            "current_balance": 95.0,
            "total_spent": 55.0,
            "total_added": 150.0,
            "generation_count": 10
        }

        result = convex_service.get_credit_summary(12345)

        assert result["current_balance"] == 95.0
        assert result["generation_count"] == 10
