"""
rule_engine/data_validator.py
数据完整性校验 —— 纯代码，不依赖 LLM。
"""
from pathlib import Path
from typing import Any, Dict, List, Tuple
import yaml

from schemas.models import ValidationIssue


class DataValidator:
    """校验输入 JSON 的字段完整性与数值类型。"""

    def __init__(self, rules_path: Path = None):
        if rules_path is None:
            rules_path = Path(__file__).parent.parent / "rules" / "batch_filter_rules.yaml"
        with open(rules_path, encoding="utf-8") as f:
            self.rules: Dict[str, Any] = yaml.safe_load(f)

    def validate_batches(self, batches: List[Dict[str, Any]]) -> Tuple[List[Dict], List[ValidationIssue]]:
        """
        Returns:
            (valid_batches, issues)
        """
        required_fields: List[str] = self.rules.get("required_fields", ["batch_id", "batch_type"])
        valid, issues = [], []

        for record in batches:
            batch_id = record.get("batch_id", "<unknown>")
            record_issues = []

            for field in required_fields:
                if field not in record or record[field] is None:
                    record_issues.append(
                        ValidationIssue(
                            field=field,
                            batch_id=batch_id,
                            message=f"批次 {batch_id} 缺少必填字段 '{field}'"
                        )
                    )

            if record_issues:
                issues.extend(record_issues)
            else:
                valid.append(record)

        return valid, issues
