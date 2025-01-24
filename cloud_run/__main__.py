import pulumi
from pulumi_gcp import cloudrun, artifactregistry, projects
from pulumi_docker import Image, DockerBuildArgs

# Set up project and region
project_id = pulumi.Config("gcp").require("project")
region = pulumi.Config("gcp").require("region")

service_name = "cv-evaluator-cloud-run-service"

# Create a Google Artifact Registry
repo_name = "my-docker-repo"
repo = artifactregistry.Repository(
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
service = cloudrun.Service(
    service_name,
    location=region,
    template=cloudrun.ServiceTemplateArgs(
        spec=cloudrun.ServiceTemplateSpecArgs(
            containers=[
                cloudrun.ServiceTemplateSpecContainerArgs(
                    image=image.base_image_name,  # Use the built Docker image
                )
            ]
        )
    ),
    autogenerate_revision_name=True,
    traffics=[
        cloudrun.ServiceTrafficArgs(
            latest_revision=True,
            percent=100,
        )
    ],
)

# noauth = organizations.get_iam_policy(bindings=[{
#     "role": "roles/run.invoker",
#     "members": ["allUsers"],
# }])

# noauth_iam_policy = cloudrun.IamPolicy("noauth",
#     location=service.location,
#     project=service.project,
#     service=service.name,
#     policy_data=noauth.policy_data)

# Configure IAM permissions for Cloud Run to access the image
artifact_registry_access = projects.IAMMember(
    "artifact-registry-access",
    member=service.statuses[0].service_account_email.apply(
        lambda email: f"serviceAccount:{email}"
    ),
    role="roles/artifactregistry.reader",
    project=service.project,
)

# Export the Cloud Run service URL
pulumi.export("service_url", service.statuses[0].url)
