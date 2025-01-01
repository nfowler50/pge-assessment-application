from aws_cdk import (
    Stack,
    aws_cloudwatch,
)
from constructs import Construct


class LambdaMonitoringStack(Stack):
    '''
    LambdaMonitoringStack defines metrics, alarms, and a dashborad for the lambda hosted application.
    Required input on instantiation:
        - lambda_stack -> stack defining resources for lambda hosted application

    Three resources from argument lambda_stack are used here:
        - model_serve_lambda -> compute resource for processing inputs and returning predictions
        - authentication_lambda -> compute resource used to validate username password and generate JWT access key
        - model_api -> interface used for lambda hosted ML inference application

    Lambda monitoring resources defined here are as follows:
        - Error metric and alarm for model_serve_lambda
        - Error metric and alarm for authentication_lambda
        - Error metric and alarm for API 4xx status code returns
        - Error metric and alarm for API 5xx status code returns
        - API latency metric and alarm
        - Metric dashboard used to monitor resources supporting lambda hosted ML inference application

    No resources are provided as output.
    '''
    def __init__(
        self, scope: Construct, construct_id: str, lambda_stack: Construct, **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Get deployment environment name (SANDBOX / BETA / PROD)
        environment = self.node.try_get_context("env")
        # If no deployment environment specified, use "SANDBOX"
        if not (environment):
            environment = "SANDBOX"

        # Reference the resources from LambdaStack
        model_serve_lambda = lambda_stack.model_serve_lambda
        authentication_lambda = lambda_stack.authentication_lambda
        model_api = lambda_stack.model_api

        # ***** 1. CloudWatch Alarms for Lambda Functions *****
        # Monitor Model Serve Lambda Errors
        model_lambda_errors_metric = model_serve_lambda.metric_errors()
        model_lambda_errors_alarm = aws_cloudwatch.Alarm(
            self,
            "{}-ModelLambdaErrorsAlarm".format(environment),
            metric=model_lambda_errors_metric,
            threshold=5,
            evaluation_periods=1,
            datapoints_to_alarm=1,
            comparison_operator=aws_cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            alarm_description="Alarm when Model Serve Lambda errors exceed 5",
        )

        # Monitor Auth Lambda Errors
        auth_lambda_errors_metric = authentication_lambda.metric_errors()
        auth_lambda_errors_alarm = aws_cloudwatch.Alarm(
            self,
            "{}-AuthLambdaErrorsAlarm".format(environment),
            metric=auth_lambda_errors_metric,
            threshold=5,
            evaluation_periods=1,
            datapoints_to_alarm=1,
            comparison_operator=aws_cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            alarm_description="Alarm when Auth Lambda errors exceed 5",
        )

        # ***** 2. CloudWatch Alarms for API Gateway *****
        # Monitor API Gateway 4xx Errors
        api_4xx_metric = model_api.metric("4XXError")
        api_4xx_alarm = aws_cloudwatch.Alarm(
            self,
            "{}-Api4xxErrorsAlarm".format(environment),
            metric=api_4xx_metric,
            threshold=10,
            evaluation_periods=1,
            datapoints_to_alarm=1,
            comparison_operator=aws_cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            alarm_description="Alarm when API Gateway 4XX errors exceed 10",
        )

        # Monitor API Gateway 5xx Errors
        api_5xx_metric = model_api.metric("5XXError")
        api_5xx_alarm = aws_cloudwatch.Alarm(
            self,
            "{}-Api5xxErrorsAlarm".format(environment),
            metric=api_5xx_metric,
            threshold=5,
            evaluation_periods=1,
            datapoints_to_alarm=1,
            comparison_operator=aws_cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            alarm_description="Alarm when API Gateway 5XX errors exceed 5",
        )

        # Monitor API Gateway Latency
        api_latency_metric = model_api.metric("Latency")
        api_latency_alarm = aws_cloudwatch.Alarm(
            self,
            "{}-ApiLatencyAlarm".format(environment),
            metric=api_latency_metric,
            threshold=2000,
            evaluation_periods=1,
            datapoints_to_alarm=1,
            comparison_operator=aws_cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            alarm_description="Alarm when API Gateway latency exceeds 2 seconds",
        )

        # ***** 3. CloudWatch Dashboard for Lambda and API Gateway *****
        dashboard = aws_cloudwatch.Dashboard(
            self, "{}-LambdaApiDashboard".format(environment)
        )

        # Add widgets to the dashboard
        dashboard.add_widgets(
            aws_cloudwatch.GraphWidget(
                title="{} - Model Serve Lambda Errors".format(environment),
                left=[model_lambda_errors_metric],
            ),
            aws_cloudwatch.GraphWidget(
                title="{} - Auth Lambda Errors".format(environment),
                left=[auth_lambda_errors_metric],
            ),
            aws_cloudwatch.GraphWidget(
                title="{} - API Gateway 4XX Errors".format(environment),
                left=[api_4xx_metric],
            ),
            aws_cloudwatch.GraphWidget(
                title="{} - API Gateway 5XX Errors".format(environment),
                left=[api_5xx_metric],
            ),
            aws_cloudwatch.GraphWidget(
                title="{} - API Gateway Latency".format(environment),
                left=[api_latency_metric],
            ),
        )
