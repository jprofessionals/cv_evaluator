from enum import StrEnum

from core.logging import get_logger
from resume.classes import Experience, Project

logger = get_logger(__name__)



# ISO 639-1 language codes, see documentation below
# https://docs.flowcase.com/country-and-language-codes#overview--language-codes
NOR = "no"


def safe_parse_description(proj: dict[str, str]) -> list[dict[str, str]]:
    """Parse and extract project description"""
    DESCRIPTION = "long_description"
    project_description = ""

    try:
        project_description = proj[DESCRIPTION][NOR]
    except KeyError:
        logger.debug("Missing project description")
    
    return project_description    

def safe_parse_skillset(proj: dict[str, list[dict]]) -> list[str]:
    """Parse and extract skillset."""
    skill_set = []
    
    project_skills = proj.get("project_experience_skills", [])

    if not isinstance(project_skills, list):
        logger.debug("Invalid or missing 'project_experience_skills' key")
        return skill_set

    for skill_dict in project_skills:
        try:
            skill_set.append(skill_dict["tags"][NOR].strip())
        except KeyError as e:
            logger.debug(f"Missing key {e} in project skill: {skill_dict}")
        except AttributeError:
            logger.debug(f"Invalid structure for skill tags: {skill_dict}")

    return sorted(skill_set)

def safe_parse_roles(
        proj: dict[str, list[dict[str, dict[str, str]]]]
    ) -> list[dict[str, str]]:

    """Parse and extract project roles"""

    DESCRIPTION = "long_description"
    NAME = "name"

    roles = []
    project_roles = proj.get("roles", [])
    
    for role in project_roles:
        try:
            # Ensure the NOR key exists in both NAME and DESCRIPTION fields
            role_name = role[NAME][NOR]
            role_description = role[DESCRIPTION][NOR]
            roles.append({role_name: role_description})
        except KeyError as e:
            logger.debug(f"Missing key {e} in role: {role}")

    return roles

def parse_experiences(experience: Experience) -> list[Project]:
    projects: list[Project] = []

    for project in experience.project:
        
        customer_name = project["customer"].get(NOR, "UKJENT")       
        project_name = project["description"].get(NOR, "UKJENT")

        logger.info(
            "Now checking:\n"
            f"Customer name: {customer_name}\n"
            f"Project name: {project_name}\n"
        )

        description = safe_parse_description(project)
        skillset = safe_parse_skillset(project)
        roles = safe_parse_roles(project)
            
        if not any([description, skillset, roles]):
            logger.info(f"{project_name}: important info missing: skip")
            continue

        projects.append(
            Project(
                customer=customer_name, 
                description=description,
                project=project_name,
                roles=roles,
                skills=skillset
            )
        )
        
    complete_projects = len(projects)
    logger.info(f"Found {complete_projects} projects to evaluate")

    return projects
