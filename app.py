#!/usr/bin/env python3
import os

import aws_cdk as cdk

from pge_assessment_application.pge_stack import PgeStack
from pge_assessment_application.lambda_hosted import LambdaHostedStack
from pge_assessment_application.lambda_monitoring_stack import LambdaMonitoringStack


app = cdk.App()

# Get deployment environment name (SANDBOX / BETA / PROD)
environment = app.node.try_get_context("env")
# If no deployment environment specified, use "SANDBOX"
if not (environment):
    environment = "SANDBOX"

# Create the main stack
pge_stack = PgeStack(
    app,
    "{}-PgeStack".format(environment),
)

# Create the lambda hosted stack
lambda_hosted_stack = LambdaHostedStack(
    app,
    "{}-LambdaHostedStack".format(environment), pge_stack=pge_stack
)

# Create the monitoring stack, passing pge_stack as argument to share ARN's
lambda_monitoring_stack = LambdaMonitoringStack(
    app, "{}-LambdaMonitoringStack".format(environment), lambda_stack=lambda_hosted_stack
)

app.synth()
