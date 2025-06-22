# ===============================================================
# app/scheduler.py
# This file defines the scheduled jobs.
# ===============================================================
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlmodel import Session, select
import datetime
from .database import engine
from .models import Config, AnalysisResult
from .services import scrape_github_trending, analyze_with_ai

async def run_analysis_task():
    """The complete analysis pipeline, from scraping to saving in DB."""
    print("="*50)
    print("RUNNING ANALYSIS TASK...")
    
    with Session(engine) as session:
        language_config = session.get(Config, "trending_language")
        language = language_config.value if language_config else "python"
    
    print(f"Current language from DB: {language}")
    
    # 1. Scrape data
    scraped_repos = await scrape_github_trending(language)
    if not scraped_repos:
        print("Scraping failed or returned no repos. Skipping analysis.")
        return

    # 2. Analyze each repo and save to DB
    for repo_data in scraped_repos:
        print(f"Analyzing {repo_data['repo_name']}...")
        ai_result = await analyze_with_ai(repo_data["readme_content"])
        
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
            with Session(engine) as session:
                session.add(new_analysis)
                session.commit()
            print(f"Successfully analyzed and saved: {repo_data['repo_name']}")
        else:
            print(f"Failed to analyze: {repo_data['repo_name']}")
    
    print("ANALYSIS TASK FINISHED.")
    print("="*50)

scheduler = AsyncIOScheduler()