import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone
from jose import jwt
from auth import AuthVerifier


@pytest.fixture
def mock_aws_secret_manager():
    with patch("boto3.client") as mock_boto_client:
        # Mock the Secrets Manager client
        mock_secrets_client = MagicMock()
        mock_boto_client.return_value = mock_secrets_client

        # Mock the response for get_secret_value
        mock_secrets_client.get_secret_value.return_value = {
            "SecretString": "mock-secret"
        }

        yield mock_secrets_client


@pytest.fixture
def mock_env_vars(monkeypatch):
    # Mock environment variables
    monkeypatch.setenv("SECRET_API_KEY", "mock-secret-arn")


@pytest.fixture
def auth_verifier(mock_aws_secret_manager, mock_env_vars):
    # Initialize the AuthVerifier
    return AuthVerifier()


def test_get_secret_success(auth_verifier, mock_aws_secret_manager):
    # Test successful secret retrieval
    assert auth_verifier.secret == "mock-secret"


def test_get_secret_failure(mock_aws_secret_manager, mock_env_vars):
    # Mock a failure in fetching the secret
    mock_aws_secret_manager.get_secret_value.side_effect = Exception("AWS error")

    with pytest.raises(Exception, match="AWS error"):
        AuthVerifier()  # Should raise an exception during initialization


def test_validate_credentials_success(auth_verifier):
    # Test valid credentials
    assert auth_verifier.validate_credentials("demo", "password") is True


def test_validate_credentials_failure(auth_verifier):
    # Test invalid credentials
    assert auth_verifier.validate_credentials("user", "wrong-password") is False


def test_generate_jwt_success(auth_verifier):
    # Test JWT generation
    identity = "test-user"
    token = auth_verifier.generate_jwt(identity)

    # Decode the token to verify its structure and contents
    decoded_token = jwt.decode(token, "mock-secret", algorithms=["HS256"])
    assert decoded_token["sub"] == identity
    assert "exp" in decoded_token

    # Ensure the token has a valid expiration time
    expiration = datetime.fromtimestamp(decoded_token["exp"], tz=timezone.utc)
    assert expiration > datetime.now(tz=timezone.utc)


def test_generate_jwt_failure(auth_verifier):
    # Test JWT generation failure by mocking an exception in jwt.encode
    with patch("auth.jwt.encode", side_effect=Exception("JWT error")):
        with pytest.raises(Exception, match="JWT error"):
            auth_verifier.generate_jwt("test-user")
