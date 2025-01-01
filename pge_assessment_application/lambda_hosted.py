from aws_cdk import (
    Stack,
    aws_lambda,
    aws_apigateway,
    aws_events,
    aws_events_targets,
    aws_iam,
    Duration,
)
from constructs import Construct


class LambdaHostedStack(Stack):
    '''
    LambdaHostedStack defines resources required for hosting a pretrained ML model in AWS Lambda, served through API Gateway.
    Required input on instantiation:
        - pge_stack -> main stack which hosts shared resources

    Two shared resources from argument pge_stack are used here:
        - s3_model_storage_bucket -> storage resource for pretrained ML model
        - secret_api_key -> secret key used to generate temporary access keys for API

    Lambda hosted application resources defined here are as follows:
        - Lambda function "authentication-lambda" to validate username & password, returns generate JWT access key
        - Lambda function "model_serve_lambda" that takes a numeric value as input, and returns prediction based off input (when JWT access key is valid).
        - API Gateway to front lambda hosted ML inference application.
        - API Gateway route /login with method POST to provide interface for authentication_lambda
        - API Gateway route /predict with method GET to provide interface for model_serve_lambda
        - Events timer to keep lambda functions warm (prevents inevitable timeout when assessor sends request)

    Three resources are provided as output here to be passed to monitoring stack:
        - model_serve_lambda
        - authentication_lambda
        - model_api
    '''

    def __init__(
        self, scope: Construct, construct_id: str, pge_stack: Construct, **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # import from main stack
        s3_model_storage_bucket=pge_stack.s3_model_storage_bucket
        secret_api_key = pge_stack.secret_api_key

        # Get deployment environment name (SANDBOX / BETA / PROD)
        environment = self.node.try_get_context("env")
        # If no deployment environment specified, use "SANDBOX"
        if not (environment):
            environment = "SANDBOX"

        #
        # **** 1. Define resources for Lambda hosted service ****

        # Create API Gateway for Lambda traffic management
        model_api = aws_apigateway.RestApi(
            self,
            "{}-pge_demo_api".format(environment),
            deploy_options=aws_apigateway.StageOptions(
                stage_name="{}".format(environment)
            ),
        )

        # Create Lambda for hosting ML model
        ## Note: This Lambda is hosting the code in a container. The container is built during cdk deployment from local assets in /lambda-hosted directory.
        ## Why: Lambda does not have access to sklearn library, so options are to create a layer or package in a container with dependencies.
        model_serve_lambda = aws_lambda.DockerImageFunction(
            self,
            "{}-ModelServeLambda".format(environment),
            code=aws_lambda.DockerImageCode.from_image_asset("lambda-hosted"),
            timeout=Duration.seconds(30),
            memory_size=128,
        )

        # Create Lambda for auth. This function takes username and password in body of POST request and returns a JWT token
        authentication_lambda = aws_lambda.DockerImageFunction(
            self,
            "{}-AuthLambda".format(environment),
            code=aws_lambda.DockerImageCode.from_image_asset("lambda-auth"),
            timeout=Duration.seconds(30),
            memory_size=128,
        )

        # Add s3 bucket name and API key to Lambda environment variables
        model_serve_lambda.add_environment(
            "MODEL_STORAGE_BUCKET", s3_model_storage_bucket.bucket_name
        )
        model_serve_lambda.add_environment(
            "SECRET_API_KEY", secret_api_key.secret_full_arn
        )
        model_serve_lambda.add_environment(
            "FLASK_ENV", environment
        )
        authentication_lambda.add_environment(
            "SECRET_API_KEY", secret_api_key.secret_full_arn
        )

        #
        # **** 2. Update roles and policies ****
        # s3 "Grant Read" below will add permissions to the policy attached to stated execution role allowing read from Model Storage bucket
        s3_model_storage_bucket.grant_read(model_serve_lambda.role)
        secret_api_key.grant_read(model_serve_lambda.role)
        secret_api_key.grant_read(authentication_lambda.role)

        #
        # **** 3. Add config details ****

        ## Configure API Gateway for Lambda hosted /predict service
        # Establish Lambda as target for API Gateway and define request template.
        lambda_integration = aws_apigateway.LambdaIntegration(
            model_serve_lambda,
            request_templates={
                "application/json": """
                {
                    "input": "$input.params('input')",
                    "authorization": "$input.params('Authorization')"
                }
                """  # Maps the 'input' query string and to the Lambda event
            },
        )

        # Configure API Gateway for Lambda-hosted /login service
        # Establish Lambda as target for API Gateway and define request template
        login_integration = aws_apigateway.LambdaIntegration(
            authentication_lambda,
            request_templates={
                "application/json": """
                {
                    "body": $input.json('$')
                }
                """  # Forward the full JSON body to the Lambda event
            },
        )

        # Add /predict path to the API
        lambda_resource = model_api.root.add_resource("predict")

        # Add /login path to the API
        login_resource = model_api.root.add_resource("login")

        # Add GET method to API, define Lambda as target, and require query paramter for model input.
        lambda_method = lambda_resource.add_method(
            "GET",
            lambda_integration,
            request_parameters={
                "method.request.querystring.input": True,  # Require the 'input' query parameter
                "method.request.header.Authorization": True,  # Require 'Authorization' header
            },
        )

        # Add POST method to the API, define Lambda as target
        login_method = login_resource.add_method(
            "POST",
            login_integration,
            request_parameters={
                "method.request.header.Authorization": False
            },
        )

        # Add keep warm timer to Lambdas - this prevents request timeouts
        # Create CloudWatch Event Rule (Trigger Lambda every 5 minutes)
        event_rule = aws_events.Rule(
            self,
            "Every5MinutesRule",
            schedule=aws_events.Schedule.expression("rate(5 minutes)")  # Trigger every 5 minutes
        )

        # Add the Lambda functions as the targets of the CloudWatch Event rule
        event_rule.add_target(aws_events_targets.LambdaFunction(model_serve_lambda))
        event_rule.add_target(aws_events_targets.LambdaFunction(authentication_lambda))

        # Grant CloudWatch permission to invoke the Lambda function
        model_serve_lambda.grant_invoke(aws_iam.ServicePrincipal("events.amazonaws.com"))
        authentication_lambda.grant_invoke(aws_iam.ServicePrincipal("events.amazonaws.com"))


        # **** 4. Output relevant details ****
        self.model_serve_lambda=model_serve_lambda
        self.authentication_lambda = authentication_lambda
        self.model_api=model_api
