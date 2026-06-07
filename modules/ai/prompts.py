# JobPilot AI
# Author: Md. Mahamudul Hasan
# License: GNU Affero General Public License v3
# https://www.gnu.org/licenses/agpl-3.0.en.html

"""AI prompt templates for JobPilot AI.

All prompts are defined as module-level string constants.
Use Python's ``str.format()`` to inject dynamic values.
"""

from typing import Any

array_of_strings: dict[str, Any] = {"type": "array", "items": {"type": "string"}}
"""JSON schema fragment for an array-of-strings response."""


extract_skills_prompt: str = """
You are a job requirements extractor and classifier. Your task is to extract all skills
mentioned in a job description and classify them into five categories:

1. "tech_stack": Programming languages, frameworks, libraries, databases, and technologies.
   Examples: Python, React.js, Node.js, MongoDB, Spring Boot, .NET
2. "technical_skills": Technical expertise beyond specific tools.
   Examples: System Architecture, Data Engineering, Microservices, Distributed Systems
3. "other_skills": Non-technical / soft skills.
   Examples: Communication, Leadership, Cross-team collaboration
4. "required_skills": All skills explicitly marked as required or expected from the candidate.
5. "nice_to_have": Skills listed as preferred or beneficial but not mandatory.

Return ONLY valid JSON in the following format — no extra commentary:
{{
    "tech_stack": [],
    "technical_skills": [],
    "other_skills": [],
    "required_skills": [],
    "nice_to_have": []
}}

JOB DESCRIPTION:
{}
"""
"""Use ``extract_skills_prompt.format(job_description)`` to build the full prompt."""


deepseek_extract_skills_prompt: str = """
You are a job requirements extractor and classifier. Extract all skills from the job
description below and classify them into five categories:

1. "tech_stack": Programming languages, frameworks, libraries, databases, and technologies.
2. "technical_skills": Technical expertise beyond specific tools.
3. "other_skills": Non-technical / soft skills.
4. "required_skills": All skills explicitly marked as required.
5. "nice_to_have": Skills listed as preferred but not mandatory.

IMPORTANT: Return ONLY a valid JSON object in the exact format below.
Do not include any extra text, explanation, or markdown.

{{
    "tech_stack": ["Example Skill 1", "Example Skill 2"],
    "technical_skills": ["Example Skill 1", "Example Skill 2"],
    "other_skills": ["Example Skill 1", "Example Skill 2"],
    "required_skills": ["Example Skill 1", "Example Skill 2"],
    "nice_to_have": ["Example Skill 1", "Example Skill 2"]
}}

JOB DESCRIPTION:
{}
"""
"""DeepSeek-optimized version. Use ``deepseek_extract_skills_prompt.format(job_description)``."""


extract_skills_response_format: dict[str, Any] = {
    "type": "json_schema",
    "json_schema": {
        "name": "Skills_Extraction_Response",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "tech_stack": array_of_strings,
                "technical_skills": array_of_strings,
                "other_skills": array_of_strings,
                "required_skills": array_of_strings,
                "nice_to_have": array_of_strings,
            },
            "required": [
                "tech_stack",
                "technical_skills",
                "other_skills",
                "required_skills",
                "nice_to_have",
            ],
            "additionalProperties": False,
        },
    },
}
"""OpenAI JSON schema response format for skill extraction."""


ai_answer_prompt: str = """
You are an intelligent AI assistant filling out a job application form.
Respond concisely and naturally based on the question type:

1. If the question asks for years of experience, duration, or a numeric value — return ONLY a number (e.g., "2", "5").
2. If the question is a Yes/No question — return ONLY "Yes" or "No".
3. If the question requires a short description — give a single-sentence response.
4. If the question requires a detailed response — provide a well-structured, human-sounding answer under 350 characters.
5. Do NOT repeat the question in your answer.

User Information (use this to answer):
{}

Question:
{}
"""
"""Use ``ai_answer_prompt.format(user_information_all, question)``."""


job_scoring_prompt: str = """
You are a job-fit evaluator. Given a job description and a candidate's profile,
score how well the candidate fits this job on a scale of 0 to 100.

Scoring guide:
- 80–100: Excellent match — candidate meets almost all requirements
- 60–79:  Good match — candidate meets most requirements
- 40–59:  Partial match — candidate meets some requirements but lacks key skills
- 0–39:   Poor match — significant gaps between job requirements and candidate profile

Return ONLY valid JSON in this exact format (no markdown, no extra text):
{{
    "score": <integer 0-100>,
    "reason": "<one concise sentence explaining the score>",
    "matched_skills": ["<skill1>", "<skill2>"],
    "missing_skills": ["<skill3>", "<skill4>"]
}}

Candidate Profile:
{}

Job Description:
{}
"""
"""Use ``job_scoring_prompt.format(user_profile, job_description)``."""


resume_tailoring_prompt: str = """
You are a professional career coach and cover letter writer.

Given the candidate's resume and a specific job description, write a concise,
tailored cover letter (3 short paragraphs, under 250 words total).

Requirements:
- Highlight the candidate's most relevant experience and skills for THIS specific job
- Mention the company name ({company}) and job title ({job_title}) naturally
- Use a professional but warm tone
- Return ONLY the cover letter body text — no subject line, no "Dear Hiring Manager" header,
  no signature block. Just the three paragraphs.

Candidate Resume:
{resume}

Job Description:
{job_description}
"""
"""
Use ``resume_tailoring_prompt.format(
    company=company,
    job_title=job_title,
    resume=base_resume_text,
    job_description=job_description
)``.
"""
