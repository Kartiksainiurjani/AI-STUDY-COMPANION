import sqlite3
import streamlit as st
from groq import Groq

MODELS = ["openai/gpt-oss-120b", "qwen/qwen3.6-27b"]

st.set_page_config(page_title="AI Study Companion", page_icon="📚")


def run(q, p=(), fetch=False):
    con = sqlite3.connect("study.db")
    con.row_factory = sqlite3.Row
    cur = con.execute(q, p)
    data = [dict(r) for r in cur.fetchall()] if fetch else None
    con.commit()
    con.close()
    return data


run("""CREATE TABLE IF NOT EXISTS history(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feature TEXT, topic TEXT, answer TEXT,
    created TEXT DEFAULT CURRENT_TIMESTAMP)""")


def ask_ai(prompt, feature, topic):
    last_error = ""
    for model in MODELS:
        try:
            client = Groq(api_key=st.secrets["GROQ_API_KEY"])
            extra = {}
            if model.startswith("openai/gpt-oss"):
                extra = {"reasoning_effort": "low"}
            reply = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                extra_body=extra,
            )
            text = reply.choices[0].message.content
            run("INSERT INTO history(feature,topic,answer) VALUES(?,?,?)",
                (feature, topic[:100], text))
            return text
        except Exception as e:
            last_error = str(e)
    return f"Error: {last_error}"


st.title("📚 AI Study Companion")
page = st.sidebar.radio("Menu", ["Ask a Doubt", "Summarize Notes", "Quiz",
                                 "Flashcards", "Study Planner", "History"])

if page == "Ask a Doubt":
    level = st.selectbox("Explain like", ["a 10 year old", "a school student",
                                          "a college student"])
    q = st.text_area("Type your doubt")
    if st.button("Explain") and q.strip():
        with st.spinner("Thinking..."):
            ans = ask_ai(f"Explain this to {level} in simple language "
                         f"with one example:\n{q}", "Doubt", q)
        st.markdown(ans)

elif page == "Summarize Notes":
    notes = st.text_area("Paste your notes", height=250)
    if st.button("Summarize") and notes.strip():
        with st.spinner("Summarizing..."):
            ans = ask_ai("Summarize these notes in 6 short bullet points "
                         f"and list 3 key terms:\n{notes}", "Summary", notes)
        st.markdown(ans)

elif page == "Quiz":
    topic = st.text_input("Topic (e.g. Photosynthesis, DBMS)")
    n = st.slider("Number of questions", 3, 10, 5)
    if st.button("Make quiz") and topic.strip():
        with st.spinner("Creating quiz..."):
            ans = ask_ai(f"Create {n} multiple choice questions on {topic}, "
                         "4 options (A-D) each. First write all questions
