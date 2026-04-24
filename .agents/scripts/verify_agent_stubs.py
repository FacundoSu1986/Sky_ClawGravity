import os
import sys

def verify_skills():
    skills_dir = r"e:\Skyclaw_Main_Sync\.agents\skills"
    required_skills = [
        "external-github-agents",
        "dify-agent-orchestrator",
        "metagpt-software-engineer",
        "langgraph-state-machine",
        "openclaw-local-automation"
    ]
    
    print("??? PurpleGuardrail v6.1 (Titan Edition) - Verifying Agent Stubs\n")
    
    all_passed = True
    for skill in required_skills:
        skill_path = os.path.join(skills_dir, skill, "SKILL.md")
        if os.path.exists(skill_path):
            print(f"?? Skill '{skill}': FOUND")
            # Basic validation: check for YAML frontmatter and required sections
            with open(skill_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if "---" in content and "name:" in content and "description:" in content:
                    print(f"   ?? Metadata: VALID")
                else:
                    print(f"   ?? Metadata: INVALID (Missing name/description)")
                    all_passed = False
        else:
            print(f"?? Skill '{skill}': NOT FOUND")
            all_passed = False
            
    if all_passed:
        print("\n?? ALL AGENT STUBS VERIFIED SUCCESSFULLY")
    else:
        print("\n?? VERIFICATION FAILED")
        sys.exit(1)

if __name__ == "__main__":
    verify_skills()
