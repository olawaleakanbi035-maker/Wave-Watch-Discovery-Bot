from pydantic import BaseModel

class WaveIssue(BaseModel):
    repo_name: str
    title: str
    points: int
    url: str
    skills: list[str] = []
