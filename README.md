# CTD-Writer: 注册申报质量总体概述 (QOS) 受控生成系统

CTD-Writer 面向制药企业注册申报（Regulatory Affairs, RA / CMC）场景，用于将 ICH eCTD Module 3（质量详细数据）中的批分析与稳定性检验结果，受控汇总并撰写为 Module 2.3（QOS, Quality Overall Summary）合规章节初稿。

项目采用 **“确定性规则代码化 + 语言组织模型化”** 的分级解耦架构。核心数值计算、超规格比对与批次准入判定全部由底层规则引擎执行，大语言模型仅在严格约束下负责合规书面语组织，从工程机制上杜绝数值幻觉。

---

## 业务背景与工程挑战

### 1. 为什么 QOS 是药政申报中的重负荷环节？
在创新药与生物类似药（如单抗、双抗、ADC）的 IND/NDA 申报中，Module 2.3 QOS 是审评老师（CDE / FDA / EMA）首先审阅的核心文件：
- **数据源分散庞杂**：Module 3 中包含数十甚至上百批次的检验报告（COA）、放行数据与长达 24~36 个月的稳定性考察台账。
- **信息提取规则严格**：QOS 并非原始数据的全量搬运，而是按申报阶段（IND vs NDA）筛选符合代表性的批次（如毒理批、关键临床批、工艺验证批、商业化规模批），剔除未经验证的早期工程批或非工艺代表批。
- **数值与标准交叉勾稽**：必须针对各项关键质量属性（CQA，如纯度、聚合体、宿主细胞蛋白残留、活性等）汇总极值范围，并核对其是否全量符合注册标准（Specification）。

### 2. 为什么不能直接端到端丢给大语言模型？
直接将海量检验表格传给通用 LLM 或采用纯 Prompt 方案，在生产实践中存在致命缺陷：
- **数值与极值幻觉**：大模型对表格长文本中的浮点数缺乏精确比较能力，易在极值计算（如 `97.5%–99.0%`）或小数修约中出错；
- **批次隐性遗漏**：在长上下文注意力衰减下，容易漏写某关键工艺验证批号；
- **缺乏数据血缘追踪**：GxP 规范（ALCOA+ 数据完整性原则）要求申报材料的每个字句必须可溯源到原始台账，纯 LLM 无法稳定提供句级的字段映射；
- **非受控编造**：遇到数据缺项时，大模型倾向于根据上下文“补全”合理数值，这在药品申报中属于严重数据合规事故。

---

## 解决思路：确定性规则与受控语言模型分离

```
                      +-----------------------------+
                      |   Module 3 检验台账 (JSON)   |
                      +--------------+--------------+
                                     |
                                     v
+------------------------------------------------------------------------+
| 1. 确定性规则引擎 (Rule Engine - 纯 Python 代码，零模型依赖)               |
|                                                                        |
|  - 批次分类与准入过滤：按 rules/batch_filter_rules.yaml 剔除工程批/重复批 |
|  - 规格限度核对 (Spec Check)：比对各项 CQA 限度，自动标记超规格 (OOS) 项   |
|  - 数据聚合与极值计算：计算 Min / Max / 范围区间与批次类型分布统计       |
|  - 稳定性变化量测算：定位各考察条件 0M 起点与最终考察点，计算 Delta 增减值  |
+------------------------------------+-----------------------------------+
                                     |
                                     | 结构化事实上下文 [DATA]
                                     v
+------------------------------------------------------------------------+
| 2. 受控行文 Agent (Writer Agent - LLM 仅负责合规语料生成)               |
|                                                                        |
|  - 零外部知识注入：Prompt 强制限定仅能引用 [DATA] 标签内的统计结果       |
|  - 缺项安全阀：未提供指标强制输出 `[待确认: 属性名]` 占位符，严禁脑补    |
|  - 行业惯用语适配：输出符合 CDE/ICH 申报书面语体的规范段落              |
|  - 溯源构建：生成句子编号与原始批号/指标的数据映射表 (Source Map)        |
+------------------------------------+-----------------------------------+
                                     |
                                     v
                      +-----------------------------+
                      |     标准交付物产出           |
                      |  - 结构化 Draft JSON (供质检) |
                      |  - 原生 Word (.docx) 申报初稿|
                      +-----------------------------+
```

---

## 实际生成示例

### 输入数据片段 (批分析台账)
```json
{
  "product_name": "示例重组人源化单克隆抗体注射液",
  "product_code": "mAb-001",
  "batches": [
    {"batch_id": "ENG-202201", "batch_type": "工程批", "attributes": {"pH": 6.7, "sec_purity_pct": 97.8}},
    {"batch_id": "PV-202403", "batch_type": "工艺验证批", "attributes": {"pH": 6.7, "sec_purity_pct": 98.8}},
    {"batch_id": "PV-202404", "batch_type": "工艺验证批", "attributes": {"pH": 6.7, "sec_purity_pct": 99.0}},
    {"batch_id": "COM-202501", "batch_type": "商业化规模批", "attributes": {"pH": 6.7, "sec_purity_pct": 98.6}}
  ],
  "specifications": [
    {"attribute": "sec_purity_pct", "display_name": "SEC-HPLC 纯度", "unit": "%", "lower_limit": 95.0}
  ]
}
```

### 规则引擎处理输出
- 自动过滤 `ENG-202201`（工程批，依准入规则排除）；
- 纳入 3 批：`PV-202403, PV-202404, COM-202501`；
- 计算 `SEC-HPLC 纯度`：最小值 `98.6%`，最大值 `99.0%`，全部满足 $\ge 95.0\%$ 限度要求。

### Writer Agent 最终输出 (Word/Markdown)
> 本品共选取 **3** 个代表性批次（工艺验证批 2 批、商业化规模批 1 批），批号：**PV-202403、PV-202404、COM-202501**，进行批分析汇总。所有放行批次各项检验结果均符合设定的质量标准（Specification），批次间质量一致性良好。
> 
> 各关键质量属性（CQA）检验结果范围如下：SEC-HPLC 纯度为 98.6–99.0 %（限度 ≥95.0 %）。上述结果显示本品生产工艺稳定，批间一致性良好。

---

## 系统模块结构

```
ctd-writer/
├── app.py                     # Streamlit 交互工作台（支持参数调整、文件上传与 DOCX 导出）
├── agents/
│   └── writer_agent.py        # 核心 Agent：串联规则引擎、组装 Prompt 与结构化提取
├── rule_engine/               # 确定性计算层（不依赖大模型）
│   ├── batch_filter.py        # 批次类型过滤与数量控制
│   ├── data_validator.py      # 输入结构与必要字段校验
│   ├── spec_checker.py        # 质量标准 (Specification) 限度核验
│   └── stability_aggregator.py# 稳定性考察时间点提取与变化量计算
├── sections/                  # 可插拔章节处理器
│   ├── base_section.py        # 章节抽象基类 (BaseSection)
│   ├── p5_4_batch_analysis.py # 2.3.P.5.4 批分析章节实现
│   └── p8_1_stability.py      # 2.3.P.8.1 稳定性综述实现
├── rules/                     # 外置业务规则（YAML，修改无需改代码）
│   ├── batch_filter_rules.yaml# 批次准入白名单与数量阈值
│   └── stability_rules.yaml   # 考察时间点优先级与储存条件映射
├── prompts/                   # 章节专属 Prompt 模板
│   ├── writer_2_3_P_5_4.txt
│   └── writer_2_3_P_8_1.txt
├── schemas/models.py          # Pydantic 数据实体定义
└── data/                      # 标准测试数据集
    ├── batch_analysis.json
    └── stability.json
```

---

## 扩展机制说明

### 1. 修改业务准入规则（零代码改动）
编辑 `rules/batch_filter_rules.yaml`：
```yaml
# 调整纳入的批次类型白名单
included_batch_types:
  - 毒理批
  - 临床批
  - 工艺验证批
  - 商业化规模批

# 如需限制每种类型的最大采纳批数：
max_per_type:
  商业化规模批: 3
```
保存后系统自动读取最新规则，无需重启或重新编译代码。

### 2. 新增 QOS 章节支持
系统设计了统一的章节基类，新增章节分为三步：
1. **新建章节实现**：在 `sections/` 创建 `p4_1_excipients.py` 并继承 `BaseSection`，实现 `run_rule_engine()` 与 `build_prompt_context()`；
2. **注册章节**：在 `sections/__init__.py` 的 `SECTION_REGISTRY` 字典加入映射项；
3. **补充提示词**：在 `prompts/` 增加 `writer_2_3_P_4_1.txt`。

前端 Streamlit 界面将自动识别新注册章节并生成对应的表单与导出入口。

---

## 快速部署与运行

### 环境准备
```bash
git clone https://github.com/zuo1999/ctd-writer.git
cd ctd-writer
pip install -r requirements.txt
```

### 配置 API Key
```bash
cp .env.example .env
# 编辑 .env 文件填入模型凭据（支持 OpenAI / DeepSeek 等兼容接口）
# OPENAI_API_KEY=your_key_here
# OPENAI_BASE_URL=https://api.deepseek.com/v1
# LLM_MODEL=deepseek-chat
```

### 启动工作台
```bash
streamlit run app.py
```
浏览器打开 `http://localhost:8501` 即可进行可视化操作与 Word 文档导出。

---

## 协议
本项目遵循 MIT 开源协议。
