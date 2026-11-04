"""
sections/p8_1_stability.py —— 2.3.P.8.1 稳定性综述章节处理器
"""
from typing import Any, Dict

from schemas.models import StabilityInput, RuleEngineResult
from sections.base_section import BaseSection
from rule_engine.stability_aggregator import StabilityAggregator


class P81Stability(BaseSection):

    @property
    def section_id(self) -> str:
        return "2.3.P.8.1"

    @property
    def section_name(self) -> str:
        return "稳定性综述与结论"

    def run_rule_engine(self, raw_data: Dict[str, Any]) -> RuleEngineResult:
        data = StabilityInput.model_validate(raw_data)
        engine = StabilityAggregator()
        return engine.run(data)

    def build_prompt_context(self, result: RuleEngineResult, raw_data: Dict[str, Any]) -> str:
        stats = result.summary_stats
        lines = []

        def _fmt_entry(entry: Dict) -> str:
            changes_str = "; ".join(
                f"{k}: {'+' if v >= 0 else ''}{v}"
                for k, v in entry.get("changes", {}).items()
            )
            return (
                f"  批号 {entry['batch_id']} ({entry['batch_type']})：\n"
                f"    考察条件：{entry['storage_condition']}\n"
                f"    起点({entry['start_time']})：{entry['start_attrs']}\n"
                f"    末点({entry['end_time']})：{entry['end_attrs']}\n"
                f"    变化量：{changes_str or '无变化'}"
            )

        lt_entries = stats.get("long_term", [])
        acc_entries = stats.get("accelerated", [])

        if lt_entries:
            lines.append(f"长期储存条件（{lt_entries[0]['storage_condition']}）：")
            for e in lt_entries:
                lines.append(_fmt_entry(e))
            lines.append("")

        if acc_entries:
            lines.append(f"加速条件（{acc_entries[0]['storage_condition']}）：")
            for e in acc_entries:
                lines.append(_fmt_entry(e))
            lines.append("")

        # 质量标准信息
        lines.append("质量标准（Specification）：")
        for sp in stats.get("specifications", []):
            lo = sp.get("lower_limit")
            hi = sp.get("upper_limit")
            if lo is not None and hi is not None:
                spec_str = f"{lo}–{hi} {sp['unit']}"
            elif lo is not None:
                spec_str = f"≥{lo} {sp['unit']}"
            elif hi is not None:
                spec_str = f"≤{hi} {sp['unit']}"
            else:
                spec_str = "按检查法"
            lines.append(f"  - {sp['display_name']}：{spec_str}")

        return "\n".join(lines)
