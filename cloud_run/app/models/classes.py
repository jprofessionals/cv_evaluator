from dataclasses import dataclass

@dataclass
class Review:
    customer: str
    project: str
    description: str
    review_text: str



@dataclass
class Reviews:
    """Represent all reviewed projects"""
    review: list[Review]

    @property
    def content(self) -> str:
        """Output content"""
        rev = self.review[0]
        return f"""
        \nEvaluert prosjekt: {rev.project} (kunde: {rev.customer})
        \nEvaluering:\n{rev.review_text}\n"""
