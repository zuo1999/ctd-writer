# CTD-Writer — 药政申报文档智能撰写 Agent

> 基于安进（Amgen）发表于 AAPS Open (2025) 的药政数字化研究，面向制药注册申报（RA CMC）场景构建的受控文档生成 Agent。

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.35+-red.svg)](https://streamlit.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 📌 背景与核心痛点

ICH CTD Module 2.3 QOS（质量总体概述）是药品申报中**耗时最长、重复性最高**的文件。撰写人员需要从 Module 3（批分析、稳定性等）海量数据中逐项筛选合规批次、提取极值与变化趋势，再按固定文风形成综述。

传统 LLM 直接生成极易出现**数值幻觉、批次错漏、超限指标漏报**。

**CTD-Writer 解决方案**：
采用 **“规则引擎确定性计算 + LLM 受控行文”** 的分层解耦架构，LLM 仅负责语言组织，严禁触碰任何数值计算与超限判断，彻底消除数据幻觉。

---

## 🏗️ 架构设计

```
M3 结构化数据 (JSON)
       │
       ▼
┌──────────────────────────────────────────────┐
│  1. 业务规则引擎 (Rule Engine - 纯代码无LLM)    │
│  - 批次类型过滤 (毒理/临床/工艺验证/商业化)      │
│  - 字段与类型校验 (Pydantic models)           │
│  - 极值范围与超规格比对 (Specification Check)   │
│  - 稳定性时间点提取与变化量计算                │
└──────────────────────┬───────────────────────┘
                       │ 注入 [DATA] 上下文
                       ▼
┌──────────────────────────────────────────────┐
│  2. 认知生成层 (Prompt + LLM)                 │
│  - 按章节加载专属 Prompt 模板                 │
│  - 严格零幻觉约束：缺失字段自动标记 [待确认]    │
│  - 生成来源溯源映射表 (Source Map)             │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│  3. 交付层 (Delivery)                         │
│  - Word (.docx) 原生文档导出                  │
│  - 标准 Draft JSON 导出 (对接 ctd-reviewer)   │
└──────────────────────────────────────────────┘
```

---

## 💡 核心设计亮点

1. **规则外置化（YAML）**：
   批次筛选逻辑、稳定性考察时间点偏好等全部外置在 `rules/*.yaml` 中，更新业务规则无需改动任何 Python 源码。
2. **章节可插拔（Pluggable Sections）**：
   所有章节处理器继承 `BaseSection` 基类，新增章节只需实现接口并在 `sections/__init__.py` 注册一行，前端自动发现。
3. **零数值幻觉**：
   大模型仅接收规则引擎产出的计算统计结果，并输出 `source_map` 数据血缘追溯。

---

## 📂 项目结构

```
ctd-writer/
├── app.py                     # Streamlit 独立交互工作台
├── agents/
│   └── writer_agent.py        # Writer Agent 核心编排器
├── rule_engine/               # 确定性规则层（零 LLM）
│   ├── batch_filter.py        # 批次类型过滤
│   ├── data_validator.py      # 字段完整性校验
│   ├── spec_checker.py        # 质量标准 (Spec) 限度比对
│   └── stability_aggregator.py# 稳定性起点/末点聚合
├── sections/                  # 可插拔章节处理器
│   ├── base_section.py        # 章节基类
│   ├── p5_4_batch_analysis.py # 2.3.P.5.4 批分析
│   └── p8_1_stability.py      # 2.3.P.8.1 稳定性综述与结论
├── rules/                     # 外置规则配置（YAML）
│   ├── batch_filter_rules.yaml
│   └── stability_rules.yaml
├── prompts/                   # 章节专属 Prompt 模板
│   ├── writer_2_3_P_5_4.txt
│   └── writer_2_3_P_8_1.txt
├── schemas/models.py          # 全局 Pydantic 数据契约
├── data/                      # 样例输入数据
│   ├── batch_analysis.json
│   └── stability.json
└── requirements.txt
```

---

## 🚀 快速上手

### 1. 安装环境

```bash
git clone https://github.com/zuo1999/ctd-writer.git
cd ctd-writer
pip install -r requirements.txt
```

### 2. 配置密钥

```bash
cp .env.example .env
# 编辑 .env，填入 OPENAI_API_KEY (支持 OpenAI / DeepSeek / 任何兼容 API)
```

### 3. 启动交互工作台

```bash
streamlit run app.py
```

访问 `http://localhost:8501`，点击“载入示例数据”即可体验一键受控生成。

---

## 🔧 扩展指南

### 如何新增章节（如 2.3.P.1 剂型与组成）
1. 在 `sections/` 新建 `p1_description.py`，继承 `BaseSection` 并实现规则提取与上下文组装；
2. 在 `sections/__init__.py` 的 `SECTION_REGISTRY` 注册一行；
3. 在 `prompts/` 增加对应的 `writer_2_3_P_1.txt`。

---

## 📄 License
MIT
