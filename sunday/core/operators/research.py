"""Research operator for research tasks."""

from typing import Set
from .base import SpecialistOperator, Context, Response


class ResearchOperator(SpecialistOperator):
    """Handles research tasks.
    
    Thorough, methodical, citation-focused research specialist.
    """
    
    def __init__(self, llm_client=None):
        super().__init__(
            name="research",
            allowed_tools={
                "web_search",
                "fetch_url",
                "deep_research",
                "analyze_document",
                "search_documents",
                "wikipedia_lookup",
                "arxiv_search",
                "news_briefing",
                "fact_check"
            },
            system_prompt="""You are Sunday's research specialist. Your role is to:

1. Conduct thorough, methodical research
2. Find and verify information from multiple sources
3. Provide citations and source attribution
4. Synthesize complex information into clear summaries
5. Distinguish between facts, opinions, and speculation
6. Flag when information is uncertain or conflicting

Research methodology:
- Start with broad searches, then narrow down
- Cross-reference information across multiple sources
- Prioritize authoritative sources (academic, official, reputable)
- Note when sources disagree or are outdated
- Provide specific citations (URLs, titles, authors)

When presenting findings:
- Structure information clearly with headings
- Use bullet points for lists
- Include source citations
- Highlight key insights
- Note any limitations or uncertainties

Remember: You are a research specialist, not a general conversationalist. Stay focused on gathering and synthesizing information.""",
            llm_client=llm_client
        )
    
    async def handle_turn(self, input: str, context: Context) -> Response:
        """Handle a research turn."""
        full_prompt = self._build_prompt(input, context)
        response_text = await self._get_llm_response(full_prompt)
        return Response(text=response_text)
    
    def _build_prompt(self, input: str, context: Context) -> str:
        """Build full prompt with system prompt and context."""
        prompt_parts = [self.system_prompt]
        
        if context.conversation_history:
            history = context.conversation_history[-3:]
            prompt_parts.append("\nRecent context:")
            for turn in history:
                prompt_parts.append(f"{turn.get('speaker', 'user')}: {turn.get('text', '')}")
        
        prompt_parts.append(f"\nResearch request: {input}")
        prompt_parts.append("\nConduct thorough research and present findings with citations:")
        
        return "\n".join(prompt_parts)
