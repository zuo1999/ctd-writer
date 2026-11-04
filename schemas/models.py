"""
schemas/models.py — 全局数据契约
所有 Agent、Rule Engine、Section 共享此模型定义。
"""
from __future__ import annotations
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 枚举
# ---------------------------------------------------------------------------

class BatchType(str, Enum):
    ENGINEERING       = "工程批"
    TOXICOLOGY        = "毒理批"
    CLINICAL          = "临床批"
    PROCESS_VALIDATION = "工艺验证批"
    COMMERCIAL        = "商业化规模批"
    REPEAT            = "重复批"


class IssueSeverity(str, Enum):
    CRITICAL = "CRITICAL"   # 数值/批号错误
    MAJOR    = "MAJOR"      # 结构缺失
    MINOR    = "MINOR"      # 格式/用语建议


class OverallStatus(str, Enum):
    APPROVED       = "APPROVED"
    NEEDS_REVISION = "NEEDS_REVISION"


# ---------------------------------------------------------------------------
# 输入层模型
# ---------------------------------------------------------------------------

class SpecLimit(BaseModel):
    attribute:    str
    display_name: str
    unit:         str = ""
    lower_limit:  Optional[float] = None
    upper_limit:  Optional[float] = None
    is_cqa:       bool = True


class BatchRecord(BaseModel):
    batch_id:   str
    batch_type: BatchType
    attributes: Dict[str, Any] = Field(default_factory=dict)


class BatchAnalysisInput(BaseModel):
    product_name: str
    product_code: str
    dosage_form:  str = ""
    batches:      List[BatchRecord]
    specifications: List[SpecLimit]


class StabilityTimePoint(BaseModel):
    time_point: str
    attributes: Dict[str, Any] = Field(default_factory=dict)


class StabilityBatch(BaseModel):
    batch_id:          str
    batch_type:        BatchType
    storage_condition: str
    time_points:       List[StabilityTimePoint]


class StabilityInput(BaseModel):
    product_name:   str
    product_code:   str
    batches:        List[StabilityBatch]
    specifications: List[SpecLimit]


# ---------------------------------------------------------------------------
# 规则引擎输出模型
# ---------------------------------------------------------------------------

class ValidationIssue(BaseModel):
    field:    str
    batch_id: Optional[str] = None
    message:  str


class ProcessedBatch(BaseModel):
    batch_id:    str
    batch_type:  BatchType
    attributes:  Dict[str, Any]
    out_of_spec: List[str] = Field(default_factory=list)


class RuleEngineResult(BaseModel):
    is_valid:          bool
    validation_issues: List[ValidationIssue] = Field(default_factory=list)
    included_batches:  List[ProcessedBatch]  = Field(default_factory=list)
    excluded_batches:  List[str]             = Field(default_factory=list)
    summary_stats:     Dict[str, Any]        = Field(default_factory=dict)
    missing_fields:    List[str]             = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Writer Agent 输出模型
# ---------------------------------------------------------------------------

class SourceMapItem(BaseModel):
    sentence_id:  int
    source_field: str
    batch_id:     Optional[str] = None
    value:        str


class DraftOutput(BaseModel):
    section_id:               str
    content:                  str
    source_map:               List[SourceMapItem] = Field(default_factory=list)
    unresolved_placeholders:  List[str]           = Field(default_factory=list)
    rule_engine_result:       Optional[RuleEngineResult] = None


# ---------------------------------------------------------------------------
# Reviewer Agent 输出模型
# ---------------------------------------------------------------------------

class QCIssue(BaseModel):
    issue_id:      str
    check_module:  str
    severity:      IssueSeverity
    location:      str
    original_text: str
    expected:      Optional[str] = None
    suggestion:    str


class ReviewReport(BaseModel):
    overall_status:          OverallStatus
    section_id:              str
    issues:                  List[QCIssue] = Field(default_factory=list)
    unresolved_placeholders: List[str]     = Field(default_factory=list)
    summary:                 str
    annotated_content:       Optional[str] = None
