
from functools import lru_cache
from openai import OpenAI

from core.config import settings
from core.logging import get_logger
from models.prompt import system_prompt, project_prompt
from models.classes import Review, Reviews
from resume.classes import Project

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def get_openai_client() -> OpenAI:
    """Creates and caches the OpenAI client"""
    return OpenAI(api_key=settings.OPENAI_API_KEY)


def get_model_response(
    message: str,
    model: str = "gpt-4o",
    temperature: float = 0,
) -> str:
    
    if not message.strip():
        raise ValueError("Message cannot be empty.")

    try:
        # Get the cached client
        client = get_openai_client()

        messages = [
            {"role": "developer", "content": system_prompt},
            {
                "role": "user",
                "content": message
            }
        ]
        completion = client.chat.completions.create(
            model=model, messages=messages, temperature=temperature
        )
        
        # Extract and return the response
        return completion.choices[0].message.content

    except Exception as e:
        logger.error(f"Failed to get model response: {e}")
        return "<FAILED>"

def get_reviews(projects: list[Project]) -> Reviews:
    reviews = []
    num = 0

    for p in projects:
        num += 1

        text = p.to_llm_format()
        message = project_prompt.format(text)
        review = get_model_response(message)
        
        reviews.append(
            Review(
                customer=p.customer, 
                project=p.project,
                description=p.description,
                review_text=review
            )
        )
        if num == 3:
            break

    return Reviews(reviews)