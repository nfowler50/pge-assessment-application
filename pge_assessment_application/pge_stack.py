from aws_cdk import (
    Stack,
    SecretValue,
    aws_s3,
    aws_s3_deployment,
    aws_secretsmanager,
)
from constructs import Construct
import os


class PgeStack(Stack):
    """
    PgeStack provides CDK IaC to generate shared resources for our two solutions:
        - Lambda hosted application
        - ECS hosted application

    Both of the above stacks will need access to:
        - Pretrained model stored in s3 (as pickle file)
        - API secret key (bad practice to hard code but simplifies assessor deployment)

    The two shared resources defined above are output at end of document as:
        - s3_model_storage_bucket
        - secret_api_key
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Get deployment environment name (SANDBOX / BETA / PROD)
        environment = self.node.try_get_context("env")
        # If no deployment environment specified, use "SANDBOX"
        if not (environment):
            environment = "SANDBOX"

        #
        # **** 1. Define general resources ****

        # Create S3 bucket for storing the ML model
        s3_model_storage_bucket = aws_s3.Bucket(
            self,
            "{}-model_storage".format(environment),
            block_public_access=aws_s3.BlockPublicAccess.BLOCK_ALL,
        )

        # Upload model to s3 bucket
        aws_s3_deployment.BucketDeployment(
            self,
            "{}-UploadModelFile".format(environment),
            sources=[
                aws_s3_deployment.Source.asset(os.path.join(os.getcwd(), "model"))
            ],
            destination_bucket=s3_model_storage_bucket,
        )

        #
        # Create a DEMO key in Secrets Manager for sample API key
        #
        # **SECURITY NOTE**: This is extremely bad practice, but for producing a sample app
        # that the assessor can easily deploy, we are creating a sample key here for sample app.
        # In production, we would build an auth app to create and cycle temporary credentials,
        # but something of that scale is out of scope here.

        secret_api_key = aws_secretsmanager.Secret(
            self,
            "{}-PgeApiKeySecret".format(environment),
            secret_name="{}-PgeApiKey".format(environment),
            secret_string_value=SecretValue.unsafe_plain_text(
                "abc-123-extremely-bad-practice-demo-key"
            ),
        )

        # **** 2. Output relevant details ****
        self.s3_model_storage_bucket = s3_model_storage_bucket
        self.secret_api_key = secret_api_key
