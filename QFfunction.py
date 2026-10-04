import json
import os

import pandas as pd
import streamlit as st

from agent import make_qianfan_caller, run_conversation
from tools import build_registry

EXAMPLE_PROMPTS = [
    "114514+973580等于多少？",
    "南京路街道附近50元以内的午餐有哪些推荐？",
    "肯德基疯狂星期四不错，就买这个20号的肯德基疯狂星期四了",
    "新入职员工李红在HR部门工作，她有研究生文凭。她的工号是918604。",
    "张三的工号是114514，他本科毕业，在技术部工作。",
    "深圳市今天气温如何？",
]
MODELS = ["ERNIE-3.5-8K", "ERNIE-4.0-8K", "ERNIE-Speed-8K"]

st.set_page_config(page_title="千帆 Function Calling", page_icon="🛠️")
st.title("🛠️ 千帆 Function Calling 演示")

if "history" not in st.session_state:
    st.session_state.history = []
if "employees" not in st.session_state:
    st.session_state.employees = []

with st.sidebar:
    st.header("设置")
    st.caption("留空时使用环境变量 QIANFAN_ACCESS_KEY / QIANFAN_SECRET_KEY 或 QIANFAN_AK / QIANFAN_SK。")
    ak = st.text_input("API Key (AK)", type="password", value=os.getenv("QIANFAN_AK", ""))
    sk = st.text_input("Secret Key (SK)", type="password", value=os.getenv("QIANFAN_SK", ""))
    model = st.selectbox("模型", MODELS)
    if st.button("清空对话"):
        st.session_state.history = []
        st.rerun()

    st.subheader("示例问题")
    for prompt in EXAMPLE_PROMPTS:
        if st.button(prompt, use_container_width=True):
            st.session_state.pending_prompt = prompt

for message in st.session_state.history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        for call in message.get("calls", []):
            with st.expander(f"🔧 调用了 {call['name']}"):
                st.code(json.dumps(call, ensure_ascii=False, indent=2), language="json")

prompt = st.chat_input("问点什么，例如：深圳市今天气温如何？") or st.session_state.pop("pending_prompt", None)

if prompt:
    st.session_state.history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    messages = [{"role": m["role"], "content": m["content"]} for m in st.session_state.history]
    with st.chat_message("assistant"):
        try:
            with st.spinner("思考中..."):
                answer, calls = run_conversation(
                    make_qianfan_caller(model, ak or None, sk or None),
                    messages,
                    build_registry(st.session_state.employees),
                )
        except Exception as exc:  # surface auth/network errors instead of hiding them
            st.session_state.history.pop()
            st.error(f"调用失败：{exc}")
            st.stop()
        st.markdown(answer)
        for call in calls:
            with st.expander(f"🔧 调用了 {call['name']}"):
                st.code(json.dumps(call, ensure_ascii=False, indent=2), language="json")
    st.session_state.history.append({"role": "assistant", "content": answer, "calls": calls})

if st.session_state.employees:
    st.subheader("已录入员工")
    st.dataframe(pd.DataFrame(st.session_state.employees), use_container_width=True)
