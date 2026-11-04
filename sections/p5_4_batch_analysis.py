"""
sections/p5_4_batch_analysis.py —— 2.3.P.5.4 批分析章节处理器
"""
import json
from typing import Any, Dict

from schemas.models import BatchAnalysisInput, RuleEngineResult
from sections.base_section import BaseSection
from rule_engine.batch_filter import BatchFilter


class P54BatchAnalysis(BaseSection):

    @property
    def section_id(self) -> str:
        return "2.3.P.5.4"

    @property
    def section_name(self) -> str:
        return "批分析"

    def run_rule_engine(self, raw_data: Dict[str, Any]) -> RuleEngineResult:
        data = BatchAnalysisInput.model_validate(raw_data)
        engine = BatchFilter()
        return engine.run(data.batches, data.specifications)

    def build_prompt_context(self, result: RuleEngineResult, raw_data: Dict[str, Any]) -> str:
        data = BatchAnalysisInput.model_validate(raw_data)
        stats = result.summary_stats

        lines = [
            f"产品名称：{data.product_name}（产品代码：{data.product_code}）",
            f"剂型：{data.dosage_form}",
            "",
            f"纳入批次数：{stats.get('batch_count', 0)}",
            f"批号列表：{', '.join(stats.get('batch_ids', []))}",
            "",
            "批次类型分布：",
        ]
        for bt, cnt in stats.get("batch_type_summary", {}).items():
            lines.append(f"  - {bt}：{cnt} 批")

        lines += ["", "各关键质量属性检验结果范围（已核对规格限度）："]
        for attr, rng in stats.get("attribute_ranges", {}).items():
            lo = rng.get("lower_limit")
            hi = rng.get("upper_limit")
            spec_str = ""
            if lo is not None and hi is not None:
                spec_str = f"（限度：{lo}–{hi} {rng['unit']}）"
            elif lo is not None:
                spec_str = f"（限度：≥{lo} {rng['unit']}）"
            elif hi is not None:
                spec_str = f"（限度：≤{hi} {rng['unit']}）"
            lines.append(
                f"  - {rng['display_name']}：{rng['min']}–{rng['max']} {rng['unit']} {spec_str}"
            )

        # 超规格批次警告
        oos_batches = [b for b in result.included_batches if b.out_of_spec]
        if oos_batches:
            lines += ["", "⚠️ 以下批次存在超规格项："]
            for b in oos_batches:
                lines.append(f"  - {b.batch_id}：{', '.join(b.out_of_spec)}")

        return "\n".join(lines)
