from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, List, Dict

QUESTION_TIME_LIMIT_SEC = 5 * 60
TOTAL_TIME_LIMIT_SEC = 25 * 60

def now():
    return datetime.utcnow()

@dataclass
class SessionState:
    candidate_id: int
    target_role: str
    started_at: datetime
    q_index: int
    retriever: Any
    current_question_started_at: datetime
    conversation_history: List[Dict[str, str]]

    def total_elapsed_sec(self) -> int:
        return int((now() - self.started_at).total_seconds())

    def question_elapsed_sec(self) -> int:
        return int((now() - self.current_question_started_at).total_seconds())

def start_session_gpt(candidate_id: int, target_role: str, cv_text: str):
    """Start GPT interview"""
    from .vector_helper import create_retriever_for_candidate
    from .gpt_interview import generate_first_question
    
    retriever = create_retriever_for_candidate(cv_text, target_role)
    first_q = generate_first_question(retriever)
    
    return SessionState(
        candidate_id=candidate_id,
        target_role=target_role,
        started_at=now(),
        q_index=0,
        retriever=retriever,
        current_question_started_at=now(),
        conversation_history=[]
    ), first_q