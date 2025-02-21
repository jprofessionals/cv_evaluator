from dataclasses import dataclass

@dataclass
class Review:
    customer: str
    project: str
    description: str
    review: str

    @property
    def content(self) -> str:
        """Output content"""
        return (
            f"\nEvaluert prosjekt: {self.project}"
            f"\nKunde: {self.customer})"
            f"\nEvaluering:\n {self.review}"
        )

@dataclass
class Reviews:
    """Represent all reviewed projects"""
    review: list[Review]

    
