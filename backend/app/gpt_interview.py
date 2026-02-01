from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import json

load_dotenv()

llm = ChatOpenAI(model="gpt-4o", temperature=0.7)

def generate_first_question(retriever):
    """Generate conversational opening"""
    
    docs = retriever.invoke("candidate resume experience skills")
    context = "\n\n".join([doc.page_content for doc in docs])
    
    template = """You are a friendly HR recruiter starting a conversation with a candidate.
    
    Context: {context}
    
    Start the conversation naturally:
    
    - Greet them warmly
    -Give a job description of the role
    - Mention something interesting from their CV
    - Ask if they have any questions before starting yhe interview
    - Ask an open-ended question about their experience
    -Ask techinal questions later as if you are an expert in the industry.
    
    Keep it to 2-3 sentences. Be conversational and formal.
    
    Example: "Hi! I really enjoyed reading about your work on [project]. That sounds fascinating! What drew you to work in that area?"
    
    Return ONLY your conversational opening."""
    
    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | llm
    result = chain.invoke({"context": context})
    return result.content.strip()
    
    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | llm
    result = chain.invoke({"context": context})
    return result.content.strip()


def evaluate_and_next_question(retriever, question, answer, history, q_num):
    """Evaluate answer and generate next question"""
    
    docs = retriever.invoke(answer)
    context = "\n\n".join([doc.page_content for doc in docs])
    
    history_text = "\n".join([f"{m['role']}: {m['content']}" for m in history[-6:]])
    
    template = """You are evaluating an interview answer.
    
    Context: {context}
    History: {history}
    Question #{q_num}: {question}
    Answer: {answer}
    
    Respond in JSON format:
    {{
        "score": 0-100,
        "qualified": true/false,
        "reasoning": "brief explanation",
        "next_question": "next question or null"
    }}
    
    Set qualified=true if question 5+ and average score 70%+."""
    
    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | llm
    result = chain.invoke({
        "context": context,
        "history": history_text,
        "question": question,
        "answer": answer,
        "q_num": q_num + 1
    })
    
    try:
        content = result.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content.strip())
    except:
        return {
            "score": 50,
            "qualified": False,
            "reasoning": "Parse error",
            "next_question": "Tell me more about your experience."
        }