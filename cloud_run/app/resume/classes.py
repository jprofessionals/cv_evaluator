from dataclasses import dataclass, field

@dataclass
class User:
    user_id: str
    cv_id: str
    email: str

@dataclass
class Experience:
    """Represent a user's experience in CV Partner"""
    project: list[dict[str, str]] = field(default_factory=list)
    work: list[dict[str, str]] = field(default_factory=list)


@dataclass
class Project:
    """Represent a customer project in CV Partner"""

    customer: str # Name of customer
    project: str # Name of project
    description: str # Project description field

    roles: list[dict[str, str]] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)

    def _process_roles(self) -> str:
        """
        Process each role and description in the project. We ignore 
        the role title for now and simply concatenate all descriptions
        """
        return " ".join(["".join(role.values()) for role in self.roles])

    def to_llm_format(self) -> str:
        """
        Output a format that is easy for language models to consume
        """
        return f"""
            KUNDE: {self.customer} 
            PROSJEKT: {self.project} 
            PROSJEKTBESKRIVELSE: {self.description} 
            ROLLER: {self._process_roles()}
            """