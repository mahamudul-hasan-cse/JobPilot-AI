# JobPilot AI — application answers template
# Author: Md. Mahamudul Hasan
#
# SETUP:
#   1. Copy this file:  copy config\questions.example.py config\questions.py
#   2. Fill in your resume path, salary expectations, cover letter, and resume text
#   3. Never commit config\questions.py to Git (it is in .gitignore)

default_resume_path = "all resumes/default/resume.pdf"

years_of_experience = "3"
require_visa = "No"
website = "https://github.com/your-username"
linkedIn = "https://www.linkedin.com/in/your-profile/"
us_citizenship = "Non-citizen allowed to work for any employer"

desired_salary = 100000
current_ctc = 70000
notice_period = 30

linkedin_headline = "Your Professional Headline"
linkedin_summary = """
Brief LinkedIn summary highlighting your skills and experience.
"""

cover_letter = """
Dear Hiring Manager,

I am excited to apply for this role. I bring relevant experience and would welcome
the opportunity to contribute to your team.

Thank you for your consideration.
Your Name
"""

user_information_all = """
Your Name — Your Title
Email: you@example.com | Phone: 00000000000 | City, Country

SKILLS
List your core technical and professional skills here.

EXPERIENCE
Summarize recent roles and responsibilities.

KEY PROJECTS
Highlight 2–3 projects with brief impact statements.

EDUCATION
Your degree, institution, and location.

CONTACT
GitHub: https://github.com/your-username
LinkedIn: https://www.linkedin.com/in/your-profile/
"""

recent_employer = "Your Most Recent Employer"
confidence_level = "8"

# JobPilot AI: AI-tailored cover letter per job (requires use_AI = True)
use_resume_tailoring = False
base_resume_text = """
Paste your full resume as plain text here for AI cover letter tailoring.
Include skills, experience, projects, and education — but no secrets or passwords.
"""

pause_before_submit = False
pause_at_failed_question = False
overwrite_previous_answers = False
