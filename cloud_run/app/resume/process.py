import requests

from requests import Session

from core.config import settings
from core.logging import get_logger
from models.llm import get_reviews
from models.classes import Review
from resume.classes import Experience, Project, User


BASE_URL = "https://jpro.cvpartner.com/api"


# Set up module logger
logger = get_logger(__name__)


def get_cv_partner_session() -> Session:
    """
    Create a session and return
    """
    api_key = settings.CV_PARTNER_API_KEY
    session = requests.Session()
    session.headers.update({'Authorization': f'Bearer {api_key}'})
    session.headers.update({'Content-Type': 'application/json'})
    return session

def process_experience(experience: Experience) -> list[Project]:
    projects: list[Project] = []

    for proj in experience.project:
        
        customer = proj["customer"]["no"]
        project_name = proj["description"]["no"]

        base_msg = f"Customer name: '{customer}'. Project name: '{project_name}'"

        try: 
            skillset = [x["tags"]["no"].strip() for x in proj["project_experience_skills"]]
        except KeyError:
            skillset = []
            warn_message = f"Warning! {base_msg}: Empty skillset!"
            logger.debug(warn_message)
        
        try:
            roles = [{x["name"]["no"]: x["long_description"]["no"]} for x in proj["roles"]]
        except KeyError:
            roles = []
            warn_message = f"Warning! {base_msg}: Empty roles!"
            logger.debug(warn_message)

        try:
            project_description = proj["long_description"]["no"]
        except KeyError:
            project_description = ""
            warn_message = f"Warning! {base_msg}: No project description!"
            logger.debug(warn_message)
            
        p = Project(
            customer=customer, 
            project=project_name,
            description=project_description,
            roles = roles,
            skills = sorted(skillset)
        )
        projects.append(p)

    logger.info(f"Found {len(projects)} projects to evaluate")

    return projects

class CVPartnerAPI:
    def __init__(self, user_email: str):
        self.email = user_email
        self.session = get_cv_partner_session()
    
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


    def get_experience(self, user: User) -> Experience:
        result = self.session.get(
            f"{BASE_URL}/v3/cvs/{user.user_id}/{user.cv_id}"
        )
        data = result.json()

        return Experience(
            project=data["project_experiences"], 
            work=data["work_experiences"]
        )
    
    def get_projects(self) -> list[Project]:
        """
        Extract project experiences from CV Partner
        """
        user = self.find_user_from_email()
        experience = self.get_experience(user)
        projects = process_experience(experience)

        return projects

def get_project_reviews(email: str) -> list[Review]:
    
    cv_partner = CVPartnerAPI(email)
    projects = cv_partner.get_projects()
    reviews = get_reviews(projects)
    
    return reviews