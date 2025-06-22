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
    """Scrapes GitHub trending page for a given language."""
    url = f"https://github.com/trending/{language}?since=daily"
    headers = {"User-Agent": "Mozilla/5.0"}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=15)
            response.raise_for_status()
        except httpx.RequestError as e:
            print(f"Error scraping GitHub: {e}")
            return []

    soup = BeautifulSoup(response.text, "html.parser")
    repos = []
    for article in soup.find_all("article", class_="Box-row")[:3]: # Analyze top 3
        repo_name_tag = article.find("h2", class_="h3").find("a")
        repo_name = repo_name_tag.get("href").strip("/")
        repo_url = f"https://github.com{repo_name_tag.get('href')}"
        description_tag = article.find("p", class_="col-9")
        description = description_tag.text.strip() if description_tag else "No description provided."
        
        readme_content = f"Repository: {repo_name}\nDescription: {description}"
        repos.append({"repo_name": repo_name, "repo_url": repo_url, "readme_content": readme_content})
    
    print(f"Scraped {len(repos)} repositories for language: {language}")
    return repos

# FIX: Added proper indentation to the entire function body.
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
    Analyze the user's request and extract two pieces of information: the programming language and the update frequency in minutes.
    1.  **Language**: The language must be one of these exact values: {valid_languages}. If no valid language is mentioned, return null for the language.
    2.  **Frequency**: Convert any time expression (e.g., '一个半小时', '10 minutes', 'half an hour') into a total number of minutes. If no frequency is mentioned, return null for the interval.
    User's request: "{user_message}"
    Return a single JSON object with the keys "language" and "interval_minutes".
    """
    json_schema = { "type": "OBJECT", "properties": { "language": { "type": "STRING", "enum": valid_languages, "description": "The programming language to track." }, "interval_minutes": { "type": "NUMBER", "description": "The update frequency converted to total minutes." } } }
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
