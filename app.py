"""
app.py —— ctd-writer 独立运行界面 (Streamlit)
运行方式：streamlit run app.py
"""
import io
import json
import os
from pathlib import Path

from docx import Document
import streamlit as st

from agents.writer_agent import WriterAgent
from sections import SECTION_REGISTRY

st.set_page_config(
    page_title="CTD Writer Agent",
    page_icon="✍️",
    layout="wide",
)

st.title("✍️ CTD Writer Agent")
st.caption("从 M3 海量检验/稳定性数据，通过确定性规则引擎与受控 LLM，自动生成 QOS 合规章节初稿")

# 侧边栏配置
with st.sidebar:
    st.header("⚙️ 模型配置")
    api_key = st.text_input("OpenAI / DeepSeek API Key", type="password", value=os.getenv("OPENAI_API_KEY", ""))
    base_url = st.text_input("API Base URL", value=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"))
    model = st.text_input("模型名称", value=os.getenv("LLM_MODEL", "gpt-4o-mini"))

    st.markdown("---")
    st.markdown("**📌 已注册章节**")
    for sid in SECTION_REGISTRY:
        st.markdown(f"- `{sid}`")

    st.markdown("---")
    st.markdown("**💡 架构特性**")
    st.caption("• 规则引擎确定性计算，严禁脑补数值\n• 规则外置 YAML，新增规则零改码\n• 章节可插拔基类，灵活拓展新章节")

if api_key:
    os.environ["OPENAI_API_KEY"] = api_key
if base_url:
    os.environ["OPENAI_BASE_URL"] = base_url
if model:
    os.environ["LLM_MODEL"] = model

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("① 选择章节 & 输入 M3 数据")
    section_id = st.selectbox(
        "目标 QOS 章节",
        list(SECTION_REGISTRY.keys()),
        format_func=lambda x: f"{x} ({'批分析' if '5.4' in x else '稳定性综述'})"
    )

    data_dir = Path(__file__).parent / "data"
    sample_map = {
        "2.3.P.5.4": data_dir / "batch_analysis.json",
        "2.3.P.8.1": data_dir / "stability.json",
    }

    if st.button("📂 载入示例数据"):
        sp = sample_map.get(section_id)
        if sp and sp.exists():
            st.session_state["writer_input_json"] = sp.read_text(encoding="utf-8")

    uploaded = st.file_uploader("或上传 JSON 原始文件", type=["json"])
    if uploaded:
        st.session_state["writer_input_json"] = uploaded.read().decode("utf-8")

    raw_json_str = st.text_area(
        "数据内容 (JSON)",
        value=st.session_state.get("writer_input_json", "{}"),
        height=320,
    )

    gen_btn = st.button("🚀 生成 QOS 章节草稿", type="primary", use_container_width=True)

if gen_btn:
    if not api_key:
        st.error("请先在侧边栏填入 API Key")
        st.stop()
    try:
        raw_data = json.loads(raw_json_str)
    except json.JSONDecodeError as e:
        st.error(f"JSON 解析失败: {e}")
        st.stop()

    with st.spinner("Writer Agent 正在执行规则过滤与受控生成..."):
        try:
            agent = WriterAgent(model=model)
            draft = agent.run(section_id, raw_data)
            st.session_state["generated_draft"] = draft
        except Exception as e:
            st.error(f"生成失败: {e}")
            st.stop()

with col2:
    st.subheader("② 生成结果与导出")
    if "generated_draft" in st.session_state:
        draft = st.session_state["generated_draft"]

        tab_text, tab_json, tab_source = st.tabs(["📄 章节正文", "📦 结构化导出 (供 Reviewer)", "🔗 来源追溯表"])

        with tab_text:
            st.markdown(draft.content)
            if draft.unresolved_placeholders:
                st.warning(f"待人工确认字段：{', '.join(draft.unresolved_placeholders)}")

            doc = Document()
            doc.add_heading(f"Module {draft.section_id} 章节草稿", level=1)
            for p in draft.content.split("\n"):
                if p.strip():
                    doc.add_paragraph(p)
            buf = io.BytesIO()
            doc.save(buf)
            buf.seek(0)

            st.download_button(
                label="📥 下载 Word 文档 (.docx)",
                data=buf,
                file_name=f"QOS_{draft.section_id.replace('.', '_')}_draft.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

        with tab_json:
            export_dict = {
                "section_id": draft.section_id,
                "content": draft.content,
                "source_map": [sm.model_dump() for sm in draft.source_map],
                "unresolved_placeholders": draft.unresolved_placeholders,
                "rule_engine_summary": {
                    "batch_ids": draft.rule_engine_result.summary_stats.get("batch_ids", []) if draft.rule_engine_result else [],
                    "attribute_ranges": draft.rule_engine_result.summary_stats.get("attribute_ranges", {}) if draft.rule_engine_result else {}
                }
            }
            json_str = json.dumps(export_dict, ensure_ascii=False, indent=2)
            st.text_area("标准 Draft JSON (可直接导入 ctd-reviewer)", json_str, height=250)
            st.download_button(
                label="📥 导出 Draft JSON",
                data=json_str,
                file_name=f"draft_{draft.section_id.replace('.', '_')}.json",
                mime="application/json"
            )

        with tab_source:
            if draft.source_map:
                st.dataframe([
                    {"序号": item.sentence_id, "来源字段": item.source_field, "批号": item.batch_id or "-", "值": item.value}
                    for item in draft.source_map
                ], use_container_width=True)
            else:
                st.info("暂无来源映射数据")
    else:
        st.info("等待输入并点击生成...")
