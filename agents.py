"""
LangChain agents and chains for MultiAgent Research Pipeline.
Features:
- Resilient multi-model fallback chain across available Gemini models
- Temperature tuning (0.3 for Writer, 0.1 for Critic)
- Explicit prompt templates and output parsers
"""

import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()


def get_resilient_llm(temperature: float = 0.2, max_retries: int = 1):
    """
    Constructs a ChatGoogleGenerativeAI instance with automatic fallback chain
    across active Gemini models to prevent quota / rate-limit failures.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError(
            "GOOGLE_API_KEY is not set. Please add your Gemini API key to .env "
            "or set the environment variable. Get a free key at https://aistudio.google.com"
        )

    preferred_model = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")

    # Priority order of candidate models with active quotas
    candidate_models = [
        preferred_model,
        "gemini-3.1-flash-lite",
        "gemini-3.1-flash-lite-preview",
        "gemini-3.5-flash-lite",
        "gemini-3.6-flash",
        "gemini-3.7-flash",
        "gemini-3.5-flash",
    ]

    # Deduplicate while preserving order
    seen = set()
    models_to_use = [m for m in candidate_models if m and not (m in seen or seen.add(m))]

    primary_model = models_to_use[0]
    base_llm = ChatGoogleGenerativeAI(
        model=primary_model,
        google_api_key=api_key,
        temperature=temperature,
        max_retries=max_retries
    )

    if len(models_to_use) > 1:
        fallbacks = [
            ChatGoogleGenerativeAI(
                model=m,
                google_api_key=api_key,
                temperature=temperature,
                max_retries=max_retries
            )
            for m in models_to_use[1:]
        ]
        return base_llm.with_fallbacks(fallbacks)

    return base_llm


# ── Prompts ──────────────────────────────────────────────────────────────────

writer_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an expert research writer. Write clear, structured, and insightful reports based strictly on the provided research."),
    ("human", """Write a detailed research report on the topic below.

Topic: {topic}

Research Gathered:
{research}

Structure the report as:
- Introduction
- Key Findings (minimum 3 well-explained points)
- Conclusion
- Sources (list all URLs found in the research)

Be detailed, factual, and professional."""),
])

critic_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a sharp, constructive research critic. Be honest, objective, and specific."),
    ("human", """Review the research report below and evaluate it strictly.

Report:
{report}

Respond in this exact format:

Score: X/10

Strengths:
- ...
- ...

Areas to Improve:
- ...
- ...

One line verdict:
..."""),
])


# ── Default Module-Level Chains ───────────────────────────────────────────────

def _build_chains():
    """Initializes writer and critic chains with appropriate temperatures."""
    writer_llm = get_resilient_llm(temperature=0.3)
    critic_llm = get_resilient_llm(temperature=0.1)

    w_chain = writer_prompt | writer_llm | StrOutputParser()
    c_chain = critic_prompt | critic_llm | StrOutputParser()
    return w_chain, c_chain


try:
    writer_chain, critic_chain = _build_chains()
except Exception as _e:
    # Allow import even if API key is not yet set (e.g. during build / testing)
    writer_chain, critic_chain = None, None