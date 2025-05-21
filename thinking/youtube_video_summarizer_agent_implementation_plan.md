# YouTube 视频内容总结 Agent - 基于 `youtube.py` 的实现方案

此文档概述了在 `examples/youtube.py` 现有框架基础上，实现 YouTube 视频内容总结 Agent 的步骤和代码结构变更。

## 1. 目标回顾

构建一个能够根据用户输入，搜索 YouTube 视频，获取其转录文本，进行总结，并返回总结内容和视频链接的 Agent 系统。

## 2. 主要修改和新增组件

### 2.1. 新增工具类 (Tool Classes)

在 `examples/youtube.py` 中定义以下新工具：

*   **`YouTubeVideoSearchTool(Tool)`**
    *   `name`: "YouTubeVideoSearchTool"
    *   `description`: 用于根据关键词搜索 YouTube 视频。
    *   `execute(query: str, max_results: int = 5) -> List[Dict[str, str]]`:
        *   输入: 搜索查询字符串，最大结果数。
        *   输出: 视频列表，每个视频包含 `title` 和 `url` (以及可选的 `snippet`, `channel_title`, `publish_time`)。
        *   实现: 调用 YouTube Data API v3 或使用 `youtube-search-python` 等库。

*   **`YouTubeVideoTranscriptTool(Tool)`**
    *   `name`: "YouTubeVideoTranscriptTool"
    *   `description`: 用于获取指定 YouTube 视频的文本转录。
    *   `extract_video_id(video_url: str) -> Optional[str]`: 辅助方法，从 URL 中提取 video ID。
    *   `execute(video_url: str, language_preference: List[str] = ['en', 'zh-CN']) -> str`:
        *   输入: YouTube 视频的完整 URL，偏好的字幕语言列表。
        *   输出: 视频转录文本字符串，或错误信息。
        *   实现: 使用 `youtube-transcript-api` 或 `yt-dlp` 等库。

### 2.2. 新增 Agent 实例

*   **`youtube_agent = ToolCallingAgent(...)`**
    *   `tools`: `[YouTubeVideoSearchTool(), YouTubeVideoTranscriptTool()]`
    *   `model`: 复用 `youtube.py` 中的 `model` 实例。
    *   `name`: "youtube_agent"
    *   `description`: "This agent can search for YouTube videos and get their transcripts."

*   **`summarization_agent = CodeAgent(...)`**
    *   `model`: 复用 `youtube.py` 中的 `model` 实例。
    *   `name`: "summarization_agent"
    *   `description`: "This agent takes text as input and provides a summary."
    *   `system_prompt`: (可选，但推荐) 定制化，以指导其进行高质量的文本/转录总结。
        *   例如: "You are an expert summarizer. Given a text, provide a concise and informative summary. Focus on the key points and main topic. If the text is a video transcript, identify the main arguments or narrative."

### 2.3. 修改现有 `ManagerAgent`

*   **`managed_agents`**: 更新列表，加入 `youtube_agent` 和 `summarization_agent`。
    *   `managed_agents=[search_agent, youtube_agent, summarization_agent]`
*   **`system_prompt`**: **关键修改**。需要详细指导 `ManagerAgent` 如何协调新的子 Agent 来完成 YouTube 视频总结任务。Prompt 应包含清晰的工作流程，参考 `thinking/youtube_video_summarizer_agent.md` 中的流程描述。
    *   **示例 Prompt 核心逻辑**:
        1.  理解用户请求。
        2.  可选：若需上下文，用 `search_agent`。
        3.  用 `youtube_agent.YouTubeVideoSearchTool` 找视频。
        4.  分析结果，选视频。
        5.  用 `youtube_agent.YouTubeVideoTranscriptTool` 获取转录。
        6.  将转录给 `summarization_agent` 总结。
        7.  评估总结，不满意则迭代 (换关键词、换视频、调整总结要求)。
        8.  返回总结和视频 URL。
        9.  处理用户直接提供视频链接的情况。

## 3. 代码结构示例 (`examples/youtube.py` 内)

```python
# --- Imports ---
# from smolagents import BaseTool, ToolCallingAgent, CodeAgent
# from smolagents.models import LiteLLMModel # or InferenceClientModel
# from typing import List, Dict, Optional
# # Potentially: from youtube_search import YoutubeSearch
# # Potentially: from youtube_transcript_api import YouTubeTranscriptApi
# import os
# from dotenv import load_dotenv

# load_dotenv()
# register() # from phoenix
# SmolagentsInstrumentor().instrument(skip_dep_check=True)

# --- Tool Definitions ---
# class YouTubeVideoSearchTool(BaseTool):
#     name: str = "YouTubeVideoSearchTool"
#     description: str = "Searches YouTube for videos..."
#     def execute(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
#         print(f"Executing YouTubeVideoSearchTool with query: {query}")
#         # ... placeholder or actual implementation ...
#         return [{"title": f"Mock Video for '{query}'", "url": "https://youtube.com/mock"}]

# class YouTubeVideoTranscriptTool(BaseTool):
#     name: str = "YouTubeVideoTranscriptTool"
#     description: str = "Fetches transcript for a YouTube video URL..."
#     def extract_video_id(self, video_url: str) -> Optional[str]:
#         # ... implementation ...
#         if "watch?v=" in video_url: return video_url.split("watch?v=")[1].split("&")[0]
#         return None
#     def execute(self, video_url: str, language_preference: List[str] = ['en']) -> str:
#         video_id = self.extract_video_id(video_url)
#         print(f"Executing YouTubeVideoTranscriptTool for URL: {video_url}, ID: {video_id}")
#         # ... placeholder or actual implementation ...
#         return f"Mock transcript for video ID {video_id}"

# --- Model Definition (reuse existing) ---
# model = LiteLLMModel(...)

# --- Agent Definitions ---
# search_agent = ToolCallingAgent(...) # Existing

# youtube_agent = ToolCallingAgent(
#     tools=[YouTubeVideoSearchTool(), YouTubeVideoTranscriptTool()],
#     model=model,
#     name="youtube_agent",
#     description="This agent can search YouTube and get video transcripts."
# )

# summarization_agent = CodeAgent(
#     model=model,
#     name="summarization_agent",
#     description="This agent summarizes text.",
#     system_prompt="You are an expert summarizer..."
# )

# manager_agent = CodeAgent(
#     tools=[],
#     model=model,
#     managed_agents=[search_agent, youtube_agent, summarization_agent],
#     system_prompt="""You are a helpful AI assistant...
#     Workflow:
#     1. Understand user request for YouTube summary.
#     2. [Optional] Use search_agent for context.
#     3. Use youtube_agent.YouTubeVideoSearchTool to find videos.
#     4. Select video(s).
#     5. Use youtube_agent.YouTubeVideoTranscriptTool for transcript.
#     6. Pass transcript to summarization_agent.
#     7. Iterate if needed.
#     8. Return summary and video URL(s).
#     """
# )

# --- Main Execution Logic ---
# user_request = "请总结关于'AI最新进展'的YouTube视频，并附上链接。"
# print(f"User Request: {user_request}")
# manager_agent.run(user_request)

```

## 4. 依赖和配置

*   **Python Libraries**: 根据工具的具体实现，可能需要安装 `youtube-search-python`, `youtube-transcript-api` 等。这些应添加到项目的依赖管理中 (如 `requirements.txt`)。
*   **API Keys**: 如果 `YouTubeVideoSearchTool` 使用 YouTube Data API v3，需要获取并配置 API Key (推荐使用环境变量)。
*   **LLM API Keys**: 确保 `LiteLLMModel` 或其他模型客户端所需的 API 密钥已在 `.env` 文件中正确配置。

## 5. 下一步

1.  在 `examples/youtube.py` 中实际编写 `YouTubeVideoSearchTool` 和 `YouTubeVideoTranscriptTool` 类的 `execute` 方法。
2.  仔细调整 `ManagerAgent` 和 `SummarizationAgent` 的 `system_prompt` 以优化其行为和输出质量。
3.  进行全面的测试，使用 `thinking/youtube_video_summarizer_agent.md` 中定义的测试用例。 