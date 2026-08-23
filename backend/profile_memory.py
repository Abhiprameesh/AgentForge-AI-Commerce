import json
import os

PROFILE_PATH = "user_profile.json"

# Save profile
def save_profile(data):

    with open(PROFILE_PATH, "w") as f:

        json.dump(data, f)

# Load profile
def load_profile():

    if not os.path.exists(PROFILE_PATH):

        return {}

    with open(PROFILE_PATH, "r") as f:

        return json.load(f)