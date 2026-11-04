"""
rule_engine/batch_filter.py
批次过滤引擎 —— 读取 rules/batch_filter_rules.yaml，不依赖 LLM。
"""
from pathlib import Path
from typing import Any, Dict, List, Tuple
import yaml

from schemas.models import BatchRecord, BatchType, ProcessedBatch, RuleEngineResult, ValidationIssue
from rule_engine.data_validator import DataValidator
from rule_engine.spec_checker import SpecChecker


class BatchFilter:
    """根据规则筛选 QOS 2.3.P.5.4 应纳入的批次。"""

    def __init__(self, rules_path: Path = None):
        if rules_path is None:
            rules_path = Path(__file__).parent.parent / "rules" / "batch_filter_rules.yaml"
        with open(rules_path, encoding="utf-8") as f:
            self.rules: Dict[str, Any] = yaml.safe_load(f)

        self.included_types: List[str] = self.rules.get("included_batch_types", [])
        self.excluded_types: List[str] = self.rules.get("excluded_batch_types", [])
        self.max_per_type: Dict[str, Any] = self.rules.get("max_per_type", {})
        self.include_oos: bool = self.rules.get("include_out_of_spec", True)

    def run(self, batches: List[BatchRecord], specifications) -> RuleEngineResult:
        validator = DataValidator()
        spec_checker = SpecChecker()

        # Step 1: 字段校验
        raw_dicts = [b.model_dump() for b in batches]
        valid_dicts, val_issues = validator.validate_batches(raw_dicts)

        included: List[ProcessedBatch] = []
        excluded: List[str] = []
        type_counts: Dict[str, int] = {}

        for record in batches:
            # Step 2: 类型过滤
            bt = record.batch_type.value
            if bt in self.excluded_types:
                excluded.append(record.batch_id)
                continue
            if self.included_types and bt not in self.included_types:
                excluded.append(record.batch_id)
                continue

            # Step 3: 数量限制
            max_n = self.max_per_type.get(bt)
            if max_n is not None and type_counts.get(bt, 0) >= max_n:
                excluded.append(record.batch_id)
                continue

            # Step 4: 规格校验
            oos = spec_checker.check(record.attributes, specifications)

            if oos and not self.include_oos:
                excluded.append(record.batch_id)
                continue

            included.append(ProcessedBatch(
                batch_id=record.batch_id,
                batch_type=record.batch_type,
                attributes=record.attributes,
                out_of_spec=oos,
            ))
            type_counts[bt] = type_counts.get(bt, 0) + 1

        # Step 5: 生成统计摘要（供 Prompt 使用）
        summary_stats = self._compute_stats(included, specifications)

        return RuleEngineResult(
            is_valid=len(val_issues) == 0,
            validation_issues=val_issues,
            included_batches=included,
            excluded_batches=excluded,
            summary_stats=summary_stats,
        )

    # ------------------------------------------------------------------
    def _compute_stats(self, batches: List[ProcessedBatch], specifications) -> Dict[str, Any]:
        """计算每个质量属性的 min/max/range，供 Prompt 直接使用。"""
        if not batches:
            return {}

        stats: Dict[str, Any] = {
            "batch_count": len(batches),
            "batch_ids": [b.batch_id for b in batches],
            "batch_type_summary": {},
            "attribute_ranges": {},
        }

        # 批次类型统计
        for b in batches:
            bt = b.batch_type.value
            stats["batch_type_summary"][bt] = stats["batch_type_summary"].get(bt, 0) + 1

        # 属性范围统计
        for spec in specifications:
            attr = spec.attribute
            values = [
                b.attributes[attr]
                for b in batches
                if attr in b.attributes and b.attributes[attr] is not None
            ]
            if not values:
                continue
            stats["attribute_ranges"][attr] = {
                "display_name": spec.display_name,
                "unit": spec.unit,
                "min": min(values),
                "max": max(values),
                "lower_limit": spec.lower_limit,
                "upper_limit": spec.upper_limit,
            }

        return stats
