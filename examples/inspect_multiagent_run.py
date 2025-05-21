from openinference.instrumentation.smolagents import SmolagentsInstrumentor
from phoenix.otel import register
from smolagents.models import LiteLLMModel
import os
from dotenv import load_dotenv

load_dotenv()

register()
SmolagentsInstrumentor().instrument(skip_dep_check=True)

from smolagents import (
    CodeAgent,
    ToolCallingAgent,
    VisitWebpageTool,
    WebSearchTool,
)

# Then we run the agentic part!
# model = InferenceClientModel()
model = LiteLLMModel(
    model_id="openai/qwen3-235b-a22b",  
    api_base=os.getenv("ALI_BASE_URL"),
    api_key=os.getenv("ALI_API_KEY"),
    provider="openai",
    enable_thinking=False,
)

search_agent = ToolCallingAgent(
    tools=[WebSearchTool(), VisitWebpageTool()],
    model=model,
    name="search_agent",
    description="This is an agent that can do web search.",
)

manager_agent = CodeAgent(
    tools=[],
    model=model,
    managed_agents=[search_agent],
)
manager_agent.run("查看youtube上的视频，告诉我红杉资本在2025年AI闭门会都说了哪些重要观点??")
