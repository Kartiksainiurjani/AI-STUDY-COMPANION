import re
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


run(
    "CREATE TABLE IF NOT EXISTS history("
    "id INTEGER PRIMARY KEY AUTOINCREMENT, "
    "feature TEXT, topic TEXT, answer TEXT, "
    "created TEXT DEFAULT CURRENT_TIMESTAMP)"
)


def ask_ai(prompt, feature, topic):
    order = [choice] + [m for m in MODELS if m != choice]
    last_error = ""
    for model in order:
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
            text = re.sub(
                r"<think>.*?</think>", "", text, flags=re.DOTALL
            ).strip()
            run(
                "INSERT INTO history(feature,topic,answer) "
                "VALUES(?,?,?)",
                (feature, topic[:100], text),
            )
            return text
        except Exception as e:
            last_error = str(e)
    return "Error: " + last_error


st.title("📚 AI Study Companion")
page = st.sidebar.radio(
    "Menu",
    ["Ask a Doubt", "Summarize Notes", "Quiz",
     "Flashcards", "Study Planner", "History"],
)
choice = st.sidebar.selectbox("AI model", MODELS)

if page == "Ask a Doubt":
    level = st.selectbox(
        "Explain like",
        ["a 10 year old", "a school student", "a college student"],
    )
    q = st.text_area("Type your doubt")
    if st.button("Explain") and q.strip():
        prompt = (
            f"Explain this to {level} in simple language "
            f"with one example:\n{q}"
        )
        with st.spinner("Thinking..."):
            ans = ask_ai(prompt, "Doubt", q)
        st.markdown(ans)

elif page == "Summarize Notes":
    notes = st.text_area("Paste your notes", height=250)
    if st.button("Summarize") and notes.strip():
        prompt = (
            "Summarize these notes in 6 short bullet points "
            f"and list 3 key terms:\n{notes}"
        )
        with st.spinner("Summarizing..."):
            ans = ask_ai(prompt, "Summary", notes)
        st.markdown(ans)

elif page == "Quiz":
    topic = st.text_input("Topic (e.g. Photosynthesis, DBMS)")
    n = st.slider("Number of questions", 3, 10, 5)
    if st.button("Make quiz") and topic.strip():
        prompt = (
            f"Create {n} multiple choice questions on {topic}. "
            "Give 4 options A to D for each. "
            "First write all the questions. "
            "Then write the line ###ANSWERS### "
            "and after it give the correct answer "
            "for each question with a short reason."
        )
        with st.spinner("Creating quiz..."):
            ans = ask_ai(prompt, "Quiz", topic)
        parts = ans.split("###ANSWERS###")
        st.markdown(parts[0])
        if len(parts) > 1:
            with st.expander("Show answers"):
                st.markdown(parts[1])

elif page == "Flashcards":
    topic = st.text_input("Topic")
    n = st.slider("Number of cards", 3, 15, 6)
    if st.button("Make flashcards") and topic.strip():
        prompt = (
            f"Create {n} flashcards on {topic}. "
            "Write one card per line in exactly this format: "
            "Q: question | A: answer. "
            "No extra text."
        )
        with st.spinner("Creating cards..."):
            ans = ask_ai(prompt, "Flashcards", topic)
        shown = False
        for line in ans.splitlines():
            if "|" in line:
                ques, answer = line.split("|", 1)
                with st.expander(ques.replace("Q:", "").strip()):
                    st.write(answer.replace("A:", "").strip())
                shown = True
        if not shown:
            st.markdown(ans)

elif page == "Study Planner":
    subjects = st.text_input("Subjects (comma separated)")
    days = st.number_input("Days left for exam", 1, 60, 7)
    hours = st.number_input("Study hours per day", 1, 12, 3)
    if st.button("Make plan") and subjects.strip():
        prompt = (
            "Make a day-wise study timetable as a table "
            f"for {days} days, {hours} hours per day, "
            f"for these subjects: {subjects}. "
            "Include short revision slots and one rest day."
        )
        with st.spinner("Planning..."):
            ans = ask_ai(prompt, "Planner", subjects)
        st.markdown(ans)

elif page == "History":
    rows = run(
        "SELECT * FROM history ORDER BY id DESC LIMIT 20", fetch=True
    )
    if not rows:
        st.info("Nothing here yet.")
    for r in rows:
        title = r["feature"] + " - " + r["topic"][:50]
        with st.expander(title):
            st.markdown(r["answer"])
