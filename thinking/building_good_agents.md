# 如何构建高质量的代理系统

在人工智能领域，基于大语言模型(LLM)的代理系统正变得越来越重要。然而，构建一个真正有效的代理系统与创建一个勉强运行的系统之间存在巨大差距。本指南将介绍构建高质量代理的最佳实践。

## 目录

- [简化工作流程](#简化工作流程)
- [改善信息流向LLM引擎](#改善信息流向LLM引擎)
- [向代理提供更多参数](#向代理提供更多参数)
- [调试代理系统](#调试代理系统)
  - [使用更强大的LLM](#使用更强大的LLM)
  - [提供更多指导](#提供更多指导)
  - [更改系统提示](#更改系统提示)
  - [启用额外规划](#启用额外规划)

## 简化工作流程

**最好的代理系统是最简单的系统**。给LLM在工作流程中引入自主能力会带来错误风险。尽管设计良好的代理系统会有错误日志和重试机制，但为了最大限度地降低LLM错误风险，应该简化工作流程。

### 关键原则：尽可能减少LLM调用次数

实施方法：

1. **整合多个工具**：将多个相关工具整合为一个。例如，不要让代理分别调用"旅行距离API"和"天气API"，而应创建一个统一的`return_spot_information`工具，一次性调用两个API并返回合并结果。

2. **尽可能基于确定性函数而非代理决策**：减少依赖LLM判断的场景，增加基于明确逻辑的处理流程。

这种简化不仅能降低成本和延迟，还能显著减少错误风险。

## 改善信息流向LLM引擎

要理解LLM引擎就像一个被困在房间里的智能机器人，与外界唯一的沟通方式是通过门缝传递纸条。如果你不显式地将信息放入提示中，它就不会知道发生了什么。

### 改进方法

1. **明确任务指令**：由于代理由LLM驱动，任务描述的微小变化可能导致完全不同的结果。确保任务描述清晰明确。

2. **优化工具的信息输出**：每个工具都应记录（通过在工具的`forward`方法中使用简单的`print`语句）对LLM引擎有用的所有信息，特别是详细记录工具执行错误。

### 工具设计示例

以下是一个获取天气数据的工具的两个版本对比：

#### 不良实现

```python
import datetime
from smolagents import tool

def get_weather_report_at_coordinates(coordinates, date_time):
    # 模拟函数，返回[温度(°C), 降雨概率(0-1), 波浪高度(m)]
    return [28.0, 0.35, 0.85]

def convert_location_to_coordinates(location):
    # 返回虚拟坐标
    return [3.3, -42.0]

@tool
def get_weather_api(location: str, date_time: str) -> str:
    """
    返回天气报告。

    Args:
        location: 你想要获取天气的地方名称。
        date_time: 你想要获取报告的日期和时间。
    """
    lon, lat = convert_location_to_coordinates(location)
    date_time = datetime.strptime(date_time)
    return str(get_weather_report_at_coordinates((lon, lat), date_time))
```

这个实现存在以下问题：
- 没有说明`date_time`应使用的格式
- 没有详细说明如何指定位置
- 没有处理位置格式不正确或日期时间格式不正确的失败情况
- 输出格式难以理解

#### 更好的实现

```python
@tool
def get_weather_api(location: str, date_time: str) -> str:
    """
    返回天气报告。

    Args:
        location: 你想要获取天气的地方名称。应该是地名，可能后跟城市名，然后是国家，例如"Anchor Point, Taghazout, Morocco"。
        date_time: 你想要获取报告的日期和时间，格式为'%m/%d/%y %H:%M:%S'。
    """
    lon, lat = convert_location_to_coordinates(location)
    try:
        date_time = datetime.strptime(date_time)
    except Exception as e:
        raise ValueError("将`date_time`转换为datetime格式失败，请确保提供格式为'%m/%d/%y %H:%M:%S'的字符串。完整追踪:" + str(e))
    temperature_celsius, risk_of_rain, wave_height = get_weather_report_at_coordinates((lon, lat), date_time)
    return f"位置{location}在{date_time}的天气报告：温度将为{temperature_celsius}°C，降雨概率为{risk_of_rain*100:.0f}%，波浪高度为{wave_height}m。"
```

这个改进版本有：
- 详细的位置格式说明
- 明确的日期时间格式要求
- 错误处理和有用的错误信息
- 格式化的、易于阅读的输出结果

一般来说，为了减轻LLM的负担，可以问自己："如果我第一次使用这个工具，编程并纠正错误会容易吗？"

## 向代理提供更多参数

除了描述任务的简单字符串外，你可能需要向代理传递其他对象。可以使用`additional_args`参数传递任何类型的对象：

```python
from smolagents import CodeAgent, InferenceClientModel

model_id = "meta-llama/Llama-3.3-70B-Instruct"

agent = CodeAgent(tools=[], model=InferenceClientModel(model_id=model_id), add_base_tools=True)

agent.run(
    "为什么Mike在纽约认识的人不多？",
    additional_args={"mp3_sound_file_url":'https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/transformers/recording.mp3'}
)
```

你可以使用`additional_args`参数传递希望代理利用的图像、字符串或其他信息。

## 调试代理系统

### 使用更强大的LLM

在代理工作流程中，有些错误是真正的错误，而另一些则是由于LLM引擎推理不当造成的。如果你的代理表现不佳，尝试使用更强大的LLM模型可能会有所改善。

### 提供更多指导

确保向代理提供充分、明确的指导和相关信息。如果代理在某些任务上表现不佳，考虑是否需要提供更多上下文或更详细的指令。

### 更改系统提示

尽管通常不建议这样做，但在某些情况下，可以修改系统提示以改变代理的行为：

```python
agent.prompt_templates["system_prompt"] = agent.prompt_templates["system_prompt"] + "\n这是额外的指令！"
```

系统提示中可以使用以下占位符：

* 插入工具描述：
```
{%- for tool in tools.values() %}
- {{ tool.name }}: {{ tool.description }}
    Takes inputs: {{tool.inputs}}
    Returns an output of type: {{tool.output_type}}
{%- endfor %}
```

* 插入托管代理的描述：
```
{%- if managed_agents and managed_agents.values() | list %}
You can also give tasks to team members.
Calling a team member works the same as for calling a tool: simply, the only argument you can give in the call is 'task', a long string explaining your task.
Given that this team member is a real human, you should be very verbose in your task.
Here is a list of the team members that you can call:
{%- for agent in managed_agents.values() %}
- {{ agent.name }}: {{ agent.description }}
{%- endfor %}
{%- endif %}
```

* 对于`CodeAgent`，插入授权导入的列表：`"{{authorized_imports}}"`

### 启用额外规划

可以启用额外的规划步骤，让代理在正常操作步骤之间定期运行规划：

```python
from smolagents import load_tool, CodeAgent, InferenceClientModel, WebSearchTool
from dotenv import load_dotenv

load_dotenv()

# 从Hub导入工具
image_generation_tool = load_tool("m-ric/text-to-image", trust_remote_code=True)

search_tool = WebSearchTool()

agent = CodeAgent(
    tools=[search_tool, image_generation_tool],
    model=InferenceClientModel(model_id="Qwen/Qwen2.5-72B-Instruct"),
    planning_interval=3  # 在这里激活规划！
)

# 运行代理
result = agent.run(
    "一只全速奔跑的猎豹需要多长时间才能跑完亚历山大三世桥的长度？",
)
```

在规划步骤中，不进行工具调用，LLM只是被要求更新它所知道的事实列表，并基于这些事实反思接下来应该采取什么步骤。

## 结论

构建高质量代理系统是一个复杂而微妙的过程。通过简化工作流程、改善信息流、提供充分的参数和有效的调试，可以显著提高代理系统的性能和可靠性。记住，最好的系统往往是最简单的那些，能够以清晰、可预测的方式完成任务。 