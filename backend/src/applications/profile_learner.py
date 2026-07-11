from src.system.logger import setup_logger
logger = setup_logger('profile_learner')
import os
import json

WORKSPACE_DIR = "/Users/yashkherwal/Downloads/hrmailfiles"
DATA_DIR = os.path.join(WORKSPACE_DIR, "data")
CONTEXT_DIR = os.path.join(DATA_DIR, "context")
JSON_PATH = os.path.join(CONTEXT_DIR, "master_candidate_profile.json")

def load_profile():
    if not os.path.exists(JSON_PATH):
        logger.info("No master_candidate_profile.json found. Run extraction first.")
        return None
    with open(JSON_PATH, 'r') as f:
        return json.load(f)

def save_profile(profile):
    with open(JSON_PATH, 'w') as f:
        json.dump(profile, f, indent=4)
        
def run_learner():
    profile = load_profile()
    if not profile:
        return
        
    logger.info("\n=== Candidate Profile Learner ===")
    logger.info("Answer the following missing questions permanently.\n")
    
    updated = False
    
    for field, data in profile.items():
        if data.get("confidence", 0) < 70 and not data.get("human_verified", False):
            logger.info(f"Missing Field: {field}")
            ans = input(f"Enter your deterministic value for {field} (or press Enter to skip): ").strip()
            if ans:
                profile[field] = {
                    "value": ans,
                    "source": "Human Verified",
                    "confidence": 100,
                    "human_verified": True
                }
                updated = True
                logger.info(f" -> Saved {field} permanently.\n")
                
    if updated:
        save_profile(profile)
        logger.info("All answers saved. master_candidate_profile.json updated!")
    else:
        logger.info("No updates made.")

if __name__ == "__main__":
    run_learner()
