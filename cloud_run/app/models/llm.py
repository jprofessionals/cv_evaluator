
from functools import lru_cache
from openai import OpenAI

from core.config import settings
from core.logging import get_logger
from models.prompt import (
    system_prompt, 
    project_prompt,
    summary_system_prompt,
    summary_user_prompt
)
from models.classes import Review
from resume.classes import Project

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def get_openai_client() -> OpenAI:
    """Creates and caches the OpenAI client"""
    return OpenAI(api_key=settings.OPENAI_API_KEY)


def get_model_response(
    message: str,
    system_prompt: str,
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
            {"role": "user", "content": message},
        ]
        completion = client.chat.completions.create(
            model=model, messages=messages, temperature=temperature
        )
        
        # Extract and return the response
        return completion.choices[0].message.content

    except Exception as e:
        logger.error(f"Failed to get model response: {e}")
        return "<FAILED>"


def evaluate_projects(projects: list[Project]) -> list[Review]:
    """Review each project in the list"""
    reviews = []

    for proj in projects:
        logger.info(f"Now reviewing: {proj.project}")

        text = proj.to_text()
        message = project_prompt.format(text)
        review = get_model_response(message, system_prompt)
        
        reviews.append(
            Review(
                customer=proj.customer, 
                project=proj.project,
                description=proj.description,
                review=review
            )
        )
    return reviews


from typing import Protocol


class PromptConstructor(Protocol):
    """Keep track of prompts related to review of candidate summary."""

    def __init__(self, context: list[Project], message: str | None):
        self.context = context
        self.message = message

    def make_system_prompt(self) -> str:
        pass 
    
    def make_user_message(self) -> str:
        pass 

    def make_model_input(self) -> list[dict[str, str]]:
        pass 


class SummmaryPromptConstructor(PromptConstructor):
    def __init__(self, context: list[Project], message: str | None):
        super().__init__(context, message)

    def make_system_prompt(self):
        return summary_system_prompt
        
    def make_user_message(self):
        context = "\n".join([p.to_text() for p in self.context])
        summary = self.message
        return summary_user_prompt.format(
            context=context, 
            summary=summary,   
        )
    
    def make_model_input(self):
        return [
            {"role": "developer", "content": self.make_system_prompt()},
            {"role": "user", "content": self.make_user_message()},
        ]


def evaluate_summary(context: list[Project], summary: str) -> list[Review]:
    """Evaluate the candidate summary"""

    logger.info("Evaluating candidate summary")

    prompt_handler = SummmaryPromptConstructor(context, message=summary)
    system_prompt = prompt_handler.make_system_prompt()
    message = prompt_handler.make_user_message()

    review = get_model_response(message, system_prompt)

    return [
        Review(
            customer="Not applicable", 
            project=" Not applicable",
            description="Candidate summary",
            review=review
        )
    ]
