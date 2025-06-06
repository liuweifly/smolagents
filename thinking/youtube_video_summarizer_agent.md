# YouTube 视频内容总结 Agent 实现思路

## 1. 核心目标

构建一个能够根据用户输入，搜索 YouTube 视频，转录内容，并进行总结的 Agent 系统。Agent 应能返回总结文本和视频链接。

## 2. Agent 架构

采用多 Agent 协作模式：

*   **Manager Agent (主控 Agent)**:
    *   类型: `CodeAgent`
    *   职责: 接收用户指令，协调子 Agent 工作，进行逻辑判断、信息综合、执行总结和迭代控制，最终向用户返回结果。
*   **Search Agent (通用搜索 Agent)**:
    *   类型: `ToolCallingAgent`
    *   职责: 执行通用网页搜索，为 YouTube 搜索提供上下文或优化关键词。(此 Agent 在当前 `youtube.py` 中独立运行，不直接被 ManagerAgent 管理，但其功能概念可被 YouTube Agent 内部工具替代或由 ManagerAgent 指挥 YouTube Agent 使用其搜索工具)。
    *   工具: `WebSearchTool`, `VisitWebpageTool` (复用现有工具)。
*   **YouTube Agent (YouTube 视频处理 Agent)**:
    *   类型: `ToolCallingAgent`
    *   职责: 负责 YouTube 视频的搜索、内容转录，并可辅助进行通用网页搜索以优化 YouTube 搜索策略或获取上下文。
    *   工具:
        *   `YouTubeVideoSearchTool` (新创建)
        *   `YouTubeVideoTranscriptTool` (新创建)
        *   `WebSearchTool` (复用现有工具)
        *   `VisitWebpageTool` (复用现有工具)
*   **Summarization Agent (总结 Agent)**:
    *   **此 Agent 已被移除。总结功能将由 Manager Agent 直接处理，或通过其内部逻辑实现，不再设立独立的 Summarization Agent。**

## 3. 工作流程

1.  **用户输入**: 用户提出查询需求，例如"总结 XX 产品的用例"或"XX 发布会的新产品功能"。
2.  **[可选] 上下文获取**:
    *   Manager Agent 判断是否需要通过通用搜索获取更多背景信息，以辅助生成更精准的 YouTube 搜索词。
    *   若需要，指示 `YouTube Agent` 使用其配备的 `WebSearchTool` 执行搜索**，或 Manager Agent 自行规划调用独立的 `Search Agent`（如果流程设计如此）。
3.  **YouTube 搜索词制定**: Manager Agent 结合用户原始输入及搜索结果（如果有），生成 YouTube 搜索关键词。
4.  **视频搜索**: Manager Agent 指示 YouTube Agent 使用 `YouTubeVideoSearchTool`，输入关键词，获取相关视频列表（包含标题、链接等）。
5.  **视频选择与转录**:
    *   Manager Agent 根据预设策略（如相关性、观看量、发布时间）或允许用户选择，从列表中选取一个或多个视频。
    *   指示 YouTube Agent 使用 `YouTubeVideoTranscriptTool` 获取选定视频的文本转录。
6.  **内容总结**: Manager Agent **直接对转录文本进行总结**。
7.  **结果评估与迭代**:
    *   Manager Agent 评估总结内容是否满足用户需求。
    *   **若不满足**:
        *   尝试用新的关键词组合重新执行步骤 3-6。
        *   选择视频列表中的其他视频重新执行步骤 5-6。
        *   提示用户当前结果，并询问是否需要调整搜索方向或关键词。
    *   **若满足**: 进入下一步。
8.  **结果返回**: Manager Agent 向用户展示总结的文本内容和对应的 YouTube 视频链接。

## 4. 关键工具设计 (概念)

### 4.1. `YouTubeVideoSearchTool`

*   **功能**: 根据文本关键词在 YouTube 上搜索视频。
*   **输入**:
    *   `query` (str): 搜索关键词。
    *   **`max_results` 参数已移除**: 最大返回结果数量在工具内部固定为 5。
*   **输出**: `str`: **包含视频信息列表的 JSON 字符串**。每个字典包含：
    *   `title` (str): 视频标题。
    *   `url` (str): 视频链接。
    *   `snippet` (str, optional): 视频简介或部分描述。
    *   `channel_title` (str, optional): 频道名称。
    *   `publish_time` (str, optional): 发布时间。
    *   `view_count` (str, optional): 观看次数文本。
    *   `lengthText` (str, optional): 视频时长文本。
    *   `thumbnail_url` (str, optional): 缩略图 URL。
    *   如果发生错误，返回包含错误信息的 JSON 字符串。
*   **实现要点**: 调用 **RapidAPI 的 `youtube-media-downloader` 服务** (具体端点为 `/v2/search/videos`)。

### 4.2. `YouTubeVideoTranscriptTool`

*   **功能**: 获取指定 YouTube **视频 ID** 的文本转录。
*   **输入**:
    *   `video_id` (str): **YouTube 视频的唯一 ID (例如 'dQw4w9WgXcQ')**。
    *   **`language_preference` 参数已移除**: 工具默认尝试获取英文 ('en') 字幕，如果不可用，则回退到第一个可用的字幕轨道。语言选择逻辑内置，不作为输入参数。
*   **输出**: `str`: **包含转录片段列表的 JSON 字符串**。每个片段包含 `start_time_secs` (起始时间，秒) 和 `text` (文本内容)。如果无法获取，返回包含错误信息的 JSON 字符串。
*   **实现要点**: 使用 **RapidAPI 的 `youtube-media-downloader` 服务** (具体端点为 `/v2/video/details` 获取字幕链接，然后下载并解析 **XML 格式的字幕文件**)。需要处理无字幕、获取字幕失败等情况。

## 5. Agent Prompting 关键点

*   **Manager Agent**:
    *   清晰定义其角色是协调者、决策者和总结者。
    *   指导其如何根据用户问题判断是否需要 `YouTube Agent` 使用其 `WebSearchTool` 进行通用搜索。
    *   指导其如何从 `YouTubeVideoSearchTool` 的结果中选择合适的视频进行转录（例如，优先考虑标题相关性、新近度）。
    *   指导其如何评估自身总结的输出质量，以及在不满意时如何调整策略（换关键词、换视频、调整总结要求）。
    *   明确输出格式（总结文本 + 视频链接）。
*   **Summarization Agent**: **此 Agent 已移除，相关 Prompting 指导不再需要。**

## 6. 迭代与优化

*   Agent 需要有明确的停止条件，例如达到满意的结果、达到最大迭代次数、或用户指示停止。
*   允许用户在迭代过程中提供反馈，以指导 Agent 的后续行为。
*   记录关键决策点和工具调用信息，方便调试和分析。

## 7. 错误处理

*   工具层面：确保 YouTube 工具能优雅处理 API 限制、视频不可用、无字幕等常见问题，并返回有意义的错误信息或状态。
*   Agent 层面：Manager Agent 需要能够理解子 Agent 或工具返回的错误，并据此调整计划（例如，如果一个视频转录失败，尝试列表中的下一个视频）。

## 8. 测试用例 (Use Cases)

### 8.1. 基础功能测试

*   **UC-BF-01: 特定主题视频总结**
    *   **用户输入**: "总结一下关于 Python 中异步编程的入门教程视频内容。"
    *   **预期行为**: Agent 搜索相关 YouTube 视频，选择一个合适的入门教程，转录并总结其核心概念和示例，返回总结文本和视频链接。
*   **UC-BF-02: 直接链接视频总结**
    *   **用户输入**: "帮我总结这个视频的内容：[特定 YouTube 视频链接]"
    *   **预期行为**: Agent 直接获取该链接视频的转录，并进行内容总结，返回总结文本和视频链接。
*   **UC-BF-03: 新闻事件总结**
    *   **用户输入**: "最近关于 AI 芯片发展有什么重要新闻？找个 YouTube 视频总结一下。"
    *   **预期行为**: Agent 搜索近期关于 AI 芯片发展的新闻类视频，选择一个信息量大的进行总结。

### 8.2. 迭代与优化测试

*   **UC-IO-01: 关键词优化与重新搜索**
    *   **用户输入**: "查找'最好的咖啡机'的评测视频并总结。"
    *   **初步搜索/总结**: 可能返回了一些广告或不相关的视频总结。
    *   **预期行为**: Agent (或在用户提示下) 意识到结果不佳，尝试优化关键词 (例如，"2024年浓缩咖啡机深度评测"，"手冲咖啡机对比")，重新搜索、转录和总结，直到找到更相关的评测内容。
*   **UC-IO-02: 用户反馈调整总结**
    *   **用户输入**: "总结一下这个关于'量子计算'的视频。"
    *   **初步总结**: Agent 返回了非常技术性的总结。
    *   **用户反馈**: "太复杂了，我需要一个更通俗易懂的解释，重点是它能做什么。"
    *   **预期行为**: Agent 根据反馈，重新指示 Summarization Agent 以更简单、面向应用的方式再次总结同一份转录文本。
*   **UC-IO-03: 多视频选择与比较提示**
    *   **用户输入**: "我想了解一下苹果 Vision Pro 的用户体验。"
    *   **预期行为**: Agent 找到多个评测视频，可能会先总结一个，然后提示用户："我还找到了另外几个关于 Vision Pro 体验的视频，您想继续了解其他视频的观点吗？"或者提供一个综合性的总结，并列出参考的视频链接。

### 8.3. 边界与错误处理测试

*   **UC-BE-01: 无相关视频**
    *   **用户输入**: "找一个关于'外星人如何使用吸尘器'的纪录片总结一下。"
    *   **预期行为**: Agent 搜索后，礼貌地告知用户未能找到相关主题的视频，或找到的视频不符合要求。
*   **UC-BE-02: 视频无字幕/转录失败**
    *   **用户输入**: "总结这个视频 [一个没有可用字幕的 YouTube 视频链接]"
    *   **预期行为**: Agent 尝试转录，失败后告知用户该视频无法获取文本内容，并询问是否需要搜索其他类似视频。
*   **UC-BE-03: API 错误或限制**
    *   **场景**: YouTube API 暂时不可用或达到速率限制。
    *   **预期行为**: Agent 捕获错误，并告知用户当前无法访问 YouTube 服务，建议稍后再试。

### 8.4. 特定需求测试

*   **UC-SN-01: 产品用例总结 (用户原始需求)**
    *   **用户输入**: "帮助我查询一下用户使用 Notion AI 的主要用例，找 YouTube 视频总结。"
    *   **预期行为**: Agent 搜索 Notion AI 用例相关的视频，转录并总结用户在实际场景中如何使用 Notion AI 解决问题或提高效率，返回用例总结和视频链接。
*   **UC-SN-02: 发布会内容总结 (用户原始需求)**
    *   **用户输入**: "OpenAI DevDay 2023 发布会上发布了哪些新产品和功能？找个视频总结一下。"
    *   **预期行为**: Agent 搜索 OpenAI DevDay 2023 的官方回顾或权威解读视频，转录并总结发布会的主要公告、新产品特性等，返回总结和视频链接。
*   **UC-SN-03: 特定信息提取**
    *   **用户输入**: "在这个关于'清洁能源转型'的访谈视频里 [链接]，专家提到了哪些主要的政策建议？"
    *   **预期行为**: Agent 转录视频后，Summarization Agent 的 Prompt 应引导其专注于提取与"政策建议"相关的内容进行总结。 