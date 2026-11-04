"""
agents/writer_agent.py —— 文档撰写 Agent
流程：Rule Engine → Prompt 构建 → LLM 调用 → 结构化输出
"""
import json
import os
import re
from pathlib import Path
from typing import Any, Dict

from openai import OpenAI
from dotenv import load_dotenv

from schemas.models import DraftOutput, SourceMapItem
from sections import get_section

load_dotenv()


class WriterAgent:
    """
    文档撰写 Agent。
    职责：确定性数据处理 + LLM 受控行文，不触碰数值判断。
    """

    def __init__(self, model: str = None):
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        )
        self.model = model or os.getenv("LLM_MODEL", "gpt-4o-mini")

    # ------------------------------------------------------------------
    def run(self, section_id: str, raw_data: Dict[str, Any]) -> DraftOutput:
        """
        Args:
            section_id: 如 "2.3.P.5.4"
            raw_data:   对应章节的输入 JSON（已解析为 dict）
        Returns:
            DraftOutput
        """
        # Step 1: 加载章节处理器
        section = get_section(section_id)

        # Step 2: 运行规则引擎（纯代码，零 LLM）
        rule_result = section.run_rule_engine(raw_data)

        # Step 3: 构建 Prompt 上下文
        data_context = section.build_prompt_context(rule_result, raw_data)
        prompt_template = section.get_prompt_template()
        full_prompt = prompt_template.replace("{data_context}", data_context)

        # Step 4: 调用 LLM
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0.0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "你是一位资深注册药学专家，只能基于提供的数据撰写内容。"},
                {"role": "user",   "content": full_prompt},
            ],
        )

        raw_output = response.choices[0].message.content
        llm_json = json.loads(raw_output)

        content   = llm_json.get("content", "")
        placeholders = llm_json.get("unresolved_placeholders", [])
        # 兜底：从正文提取 [待确认:...] 占位符
        found = re.findall(r"\[待确认[：:][^\]]+\]", content)
        placeholders = list(set(placeholders + found))

        # Step 5: 生成来源映射（基于规则引擎统计，粗粒度）
        source_map = self._build_source_map(rule_result)

        return DraftOutput(
            section_id=section_id,
            content=content,
            source_map=source_map,
            unresolved_placeholders=placeholders,
            rule_engine_result=rule_result,
        )

    # ------------------------------------------------------------------
    def _build_source_map(self, rule_result) -> list[SourceMapItem]:
        items = []
        stats = rule_result.summary_stats
        sid = 0

        for batch_id in stats.get("batch_ids", []):
            sid += 1
            items.append(SourceMapItem(
                sentence_id=sid,
                source_field="batch_id",
                batch_id=batch_id,
                value=batch_id,
            ))

        for attr, rng in stats.get("attribute_ranges", {}).items():
            sid += 1
            items.append(SourceMapItem(
                sentence_id=sid,
                source_field=attr,
                value=f"{rng['min']}–{rng['max']} {rng.get('unit','')}",
            ))

        return items
