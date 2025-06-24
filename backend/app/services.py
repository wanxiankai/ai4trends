# ===============================================================
# app/services.py
# New file for business logic (scraping, AI calls).
# ===============================================================
import httpx
import json
from typing import Optional
from .config import settings

async def get_trending_repos_from_github_api(language: str) -> list[dict]:
    """Fetches trending repositories using the official GitHub Search API."""
    api_url = f"https://api.github.com/search/repositories?q=language:{language}+stars:>100&sort=stars&order=desc"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"Bearer {settings.github_token}"
    }
    print(f"Fetching trending repos from official GitHub API: {api_url}")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(api_url, headers=headers, timeout=20)
            response.raise_for_status()
            data = response.json()
            items = data.get("items", [])
        except (httpx.RequestError, json.JSONDecodeError, KeyError) as e:
            print(f"Error fetching from GitHub API: {e}")
            return []

    repos = []
    for repo_info in items[:3]: # Take top 3
        repo_name = repo_info.get('full_name')
        repo_url = repo_info.get('html_url', '#')
        description = repo_info.get('description', 'No description provided.')
        
        if not repo_name:
            continue

        readme_content = f"Repository: {repo_name}\nDescription: {description}"
        repos.append({"repo_name": repo_name, "repo_url": repo_url, "readme_content": readme_content})
    
    print(f"Fetched {len(repos)} repositories for language: {language} from GitHub API.")
    return repos

async def analyze_repo_with_ai(content: str) -> Optional[dict]:
    # ... (this function remains the same)
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={settings.ai_api_key}"
    prompt = f"Analyze the following repository information. Based on the text, return a JSON object with keys 'one_liner_summary', 'tech_stack', 'key_features', 'community_focus'. Respond with only the raw JSON object. Content: --- {content} ---"
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
            print(f"Error calling AI for repo analysis: {e}")
            return None

async def parse_language_with_ai(user_message: str) -> Optional[str]:
    # ... (this function remains the same)
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={settings.ai_api_key}"
    valid_languages = ['javascript', 'python', 'typescript', 'go', 'rust', 'java', 'c++']
    prompt = f"""Analyze the user's request to find the programming language. The language MUST be one of these exact values: {valid_languages}. If no valid language is mentioned, return null. User's request: "{user_message}". Return a single JSON object with only one key: "language"."""
    json_schema = {"type": "OBJECT", "properties": {"language": {"type": "STRING", "enum": valid_languages}}}
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "application/json", "responseSchema": json_schema}}
    print(f"Sending to Gemini for LANGUAGE parsing: {user_message}")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(api_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            intent_data = response.json()['candidates'][0]['content']['parts'][0]['text']
            language = json.loads(intent_data).get("language")
            print(f"Received language from Gemini: {language}")
            return language
        except Exception as e:
            print(f"Error calling AI for language parsing: {e}")
            return None
