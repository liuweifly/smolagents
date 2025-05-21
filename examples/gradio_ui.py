import os
from dotenv import load_dotenv

from smolagents import CodeAgent, GradioUI, InferenceClientModel
from smolagents.models import LiteLLMModel
load_dotenv()

model = LiteLLMModel(
    model_id="openai/qwen3-235b-a22b",  # Using qwen-plus as a more stable option
    api_base=os.getenv("ALI_BASE_URL"),
    api_key=os.getenv("ALI_API_KEY"),
    provider="openai",
    enable_thinking=False,
)

agent = CodeAgent(
    tools=[],
    model=model,
    verbosity_level=1,
    planning_interval=3,
    name="example_agent",
    description="This is an example agent.",
    step_callbacks=[],
    additional_authorized_imports=["PyPDF2"]

)

GradioUI(agent, file_upload_folder="./data").launch()
