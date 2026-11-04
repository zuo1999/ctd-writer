"""
rule_engine/spec_checker.py
数值与 Specification 限度比对 —— 纯代码，零 LLM。
"""
from typing import Any, Dict, List


class SpecChecker:
    """将批次属性值与质量标准限度比对，返回超限属性名列表。"""

    def check(self, attributes: Dict[str, Any], specifications) -> List[str]:
        out_of_spec = []
        for spec in specifications:
            attr = spec.attribute
            if attr not in attributes or attributes[attr] is None:
                continue
            val = float(attributes[attr])
            if spec.lower_limit is not None and val < spec.lower_limit:
                out_of_spec.append(attr)
            elif spec.upper_limit is not None and val > spec.upper_limit:
                out_of_spec.append(attr)
        return out_of_spec
