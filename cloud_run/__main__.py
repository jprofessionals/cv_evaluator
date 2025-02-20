import pulumi
import pulumi_gcp as gcp 
from pulumi_docker import Image, DockerBuildArgs
from dotenv import dotenv_values

CLOUD_RUN_SERVICE_NAME = "cv-evaluator-cloud-run-service"
DOCKER_REPOSITORY_ID = "my-docker-repo"

config = pulumi.Config("gcp")
region = config.require("region")
project_id = config.require("project")

# Create a Google Artifact Registry
repo = gcp.artifactregistry.Repository(
    "docker-repo",
    format="DOCKER",
    location=region,
    repository_id=DOCKER_REPOSITORY_ID,
    description="Docker repository for Cloud Run deployment",
    opts=pulumi.ResourceOptions(protect=True)
)

# Build and push Docker image to Artifact Registry
docker_registry_url = (
    f"{region}-docker.pkg.dev/{project_id}/{DOCKER_REPOSITORY_ID}"
)
image = Image(
    "my-docker-image",
    build=DockerBuildArgs(
        # Dir containing Dockerfile
        context="./app", 
        platform="linux/amd64"
    ),  
    image_name=f"{docker_registry_url}/my-app:latest",
    # Ensure repo exists
    opts=pulumi.ResourceOptions(depends_on=[repo])  
)

# Create a dedicated service account for Cloud Run
sa = gcp.serviceaccount.Account(
    "cloud-run-sa",
    account_id=project_id,
    display_name="Cloud Run Service Account",
)

# Create a Google Cloud Run service
service = gcp.cloudrun.Service(
    CLOUD_RUN_SERVICE_NAME,
    location=region,
    opts=pulumi.ResourceOptions(
        parent=image,
        depends_on=[image],
    ),
    template=gcp.cloudrun.ServiceTemplateArgs(
        spec=gcp.cloudrun.ServiceTemplateSpecArgs(
            service_account_name=sa.email,
            containers=[
                gcp.cloudrun.ServiceTemplateSpecContainerArgs(
                    image=image.base_image_name, 
                    envs=[
                        gcp.cloudrun.ServiceTemplateSpecContainerEnvArgs(
                            name="IMAGE_DIGEST",
                            value=image.repo_digest  
                        ),
                    ],
                    startup_probe=gcp.cloudrun.ServiceTemplateSpecContainerStartupProbeArgs(
                        initial_delay_seconds=120,
                        timeout_seconds=60,
                        period_seconds=240,
                        failure_threshold=3,
                        http_get=gcp.cloudrun.ServiceTemplateSpecContainerStartupProbeHttpGetArgs(
                            path="/health", 
                            port=8080    
                        )
                    ),
                )
            ]
        )
    ),
    autogenerate_revision_name=True,
    traffics=[
        gcp.cloudrun.ServiceTrafficArgs(
            latest_revision=True,
            percent=100,
        )
    ],
)

# Configure IAM permissions for Cloud Run
artifact_registry_access = gcp.projects.IAMMember(
    "artifact-registry-access",
    member=sa.email.apply(lambda email: f"serviceAccount:{email}"),
    role="roles/run.sourceDeveloper",
    project=service.project,
)

# Export the Cloud Run service URL
pulumi.export("service_url", service.statuses[0].url)
