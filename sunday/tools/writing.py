from typing import Any
from .registry import tool, ToolResult, ToolRisk

_writing = ["draft_content", "rewrite_text", "summarize_content", "expand_content", "brainstorm", "draft_email", "draft_cv", "interview_prep", "social_media_plan", "proofread", "translate_text", "meeting_to_actions", "reflective_chat", "marketing_strategy"]

@tool(name="draft_content", category="writing", risk=ToolRisk.LOW, description="Write article, email, post, essay", reversible=True, idempotent=True, required_args=["topic", "content_type"])
async def draft_content(topic: str, content_type: str = "article", tone: str = "professional", length: str = "medium") -> ToolResult:
    """Write article, email, post, essay."""
    try:
        # Placeholder for LLM-based content generation
        # In production, would call Ollama to generate content
        draft = f"# {topic.title()}\n\nThis is a {content_type} about {topic} with a {tone} tone. "
        draft += f"The content length is {length}. [LLM generation would go here]"
        
        return ToolResult(success=True, data={
            "topic": topic,
            "content_type": content_type,
            "tone": tone,
            "draft": draft
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))

@tool(name="rewrite_text", category="writing", risk=ToolRisk.LOW, description="Rewrite for tone/clarity/length", reversible=True, idempotent=True, required_args=["text"])
async def rewrite_text(text: str, tone: str = "professional", clarity: str = "high") -> ToolResult:
    """Rewrite for tone/clarity/length."""
    try:
        # Placeholder for LLM-based rewriting
        rewritten = f"[Rewritten with {tone} tone and {clarity} clarity]\n\n{text}"
        
        return ToolResult(success=True, data={
            "original": text,
            "rewritten": rewritten,
            "tone": tone,
            "clarity": clarity
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))

@tool(name="summarize_content", category="writing", risk=ToolRisk.LOW, description="Summarize text, email, doc, meeting", reversible=True, idempotent=True, required_args=["text"])
async def summarize_content(text: str, max_length: int = 200) -> ToolResult:
    """Summarize text, email, doc, meeting."""
    try:
        # Simple summary - take first N chars as placeholder
        # In production, would use LLM for intelligent summarization
        summary = text[:max_length] + "..." if len(text) > max_length else text
        
        return ToolResult(success=True, data={
            "original_length": len(text),
            "summary": summary,
            "summary_length": len(summary)
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))

@tool(name="expand_content", category="writing", risk=ToolRisk.LOW, description="Elaborate bullet points into prose", reversible=True, idempotent=True, required_args=["text"])
async def expand_content(text: str, expansion_factor: int = 2) -> ToolResult:
    """Elaborate bullet points into prose."""
    try:
        # Placeholder for LLM-based expansion
        expanded = f"[Expanded {expansion_factor}x]\n\n{text}"
        
        return ToolResult(success=True, data={
            "original": text,
            "expanded": expanded,
            "expansion_factor": expansion_factor
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))

@tool(name="brainstorm", category="writing", risk=ToolRisk.LOW, description="Generate ideas on a topic", reversible=True, idempotent=True, required_args=["topic"])
async def brainstorm(topic: str, num_ideas: int = 5) -> ToolResult:
    """Generate ideas on a topic."""
    try:
        # Placeholder for LLM-based brainstorming
        ideas = [f"Idea {i+1} for {topic}" for i in range(num_ideas)]
        
        return ToolResult(success=True, data={
            "topic": topic,
            "ideas": ideas,
            "count": len(ideas)
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))

@tool(name="draft_email", category="writing", risk=ToolRisk.LOW, description="Compose email (draft only)", reversible=True, idempotent=True, required_args=["recipient", "subject"])
async def draft_email(recipient: str, subject: str, body: str = "", tone: str = "professional") -> ToolResult:
    """Compose email (draft only)."""
    try:
        email = f"To: {recipient}\nSubject: {subject}\n\n{body}"
        
        return ToolResult(success=True, data={
            "recipient": recipient,
            "subject": subject,
            "body": body,
            "tone": tone,
            "draft": email
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))

@tool(name="draft_cv", category="writing", risk=ToolRisk.LOW, description="Generate/update CV/resume sections", reversible=True, idempotent=True, required_args=["section", "details"])
async def draft_cv(section: str, details: dict) -> ToolResult:
    """Generate/update CV/resume sections."""
    try:
        cv_section = f"# {section.title()}\n\n"
        for key, value in details.items():
            cv_section += f"**{key}:** {value}\n"
        
        return ToolResult(success=True, data={
            "section": section,
            "content": cv_section
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))

@tool(name="interview_prep", category="writing", risk=ToolRisk.LOW, description="Mock Q&A, talking points for role", reversible=True, idempotent=True, required_args=["role", "company"])
async def interview_prep(role: str, company: str = "") -> ToolResult:
    """Mock Q&A, talking points for role."""
    try:
        prep = {
            "role": role,
            "company": company,
            "talking_points": [
                f"Experience relevant to {role}",
                "Key achievements",
                "Questions to ask interviewer"
            ],
            "mock_questions": [
                f"Tell me about yourself",
                f"Why do you want this {role} position?",
                f"What are your strengths?"
            ]
        }
        
        return ToolResult(success=True, data=prep)
    except Exception as e:
        return ToolResult(success=False, error=str(e))

@tool(name="social_media_plan", category="writing", risk=ToolRisk.LOW, description="Content calendar / post drafts", reversible=True, idempotent=True, required_args=["topic", "platform"])
async def social_media_plan(topic: str, platform: str = "twitter") -> ToolResult:
    """Content calendar / post drafts."""
    try:
        plan = {
            "topic": topic,
            "platform": platform,
            "posts": [
                f"Post 1 about {topic}",
                f"Post 2 about {topic}",
                f"Post 3 about {topic}"
            ],
            "schedule": "Weekly posting recommended"
        }
        
        return ToolResult(success=True, data=plan)
    except Exception as e:
        return ToolResult(success=False, error=str(e))

@tool(name="proofread", category="writing", risk=ToolRisk.LOW, description="Grammar, clarity, fact-check suggestions", reversible=True, idempotent=True, required_args=["text"])
async def proofread(text: str) -> ToolResult:
    """Grammar, clarity, fact-check suggestions."""
    try:
        suggestions = [
            "Check for spelling errors",
            "Verify grammar",
            "Improve clarity",
            "Check factual accuracy"
        ]
        
        return ToolResult(success=True, data={
            "text": text,
            "suggestions": suggestions,
            "word_count": len(text.split())
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))

@tool(name="translate_text", category="writing", risk=ToolRisk.LOW, description="Translate between languages", reversible=True, idempotent=True, required_args=["text", "target_language"])
async def translate_text(text: str, target_language: str = "Spanish") -> ToolResult:
    """Translate between languages."""
    try:
        # Placeholder for translation service
        translated = f"[Translated to {target_language}]\n\n{text}"
        
        return ToolResult(success=True, data={
            "original": text,
            "translated": translated,
            "target_language": target_language
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))

@tool(name="meeting_to_actions", category="writing", risk=ToolRisk.LOW, description="Meeting notes → action items", reversible=True, idempotent=True, required_args=["meeting_notes"])
async def meeting_to_actions(meeting_notes: str) -> ToolResult:
    """Meeting notes → action items."""
    try:
        # Simple extraction - look for action items
        lines = meeting_notes.split('\n')
        actions = []
        for line in lines:
            line = line.strip()
            if line and (line.lower().startswith("action") or line.startswith("-") or line.startswith("*")):
                actions.append(line.lstrip("action-").lstrip("*").strip())
        
        return ToolResult(success=True, data={
            "meeting_notes": meeting_notes,
            "action_items": actions,
            "count": len(actions)
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))

@tool(name="reflective_chat", category="writing", risk=ToolRisk.LOW, description="Pi-mode supportive conversation (no tools)", reversible=True, idempotent=True, required_args=["user_input"])
async def reflective_chat(user_input: str) -> ToolResult:
    """Pi-mode supportive conversation (no tools)."""
    try:
        # Placeholder for reflective conversation
        # In production, would use LLM with empathetic persona
        response = f"I hear you. {user_input} sounds important. Would you like to talk more about it?"
        
        return ToolResult(success=True, data={
            "user_input": user_input,
            "response": response,
            "mode": "reflective"
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))

@tool(name="marketing_strategy", category="writing", risk=ToolRisk.LOW, description="Draft marketing plan / campaign outline", reversible=True, idempotent=True, required_args=["product", "target_audience"])
async def marketing_strategy(product: str, target_audience: str) -> ToolResult:
    """Draft marketing plan / campaign outline."""
    try:
        strategy = {
            "product": product,
            "target_audience": target_audience,
            "key_messages": [
                f"Value proposition for {product}",
                f"Benefits for {target_audience}",
                "Call to action"
            ],
            "channels": ["Social media", "Email", "Content marketing"],
            "timeline": "3-month campaign recommended"
        }
        
        return ToolResult(success=True, data=strategy)
    except Exception as e:
        return ToolResult(success=False, error=str(e))
