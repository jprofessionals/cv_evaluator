from collections import deque
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_sdk.signature import SignatureVerifier

from core.config import settings
from core.logging import get_logger
from resume.process import get_project_reviews, get_candidate_summary

logger = get_logger(__name__)

router = APIRouter()

verifier = SignatureVerifier(settings.SLACK_SIGNING_SECRET)
slack_client = WebClient(token=settings.SLACK_BOT_TOKEN)

# Use a queue to handle deduplication of event handling
processed_event_ids = deque(maxlen=100)


def extract_email_from_user_id(user_id: str) -> str:
    """Poll the client for user's email address"""

    result = slack_client.users_info(user=user_id)
    try:
        email_address = result["user"]["profile"]["email"]
        return email_address
    except Exception as e:
        logger.error(f"Could not extract email from user={user_id}")
        return ""


@router.post("/slack/events", response_model=None)
async def slack_event_handler(
    request: Request,
    x_slack_signature: str = Header(None),
    x_slack_request_timestamp: str = Header(None),
):
    payload = await request.json()

    # Handle Slack's URL verification challenge
    if payload.get("type") == "url_verification":
        return {"challenge": payload["challenge"]}

    # Verify Slack signature for security
    if not verifier.is_valid_request(await request.body(), request.headers):
        raise HTTPException(status_code=403, detail="Invalid request signature")

    event: dict[str, Any] = payload.get("event", {})
    event_id = payload.get("event_id")

    if event_id in processed_event_ids:
        return JSONResponse(content={"status": "ignored"})
    processed_event_ids.append(event_id)

    create_and_send_reviews(event)

    return JSONResponse(content={"status": "ok"})


def send_slack_message(user_id: str, text: str) -> None:
    """Send message to slack user"""
    try:
        # Send text as private message to the user
        slack_client.chat_postMessage(
            channel=user_id,
            text=text,
        )
    except SlackApiError as e:
        raise HTTPException(
            status_code=500, detail=f"Slack API Error: {e.response['error']}"
        )


def create_and_send_reviews(event: dict[str, Any]) -> None:
    """Process input event text and look for trigger phrase"""

    if not (event.get("type") == "message" and event.get("bot_id") is None):
        return 
    
    user_id = event.get("user")
    email = extract_email_from_user_id(user_id)

    match event.get("text").lower():
        case "make_review":
            logger.info("Flow triggered: Project reviews")
            reviews = get_project_reviews(email)
        case "make_summary":
            logger.info("Flow triggered: Summary review")
            reviews = get_candidate_summary(email)
        case _:
            return

    for review in reviews:
        send_slack_message(user_id, review.content)
