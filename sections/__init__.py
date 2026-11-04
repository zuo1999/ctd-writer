"""
sections/ —— 章节注册表
新增章节只需：
  1. 在此目录新建 pX_Y_name.py，继承 BaseSection
  2. 在此 __init__.py 的 SECTION_REGISTRY 中注册
"""
from sections.p5_4_batch_analysis import P54BatchAnalysis
from sections.p8_1_stability import P81Stability

SECTION_REGISTRY = {
    "2.3.P.5.4": P54BatchAnalysis,
    "2.3.P.8.1": P81Stability,
    # 新章节在此注册，例如：
    # "2.3.P.4.1": P41ControlOfExcipients,
}

def get_section(section_id: str):
    cls = SECTION_REGISTRY.get(section_id)
    if cls is None:
        raise ValueError(
            f"未知章节 '{section_id}'。已注册章节：{list(SECTION_REGISTRY.keys())}"
        )
    return cls()
