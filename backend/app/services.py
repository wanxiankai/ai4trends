# ===============================================================
# app/services.py
# New file for business logic (scraping, AI calls).
# ===============================================================
import httpx
from bs4 import BeautifulSoup
import json
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
    for article in soup.find_all("article", class_="Box-row")[:3]: # Analyze top 3 repos
        repo_name_tag = article.find("h2", class_="h3").find("a")
        repo_name = repo_name_tag.get("href").strip("/")
        repo_url = f"https://github.com{repo_name_tag.get('href')}"
        description_tag = article.find("p", class_="col-9")
        description = description_tag.text.strip() if description_tag else "No description provided."
        
        readme_content = f"Repository: {repo_name}\nDescription: {description}"
        repos.append({"repo_name": repo_name, "repo_url": repo_url, "readme_content": readme_content})
    
    print(f"Scraped {len(repos)} repositories for language: {language}")
    return repos

async def analyze_with_ai(content: str) -> dict:
    """Sends content to the Gemini 2.0 Flash model for analysis."""
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={settings.ai_api_key}"
    
    prompt = f"""
    You are a professional software engineer and tech analyst. Analyze the following repository information.
    Based on the text, return a JSON object. Do NOT include any other text or markdown formatting, just the raw JSON object.
    
    Here is the content:
    ---
    {content}
    ---
    """
    
    # Define the required JSON schema for the response
    json_schema = {
        "type": "OBJECT",
        "properties": {
            "one_liner_summary": {"type": "STRING", "description": "A single, concise sentence summarizing the project."},
            "tech_stack": {
                "type": "ARRAY",
                "items": {"type": "STRING"},
                "description": "List of the primary language and key frameworks or libraries mentioned."
            },
            "key_features": {
                "type": "ARRAY",
                "items": {"type": "STRING"},
                "description": "A list of up to 3 most important features or goals."
            },
            "community_focus": {
                "type": "ARRAY",
                "items": {"type": "STRING"},
                "description": "Based on the description, infer what the community might be interested in."
            }
        },
        "required": ["one_liner_summary", "tech_stack", "key_features", "community_focus"]
    }

    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": json_schema,
        }
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(api_url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            
            # Extract the JSON string from the response
            response_json = response.json()
            analysis_text = response_json['candidates'][0]['content']['parts'][0]['text']
            
            # The response text should be a valid JSON string
            return json.loads(analysis_text)
        except (httpx.RequestError, json.JSONDecodeError, KeyError, IndexError) as e:
            print(f"Error calling Gemini API or parsing response: {e}")
            if 'response' in locals():
                print(f"API Response Body: {response.text}")
            return None
