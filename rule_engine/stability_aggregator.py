"""
rule_engine/stability_aggregator.py
稳定性数据三层聚合引擎 —— 读取 rules/stability_rules.yaml，纯代码。
"""
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

from schemas.models import StabilityBatch, StabilityInput, RuleEngineResult, ProcessedBatch, BatchType


class StabilityAggregator:
    """
    对稳定性数据执行：
      1. 批次过滤（按 included_batch_types）
      2. 时间点聚合（提取起点 & 末点）
      3. 变化幅度计算
      4. 生成 summary_stats 供 Prompt 使用
    """

    def __init__(self, rules_path: Path = None):
        if rules_path is None:
            rules_path = Path(__file__).parent.parent / "rules" / "stability_rules.yaml"
        with open(rules_path, encoding="utf-8") as f:
            self.rules: Dict[str, Any] = yaml.safe_load(f)

        self.included_types: List[str] = self.rules.get("included_batch_types", [])
        self.lt_keywords: List[str]    = self.rules.get("long_term_condition_keywords", ["2–8", "2-8"])
        self.acc_keywords: List[str]   = self.rules.get("accelerated_condition_keywords", ["25°C", "25℃"])
        self.lt_end_pref: List[str]    = self.rules["long_term_key_time_points"]["end_preference"]
        self.acc_end_pref: List[str]   = self.rules["accelerated_key_time_points"]["end_preference"]

    def run(self, data: StabilityInput) -> RuleEngineResult:
        summary_stats: Dict[str, Any] = {
            "long_term": [],
            "accelerated": [],
        }

        for batch in data.batches:
            if self.included_types and batch.batch_type.value not in self.included_types:
                continue

            is_lt  = any(kw in batch.storage_condition for kw in self.lt_keywords)
            is_acc = any(kw in batch.storage_condition for kw in self.acc_keywords)

            tp_dict = {tp.time_point: tp.attributes for tp in batch.time_points}
            start_attrs = tp_dict.get("0M", {})
            end_time, end_attrs = self._pick_end(tp_dict, self.lt_end_pref if is_lt else self.acc_end_pref)

            changes: Dict[str, Any] = {}
            for attr, start_val in start_attrs.items():
                if attr in end_attrs and start_val is not None and end_attrs[attr] is not None:
                    changes[attr] = round(float(end_attrs[attr]) - float(start_val), 4)

            entry = {
                "batch_id": batch.batch_id,
                "batch_type": batch.batch_type.value,
                "storage_condition": batch.storage_condition,
                "start_time": "0M",
                "start_attrs": start_attrs,
                "end_time": end_time,
                "end_attrs": end_attrs,
                "changes": changes,
            }

            if is_lt:
                summary_stats["long_term"].append(entry)
            elif is_acc:
                summary_stats["accelerated"].append(entry)

        # 合规性摘要
        summary_stats["specifications"] = [
            {
                "attribute": s.attribute,
                "display_name": s.display_name,
                "unit": s.unit,
                "lower_limit": s.lower_limit,
                "upper_limit": s.upper_limit,
            }
            for s in data.specifications
        ]

        return RuleEngineResult(
            is_valid=True,
            included_batches=[],
            summary_stats=summary_stats,
        )

    # ------------------------------------------------------------------
    def _pick_end(self, tp_dict: Dict, preference: List[str]):
        for t in preference:
            if t in tp_dict:
                return t, tp_dict[t]
        # 取最后一个有数据的时间点
        if tp_dict:
            last = list(tp_dict.keys())[-1]
            return last, tp_dict[last]
        return "N/A", {}
