from openinference.instrumentation.smolagents import SmolagentsInstrumentor
from phoenix.otel import register
from smolagents.models import LiteLLMModel
import os
from dotenv import load_dotenv
import json 

from tools.youtube_tools import YouTubeVideoSearchTool, YouTubeVideoTranscriptTool, GetCurrentTimeTool

load_dotenv()
file_path = '../grand-song-460414-k6-b7c869f50e10.json'
# Load the JSON file
with open(file_path, 'r') as file:
    vertex_credentials = json.load(file)
# Convert to JSON string
vertex_credentials_json = json.dumps(vertex_credentials)

register()
SmolagentsInstrumentor().instrument(skip_dep_check=True)


from smolagents import (
    # Tool, # No longer directly defining tools here
    CodeAgent,
    ToolCallingAgent,
    VisitWebpageTool,
    WebSearchTool,
)

# --- Tool Class Definitions for YouTubeVideoSearchTool and YouTubeVideoTranscriptTool have been moved to examples/tools/youtube_tools.py ---

modelQwen = LiteLLMModel(
    model_id="openai/qwen3-235b-a22b",  
    api_base=os.getenv("ALI_BASE_URL"),
    api_key=os.getenv("ALI_API_KEY"),
    provider="openai",
    enable_thinking=False,
)

custom_role_conversions = {"tool-call": "assistant", "tool-response": "user"}

modelGemini = LiteLLMModel(
    model_id="vertex_ai/gemini-2.5-pro-preview-05-06",
    vertex_credentials=vertex_credentials_json,
)

# --- Agent Definitions ---

# 1. YouTube Agent
youtube_agent = ToolCallingAgent(
    tools=[YouTubeVideoSearchTool(), YouTubeVideoTranscriptTool(), WebSearchTool(), VisitWebpageTool()],
    model=modelGemini, 
    name="youtube_agent",
    max_steps=20,
    verbosity_level=2,
    planning_interval=4,
    # additional_authorized_imports=["*"],
    description=(
        "This agent is specialized for YouTube. It can search for YouTube videos based on a query "
        "(using YouTubeVideoSearchTool) and fetch the timed transcript of a specific YouTube video ID "
        "(using YouTubeVideoTranscriptTool). The transcript is returned as a JSON string of timed segments."
    )
)


manager_agent = CodeAgent(
    tools=[], 
    model=modelGemini,
    managed_agents=[youtube_agent], 
    max_steps=12,
    verbosity_level=2,
    additional_authorized_imports=["*"],
    planning_interval=4,
    description="A manager agent that can orchestrate web searches, YouTube video processing, and summarize content to answer user queries." 
)

# youtube_agent.run("讲一下今天 GoogleIO 大会的主要内容，详细总结要点，不少于 1000 字。最终结果请用文字内容以MD格式呈现结果，为了辅助用户理解和内容真实性，请在内容中通过引用的方式包含视频链接，并且要说说明内容引自视频的'HH:MM:SS'位置。今日时间是 2025-05-21 10:00:00")
youtube_agent.run("总结一下这个视频的内容，视频链接是 https://www.youtube.com/watch?v=o8NiE3XMPrM&t=186s，最终结果请用文字内容以MD格式呈现结果，为了辅助用户理解和内容真实性，请在内容中通过引用的方式包含视频链接，并且要说说明内容引自视频的'HH:MM:SS'位置。今日时间是 2025-05-21 10:00:00")

