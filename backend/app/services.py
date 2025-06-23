# ===============================================================
# app/services.py
# New file for business logic (scraping, AI calls).
# ===============================================================
import httpx
from bs4 import BeautifulSoup
import json
from typing import Optional
from .models import AnalysisResult
from .config import settings # Import settings to get the API key

async def scrape_github_trending(language: str) -> list[dict]:
    """
    Fetches GitHub trending data from a stable, public API instead of scraping.
    """
    # This public API is more reliable than scraping the GitHub website directly.
    api_url = f"https://gtrend.yapie.me/repositories?language={language}&since=daily"
    headers = {"Accept": "application/json"}
    
    print(f"Fetching trending repos from API: {api_url}")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(api_url, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
        except (httpx.RequestError, json.JSONDecodeError) as e:
            print(f"Error fetching from GitHub Trending API: {e}")
            return []

    repos = []
    # Take the top 3 repositories from the API response
    for repo_info in data[:3]:
        repo_name = f"{repo_info.get('author')}/{repo_info.get('name')}"
        repo_url = repo_info.get('url', '#')
        description = repo_info.get('description', 'No description provided.')
        
        # We still create a combined content string for the AI to analyze
        readme_content = f"Repository: {repo_name}\nDescription: {description}"
        repos.append({"repo_name": repo_name, "repo_url": repo_url, "readme_content": readme_content})
    
    print(f"Fetched {len(repos)} repositories for language: {language} from API.")
    return repos

async def analyze_with_ai(content: str) -> Optional[dict]:
    """Sends content to the Gemini 2.0 Flash model for analysis."""
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={settings.ai_api_key}"
    prompt = f"""
    You are a professional software engineer and tech analyst. Analyze the following repository information.
    Based on the text, return a JSON object. Do NOT include any other text or markdown formatting, just the raw JSON object.
    Here is the content: --- {content} ---
    """
    json_schema = { "type": "OBJECT", "properties": { "one_liner_summary": {"type": "STRING"}, "tech_stack": {"type": "ARRAY", "items": {"type": "STRING"}}, "key_features": {"type": "ARRAY", "items": {"type": "STRING"}}, "community_focus": {"type": "ARRAY", "items": {"type": "STRING"}} } }
    headers = {"Content-Type": "application/json"}
    payload = { "contents": [{"parts": [{"text": prompt}]}], "generationConfig": { "responseMimeType": "application/json", "responseSchema": json_schema } }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(api_url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            response_json = response.json()
            analysis_text = response_json['candidates'][0]['content']['parts'][0]['text']
            return json.loads(analysis_text)
        except Exception as e:
            print(f"Error calling AI for analysis: {e}")
            return None

async def parse_intent_with_ai(user_message: str) -> Optional[dict]:
    """Uses Gemini to parse the user's message into structured intent data."""
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={settings.ai_api_key}"
    
    valid_languages = ['javascript', 'python', 'typescript', 'go', 'rust', 'java', 'c++']
    prompt = f"""
    Analyze the user's request to find the programming language and update frequency.
    1.  **language**: Identify the programming language. It MUST be one of these exact values: {valid_languages}. If no valid language is mentioned, return null.
    2.  **time_value**: Extract only the numerical value of the time (e.g., for "1.5 hours" extract 1.5, for "10 minutes" extract 10). If not found, return null.
    3.  **time_unit**: If you extract a 'time_value', you MUST identify its unit. The unit must be either "minutes" or "hours".
    User's request: "{user_message}"
    Return a single JSON object with the keys "language", "time_value", and "time_unit".
    """
    json_schema = { "type": "OBJECT", "properties": { "language": { "type": "STRING", "enum": valid_languages }, "time_value": { "type": "NUMBER" }, "time_unit": { "type": "STRING", "enum": ["minutes", "hours"] } } }
    headers = {"Content-Type": "application/json"}
    payload = { "contents": [{"parts": [{"text": prompt}]}], "generationConfig": { "responseMimeType": "application/json", "responseSchema": json_schema } }

    print(f"Sending to Gemini for intent parsing: {user_message}")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(api_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            response_json = response.json()
            intent_text = response_json['candidates'][0]['content']['parts'][0]['text']
            intent_data = json.loads(intent_text)
            print(f"Received intent from Gemini: {intent_data}")
            return intent_data
        except Exception as e:
            print(f"Error calling AI for intent parsing: {e}")
            if 'response' in locals():
                print(f"API Response Body: {response.text}")
            return None