# JobPilot AI — credentials template
# Author: Md. Mahamudul Hasan
#
# SETUP:
#   1. Copy this file:  copy config\secrets.example.py config\secrets.py
#   2. Edit config\secrets.py with your real LinkedIn and API credentials
#   3. Never commit config\secrets.py to Git (it is in .gitignore)
#
# Get a free Gemini API key: https://aistudio.google.com/apikey

###################################################### LINKEDIN CREDENTIALS ######################################################

username = "your.email@example.com"   # LinkedIn login email
password = "your_linkedin_password"   # LinkedIn login password

###################################################### AI CONFIGURATION ######################################################

use_AI = True                         # Enable AI features (scoring, Q&A, cover letters)
ai_provider = "gemini"                # Options: "gemini", "openai", "deepseek"

llm_api_url = "https://generativelanguage.googleapis.com/"  # Used by OpenAI-compatible clients
llm_api_key = "YOUR_GEMINI_API_KEY"   # Replace with your API key
llm_model = "gemini-2.0-flash"        # Model name for your provider
llm_spec = "gemini"                   # Provider spec hint
stream_output = False                 # Stream AI responses to console

###################################################### JOBPILOT AI FEATURES ######################################################

use_relevance_scoring = True          # Score each job 0–100 before applying
ai_relevance_threshold = 65           # Skip jobs scoring below this value
strict_relevance_scoring = False      # If True, skip jobs when AI scoring fails (e.g. quota errors)
