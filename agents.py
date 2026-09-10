import os

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

# model setup with automatic fallback chain for quota/rate-limit resilience
api_key = os.getenv("GOOGLE_API_KEY")
preferred_model = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")

candidate_models = [
    preferred_model,
    "gemini-3.1-flash-lite",
    "gemini-3.1-flash-lite-preview",
    "gemini-3.5-flash-lite",
    "gemini-3.6-flash",
    "gemini-3.7-flash",
    "gemini-3.5-flash",
]

# Deduplicate while preserving priority order
seen = set()
models_to_use = [m for m in candidate_models if m and not (m in seen or seen.add(m))]

primary_model = models_to_use[0]
llm = ChatGoogleGenerativeAI(
    model=primary_model,
    google_api_key=api_key,
    max_retries=1
)

if len(models_to_use) > 1:
    fallbacks = [
        ChatGoogleGenerativeAI(
            model=m,
            google_api_key=api_key,
            max_retries=1
        )
        for m in models_to_use[1:]
    ]
    llm = llm.with_fallbacks(fallbacks)



#writer chain

writer_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an expert research writer. Write clear, structured and insightful reports."),
    ("human", """Write a detailed research report on the topic below.

Topic: {topic}

Research Gathered:
{research}

Structure the report as:
- Introduction
- Key Findings (minimum 3 well-explained points)
- Conclusion
- Sources (list all URLs found in the research)

Be detailed, factual and professional."""),
])

writer_chain = writer_prompt | llm | StrOutputParser()

#critic_chain

critic_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a sharp and constructive research critic. Be honest and specific."),
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

critic_chain = critic_prompt | llm | StrOutputParser()