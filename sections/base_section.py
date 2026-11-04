"""
sections/base_section.py
新增章节时继承此基类，实现三个抽象方法即可接入 Writer Agent。
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict

from schemas.models import RuleEngineResult


class BaseSection(ABC):
    """所有 QOS 章节处理器的基类。"""

    @property
    @abstractmethod
    def section_id(self) -> str:
        """返回 CTD 章节编号，如 '2.3.P.5.4'"""

    @property
    @abstractmethod
    def section_name(self) -> str:
        """返回章节中文名称，如 '批分析'"""

    @abstractmethod
    def run_rule_engine(self, raw_data: Dict[str, Any]) -> RuleEngineResult:
        """
        执行确定性规则引擎：数据校验、过滤、聚合、统计。
        纯代码，不调用 LLM。
        """

    @abstractmethod
    def build_prompt_context(self, result: RuleEngineResult, raw_data: Dict[str, Any]) -> str:
        """
        将规则引擎结果转为注入 Prompt 的结构化文本块（[DATA] 标签内容）。
        """

    def get_prompt_template(self) -> str:
        """加载该章节的 Prompt 模板文件。"""
        tmpl_path = (
            Path(__file__).parent.parent / "prompts" / f"writer_{self.section_id.replace('.', '_')}.txt"
        )
        if not tmpl_path.exists():
            raise FileNotFoundError(f"找不到 Prompt 模板文件：{tmpl_path}")
        return tmpl_path.read_text(encoding="utf-8")
