from dataclasses import dataclass

@dataclass
class Review:
    customer: str
    project: str
    description: str
    review_text: str

    @property
    def content(self) -> str:
        """Output content"""
        return f"""
        \nEvaluert prosjekt: {self.project} (kunde: {self.customer})
        \nEvaluering:\n{self.review_text}\n"""

@dataclass
class Reviews:
    """Represent all reviewed projects"""
    review: list[Review]

    
