"""Pydantic v2 schemas for the configurable rule engine."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, field_validator

from app.services.rules.registry import (
    VALID_ACTIONS, VALID_CATEGORIES, VALID_OPERATORS,
    VALID_RULE_TYPES, VALID_SEVERITIES,
)


# ── Condition ─────────────────────────────────────────────────────────────────

class ConditionCreate(BaseModel):
    field:       str
    operator:    str
    value:       str
    value_type:  str = "number"
    description: Optional[str] = None

    @field_validator("operator")
    @classmethod
    def validate_operator(cls, v: str) -> str:
        if v not in VALID_OPERATORS:
            raise ValueError(f"operator must be one of: {sorted(VALID_OPERATORS)}")
        return v

    @field_validator("value_type")
    @classmethod
    def validate_value_type(cls, v: str) -> str:
        if v not in ("number", "string", "boolean", "list"):
            raise ValueError("value_type must be number | string | boolean | list")
        return v


class ConditionOut(BaseModel):
    id:          UUID
    field:       str
    operator:    str
    value:       str
    value_type:  str
    description: Optional[str]

    model_config = {"from_attributes": True}


# ── Action ────────────────────────────────────────────────────────────────────

class ActionCreate(BaseModel):
    action_type:     str
    action_order:    int = 1
    parameters_json: str = "{}"
    is_enabled:      bool = True

    @field_validator("action_type")
    @classmethod
    def validate_action_type(cls, v: str) -> str:
        if v not in VALID_ACTIONS:
            raise ValueError(f"action_type must be one of: {sorted(VALID_ACTIONS)}")
        return v


class ActionOut(BaseModel):
    id:              UUID
    action_type:     str
    action_order:    int
    parameters_json: str
    is_enabled:      bool

    model_config = {"from_attributes": True}


# ── Rule ──────────────────────────────────────────────────────────────────────

class RuleCreate(BaseModel):
    name:            str
    description:     Optional[str] = None
    category:        str
    rule_type:       str
    severity:        str = "warning"
    priority:        int = 100
    platform:        Optional[str] = None
    is_enabled:      bool = True
    condition_logic: str = "all"
    parameters_json:        str = "{}"
    recovery_metadata_json: str = "{}"
    conditions: list[ConditionCreate] = []
    actions:    list[ActionCreate]    = []

    # Playbook / legal context
    verdict:          Optional[str]     = None
    legal_basis:      Optional[str]     = None
    evidence_json:    str               = "[]"
    dispute_window:   Optional[str]     = None
    success_rate_pct: Optional[Decimal] = None
    recovery_min:     Optional[Decimal] = None
    recovery_max:     Optional[Decimal] = None
    auto_raise:       bool              = False
    playbook_notes:   Optional[str]     = None

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        if v not in VALID_CATEGORIES:
            raise ValueError(f"category must be one of: {sorted(VALID_CATEGORIES)}")
        return v

    @field_validator("rule_type")
    @classmethod
    def validate_rule_type(cls, v: str) -> str:
        if v not in VALID_RULE_TYPES:
            raise ValueError(f"rule_type must be one of: {sorted(VALID_RULE_TYPES)}")
        return v

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        if v not in VALID_SEVERITIES:
            raise ValueError(f"severity must be one of: {sorted(VALID_SEVERITIES)}")
        return v

    @field_validator("condition_logic")
    @classmethod
    def validate_logic(cls, v: str) -> str:
        if v not in ("all", "any"):
            raise ValueError("condition_logic must be 'all' or 'any'")
        return v


class RuleUpdate(BaseModel):
    name:            Optional[str]  = None
    description:     Optional[str]  = None
    severity:        Optional[str]  = None
    priority:        Optional[int]  = None
    platform:        Optional[str]  = None
    is_enabled:      Optional[bool] = None
    condition_logic: Optional[str]  = None
    parameters_json:        Optional[str] = None
    recovery_metadata_json: Optional[str] = None

    # Playbook / legal context
    verdict:          Optional[str]     = None
    legal_basis:      Optional[str]     = None
    evidence_json:    Optional[str]     = None
    dispute_window:   Optional[str]     = None
    success_rate_pct: Optional[Decimal] = None
    recovery_min:     Optional[Decimal] = None
    recovery_max:     Optional[Decimal] = None
    auto_raise:       Optional[bool]    = None
    playbook_notes:   Optional[str]     = None


class RuleOut(BaseModel):
    id:              UUID
    company_id:      Optional[UUID]
    name:            str
    description:     Optional[str]
    category:        str
    rule_type:       str
    severity:        str
    priority:        int
    platform:        Optional[str]
    is_enabled:      bool
    condition_logic: str
    parameters_json:        str
    recovery_metadata_json: str
    conditions: list[ConditionOut] = []
    actions:    list[ActionOut]    = []
    created_at: datetime
    updated_at: datetime

    # Playbook / legal context
    verdict:          Optional[str]     = None
    legal_basis:      Optional[str]     = None
    evidence_json:    Optional[str]     = "[]"
    dispute_window:   Optional[str]     = None
    success_rate_pct: Optional[Decimal] = None
    recovery_min:     Optional[Decimal] = None
    recovery_max:     Optional[Decimal] = None
    auto_raise:       bool              = False
    playbook_notes:   Optional[str]     = None

    model_config = {"from_attributes": True}


# ── Override ──────────────────────────────────────────────────────────────────

class OverrideCreate(BaseModel):
    is_enabled:      Optional[bool] = None
    severity:        Optional[str]  = None
    priority:        Optional[int]  = None
    parameters_json: Optional[str]  = None


class OverrideOut(BaseModel):
    id:              UUID
    rule_id:         UUID
    company_id:      UUID
    is_enabled:      Optional[bool]
    severity:        Optional[str]
    priority:        Optional[int]
    parameters_json: Optional[str]
    created_at:      datetime
    updated_at:      datetime

    model_config = {"from_attributes": True}


# ── Test / Evaluation results ─────────────────────────────────────────────────

class TestRuleRequest(BaseModel):
    context: dict[str, Any]
    dry_run: bool = True


class RuleEvaluationOut(BaseModel):
    rule_id:       str
    rule_type:     str
    rule_name:     str
    severity:      str
    matched:       bool
    actions_taken: list[dict]
    error_message: Optional[str]
    duration_ms:   int
    is_dry_run:    bool


class BatchEvaluationOut(BaseModel):
    settlement_id:   str
    company_id:      str
    platform:        str
    rules_evaluated: int
    rules_matched:   int
    total_actions:   int
    results:         list[RuleEvaluationOut]
    duration_ms:     int
    error_message:   Optional[str]
