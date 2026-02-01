from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
import json

from .db import init_db, get_conn, now_iso
from .cv_parser import parse_cv
from .interview import start_session_gpt, QUESTION_TIME_LIMIT_SEC, TOTAL_TIME_LIMIT_SEC, now
from .gpt_interview import evaluate_and_next_question
from langchain.prompts import ChatPromptTemplate
    
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
load_dotenv()
    

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

SESSIONS = {}

@app.on_event("startup")
def _startup():
    init_db()

class RegisterReq(BaseModel):
    name: str
    email: str
    target_role: str

class StartInterviewReq(BaseModel):
    candidate_id: int

class AnswerReq(BaseModel):
    session_id: int
    answer: str

@app.get("/")
def root():
    return {"message": "HerStack API Running"}

@app.post("/api/candidate/register")
def register(req: RegisterReq):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO candidates (name, email, target_role, created_at) VALUES (?, ?, ?, ?)",
        (req.name, req.email, req.target_role, now_iso())
    )
    conn.commit()
    cid = cur.lastrowid
    conn.close()
    return {"candidate_id": cid}

@app.post("/api/candidate/{candidate_id}/upload_cv")
async def upload_cv(candidate_id: int, file: UploadFile = File(...)):
    suffix = Path(file.filename).suffix.lower()
    if suffix not in [".pdf", ".txt"]:
        return {"ok": False, "error": "Only PDF/TXT"}

    save_path = UPLOAD_DIR / f"candidate_{candidate_id}{suffix}"
    content = await file.read()
    save_path.write_bytes(content)
    cv_text = parse_cv(save_path)

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE candidates SET cv_filename=?, cv_text=? WHERE id=?",
        (save_path.name, cv_text, candidate_id)
    )
    conn.commit()
    conn.close()

    return {"ok": True, "cv_chars": len(cv_text)}

@app.post("/api/interview/start")
def interview_start(req: StartInterviewReq):
    conn = get_conn()
    cur = conn.cursor()
    row = cur.execute("SELECT target_role, cv_text FROM candidates WHERE id=?", (req.candidate_id,)).fetchone()
    if not row or not row["cv_text"]:
        conn.close()
        return {"ok": False, "error": "Upload CV first"}

    cur.execute(
        "INSERT INTO sessions (candidate_id, status, started_at) VALUES (?, ?, ?)",
        (req.candidate_id, "running", now_iso())
    )
    conn.commit()
    session_id = cur.lastrowid
    conn.close()

    state, first_q = start_session_gpt(req.candidate_id, row["target_role"], row["cv_text"])
    SESSIONS[session_id] = state

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO turns (session_id, q_index, question, asked_at) VALUES (?, ?, ?, ?)",
        (session_id, 0, first_q, now_iso())
    )
    conn.commit()
    conn.close()

    return {
        "ok": True,
        "session_id": session_id,
        "question": first_q,
        "question_time_limit_sec": QUESTION_TIME_LIMIT_SEC,
        "total_time_limit_sec": TOTAL_TIME_LIMIT_SEC,
    }

@app.post("/api/interview/answer")
def interview_answer(req: AnswerReq):
    if req.session_id not in SESSIONS:
        return {"ok": False, "error": "Session not found"}

    state = SESSIONS[req.session_id]
    
    conn = get_conn()
    cur = conn.cursor()
    
    # Get conversation history from DB
    turns = cur.execute(
        "SELECT question, answer FROM turns WHERE session_id=? AND answer IS NOT NULL ORDER BY q_index",
        (req.session_id,)
    ).fetchall()
    
    conversation_history = []
    for t in turns:
        conversation_history.append({"role": "interviewer", "content": t["question"]})
        conversation_history.append({"role": "candidate", "content": t["answer"]})
    
    # Get current question
    turn = cur.execute(
        "SELECT id, question FROM turns WHERE session_id=? AND q_index=? ORDER BY id DESC LIMIT 1",
        (req.session_id, state.q_index)
    ).fetchone()

    current_q = turn["question"]
    
    # Add current exchange to history
    conversation_history.append({"role": "interviewer", "content": current_q})
    conversation_history.append({"role": "candidate", "content": req.answer})
    
    # Use GPT to respond conversationally
    docs = state.retriever.invoke(req.answer)
    context = "\n\n".join([doc.page_content for doc in docs])
    
    history_text = "\n".join([m['content'] for m in conversation_history[-10:]])
    # Conversational template
    
    llm = ChatOpenAI(model="gpt-4o", temperature=0.7)
    
    template = template = """You are a friendly HR recruiter having a conversation with a candidate.

Context from job description and CV:
{context}

Conversation so far:
{history}

Instructions:
-Ask if the candidate has any questions about the role or company
- Respond naturally to what the candidate said
- After 3-4 quality exchanges, if the candidate demonstrates relevant experience and skills, END THE INTERVIEW by saying: "You seem like a great fit! We'll move you forward to the next stage of our recruitment process."
- IMPORTANT: When you qualify them, DO NOT ask any more questions. Just give the positive feedback and stop.
- If not ready to qualify yet, ask ONE relevant technical question
- Be warm, professional, and efficient
- Keep responses 4-5 sentences max

Respond naturally to continue the conversation."""
    
    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | llm
    
    response = chain.invoke({
        "context": context,
        "history": history_text
    })
    
    next_message = response.content
    
    # Simple scoring based on keyword matching
    accuracy = 0.5  # Default score
    
    # Update turn
    cur.execute(
        "UPDATE turns SET answer=?, accuracy=?, answered_at=? WHERE id=?",
        (req.answer, accuracy, now_iso(), turn["id"])
    )
    conn.commit()
    
    # Check if conversation should end
    qualified = "great fit" in next_message.lower() or "move you forward" in next_message.lower()
    
    # Check time limits
    # Check if conversation should end
    # Check if conversation should end
    # Check if conversation should end
# Check if conversation should end
    stop_reason = None

    # Hard limit: Stop after 5 questions
    if state.q_index >= 5:
        stop_reason = "Interview complete - Thank you for your time!"
    # Check time limits
    elif state.total_elapsed_sec() >= TOTAL_TIME_LIMIT_SEC:
        stop_reason = "Time limit reached"
    # Check if qualified early
    elif state.q_index >= 2:
        qualified_phrases = ["great fit", "move you forward", "next stage", "qualified", "perfect match"]
        if any(phrase in next_message.lower() for phrase in qualified_phrases):
            stop_reason = "Candidate qualified - Great match for the role!"

    if stop_reason:
        rows = cur.execute(
            "SELECT accuracy FROM turns WHERE session_id=? AND answer IS NOT NULL",
            (req.session_id,)
        ).fetchall()
        avg_acc = sum([r["accuracy"] for r in rows]) / len(rows) if rows else 0.5
        cur.execute(
            "UPDATE sessions SET status=?, ended_at=?, stop_reason=?, total_questions=?, avg_accuracy=? WHERE id=?",
            ("ended", now_iso(), stop_reason, len(rows), avg_acc, req.session_id)
        )
        conn.commit()
        conn.close()
        SESSIONS.pop(req.session_id, None)
        return {
            "ok": True,
            "ended": True,
            "stop_reason": stop_reason,
            "last_accuracy": accuracy,
            "last_ai_percent": 0,
            "avg_accuracy": avg_acc,
            "avg_ai_percent": 0,
            "message": next_message
        }

    state.q_index += 1
    state.current_question_started_at = now()
    cur.execute(
        "INSERT INTO turns (session_id, q_index, question, asked_at) VALUES (?, ?, ?, ?)",
        (req.session_id, state.q_index, next_message, now_iso())
    )
    conn.commit()
    conn.close()
    return {
        "ok": True,
        "ended": False,
        "last_accuracy": accuracy,
        "last_ai_percent": 0,
        "next_question": next_message,
        "question_time_limit_sec": QUESTION_TIME_LIMIT_SEC
    }