from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, model_validator

Agent = Literal["REPOSITORY", "RESEARCH", "CODE_ANALYST", "SECURITY", "DEVELOPER", "TESTER", "DEBUGGER", "REVIEWER", "REPORTER"]
Tool = Literal["list_files", "read_file", "search_code", "inspect_project", "inspect_dependencies", "security_scan", "inspect_git_diff", "modify_file", "run_tests"]

class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")

class Task(Strict):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,40}$")
    objective: str = Field(min_length=1, max_length=1000)
    agent: str = Field(min_length=1, max_length=80)
    dependencies: list[str] = Field(default_factory=list, max_length=12)
    tools: list[Tool] = Field(default_factory=list, max_length=9)
    success_criteria: str = Field(min_length=1, max_length=1000)
    priority: int = Field(default=1, ge=1, le=20)

class Plan(Strict):
    tasks: list[Task] = Field(min_length=1, max_length=12)

    @model_validator(mode="after")
    def valid_dag(self):
        seen = set()
        for task in self.tasks:
            if task.id in seen or any(dep not in seen for dep in task.dependencies):
                raise ValueError("Tasks require unique IDs and topologically ordered dependencies")
            seen.add(task.id)
        return self

class ToolRequest(Strict):
    name: Tool
    path: str = Field(default=".", max_length=240)
    query: str = Field(default="", max_length=200)
    content: str = Field(default="", max_length=24000)
    expected_sha256: str = Field(default="", max_length=64)

class Finding(Strict):
    severity: Literal["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
    title: str = Field(max_length=200)
    description: str = Field(max_length=2000)
    evidence_id: str = Field(max_length=80)
    affected_file: str = Field(max_length=240)
    recommendation: str = Field(max_length=2000)

class AgentResponse(Strict):
    summary: str = Field(max_length=3000)
    tool_requests: list[ToolRequest] = Field(default_factory=list, max_length=3)
    findings: list[Finding] = Field(default_factory=list, max_length=12)
    complete: bool = False

class Evaluation(Strict):
    accepted: bool
    summary: str = Field(max_length=2000)
    retry: bool = False

class Start(Strict):
    run_id: str = Field(pattern=r"^[a-f0-9-]{36}$")
    project_id: str = Field(pattern=r"^[a-f0-9-]{36}$")
    objective: str = Field(min_length=1, max_length=4000)
    workspace: str = Field(min_length=1, max_length=240)
    mode: Literal["READ_ONLY", "EDIT_MODE"] = "READ_ONLY"
    agents: list[dict] = Field(default_factory=list, max_length=30)
    tools: list[Tool] = Field(default_factory=list, max_length=20)
    workflow: dict | None = None

class Decision(Strict):
    approval_id: str = Field(max_length=80)
    approved: bool
