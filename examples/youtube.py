from openinference.instrumentation.smolagents import SmolagentsInstrumentor
from phoenix.otel import register
from smolagents.models import LiteLLMModel
import os
from dotenv import load_dotenv
import requests # Added for API calls
from typing import List, Dict, Optional # Added for type hinting
import re # Added for VTT parsing
import json # Added for serializing list output to JSON string
import xml.etree.ElementTree as ET # Added for parsing XML timed text

load_dotenv()


register()
SmolagentsInstrumentor().instrument(skip_dep_check=True)


from smolagents import (
    Tool, 
    CodeAgent,
    ToolCallingAgent,
    VisitWebpageTool,
    WebSearchTool,
)

class YouTubeVideoSearchTool(Tool):
    name: str = "YouTubeVideoSearchTool"
    description: str = (
        "Searches YouTube for videos based on a keyword query. "
        "Returns a JSON string representing a list of up to 5 videos with titles, URLs, descriptions, etc."
    )
    
    inputs: Dict[str, Dict[str, str]] = {
        "query": {
            "type": "string",
            "description": "The search keyword or phrase."
        }
    }
    output_type: str = "string" # Changed from "list" to "string"

    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("RAPIDAPI_KEY")
        if not self.api_key:
            raise ValueError("RAPIDAPI_KEY environment variable not set.")
        self.api_host = "youtube-media-downloader.p.rapidapi.com"
        self.base_url = "https://youtube-media-downloader.p.rapidapi.com/v2/search/videos"
        self.fixed_max_results = 5 # Internal fixed limit for results

    def forward(self, query: str) -> str: # Return type changed to str
        """
        Args:
            query: The search keyword or phrase.
        Returns:
            A JSON string representing a list of video details (up to 5 videos),
            or a JSON string representing an error object if an error occurs.
        """
        if not self.api_key:
            return json.dumps([{"error": "API key not configured for YouTubeVideoSearchTool."}])

        headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.api_host,
        }
        params = {
            "keyword": query,
            "uploadDate": "all", 
            "duration": "all",   
            "sortBy": "relevance",
        }

        try:
            response = requests.get(self.base_url, headers=headers, params=params, timeout=15)
            response.raise_for_status() 
            data = response.json()

            if data.get("status") is not True or "items" not in data:
                error_msg = data.get("errorID", "Unknown API error or malformed response")
                if isinstance(error_msg, dict) and "text" in error_msg : 
                    error_msg = error_msg["text"]
                return json.dumps([{"error": f"YouTube API error: {error_msg}"}])

            videos = []
            for item in data.get("items", []):
                if item.get("type") == "video" and len(videos) < self.fixed_max_results: # Use internal fixed limit
                    video_id = item.get("id")
                    if not video_id:
                        continue

                    channel_info = item.get("channel", {})
                    videos.append({
                        "title": item.get("title", "N/A"),
                        "url": f"https://www.youtube.com/watch?v={video_id}",
                        "snippet": item.get("description", ""),
                        "channel_title": channel_info.get("name", "N/A"),
                        "publish_time": item.get("publishedTimeText", ""),
                        "view_count": item.get("viewCountText", ""),
                        'lengthText': item.get("lengthText"), # Kept user's change
                        'thumbnail_url': item.get("thumbnails", [{}])[0].get("url") if item.get("thumbnails") else None, # Kept user's change
                    })
            
            if not videos and data.get("items"): 
                 return json.dumps([{"message": "No videos found matching the criteria, though other item types might exist."}])
            elif not videos:
                 return json.dumps([{"message": "No items found for the given query."}])

            return json.dumps(videos) # Serialize successful list to JSON string

        except requests.exceptions.RequestException as e:
            return json.dumps([{"error": f"API request failed: {str(e)}"}])
        except ValueError as e: 
            return json.dumps([{"error": f"Failed to parse API response: {str(e)}"}])

class YouTubeVideoTranscriptTool(Tool):
    name: str = "YouTubeVideoTranscriptTool"
    description: str = (
        "Fetches and parses the timed text (subtitles) of a given YouTube video ID. "
        "Returns a JSON string representing a list of transcript segments, each with a start time (in seconds) and text. "
        "It attempts to get an English ('en') transcript by default. If English is not available, "
        "it falls back to the first available subtitle track."
    )

    inputs: Dict[str, Dict[str, any]] = {
        "video_id": {
            "type": "string",
            "description": "The unique ID of the YouTube video (e.g., 'G3JjSQI4FE8')."
        }
    }
    output_type: str = "string" 

    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("RAPIDAPI_KEY")
        if not self.api_key:
            raise ValueError("RAPIDAPI_KEY environment variable not set.")
        self.api_host = "youtube-media-downloader.p.rapidapi.com"
        self.base_url = "https://youtube-media-downloader.p.rapidapi.com/v2/video/details"

    def _parse_timed_text_xml(self, xml_content: str) -> List[Dict[str, str]]:
        segments = []
        try:
            root = ET.fromstring(xml_content)
            for text_element in root.findall('text'):
                start_time = text_element.get('start')
                text_content = text_element.text.strip() if text_element.text else ""
                
                if start_time is not None and text_content:
                    segments.append({
                        "start_time_secs": start_time,
                        "text": text_content
                    })
        except ET.ParseError as e:
            print(f"Error parsing XML timed text: {e}")
            return [] 
        return segments

    def forward(self, video_id: str) -> str: 
        if not self.api_key:
            return json.dumps([{"error": "API key not configured for YouTubeVideoTranscriptTool."}])

        default_preferred_lang = 'en'
        headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.api_host,
        }
        params = {
            "videoId": video_id,
            "urlAccess": "blocked", 
            "subtitles": "true"
        }

        try:
            response_details = requests.get(self.base_url, headers=headers, params=params, timeout=15)
            response_details.raise_for_status()
            data_details = response_details.json()

            if not data_details.get("status") or "subtitles" not in data_details:
                return json.dumps([{"error": f"Could not retrieve subtitle information. API status: {data_details.get('status')}, message: {data_details.get('errorID', 'Unknown error')}"}])
            
            subtitles_info = data_details.get("subtitles", {})
            if not subtitles_info.get("status") or not subtitles_info.get("items"):
                return json.dumps([{"error": f"Subtitles not available or retrieval failed. Status: {subtitles_info.get('status')}, Message: {subtitles_info.get('errorID', 'No subtitle items found')}"}])

            subtitle_items = subtitles_info.get("items", [])
            selected_subtitle_url = None
            found_lang_code = None

            for item in subtitle_items:
                if item.get("code") == default_preferred_lang and item.get("url"):
                    selected_subtitle_url = item["url"]
                    found_lang_code = default_preferred_lang
                    break
            
            if not selected_subtitle_url and subtitle_items:
                first_item = subtitle_items[0]
                if first_item.get("url"):
                    selected_subtitle_url = first_item.get("url")
                    found_lang_code = first_item.get('code', 'unknown_code')
                    print(f"Warning: English ('{default_preferred_lang}') transcript not found. Falling back to first available: {found_lang_code}")

            if not selected_subtitle_url:
                return json.dumps([{"error": "No suitable subtitle track found or URL missing."}])

            response_timed_text = requests.get(selected_subtitle_url, timeout=15) 
            response_timed_text.raise_for_status()
            timed_text_content = response_timed_text.text 

            # print("\n--- 原始 Timed Text 内容 (前1000字符) ---") 
            # print(timed_text_content[:1000])
            # print("--- 结束原始 Timed Text 内容 ---")

            timed_segments = self._parse_timed_text_xml(timed_text_content) 
            
            if not timed_segments:
                return json.dumps([{"error": "Failed to parse timed text XML or transcript is empty."}]) 
            
            return json.dumps(timed_segments)

        except requests.exceptions.RequestException as e:
            return json.dumps([{"error": f"Error during API request: {str(e)}"}])
        except ValueError as e: 
            return json.dumps([{"error": f"Error parsing API detail response: {str(e)}"}])
        except Exception as e:
            return json.dumps([{"error": f"An unexpected error occurred: {str(e)}"}])

# model = LiteLLMModel(
#     model_id="openai/qwen3-235b-a22b",  
#     api_base=os.getenv("ALI_BASE_URL"),
#     api_key=os.getenv("ALI_API_KEY"),
#     provider="openai",
#     enable_thinking=False,
# )

model = LiteLLMModel(model_id="deepseek/deepseek-chat")

# --- Agent Definitions ---

# 1. YouTube Agent
youtube_agent = CodeAgent(
    tools=[YouTubeVideoSearchTool(), YouTubeVideoTranscriptTool()],
    model=model, 
    name="youtube_agent",
    max_steps=20,
    verbosity_level=2,
    planning_interval=4,
    additional_authorized_imports=["*"],
    description=(
        "This agent is specialized for YouTube. It can search for YouTube videos based on a query "
        "(using YouTubeVideoSearchTool) and fetch the timed transcript of a specific YouTube video ID "
        "(using YouTubeVideoTranscriptTool). The transcript is returned as a JSON string of timed segments."
    )
)

# SummarizationAgent is no longer needed, ManagerAgent will do the summarization.
# summarization_agent = CodeAgent(
#     model=model, 
#     name="summarization_agent",
#     description=(
#         "This agent is skilled at summarizing text. It takes a structured transcript (JSON string with timed segments) "
#         "and produces a concise, coherent summary of the content."
#     )
# )

search_agent = ToolCallingAgent(
    tools=[WebSearchTool(), VisitWebpageTool()], 
    model=model,
    name="search_agent",
    max_steps=5,
    verbosity_level=2,
    description="This agent can perform general web searches and visit webpages to gather information for Providing context or optimizing keywords for YouTube search."
)

manager_agent = CodeAgent(
    tools=[], 
    model=model,
    managed_agents=[youtube_agent], 
    max_steps=12,
    verbosity_level=2,
    additional_authorized_imports=["*"],
    planning_interval=4,
    description="A manager agent that can orchestrate web searches, YouTube video processing, and summarize content to answer user queries." 
)

manager_agent.run("最近openai新发布的codex在youtube上评价如何，需要结合多个youtube视频内容具体讲一下。最终结果请用文字内容以MD格式呈现结果，为了辅助用户理解和内容真实性，请在内容中通过引用的方式包含视频链接，并且要说说明内容引自视频的‘HH:MM:SS’位置。此刻是2025年5月20号")

