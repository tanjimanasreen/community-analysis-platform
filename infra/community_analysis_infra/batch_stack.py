"""AWS CDK Stack for AWS Batch analytical compute infrastructure.

Manages:
- Dedicated private ECR repository for analytical container images
- Dedicated 2-AZ public VPC (0 NAT Gateways)
- Spot and On-Demand Fargate Compute Environments (maxv_cpus=16, scale-to-zero)
- Prioritized Batch Job Queue (Spot priority 1, On-Demand priority 2)
- Fargate ARM64 Job Definition (4 vCPUs, 16 GiB RAM, 30 GiB ephemeral storage)
- Scoped IAM execution and job task roles
- CloudWatch log group with stage-specific retention
"""

from __future__ import annotations

import aws_cdk as cdk
import aws_cdk.aws_batch as batch
import aws_cdk.aws_ec2 as ec2
import aws_cdk.aws_ecr as ecr
import aws_cdk.aws_ecs as ecs
import aws_cdk.aws_iam as iam
import aws_cdk.aws_logs as logs
import aws_cdk.aws_s3 as s3
import constructs

from community_analysis_infra.config import StageConfig


class BatchStack(cdk.Stack):
    """Stack managing AWS Batch analytical compute and container registry."""

    def __init__(
        self,
        scope: constructs.Construct,
        construct_id: str,
        *,
        stage_config: StageConfig,
        bucket: s3.IBucket,
        batch_image_tag: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.stage_config = stage_config
        is_dev = stage_config.stage_name == "dev"
        removal_policy = (
            cdk.RemovalPolicy.DESTROY if is_dev else cdk.RemovalPolicy.RETAIN
        )

        # 1. Dedicated Analytics ECR Repository
        repo_name = f"{stage_config.project_name}-{stage_config.stage_name}-analytics"
        self.repository = ecr.Repository(
            self,
            "AnalyticsRepository",
            repository_name=repo_name,
            image_tag_mutability=ecr.TagMutability.IMMUTABLE,
            encryption=ecr.RepositoryEncryption.AES_256,
            removal_policy=removal_policy,
            empty_on_delete=is_dev,
            lifecycle_rules=[
                ecr.LifecycleRule(
                    description="Expire untagged images after 1 day",
                    max_image_age=cdk.Duration.days(1),
                    tag_status=ecr.TagStatus.UNTAGGED,
                ),
            ],
        )

        # 2. Dedicated Batch VPC (2 AZs, Public Subnets Only, 0 NAT Gateways)
        vpc_name = f"{stage_config.project_name}-{stage_config.stage_name}-batch-vpc"
        self.vpc = ec2.Vpc(
            self,
            "BatchVpc",
            vpc_name=vpc_name,
            max_azs=2,
            nat_gateways=0,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                ),
            ],
        )

        # 3. Security Group (No Inbound Rules, Outbound Egress Allowed)
        sg_name = f"{stage_config.project_name}-{stage_config.stage_name}-batch-sg"
        self.security_group = ec2.SecurityGroup(
            self,
            "BatchSecurityGroup",
            vpc=self.vpc,
            security_group_name=sg_name,
            description="Security group for AWS Batch analytical Fargate tasks",
            allow_all_outbound=True,
        )

        # 4. CloudWatch Log Group
        log_group_name = (
            f"/aws/batch/job/{stage_config.project_name}-{stage_config.stage_name}"
        )
        retention = (
            logs.RetentionDays.ONE_WEEK if is_dev else logs.RetentionDays.ONE_MONTH
        )
        self.log_group = logs.LogGroup(
            self,
            "BatchLogGroup",
            log_group_name=log_group_name,
            retention=retention,
            removal_policy=removal_policy,
        )

        # 5. IAM Execution Role (ECR pull + CloudWatch logs for Fargate agent)
        self.execution_role = iam.Role(
            self,
            "BatchExecutionRole",
            role_name=f"{stage_config.project_name}-{stage_config.stage_name}-batch-exec-role",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            description="Task execution role for AWS Batch analytical container agent",
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AmazonECSTaskExecutionRolePolicy"
                ),
            ],
        )

        # 6. IAM Job Role (Task process permissions - strictly scoped S3 read/write)
        self.job_role = iam.Role(
            self,
            "BatchJobRole",
            role_name=f"{stage_config.project_name}-{stage_config.stage_name}-batch-job-role",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            description="Task IAM role for AWS Batch analytical pipeline process",
        )

        # Grant least-privilege S3 permissions on Plan 089 data bucket
        self.job_role.add_to_policy(
            iam.PolicyStatement(
                sid="BatchS3ListBucketScoped",
                effect=iam.Effect.ALLOW,
                actions=["s3:ListBucket"],
                resources=[bucket.bucket_arn],
                conditions={
                    "StringLike": {
                        "s3:prefix": ["raw/*", "cache/*"],
                    },
                },
            )
        )
        self.job_role.add_to_policy(
            iam.PolicyStatement(
                sid="BatchS3GetObjectScoped",
                effect=iam.Effect.ALLOW,
                actions=["s3:GetObject"],
                resources=[
                    bucket.arn_for_objects("raw/*"),
                    bucket.arn_for_objects("cache/*"),
                ],
            )
        )
        self.job_role.add_to_policy(
            iam.PolicyStatement(
                sid="BatchS3PutObjectScoped",
                effect=iam.Effect.ALLOW,
                actions=["s3:PutObject"],
                resources=[
                    bucket.arn_for_objects("runs/*"),
                    bucket.arn_for_objects("reports/*"),
                    bucket.arn_for_objects("cache/*"),
                ],
            )
        )

        # 7. Compute Environments (Spot & On-Demand Fargate with maxv_cpus=16, scale-to-zero)
        spot_env_name = (
            f"{stage_config.project_name}-{stage_config.stage_name}-spot-compute"
        )
        self.spot_compute_environment = batch.FargateComputeEnvironment(
            self,
            "SpotComputeEnvironment",
            compute_environment_name=spot_env_name,
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            security_groups=[self.security_group],
            spot=True,
            maxv_cpus=16,
        )

        ondemand_env_name = (
            f"{stage_config.project_name}-{stage_config.stage_name}-ondemand-compute"
        )
        self.ondemand_compute_environment = batch.FargateComputeEnvironment(
            self,
            "OnDemandComputeEnvironment",
            compute_environment_name=ondemand_env_name,
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            security_groups=[self.security_group],
            spot=False,
            maxv_cpus=16,
        )

        # 8. Prioritized Job Queue (Spot order 1, On-Demand order 2)
        queue_name = f"{stage_config.project_name}-{stage_config.stage_name}-queue"
        self.job_queue = batch.JobQueue(
            self,
            "JobQueue",
            job_queue_name=queue_name,
            priority=1,
            compute_environments=[
                batch.OrderedComputeEnvironment(
                    compute_environment=self.spot_compute_environment,
                    order=1,
                ),
                batch.OrderedComputeEnvironment(
                    compute_environment=self.ondemand_compute_environment,
                    order=2,
                ),
            ],
        )

        # 9. Container Definition (ARM64, 4 vCPUs, 16 GiB RAM, 30 GiB Ephemeral Storage)
        self.container = batch.EcsFargateContainerDefinition(
            self,
            "AnalyticsContainer",
            image=ecs.ContainerImage.from_ecr_repository(
                self.repository,
                tag=batch_image_tag,
            ),
            cpu=4,
            memory=cdk.Size.gibibytes(16),
            ephemeral_storage_size=cdk.Size.gibibytes(30),
            fargate_cpu_architecture=ecs.CpuArchitecture.ARM64,
            fargate_operating_system_family=ecs.OperatingSystemFamily.LINUX,
            assign_public_ip=True,
            execution_role=self.execution_role,
            job_role=self.job_role,
            logging=ecs.LogDrivers.aws_logs(
                log_group=self.log_group,
                stream_prefix="analytics",
            ),
            environment={
                "COMMUNITY_ANALYSIS_STORAGE_BACKEND": "s3",
                "COMMUNITY_ANALYSIS_S3_BUCKET": bucket.bucket_name,
                "LOG_FORMAT": "json",
                "LOG_LEVEL": "INFO",
            },
        )

        # 10. Job Definition (2-hour operational timeout, 2 retry attempts)
        job_def_name = (
            f"{stage_config.project_name}-{stage_config.stage_name}-analytics-job"
        )
        self.job_definition = batch.EcsJobDefinition(
            self,
            "AnalyticsJobDefinition",
            job_definition_name=job_def_name,
            container=self.container,
            timeout=cdk.Duration.seconds(7200),
            retry_attempts=2,
        )

        # 11. Stack Outputs
        cdk.CfnOutput(
            self,
            "AnalyticsRepositoryUri",
            value=self.repository.repository_uri,
            description="URI of the analytical ECR repository",
        )
        cdk.CfnOutput(
            self,
            "BatchVpcId",
            value=self.vpc.vpc_id,
            description="ID of the dedicated Batch VPC",
        )
        cdk.CfnOutput(
            self,
            "BatchJobQueueArn",
            value=self.job_queue.job_queue_arn,
            description="ARN of the prioritized Batch job queue",
        )
        cdk.CfnOutput(
            self,
            "BatchJobQueueName",
            value=self.job_queue.job_queue_name,
            description="Name of the prioritized Batch job queue",
        )
        cdk.CfnOutput(
            self,
            "BatchJobDefinitionArn",
            value=self.job_definition.job_definition_arn,
            description="ARN of the analytical Batch job definition",
        )
        cdk.CfnOutput(
            self,
            "BatchJobDefinitionName",
            value=self.job_definition.job_definition_name,
            description="Name of the analytical Batch job definition",
        )
