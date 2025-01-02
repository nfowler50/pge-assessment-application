from aws_cdk import (
    Stack,
    aws_cloudwatch,
    aws_elasticloadbalancingv2
)
from constructs import Construct

class EcsMonitoringStack(Stack):
    def __init__(
        self, scope: Construct, construct_id: str, ecs_stack: Construct, **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Get deployment environment name (SANDBOX / BETA / PROD)
        environment = self.node.try_get_context("env")
        if not environment:
            environment = "SANDBOX"

        # Reference the ECS service and ALB from the ECS stack
        ecs_service = ecs_stack.ecs_serve_service
        ecs_alb = ecs_stack.ecs_serve_alb

        # ***** 1. CloudWatch Alarms for ECS Service *****
        # Monitor ECS CPU Utilization
        ecs_cpu_utilization_metric = ecs_service.metric_cpu_utilization()
        ecs_cpu_utilization_alarm = aws_cloudwatch.Alarm(
            self,
            "{}-EcsCpuUtilizationAlarm".format(environment),
            metric=ecs_cpu_utilization_metric,
            threshold=70,
            evaluation_periods=1,
            datapoints_to_alarm=1,
            comparison_operator=aws_cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            alarm_description="Alarm when ECS service CPU utilization exceeds 70%",
        )

        # Monitor ECS Memory Utilization
        ecs_memory_utilization_metric = ecs_service.metric_memory_utilization()
        ecs_memory_utilization_alarm = aws_cloudwatch.Alarm(
            self,
            "{}-EcsMemoryUtilizationAlarm".format(environment),
            metric=ecs_memory_utilization_metric,
            threshold=80,
            evaluation_periods=1,
            datapoints_to_alarm=1,
            comparison_operator=aws_cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            alarm_description="Alarm when ECS service memory utilization exceeds 80%",
        )

        # ***** 2. CloudWatch Alarms for ALB *****
        # Monitor ALB 5xx Errors
        alb_5xx_metric = ecs_alb.metrics.http_code_target(
            code=aws_elasticloadbalancingv2.HttpCodeTarget.TARGET_5XX_COUNT, 
            statistic="Sum"
        )
        alb_5xx_alarm = aws_cloudwatch.Alarm(
            self,
            "{}-Alb5XXErrorAlarm".format(environment),
            metric=alb_5xx_metric,
            threshold=5,
            evaluation_periods=1,
            datapoints_to_alarm=1,
            comparison_operator=aws_cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            alarm_description="Alarm when ALB 5XX errors exceed 5",
        )
        # Monitor 4xx auth failures
        alb_4xx_metric = ecs_alb.metrics.http_code_target(
            code=aws_elasticloadbalancingv2.HttpCodeTarget.TARGET_4XX_COUNT, 
            statistic="Sum"
        )
        alb_4xx_alarm = aws_cloudwatch.Alarm(
            self,
            "{}-Alb4XXErrorAlarm".format(environment),
            metric=alb_4xx_metric,
            threshold=5,
            evaluation_periods=1,
            datapoints_to_alarm=1,
            comparison_operator=aws_cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            alarm_description="Alarm when ALB 5XX errors exceed 5",
        )

        # Monitor ALB Latency
        alb_latency_metric = ecs_alb.metric_target_response_time(statistic="Average")
        alb_latency_alarm = aws_cloudwatch.Alarm(
            self,
            "{}-AlbLatencyAlarm".format(environment),
            metric=alb_latency_metric,
            threshold=2,
            evaluation_periods=1,
            datapoints_to_alarm=1,
            comparison_operator=aws_cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            alarm_description="Alarm when ALB response latency exceeds 2 seconds",
        )

        # ***** 3. CloudWatch Dashboard for ECS and ALB *****
        dashboard = aws_cloudwatch.Dashboard(
            self, "{}-EcsDashboard".format(environment)
        )

        # Add widgets to the dashboard
        dashboard.add_widgets(
            aws_cloudwatch.GraphWidget(
                title="{} - ECS CPU Utilization".format(environment),
                left=[ecs_cpu_utilization_metric],
            ),
            aws_cloudwatch.GraphWidget(
                title="{} - ECS Memory Utilization".format(environment),
                left=[ecs_memory_utilization_metric],
            ),
            aws_cloudwatch.GraphWidget(
                title="{} - ALB 5XX Errors".format(environment),
                left=[alb_5xx_metric],
            ),
            aws_cloudwatch.GraphWidget(
                title="{} - ALB 4XX Errors".format(environment),
                left=[alb_4xx_metric],
            ),
            aws_cloudwatch.GraphWidget(
                title="{} - ALB Response Latency".format(environment),
                left=[alb_latency_metric],
            ),
        )