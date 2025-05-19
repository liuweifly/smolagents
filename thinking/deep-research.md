下面是对 `examples/open_deep_research` 文件夹代码的解读和梳理：

---

## 1. 这个文件夹的定位

该目录是 HuggingFace 团队对 OpenAI Deep Research Agent 的开源复现，目标是实现类似的“深度研究”智能体，能自动完成复杂的开放式研究类问题（如 GAIA benchmark），并支持多模态（文本+图片）推理、网页浏览、文件分析等能力。

---

## 2. 主要内容和结构

- `README.md`：说明了项目目标、依赖安装、环境变量配置、用法（如如何运行主脚本）、数据处理细节等。
- `requirements.txt`：列出运行所需的 Python 依赖。
- `run.py`：**主入口脚本**，命令行接收问题，构建智能体，自动调用多种工具和子智能体，最终输出答案。
- `run_gaia.py`：用于在 GAIA benchmark 上批量评测，自动加载数据集、运行 agent 并记录结果。
- `analysis.ipynb`、`visual_vs_text_browser.ipynb`：Jupyter 分析/对比实验用 notebook。
- `app.py`：极简的 web app 启动脚本。
- `scripts/`：**核心工具和子模块**，如文本网页浏览器、视觉问答、文件处理、工具集成等。

---

## 3. 关键代码解读

### 3.1 主入口 run.py

- 解析命令行参数（问题、模型ID）。
- 构建一个“管理型”智能体（manager_agent），其下可调用：
  - 文本网页浏览子智能体（text_webbrowser_agent）：具备网页搜索、访问、滚动、查找、归档、文本分析等工具。
  - 视觉问答工具（visualizer）：对图片进行理解和问答。
  - 文本分析工具（TextInspectorTool）：对文本内容做进一步分析。
- 支持多模型（如 OpenAI o1、LiteLLM）。
- 通过 `agent.run(question)` 自动完成多步推理、工具调用，最终输出答案。

### 3.2 scripts/text_web_browser.py

- 实现了一个极简文本网页浏览器（SimpleTextBrowser），支持：
  - 访问网页、滚动页面、查找关键词、归档快照、下载文件等。
  - 通过一系列 Tool 封装成可被 agent 调用的“动作”，如 VisitTool、PageUpTool、FinderTool、ArchiveSearchTool 等。
  - 支持 Google/Serper API 搜索。
- 设计目的是让 agent 能像人一样“浏览网页”，并能自动化操作和提取信息。

### 3.3 scripts/visual_qa.py

- 实现了视觉问答工具（VisualQATool/visualizer）：
  - 支持对本地图片或下载图片进行问题回答（如图片描述、细节提问等）。
  - 可调用 HuggingFace 的 Idefics2-8b-chatty 或 OpenAI gpt-4o 进行多模态推理。
  - 自动处理图片编码、缩放、API请求等细节。

### 3.4 其他脚本

- `text_inspector_tool.py`：对网页或文件中的文本内容做进一步分析（如提取、摘要、查找等）。
- `gaia_scorer.py`：GAIA benchmark 评测相关。
- `mdconvert.py`：多种文件格式转 markdown，便于 agent 统一处理。
- `reformulator.py`：问题重写、改写相关工具。
- `cookies.py`：浏览器 cookies 管理。

---

## 4. 典型工作流

1. 用户输入一个复杂问题（如“2007年前 Mercedes Sosa 发行了多少张录音室专辑？”）。
2. agent 自动调用网页搜索、访问、滚动、查找、归档、文件下载、文本分析、视觉问答等工具，分步推理，逐步获取和整合信息。
3. agent 可以调用子 agent（如 text_webbrowser_agent）专门负责网页浏览任务，主 agent 负责全局规划和最终答案整合。
4. 支持多模态输入（如遇到 PDF、图片等，自动截图、转图片、再用视觉问答工具分析）。
5. 最终输出结构化答案。

---

## 5. 总结

- 该目录是一个“多工具、多智能体协作”的复杂 agent 复现方案，核心是自动化“深度研究”任务。
- 代码结构清晰，分为主流程（run.py）、工具/子模块（scripts/）、分析/评测（notebook、run_gaia.py）。
- 重点在于如何将网页浏览、文件处理、视觉问答等能力集成到一个可自动推理的 agent 体系中。

---

如果你想了解某个具体脚本或工具的详细用法/原理，可以指定文件名，我可以进一步详细解读！
