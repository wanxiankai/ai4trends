# ===============================================================
# app/tasks.py
# NEW FILE: We are moving the task logic here to keep things clean.
# ===============================================================
from sqlmodel import Session
import datetime
from .database import engine
from .models import Config, AnalysisResult
from . import services

async def run_analysis_task():
    """The complete analysis pipeline, now as a standalone callable task."""
    print("="*50)
    print("BACKGROUND TASK TRIGGERED...")
    with Session(engine) as session:
        language_config = session.get(Config, "trending_language")
        language = language_config.value if language_config else "python"
    print(f"Current language from DB: {language}")
    
    scraped_repos = await services.scrape_github_trending(language)
    if not scraped_repos:
        print("Scraping failed or returned no repos. Skipping analysis.")
        return
        
    for repo_data in scraped_repos:
        print(f"Analyzing {repo_data['repo_name']} with Gemini...")
        ai_result = await services.analyze_with_ai(repo_data["readme_content"])
        if ai_result:
            new_analysis = AnalysisResult(
                repo_name=repo_data["repo_name"],
                repo_url=repo_data["repo_url"],
                analysis_timestamp=datetime.datetime.now(),
                one_liner_summary=ai_result.get("one_liner_summary", "N/A"),
                tech_stack=ai_result.get("tech_stack", []),
                key_features=ai_result.get("key_features", []),
                community_focus=ai_result.get("community_focus", [])
            )
            try:
                with Session(engine) as session:
                    session.add(new_analysis)
                    session.commit()
                print(f"Successfully analyzed and saved: {repo_data['repo_name']}")
            except Exception as e:
                print(f"CRITICAL: Failed to write analysis result to database for {repo_data['repo_name']}. Error: {e}")
        else:
            print(f"Failed to analyze: {repo_data['repo_name']}")
    
    print("BACKGROUND TASK FINISHED.")
    print("="*50)
