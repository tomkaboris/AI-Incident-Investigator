from pydantic import BaseModel


class IncidentReport(BaseModel):
    title: str
    executive_summary: str
    impact: str
    timeline: list[str]
    root_cause: str
    resolution: str
    preventive_actions: list[str]
    markdown: str
