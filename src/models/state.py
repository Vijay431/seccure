from pydantic import BaseModel, Field


class IssueSummary(BaseModel):
    issue_number: int
    title: str
    labels: list[str]
    url: str


class PRSummary(BaseModel):
    pr_number: int
    package: str
    from_version: str
    to_version: str


class VulnerabilitySummary(BaseModel):
    cve_id: str
    severity: str
    package: str
    patched_version: str


class AlertSummary(BaseModel):
    critical_count: int
    high_count: int
    vulnerabilities: list[VulnerabilitySummary]


class SeccureState(BaseModel):
    issues: list[IssueSummary] = Field(default_factory=list)
    pull_requests: list[PRSummary] = Field(default_factory=list)
    alerts: AlertSummary = Field(
        default_factory=lambda: AlertSummary(
            critical_count=0, high_count=0, vulnerabilities=[]
        )
    )
