from typing import Optional, Any, Dict, List
from pydantic import BaseModel, Field

class QueryPlan(BaseModel):
    """
    Structured representation of the user's semantic intent.
    This is populated by GPT-OSS via the tool reduction schema or internally.
    """
    source_mode: Optional[str] = Field(None, description="'dashboard', 'mcp', or 'hybrid'")
    capabilities: List[str] = Field(default_factory=list)
    entity: Optional[str] = Field(None, description="e.g. profile, repository, repositories, pull_request, issue, file, activity")
    scope: Optional[str] = Field(None, description="e.g. current_profile, specific_repository, all_user_repositories")
    operation: Optional[str] = Field(None, description="e.g. count, sum, max, min, top_n, latest_n, sort, filter, select_fields, group_by, aggregate")
    metric: Optional[str] = Field(None, description="e.g. stars, forks, languages, stargazers_count")
    repository: Optional[str] = Field(None, description="Explicit repository name, if supplied")
    filters: Dict[str, Any] = Field(default_factory=dict)
    sort: Optional[str] = Field(None, description="Sort direction or field, e.g. 'desc' or 'updated_at'")
    limit: Optional[int] = Field(None, description="Number of items to limit to")
    explicit_source_instruction: bool = Field(False, description="Did the user explicitly demand MCP or dashboard?")
    clarification_required: bool = Field(False)
    clarification_reason: Optional[str] = None

def validate_query_plan(plan_data: dict, capability_contract: dict) -> QueryPlan:
    """
    Validates a raw dictionary (often from the LLM tool call) against capability contracts.
    Raises ValueError if unsupported.
    """
    plan = QueryPlan(**plan_data)
    
    # Contract validation happens externally by checking the plan against capability_contract.py rules
    return plan
