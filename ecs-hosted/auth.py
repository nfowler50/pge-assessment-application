import boto3
import os
import logging


class AuthVerifier:
    def __init__(self, logger=None):
        if logger:
            self.logger = logger
        else:
            self._set_logger()

        self.secret_client = boto3.client("secretsmanager")
        self.secret_arn = os.getenv("SECRET_API_KEY")
        self.secret = self.get_secret_from_aws()

    def _set_logger(self):
        # Set up logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

    def get_secret_from_aws(self):
        """Fetch the JWT secret key from AWS Secrets Manager."""
        try:
            response = self.secret_client.get_secret_value(SecretId=self.secret_arn)
            secret = response.get("SecretString")
            if not secret:
                raise ValueError("SecretString is missing in the secret response")
            return secret
        except Exception as e:
            self.logger.error(f"Error fetching secret: {e}")
            raise e
