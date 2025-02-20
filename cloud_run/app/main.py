import os
from fastapi import FastAPI, Response
from dotenv import find_dotenv, load_dotenv

from core.config import settings
from core.logging import setup_logging, get_logger
from slack.routes import router as slack_router

find_dotenv()
load_dotenv()

# Set up logging config
setup_logging()

# Get logger for this module
logger = get_logger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME, 
    debug=settings.DEBUG
)

app.router.include_router(slack_router)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/")
async def read_root() -> Response:
    logger.debug("Root endpoint called")
    return Response(f"Welcome to {settings.PROJECT_NAME} API. {settings}")
