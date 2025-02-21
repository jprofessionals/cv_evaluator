
# JPro CV Reviewer

This service runs in a container deployed on Google cloud run. 

To start, make sure you have `uv` and python version `3.12` available. 
Your can install `uv` using `pip`:
```bash
pip install uv
```
See the docs for other methods of installation: https://docs.astral.sh/uv/getting-started/installation/#standalone-installer

Dependencies in `pyproject.toml`
are needed for the environment used to launch infrastructure code. 

The application code run inside a docker container which uses `app/requirements.txt` to specify dependencies.
The container is deployed using the docker file `app/Dockerfile`.

The API exposes a POST endpoint, `/slack/events`, which listens for slack messages and looks for keywords
that trigger flows. Currently these flows 1) Reviews all projects in a user's portfolio and suggests updates, 
or 2) Reviews their CV summary and suggests updates. The responses are posted to slack as private messages from
the slack bot. 

### How to use the application (this may change)

With current settings you are able to trigger a request by 
- 1. Join the channel `#updated-cv-reviewer-test` 
- 2. To trigger the project review flow type `"make_review"`
- 3. To trigger the candidate summary review flow type `"make_summary"`

The slack bot will send a request to the application which will be processed. Once the workflow comes to an end
the response will be posted as a private slack message. This means that currently you can only trigger the flow
on your own behalf. 

### CI/CD
For now we use `.github/workflows/pulumi_cicd.yaml` to run a Github Action when new commits are pushed to 
the repository. The script uses `Pulumi` to create and update our cloud infrastructure when the codebase updates.
More concretely the `pulumi up` command is run. 

