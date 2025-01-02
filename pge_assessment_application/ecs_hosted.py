from aws_cdk import (
    Stack,
    aws_ec2,
    aws_ecs,
    aws_elasticloadbalancingv2,
    CfnOutput
)
from constructs import Construct


class EcsHostedStack(Stack):
    '''
    EcsHostedStack defines resources required for hosting a pretrained ML model in AWS ECS, served through an Application Load Balancer.
    Required input on instantiation:
        - pge_stack -> main stack which hosts shared resources

    Two shared resources from argument pge_stack are used here:
        - s3_model_storage_bucket -> storage resource for pretrained ML model
        - secret_api_key -> secret key used to generate temporary access keys for API

    ECS hosted application resources defined here are as follows:
        - ECS Cluster to host our service
        - ECS Task to define container and configuration
        - ECS Service to associate cluster, task, and define capacity provider (Fargate Spot)
        - Container image defining our Flask app
        - VPC to define network ecosystem for ECS and ALB to run in.
        - VPC Endpoints to allow services in private subnet to communicate directly with s3 and Secrets Manager (not over public internet)
        - Autoscling group to support service autoscaling.
        - Application Load Balancer to distribute traffic across targets in autoscaling group.

    Two resources are provided as output here to be passed to monitoring stack:
        - ecs_serve_service
        - ecs_serve_alb
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
        # **** 1. Define resources for ECS hosted service

        # Create VPC for ECS served model
        ecs_vpc = aws_ec2.Vpc(
            self, "{}-ECS-Model-Vpc".format(environment), max_azs=2
        )  # Default is all AZs in region

        # Create ECS cluster to host container
        ecs_serve_cluster = aws_ecs.Cluster(
            self, "{}-Model-Serve-Cluster".format(environment), vpc=ecs_vpc
        )

        # Define task with Docker image from a local asset
        ecs_serve_task_definition = aws_ecs.FargateTaskDefinition(
            self, "{}-TaskDef".format(environment), memory_limit_mib=512, cpu=256
        )

        ## Note: Deploying container from local asset still leverages ECR but abstracts this layer away.
        ## By abstracting the ECR layer away, we reduce number of resources to manage, and we eliminate the
        ## issue of existing resources leveraging outdated code or needing a force update. This also allows
        ## us to consolidate version control. Version control still available through Git.
        ecs_serve_container_image = aws_ecs.ContainerImage.from_asset("./ecs-hosted/")
        ecs_serve_container = ecs_serve_task_definition.add_container(
            "{}-ECS-Serve-Container".format(environment),
            image=ecs_serve_container_image,
            logging=aws_ecs.LogDrivers.aws_logs(stream_prefix="ecs-container"),
        )

        # Set port mapping to use Flask's default port
        ecs_serve_container.add_port_mappings(aws_ecs.PortMapping(container_port=5000))

        # Add s3 model location and API key ARN so service can find data
        ecs_serve_container.add_environment(
            "MODEL_STORAGE_BUCKET", s3_model_storage_bucket.bucket_name
        )
        ecs_serve_container.add_environment(
            "SECRET_API_KEY", secret_api_key.secret_full_arn
        )
        ecs_serve_container.add_environment(
            "FLASK_ENV", environment
        )

        # From task definition and cluster, create a service leveraging Fargate Spot.
        # Fargate Spot allows us to minimize resource management with serverless functionality,
        # but still get the benefit of Spot instance reduced price.
        ecs_serve_service = aws_ecs.FargateService(
            self,
            "{}-ECS-Serve-Service".format(environment),
            cluster=ecs_serve_cluster,
            task_definition=ecs_serve_task_definition,
            capacity_provider_strategies=[
                aws_ecs.CapacityProviderStrategy(
                    capacity_provider="FARGATE_SPOT", weight=1
                )
            ],
        )

        # Create a Application Load Balancer (ALB) with public IP
        # Setting internet facing to True allows us to use the assigned DNS name
        # to reach our API from the internet.
        ecs_serve_alb = aws_elasticloadbalancingv2.ApplicationLoadBalancer(
            self,
            "{}-ECS-Serve-ALB".format(environment),
            vpc=ecs_vpc,
            internet_facing=True,
        )

        # Set listener for HTTP traffic
        # ** SECURITY NOTE: HTTP is not secure. This can be easily mitigated with ACM, but that requires custom domain name
        # For demo purposes, I am NOT creating a custom domain and ACM certificate, so traffic will remain unencrypted.
        ecs_serve_listener = ecs_serve_alb.add_listener(
            "{}-ECS-Serve-Listener".format(environment), port=80
        )

        # Set target for listener to container port mapping
        ecs_serve_listener.add_targets(
            "ECS",
            port=5000,
            protocol=aws_elasticloadbalancingv2.ApplicationProtocol.HTTP,
            targets=[
                ecs_serve_service.load_balancer_target(
                    container_name="{}-ECS-Serve-Container".format(environment),
                    container_port=5000,
                )
            ],
        )

        # Add simple auto-scaling configuration
        ecs_serve_scaling = ecs_serve_service.auto_scale_task_count(
            min_capacity=1, max_capacity=2
        )

        ecs_serve_scaling.scale_on_cpu_utilization(
            "{}-ECS-Serve-CpuScaling".format(environment), target_utilization_percent=70
        )

        # **** 2. Update roles and policies ****
        # s3 "Grant Read" below will add permissions to the policy attached to stated execution role allowing read from Model Storage bucket
        s3_model_storage_bucket.grant_read(ecs_serve_service.task_definition.task_role)
        secret_api_key.grant_read(ecs_serve_service.task_definition.task_role)

        
        # **** 3. Add config details ****
        #

        ## Add S3 Gateway Endpoint to the VPC
        # This allows our container to retrieve data from s3 directly, without traversing public internet.
        # Adding gateway endpoint here automatically updates route tables.
        ecs_vpc.add_gateway_endpoint(
            "{}-ECS-Serve-S3GatewayEndpoint".format(environment),
            service=aws_ec2.GatewayVpcEndpointAwsService.S3,
        )

        # **** 4. Output relevant details ****
        self.ecs_serve_service = ecs_serve_service
        self.ecs_serve_alb = ecs_serve_alb
        self.ecs_serve_alb_dns = ecs_serve_alb.load_balancer_dns_name

        # Add the ALB URL to the stack outputs
        CfnOutput(
            self,
            "{}-EcsServeAlbUrl".format(environment),
            value=f"http://{ecs_serve_alb.load_balancer_dns_name}",
            description="URL of the ECS Serve ALB",
        )
