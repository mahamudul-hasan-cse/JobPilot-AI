# JobPilot AI
# Author: Md. Mahamudul Hasan
# License: GNU Affero General Public License v3
# https://www.gnu.org/licenses/agpl-3.0.en.html


###################################################### BOT BEHAVIOR SETTINGS ######################################################


# >>>>>>>>>>> LinkedIn Settings <<<<<<<<<<<

# Keep external application tabs open? (False = close them after saving the link)
close_tabs = False                  # True or False (case-sensitive)

# Follow companies you Easy Apply to?
follow_companies = False            # True or False (case-sensitive)

# Run the bot continuously until stopped or daily limit reached?
run_non_stop = False                # True or False (case-sensitive)
'''
Note: Treated as False if run_in_background = True
'''

# Alternate between "Most recent" and "Most relevant" sort on each cycle?
alternate_sortby = True             # True or False (case-sensitive)

# Cycle through date_posted values on each run?
cycle_date_posted = True            # True or False (case-sensitive)

# Stop cycling date_posted once it reaches "Past 24 hours"?
stop_date_cycle_at_24hr = True      # True or False (case-sensitive)


# >>>>>>>>>>> File Paths <<<<<<<<<<<

# Folder for generated/tailored resumes
generated_resume_path = "all resumes/"

# CSV history files
file_name = "all excels/all_applied_applications_history.csv"
failed_file_name = "all excels/all_failed_applications_history.csv"

# Log output folder
logs_folder_path = "logs/"


# >>>>>>>>>>> Performance & Browser Settings <<<<<<<<<<<

# Max seconds to wait between each click (randomized within this range)
click_gap = 0                       # 0 = fastest; 1+ adds human-like delay

# Run Chrome in headless/background mode (no visible window)?
run_in_background = False           # True or False — if True, disables pause_* and run_non_stop

# Disable Chrome extensions (faster, but may affect some sites)?
disable_extensions = False          # True or False

# Selenium wait timeouts (seconds) — lower = faster, higher = more stable
implicit_wait = 6
page_load_timeout = 30

# Use smooth scrolling? (prettier but slightly slower)
smooth_scroll = False               # True or False

# Keep screen awake using keyboard events to prevent PC sleep?
keep_screen_awake = True            # True or False

# Use undetected-chromedriver to bypass anti-bot protections?
stealth_mode = True                 # True or False (recommended: True)

# Show popup alerts when AI connection errors occur?
showAiErrorAlerts = False           # True or False


# >>>>>>>>>>> Chrome Profile (Windows) <<<<<<<<<<<

# Guest mode (recommended): fresh Chrome profile + auto login from config/secrets.py
# Saved profile mode: set safe_mode = False and set chrome_profile_directory below
safe_mode = True                    # True = guest (fast start) | False = saved Chrome profile (slow first sync)

# Only used when safe_mode = False — close ALL Chrome windows before running
chrome_user_data_dir = ""
chrome_profile_directory = "Profile 5"   # Mahamudul profile in Chrome picker
