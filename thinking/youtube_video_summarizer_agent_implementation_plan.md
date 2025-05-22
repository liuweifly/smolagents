# YouTube 视频内容总结 Agent - 基于 `youtube.py` 的实现方案

此文档概述了在 `examples/youtube.py` 现有框架基础上，实现 YouTube 视频内容总结 Agent 的步骤和代码结构变更。

## 1. 目标回顾

构建一个能够根据用户输入，搜索 YouTube 视频，获取其转录文本，进行总结，并返回总结内容和视频链接的 Agent 系统。

## 2. 主要修改和新增组件

### 2.1. 新增工具类 (Tool Classes)

在 `examples/youtube.py` 中定义以下新工具：

*   **`YouTubeVideoSearchTool(Tool)`**
    *   `name`: "YouTubeVideoSearchTool"
    *   `description`: 用于根据关键词搜索 YouTube 视频，返回 JSON 字符串。
    *   `forward(self, query: str) -> str`:
        *   输入: 搜索查询字符串 `query`。
        *   输出: JSON 字符串，包含视频列表（每个视频包含 `title`, `url`, `snippet`, `channel_title`, `publish_time`, `view_count`, `lengthText`, `thumbnail_url`）或错误信息。
        *   实现: 调用 RapidAPI 的 `youtube-media-downloader` 服务的 `/v2/search/videos` 端点。内部固定返回最多5个结果。

*   **`YouTubeVideoTranscriptTool(Tool)`**
    *   `name`: "YouTubeVideoTranscriptTool"
    *   `description`: 用于获取指定 YouTube 视频 ID 的文本转录，返回 JSON 字符串。
    *   `forward(self, video_id: str) -> str`:
        *   输入: YouTube 视频的唯一 ID `video_id`。
        *   输出: JSON 字符串，包含转录片段列表（每个片段含 `start_time_secs` 和 `text`）或错误信息。
        *   实现: 调用 RapidAPI 的 `youtube-media-downloader` 服务的 `/v2/video/details` 端点获取字幕链接，然后下载并解析 XML 格式的字幕。默认尝试英文，失败则回退。

### 2.2. 新增 Agent 实例

*   **`youtube_agent = ToolCallingAgent(...)`**
    *   `tools`: `[YouTubeVideoSearchTool(), YouTubeVideoTranscriptTool(), WebSearchTool(), VisitWebpageTool()]`
    *   `model`: 复用 `youtube.py` 中的 `model` 实例。
    *   `name`: "youtube_agent"
    *   `description`: "This agent can search for YouTube videos, get their transcripts, and perform web searches to gather more context."

*   **`summarization_agent = CodeAgent(...)`**
    *   **此 Agent 已被移除。** 总结功能将由 `ManagerAgent` 直接承担，因此不再创建独立的 `summarization_agent`。

### 2.3. 修改现有 `ManagerAgent`

*   **`managed_agents`**: 更新列表，仅包含 `youtube_agent`。
    *   `managed_agents=[youtube_agent]`
*   **`system_prompt`**: **关键修改**。需要详细指导 `ManagerAgent` 如何协调 `youtube_agent` 并自行完成总结。Prompt 应包含清晰的工作流程。
    *   **示例 Prompt 核心逻辑**:
        1.  理解用户请求。
        2.  可选：若需上下文，指示 `youtube_agent` 使用其 `WebSearchTool` 进行搜索。
        3.  指示 `youtube_agent` 使用 `YouTubeVideoSearchTool` 找视频。
        4.  分析结果，选视频。
        5.  指示 `youtube_agent` 使用 `YouTubeVideoTranscriptTool` 获取转录。
        6.  `ManagerAgent` **直接对转录文本进行总结**。
        7.  评估总结，不满意则迭代 (换关键词、换视频、调整总结要求)。
        8.  返回总结和视频 URL。
        9.  处理用户直接提供视频链接的情况 (此时直接让 `youtube_agent` 获取转录)。

## 3. 代码结构示例 (`examples/youtube.py` 内)

```python
# --- Imports ---
# from smolagents import Tool, CodeAgent, ToolCallingAgent, VisitWebpageTool, WebSearchTool
# from smolagents.models import LiteLLMModel
# import os
# from dotenv import load_dotenv
# import requests
# from typing import List, Dict, Optional
# import json
# import xml.etree.ElementTree as ET

# load_dotenv()
# # register() and SmolagentsInstrumentor() if used

# --- Tool Definitions (Actual implementations in youtube.py) ---
# class YouTubeVideoSearchTool(Tool):
#     name: str = "YouTubeVideoSearchTool"
#     description: str = (
#         "Searches YouTube for videos based on a keyword query. "
#         "Returns a JSON string representing a list of up to 5 videos with titles, URLs, descriptions, etc."
#     )
#     # ... (inputs, output_type as in youtube.py)
#     def forward(self, query: str) -> str:
#         print(f"Executing YouTubeVideoSearchTool with query: {query}")
#         # ... actual implementation using RapidAPI ...
#         return json.dumps([{"title": f"Mock Video for '{query}'", "url": "https://youtube.com/mock"}])

# class YouTubeVideoTranscriptTool(Tool):
#     name: str = "YouTubeVideoTranscriptTool"
#     description: str = (
#         "Fetches and parses the timed text (subtitles) of a given YouTube video ID. "
#         "Returns a JSON string representing a list of transcript segments..."
#     )
#     # ... (inputs, output_type as in youtube.py)
#     def forward(self, video_id: str) -> str:
#         print(f"Executing YouTubeVideoTranscriptTool for video ID: {video_id}")
#         # ... actual implementation using RapidAPI ...
#         return json.dumps([{"start_time_secs": "0.0", "text": f"Mock transcript for video ID {video_id}"}])

# --- Model Definition (reuse existing from youtube.py) ---
# model = LiteLLMModel(...) # Or other model from youtube.py

# --- Agent Definitions (Reflecting youtube.py structure) ---
# # search_agent might be defined separately if used independently
# search_agent = ToolCallingAgent(
#     tools=[WebSearchTool(), VisitWebpageTool()], 
#     model=model,
#     # ... other params from youtube.py
# )

# youtube_agent = ToolCallingAgent(
#     tools=[YouTubeVideoSearchTool(), YouTubeVideoTranscriptTool(), WebSearchTool(), VisitWebpageTool()],
#     model=model,
#     name="youtube_agent",
#     # ... other params from youtube.py ...
#     description=(
#         "This agent is specialized for YouTube. It can search for YouTube videos... and fetch the timed transcript..."
#     )
# )

# # SummarizationAgent is removed

# manager_agent = CodeAgent(
#     tools=[], # Manager might not directly use tools if all are in youtube_agent
#     model=model,
#     managed_agents=[youtube_agent], # Manages only youtube_agent
#     # ... other params from youtube.py ...
#     description="A manager agent that can orchestrate YouTube video processing and summarize content...",
#     system_prompt="""You are a helpful AI assistant and manager...
#     Your primary goal is to process user requests related to YouTube videos (searching, transcribing, summarizing).
#     You have a specialized 'youtube_agent' at your disposal.

#     Workflow:
#     1.  Understand the user's request carefully.
#     2.  If the user provides a direct YouTube video URL or ID, instruct 'youtube_agent' to use 'YouTubeVideoTranscriptTool' to get the transcript.
#     3.  If the user asks to find videos on a topic:
        a.  Determine appropriate search keywords. You might need to refine the user's query.
        b.  [Optional] If you need broader context to formulate better YouTube search terms, you can instruct 'youtube_agent' to use its 'WebSearchTool'.
        c.  Instruct 'youtube_agent' to use 'YouTubeVideoSearchTool' with the keywords.
#     4.  Review the search results from 'youtube_agent'. Select the most relevant video(s). You might need to ask the user for clarification if multiple good options exist or if results are ambiguous.
#     5.  Instruct 'youtube_agent' to use 'YouTubeVideoTranscriptTool' to get the transcript for the selected video(s).
#     6.  Once you have the transcript (which will be a JSON string of timed segments), you need to parse it and then create a concise and informative summary of the video content.
#     7.  Present the summary to the user. Also, provide the URL of the YouTube video that was summarized.
#     8.  If the initial summary is not satisfactory, or if the search did not yield good results, try to adapt: refine search keywords, pick a different video from previous search results, or adjust your summarization approach.
#     9.  Communicate clearly with the user throughout the process, especially if you need choices or feedback.
#     """
# )

# --- Main Execution Logic ---
# if __name__ == "__main__":
#     user_request = "请总结关于'AI最新进展'的YouTube视频，并附上链接。"
#     print(f"User Request: {user_request}")
#     # result = manager_agent.run(user_request) # Or the direct run command in youtube.py
#     # print(result)

```

## 4. 依赖和配置

*   **Python Libraries**: `requests` is essential for API calls. Ensure `smolagents` and its dependencies are installed. Remove mentions of `youtube-search-python` and `youtube-transcript-api` as direct dependencies if using RapidAPI.
*   **API Keys**: A `RAPIDAPI_KEY` environment variable is required for the `youtube-media-downloader.p.rapidapi.com` service used by the tools.
*   **LLM API Keys**: Ensure LLM (e.g., LiteLLM, Vertex AI) API keys and configurations are correctly set in `.env` or as per `youtube.py` setup.

## 5. 下一步

1.  在 `examples/youtube.py` 中实际编写 `YouTubeVideoSearchTool` 和 `YouTubeVideoTranscriptTool` 类的 `forward` 方法。
2.  仔细调整 `ManagerAgent` 的 `system_prompt` 以优化其行为和输出质量。
3.  进行全面的测试，使用 `thinking/youtube_video_summarizer_agent.md` 中定义的测试用例。 