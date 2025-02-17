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

# Create a Google Cloud Run service
service = gcp.cloudrun.Service(
    service_name,
    location=region,
    template=gcp.cloudrun.ServiceTemplateArgs(
        spec=gcp.cloudrun.ServiceTemplateSpecArgs(
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
    member=service.statuses[0].service_account_email.apply(
        lambda email: f"serviceAccount:{email}"
    ),
    role="roles/artifactregistry.reader",
    project=service.project,
)

# Create a service account for the Slack Bot
slack_bot_sa = gcp.serviceaccount.Account(
    resource_name="slack-bot-sa",
    account_id="slack-bot-access",
    display_name="Slack Bot Service Account"
)

# Grant Cloud Run Invoker role to the slack bot service account
iam_binding = gcp.cloudrun.IamBinding("slack-bot-access",
    location=service.location,
    project=service.project,
    service=service.name,
    role="roles/run.invoker",
    members=[
        f"serviceAccount:{slack_bot_sa.email}"
    ]
)

# Create a Service Account Key (Needed for slack bot authentication)
slack_bot_sa_key = gcp.serviceaccount.Key(
    resource_name="slack-bot-sa-key", 
    service_account_id=slack_bot_sa.id
)

# Export the Cloud Run service URL
pulumi.export("service_url", service.statuses[0].url)

# Output the private key (store securely)
pulumi.export("slack_bot_private_key", slack_bot_sa_key.private_key)


