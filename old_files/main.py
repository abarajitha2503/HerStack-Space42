
=======
import os
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from vector import retriever

# Set your OpenAI API key
os.environ["OPENAI_API_KEY"] = "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"  # Replace with your actual key

# Model - Using GPT-4 for better reasoning
llm = ChatOpenAI(
    model="gpt-4o",  # or "gpt-4o-mini" for faster/cheaper, or "gpt-4" for classic
    temperature=0.7
)

# Recruitment Assistant Prompt
template = """
You are an expert HR recruitment assistant specializing in technical recruitment.

Your role:
1. Explain the job role, responsibilities, and required skills clearly
2. Analyze the candidate's resume against job requirements  
3. Ask relevant technical questions to assess expertise in the role
4. Determine if the candidate is technically qualified
5. If qualified, recommend transfer to human HR for culture fit assessment

Context from documents:
{context}

Conversation history:
{history}

Current question/response: {question}

Instructions:
- Be professional, friendly, warm, and encouraging
- Provide specific examples from the job description and resume
- Ask probing technical questions when needed to verify expertise
- Assess both hard skills (technical abilities) and soft skills (communication, problem-solving)
- If the candidate clearly meets technical requirements (skills match, relevant experience, appropriate education), state: "✅ QUALIFIED FOR HUMAN REVIEW" and provide a detailed summary of why they're a strong match
- Be constructive if there are gaps - highlight strengths and suggest areas for growth
- Keep responses concise but informative (2-4 paragraphs typically)
"""

prompt = ChatPromptTemplate.from_template(template)
chain = prompt | llm

# Track conversation
conversation_history = []
candidate_qualified = False

print("=" * 70)
print("🤖 Welcome to the AI HR Recruitment Assistant!")
print("=" * 70)
print("\nI'll help you understand the role and assess your qualifications.")
print("Type 'q' to quit at any time.\n")

# Initial greeting
initial_docs = retriever.invoke("job description role responsibilities required skills")
initial_context = "\n\n---\n\n".join([
    f"[{doc.metadata.get('source_type', 'document').upper()}] Excerpt {i+1}:\n{doc.page_content}"
    for i, doc in enumerate(initial_docs)
])

greeting_result = chain.invoke({
    "context": initial_context,
    "history": "",
    "question": "Greet the candidate warmly. Briefly introduce the role we're hiring for (title, key responsibilities, team). Then ask if they'd like to learn more about specific aspects like requirements, day-to-day work, or team culture."
})

print(f"Assistant: {greeting_result.content}\n")
conversation_history.append(f"Assistant: {greeting_result.content}")

# Main conversation loop
while True:
    print("-" * 70)
    user_input = input("You: ")
    
    if user_input.lower() == "q":
        print("\n👋 Thank you for your time! We appreciate your interest. Goodbye!")
        break
    
    # Retrieve relevant context
    docs = retriever.invoke(user_input)
    
    context_text = "\n\n---\n\n".join([
        f"[{doc.metadata.get('source_type', 'document').upper()}] Excerpt {i+1}:\n{doc.page_content}"
        for i, doc in enumerate(docs)
    ])
    
    # Build history (last 6 messages for context)
    history_text = "\n".join(conversation_history[-6:])
    
    # Get response
    result = chain.invoke({
        "context": context_text,
        "history": history_text,
        "question": user_input
    })
    
    assistant_response = result.content
    print(f"\nAssistant: {assistant_response}\n")
    
    # Update history
    conversation_history.append(f"User: {user_input}")
    conversation_history.append(f"Assistant: {assistant_response}")
    
    # Check if candidate is qualified
    if "✅ QUALIFIED FOR HUMAN REVIEW" in assistant_response and not candidate_qualified:
        candidate_qualified = True
        print("\n" + "=" * 70)
        print("🎉 CONGRATULATIONS - TECHNICALLY QUALIFIED! 🎉")
        print("=" * 70)
        print("\n✅ You meet the technical requirements for this position!")
        print("📞 Next Step: Our HR team will schedule a culture fit interview.")
        print("💼 This will help us understand if you're a great match for our team.")
        print("=" * 70 + "\n")
        
        continue_chat = input("Continue chatting or finish here? (continue/end): ")
        if continue_chat.lower() == "end":
            print("\n✨ Excellent! We'll be in touch soon. Best of luck!")
            break

print("\n" + "=" * 70)
print("Session ended. Have a great day!")
print("=" * 70)

