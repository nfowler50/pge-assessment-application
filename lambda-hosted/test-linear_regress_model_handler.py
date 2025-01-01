import pytest
from unittest.mock import patch, MagicMock
import pickle
import boto3
import json
import io
import os
from linear_regress_model_handler import LinearRegressModelHandler


# Mocking the model's predict method
class MockModel:
    def predict(self, input_data):
        return [sum(input_data[0])]  # A dummy prediction logic for testing


@pytest.fixture
def mock_s3():
    with patch("boto3.client") as mock_boto_client:
        # Mock the S3 client
        mock_s3_client = MagicMock()
        mock_boto_client.return_value = mock_s3_client

        # Create a mock response for get_object
        mock_s3_client.get_object.return_value = {
            "Body": io.BytesIO(pickle.dumps(MockModel()))  # Serialize the mock model
        }

        yield mock_s3_client


@pytest.fixture
def mock_env_vars(monkeypatch):
    # Mock environment variables
    monkeypatch.setenv("MODEL_STORAGE_BUCKET", "test-bucket")
    monkeypatch.setenv("model_file_key", "linear_regression_model.pkl")


@pytest.fixture
def handler(mock_s3, mock_env_vars):
    # Initialize the model handler
    return LinearRegressModelHandler()


def test_load_model_success(handler, mock_s3):
    # Check if model is loaded successfully
    assert handler.model is not None


def test_predict_success(handler):
    # Test prediction with valid input
    prediction = handler.predict(3.0)
    assert isinstance(prediction, list)
    assert isinstance(prediction[0], float)


def test_predict_invalid_input(handler):
    # Test prediction with invalid input
    with pytest.raises(ValueError, match="Invalid input data: 5.0"):
        handler.predict(5.0)  # Input out of valid range


def test_predict_model_not_loaded():
    # Test if prediction raises error when model is not loaded
    handler = LinearRegressModelHandler(logger=None)
    with pytest.raises(ValueError, match="Model is not loaded. Unable to perform predictions."):
        handler.predict(3.0)


def test_validate_input_invalid_data():
    # Test invalid input validation (out of range)
    assert not LinearRegressModelHandler._validate_input_data(5.0)


def test_validate_input_valid_data():
    # Test valid input validation
    assert LinearRegressModelHandler._validate_input_data(3.0)
