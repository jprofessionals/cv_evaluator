import pulumi
import pulumi_gcp as gcp 
from pulumi_docker import Image, DockerBuildArgs

# Set up project and region
config = pulumi.Config("gcp")
project_id = config.require("project")
region = config.require("region")

service_name = "cv-evaluator-cloud-run-service"

# Create a Google Artifact Registry
repo_name = "my-docker-repo"

repo_exists = True
try:
    repo = gcp.artifactregistry.get_repository(
        location=region,
        repository_id=repo_name
    )
except Exception as e:
    pulumi.log.info(f"Repository {repo_name} not found: {e}")
    repo_exists = False

if not repo_exists:
    repo = gcp.artifactregistry.Repository(
        "docker-repo",
        format="DOCKER",
        location=region,
        repository_id=repo_name,
        description="Docker repository for Cloud Run deployment"
    )

# Enable Artifact Registry for Docker
docker_registry_url = f"{region}-docker.pkg.dev/{project_id}/{repo_name}"

# Build and push Docker image to Artifact Registry
image_name = f"{docker_registry_url}/my-app"
image = Image(
    "my-docker-image",
    build=DockerBuildArgs(context="./app", platform="linux/amd64"),  # Path to the directory containing your Dockerfile
    image_name=image_name,
)

# Create a dedicated service account for Cloud Run
sa = gcp.serviceaccount.Account(
    "cloud-run-sa",
    account_id=project_id,
    display_name="Cloud Run Service Account",
)


# Create a Google Cloud Run service
service = gcp.cloudrun.Service(
    service_name,
    location=region,
    template=gcp.cloudrun.ServiceTemplateArgs(
        spec=gcp.cloudrun.ServiceTemplateSpecArgs(
            service_account_name=sa.email,
            containers=[
                gcp.cloudrun.ServiceTemplateSpecContainerArgs(
                    image=image.base_image_name,  # Use the built Docker image
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

# Configure IAM permissions for Cloud Run to access the image
artifact_registry_access = gcp.projects.IAMMember(
    "artifact-registry-access",
    member=sa.email.apply(lambda email: f"serviceAccount:{email}"),
    role="roles/artifactregistry.reader",
    project=service.project,
)

# Export the Cloud Run service URL
pulumi.export("service_url", service.statuses[0].url)
