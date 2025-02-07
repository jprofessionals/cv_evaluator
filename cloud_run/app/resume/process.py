import requests

from requests import Session

from core.config import settings
from core.logging import get_logger
from models.llm import evaluate_projects, evaluate_summary
from models.classes import Review
from resume.classes import Experience, Project, User
from resume.parse import parse_experiences, safe_parse_summary

BASE_URL = "https://jpro.cvpartner.com/api"

# Set up module logger
logger = get_logger(__name__)


def get_cv_partner_session() -> Session:
    """Create a session and return it"""

    api_key = settings.CV_PARTNER_API_KEY
    session = requests.Session()
    session.headers.update({'Authorization': f'Bearer {api_key}'})
    session.headers.update({'Content-Type': 'application/json'})
    return session

class CVPartnerAPI:

    def __init__(self, user_email: str):
        self.email = user_email
        self.session = get_cv_partner_session()
        user = self.find_user_from_email()
        self.resume = self.get_resume(user)

    def find_user_from_email(self) -> User:
        result = self.session.get(
            f"{BASE_URL}/v1/users/find?email={self.email}")
        try:
            user_data = result.json()
        except requests.JSONDecodeError:
            logger.error(
                f"Unable to extract user info from email: {self.email}"
            )
            raise
        
        return User(
            user_id=user_data["user_id"], 
            cv_id=user_data["default_cv_id"], 
            email=self.email
        )

    def get_resume(self, user: User) -> Experience:
        resume_path = f"{BASE_URL}/v3/cvs/{user.user_id}/{user.cv_id}"
        result = self.session.get(resume_path)
            
        data = result.json()

        return Experience(
            project=data["project_experiences"], 
            work=data["work_experiences"],
            summary=data["key_qualifications"]
        )
    
    def get_projects(self) -> list[Project]:
        """Extract candidate experience from CV Partner"""
        return parse_experiences(self.resume.project)

    def get_summary(self) -> str:
        return safe_parse_summary(self.resume.summary)
        

def get_project_reviews(email: str) -> list[Review]:
    """Utility fn for extracting project descriptions and send to reviewer."""
    cv_partner = CVPartnerAPI(email)
    projects = cv_partner.get_projects()
    return evaluate_projects(projects)


def get_candidate_summary(email: str) -> str:
    """Utility fn for processing"""
    cv_partner = CVPartnerAPI(email)
    context = cv_partner.get_projects()
    summary = cv_partner.get_summary()
    return evaluate_summary(context, summary)
