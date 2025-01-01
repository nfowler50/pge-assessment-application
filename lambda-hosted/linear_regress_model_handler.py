import pickle
import boto3
import io
import os
import numpy
import logging

from sklearn.linear_model import LinearRegression


class LinearRegressModelHandler:
    def __init__(self, logger=None) -> None:
        self.s3_client = boto3.client("s3")
        self.bucket_name = os.getenv("MODEL_STORAGE_BUCKET")
        self.file_key = "linear_regression_model.pkl"
        self.model = None

        if logger:
            self.logger = logger
        else:
            self._set_logger()

        self._load_model()


    def _set_logger(self):
        # Set up logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)


    def _get_env_variables(self) -> None:
        # Get bucket name from environemnt variable. This is dynamically populated on deployment.
        self.bucket_name = os.environ["model_storage_bucket_name"]
        self.file_key = "linear_regression_model.pkl"


    def _load_model(self) -> None:
        ## Retrieve model from s3 and load/initialize
        try:
            if not self.bucket_name:
                raise ValueError("Environment variable 'model_storage_bucket_name' is not set.")

            # Retrieve the pickle file from S3
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=self.file_key)

            # Read the content of the file (binary)
            file_content = response["Body"].read()

            # Load the pickle file from the binary content
            self.model = pickle.load(io.BytesIO(file_content))
            self.logger.info("Model successfully loaded.")

        except Exception as e:
            self.logger.error(f"Failed to load model: {str(e)}")

    @staticmethod
    def _validate_input_data(input_data) -> bool:
        # Check if the input is number within the valid range (0.0 to 4.0)
        try:
            input_data = float(input_data)
            return 0.0 <= input_data <= 4.0
        except ValueError:
            return False
        
    def predict(self,input_data: float) -> list:
        if not self.model:
            raise ValueError("Model is not loaded. Unable to perform predictions.")

        if not self._validate_input_data(input_data):
            raise ValueError(f"Invalid input data: {input_data}")
        
        prediction = list(self.model.predict([[float(input_data)]]))

        return prediction

