# JobPilot AI
# Author: Md. Mahamudul Hasan
# License: GNU Affero General Public License v3

###################################################### LINKEDIN SEARCH PREFERENCES ######################################################

search_terms = ["AI Engineer", "ML Engineer"]

search_location = "Remote"
remote = True                         # Remote-only work type filter in search URL
switch_number = 3                     # Safe test run: apply to 3 jobs per search term
randomize_search_order = False

sort_by = "Most recent"
date_posted = "Past week"
salary = ""

easy_apply_only = True

experience_level = ["Entry level", "Associate", "Mid-Senior level"]
job_type = ["Full-time", "Contract"]
on_site = ["Remote"] if remote else ["Remote", "Hybrid"]

# Skip these companies from the job card (no detail pane opened)
company_skip_patterns = ["Crossing Hurdle", "Crossing Hurdles", "Bdjobs", "Turin"]

# Skip job titles containing these (irrelevant roles on AI searches)
title_skip_keywords = ["Flutter", "Mobile Developer", "iOS/Android", "Code Review", "Full Stack JavaScript"]

# Max job cards to inspect per page before paginating (avoids slow spam pages)
max_jobs_to_scan = 12

companies = []
location = []
industry = []
job_function = []
job_titles = []
benefits = []
commitments = []

under_10_applicants = False
in_your_network = False
fair_chance_employer = False

pause_after_filters = False
use_ui_filters = False              # False = filters via URL (more reliable in guest Chrome)

about_company_bad_words = ["Crossover", "Staffing", "Recruiting", "Crossing Hurdle", "Crossing Hurdles"]
about_company_good_words = []

bad_words = [
    "US Citizen only",
    "USA Citizen only",
    "No C2C",
    "Security Clearance",
    "Polygraph",
]

security_clearance = False
did_masters = False
current_experience = 3
