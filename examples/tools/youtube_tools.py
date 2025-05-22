import os
import json
import requests
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional, Any
from smolagents import Tool
from dotenv import load_dotenv

# Load environment variables for the tools, e.g., RAPIDAPI_KEY
# This assumes .env file is found relative to where this script is run from,
# or it's already loaded if this module is imported by another script that called load_dotenv().
# Calling it here ensures tools can access their env vars if run/tested standalone.
load_dotenv()

class YouTubeVideoSearchTool(Tool):
    name: str = "YouTubeVideoSearchTool"
    description: str = (
        "Searches YouTube for videos based on a given keyword query. "
        "This tool aims to return a JSON string representing a list of up to 20 video items. "
        "Each video item in the list is a dictionary containing keys such as 'title' (video title), "
        "'url' (direct link to the YouTube video), 'snippet' (a brief description or summary of the video), "
        "'channel_title' (the name of the YouTube channel that uploaded the video), "
        "'publish_time' (text indicating when the video was published, e.g., '2 weeks ago'), "
        "'view_count' (text indicating the number of views, e.g., '1.2M views'), "
        "'lengthText' (text indicating video duration, e.g., '10:35'), and "
        "'thumbnail_url' (URL of the video's thumbnail image). "
        "If no videos are found matching the query, or if an API error occurs, "
        "it will return a JSON string representing a list with a single dictionary "
        "containing an 'error' or 'message' key with a descriptive message detailing the outcome."
    )
    
    inputs: Dict[str, Dict[str, str]] = {
        "query": {
            "type": "string",
            "description": "The search keyword or phrase."
        }
    }
    output_type: str = "string"

    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("RAPIDAPI_KEY")
        if not self.api_key:
            raise ValueError("RAPIDAPI_KEY environment variable not set for YouTubeVideoSearchTool.")
        self.api_host = "youtube-media-downloader.p.rapidapi.com"
        self.base_url = "https://youtube-media-downloader.p.rapidapi.com/v2/search/videos"
        self.fixed_max_results = 20

    def forward(self, query: str) -> str:
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
                if item.get("type") == "video" and len(videos) < self.fixed_max_results:
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
                        'lengthText': item.get("lengthText"),
                        'thumbnail_url': item.get("thumbnails", [{}])[0].get("url") if item.get("thumbnails") else None,
                    })
            
            if not videos and data.get("items"): 
                 return json.dumps([{"message": "No videos found matching the criteria, though other item types might exist."}])
            elif not videos:
                 return json.dumps([{"message": "No items found for the given query."}])

            return json.dumps(videos)

        except requests.exceptions.RequestException as e:
            return json.dumps([{"error": f"API request failed: {str(e)}"}])
        except ValueError as e: # Catches json.JSONDecodeError as it's a subclass of ValueError
            return json.dumps([{"error": f"Failed to parse API response: {str(e)}"}])

class YouTubeVideoTranscriptTool(Tool):
    name: str = "YouTubeVideoTranscriptTool"
    description: str = (
        "Fetches and parses timed text (subtitles) for a list of up to 5 YouTube video IDs. "
        "The input 'video_ids' should be a list of strings, where each string is a unique YouTube video ID (e.g., ['G3JjSQI4FE8', 'dQw4w9WgXcQ']). "
        "Returns a JSON string representing a list of results. Each item in this list is a dictionary "
        "corresponding to one of the input video IDs. This dictionary will contain: "
        "1. 'video_id': The original video ID string. "
        "2. 'transcript_result': This field will contain either: "
        "   a) A list of transcript segments if successful (each segment is a dictionary with 'start_time_secs' and 'text'). " # Reflects user's latest change
        "   b) An error object (a dictionary with an 'error' key and descriptive message) if transcription failed for that specific video. "
        "The tool attempts to get an English ('en') transcript by default for each video; if English is not available, "
        "it falls back to the first available subtitle track for that video."
    )

    inputs: Dict[str, Dict[str, Any]] = {
        "video_ids": {
            "type": "array",
            "description": "A list of unique YouTube video IDs (strings, e.g., ['G3JjSQI4FE8', 'dQw4w9WgXcQ']). Maximum of 5 video IDs.",
            "items": {"type": "string"}
        }
    }
    output_type: str = "string" 

    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("RAPIDAPI_KEY")
        if not self.api_key:
            raise ValueError("RAPIDAPI_KEY environment variable not set for YouTubeVideoTranscriptTool.")
        self.api_host = "youtube-media-downloader.p.rapidapi.com"
        self.base_url = "https://youtube-media-downloader.p.rapidapi.com/v2/video/details"
        self.max_videos_per_call = 5

    def _parse_timed_text_xml(self, xml_content: str) -> List[Dict[str, str]]: # Reflects user's latest change
        segments = []
        try:
            root = ET.fromstring(xml_content)
            for text_element in root.findall('text'):
                start_time = text_element.get('start') # This is a string
                text_content = text_element.text.strip() if text_element.text else ""
                
                if start_time is not None and text_content:
                    segments.append({
                        "start_time_secs": start_time, # Stored as string
                        "text": text_content
                    })
        except ET.ParseError as e:
            # This print is for server-side logging/debugging.
            print(f"Error parsing XML timed text: {e}")
            return [] 
        return segments

    def _fetch_single_transcript(self, video_id: str) -> Any: 
        if not self.api_key:
            return {"error": "API key not configured for YouTubeVideoTranscriptTool."}

        default_preferred_lang = 'en'
        headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.api_host,
        }
        params_details = {
            "videoId": video_id,
            "urlAccess": "blocked", 
            "subtitles": "true"
        }

        try:
            response_details = requests.get(self.base_url, headers=headers, params=params_details, timeout=15)
            response_details.raise_for_status()
            data_details = response_details.json()

            if not data_details.get("status") or "subtitles" not in data_details:
                error_message_detail = data_details.get('errorID', 'Unknown error')
                if isinstance(error_message_detail, dict) and 'text' in error_message_detail:
                    error_message_detail = error_message_detail['text']
                return {"error": f"Could not retrieve subtitle information for {video_id}. API status: {data_details.get('status')}, message: {error_message_detail}"}
            
            subtitles_info = data_details.get("subtitles", {})
            if not subtitles_info.get("status") or not subtitles_info.get("items"):
                error_message_detail = subtitles_info.get('errorID', 'No subtitle items found')
                if isinstance(error_message_detail, dict) and 'text' in error_message_detail:
                    error_message_detail = error_message_detail['text']
                return {"error": f"Subtitles not available or retrieval failed for {video_id}. Status: {subtitles_info.get('status')}, Message: {error_message_detail}"}

            subtitle_items = subtitles_info.get("items", [])
            selected_subtitle_url = None
            
            for item in subtitle_items:
                if item.get("code") == default_preferred_lang and item.get("url"):
                    selected_subtitle_url = item["url"]
                    break
            
            if not selected_subtitle_url and subtitle_items:
                first_item = subtitle_items[0]
                if first_item.get("url"):
                    selected_subtitle_url = first_item.get("url")
                    # found_lang_code = first_item.get('code', 'unknown_code')
                    # print(f"Warning: English ('{default_preferred_lang}') transcript not found for {video_id}. Falling back to {found_lang_code}")

            if not selected_subtitle_url:
                return {"error": f"No suitable subtitle track found or URL missing for {video_id}."}

            response_timed_text = requests.get(selected_subtitle_url, timeout=15) 
            response_timed_text.raise_for_status()
            timed_text_content = response_timed_text.text 

            timed_segments = self._parse_timed_text_xml(timed_text_content) 
            
            if not timed_segments:
                return {"error": f"Failed to parse timed text XML or transcript is empty for {video_id}."} 
            
            return timed_segments

        except requests.exceptions.HTTPError as e:
            error_content = "No additional error content in response."
            if e.response is not None:
                try:
                    error_content = e.response.json()
                except json.JSONDecodeError:
                    error_content = e.response.text[:500] 
            return {"error": f"API HTTP error for {video_id}: {str(e)}, Response: {error_content}"}
        except requests.exceptions.RequestException as e:
            return {"error": f"API request failed for {video_id}: {str(e)}"}
        except json.JSONDecodeError as e: # Ensure this is ValueError or a more specific JSONDecodeError if available
            return {"error": f"Failed to parse API JSON response for {video_id}: {str(e)}"}
        except Exception as e:
            return {"error": f"An unexpected error occurred while processing {video_id}: {str(e)}"}

    def forward(self, video_ids: List[str]) -> str: 
        all_results = []
        
        if not isinstance(video_ids, list):
            return json.dumps([{
                "error": "Input 'video_ids' must be a list of strings.",
                "received_type": str(type(video_ids))
            }])

        if not video_ids:
            return json.dumps([{"message": "No video IDs provided in the list."}])

        if len(video_ids) > self.max_videos_per_call:
            return json.dumps([{
                "error": f"Too many video IDs provided. Maximum is {self.max_videos_per_call}. Received {len(video_ids)}.",
                "video_ids_preview": [str(vid) for vid in video_ids[:self.max_videos_per_call+2]] 
            }])

        for video_id in video_ids:
            if not isinstance(video_id, str) or not video_id.strip():
                all_results.append({
                    "video_id": str(video_id) if video_id is not None else "NoneProvided",
                    "transcript_result": {"error": "Invalid video_id: must be a non-empty string."}
                })
                continue
            
            cleaned_video_id = video_id.strip()
            transcript_data = self._fetch_single_transcript(cleaned_video_id)
            all_results.append({
                "video_id": cleaned_video_id,
                "transcript_result": transcript_data
            })
            
        return json.dumps(all_results)

class GetCurrentTimeTool(Tool):
    name: str = "GetCurrentTimeTool"
    description: str = (
        "Gets the current time. Returns UTC time if no location is specified. "
        "If a location is specified (format: 'Region/City', e.g., 'Europe/London' or 'America/New_York'), "
        "it returns the current time in that location. "
        "The time information includes date, time, and timezone."
    )
    inputs: Dict[str, Dict[str, Any]] = {
        "location": {
            "type": "string",
            "description": "Optional. The location for which to fetch the current time, formatted as 'Region/City' (e.g., 'America/Los_Angeles'). Defaults to 'Etc/UTC' if not provided.",
            "default": "Etc/UTC", # Default to UTC if not provided
            "nullable": True      # Added to indicate the argument can be omitted
        }
    }
    output_type: str = "string"

    def __init__(self):
        super().__init__()
        self.base_url = "http://worldtimeapi.org/api/timezone"

    def forward(self, location: Optional[str] = "Etc/UTC") -> str:
        """
        Fetches the current time for a given location or UTC if no location is provided.
        Args:
            location: Optional. The location for which to fetch the current time, 
                      formatted as 'Region/City'. Defaults to 'Etc/UTC'.
        Returns:
            str: A string indicating the current time and timezone, or an error message.
        """
        if not location or location.strip() == "":
            effective_location = "Etc/UTC"
        else:
            effective_location = location.strip()

        url = f"{self.base_url}/{effective_location}.json"

        try:
            response = requests.get(url, timeout=10) # Added timeout
            response.raise_for_status() # Raises HTTPError for bad responses (4XX or 5XX)

            data = response.json()
            datetime_str = data.get("datetime")
            timezone_abbr = data.get("abbreviation")
            utc_offset = data.get("utc_offset")
            # week_number = data.get("week_number") # Example of other available info

            if not datetime_str:
                return f"Error: Could not retrieve a valid datetime from API for {effective_location}. Response: {data}"
            
            # Reconstruct a more descriptive time string
            # The datetime string from the API usually looks like: 2024-05-22T10:00:00.123456+00:00
            # We can parse it or use parts of it.
            # For simplicity, let's directly use what the API gives if it's clear enough, or format it.
            # The API also provides timezone and utc_offset which are useful.
            
            return f"The current time in {effective_location} ({timezone_abbr}, UTC{utc_offset}) is: {datetime_str}."

        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return f"Error: The specified location '{effective_location}' was not found by the World Time API. Please check the Region/City format (e.g., 'America/New_York' or 'Europe/Paris')."
            return f"Error fetching time data for '{effective_location}': HTTP {e.response.status_code if e.response else 'Unknown status'} - {str(e)}"
        except requests.exceptions.RequestException as e:
            return f"Error fetching time data for '{effective_location}': Request failed - {str(e)}"
        except json.JSONDecodeError:
            return f"Error: Could not parse JSON response from World Time API for '{effective_location}'."
        except Exception as e:
            return f"An unexpected error occurred while fetching time for '{effective_location}': {str(e)}" 