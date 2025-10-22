import json
import os
from dotenv import load_dotenv

load_dotenv(override=True)

# Expand the home directory properly

def switch_claude_mode():
    claude_settings_path = os.path.expanduser("~/.claude/settings.json")
    
    if not os.path.exists(claude_settings_path):
        os.makedirs(os.path.dirname(claude_settings_path), exist_ok=True)
        with open(claude_settings_path, 'w') as f:
            json.dump({}, f)
            
    with open(claude_settings_path) as f:
        claude_settings = json.load(f)
        
    current_mode = "z.ai" if "env" in claude_settings else "default"
    input(f"Current Claude mode is '{current_mode}'. Press Enter to switch modes...")

    # If "env" exists, remove it to switch back to default Claude
    if "env" in claude_settings:
        del claude_settings["env"]
        with open(claude_settings_path, 'w') as f:
            json.dump(claude_settings, f, indent=4)

        print("Switched Claude environment to: default")
        return
    
    # Set the environment variables for z.ai
    claude_settings["env"] = {
        "ANTHROPIC_AUTH_TOKEN": os.getenv("ZAI_AUTH_TOKEN"),
        "ANTHROPIC_BASE_URL": os.getenv("ZAI_BASE_URL"),
        "API_TIMEOUT_MS": int(os.getenv("API_TIMEOUT_MS", "30000"))
    }
    with open(claude_settings_path, 'w') as f:
        json.dump(claude_settings, f, indent=4)
        

    print(f"Switched Claude environment to: z.ai")
    return
# remove claude_settings["env"] if it exists

if __name__ == "__main__":
    switch_claude_mode()