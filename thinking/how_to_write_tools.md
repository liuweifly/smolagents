# 如何在smolagents中编写工具

在smolagents框架中，工具(Tool)是代理(Agent)与外部环境交互的能力扩展，能够让LLM执行API调用、网络搜索、文件处理等各种任务。本教程将详细介绍如何使用不同方式创建工具。

## 目录

- [工具的基本概念](#工具的基本概念)
- [使用@tool装饰器创建简单工具](#使用tool装饰器创建简单工具)
- [通过继承Tool类创建复杂工具](#通过继承tool类创建复杂工具)
- [选择合适的创建方式](#选择合适的创建方式)
- [常见错误和改进示例](#常见错误和改进示例)
- [向代理传递额外参数](#向代理传递额外参数)
- [将工具分享到Hub](#将工具分享到hub)
- [导入和使用工具](#导入和使用工具)
- [最佳实践](#最佳实践)

## 工具的基本概念

工具的本质是一个带有元数据的函数，这些元数据帮助LLM理解如何调用它：

- **名称**：描述工具的功能
- **描述**：帮助LLM理解该工具的用途
- **输入参数**：包括类型和描述
- **输出类型**：返回值的类型

smolagents提供了两种创建工具的方式：使用`@tool`装饰器和继承`Tool`类。

## 使用@tool装饰器创建简单工具

`@tool`装饰器是创建简单工具的推荐方式，它允许你将任何Python函数转换成一个工具。

### 基本示例

```python
from smolagents import tool

@tool
def convert_currency(amount: float, from_currency: str, to_currency: str) -> str:
    """
    将指定金额从一种货币转换为另一种货币。
    
    Args:
        amount: 要转换的金额
        from_currency: 源货币代码(例如 'USD')
        to_currency: 目标货币代码(例如 'EUR')
        
    Returns:
        str: 描述转换后金额的字符串，或转换失败的错误信息
    """
    # 实现货币转换逻辑
    # ...
    converted_amount = amount * exchange_rate
    return f"{amount} {from_currency} 相当于 {converted_amount} {to_currency}"
```

### 关键要点

1. **类型提示**：始终为参数和返回值提供准确的类型提示
2. **文档字符串**：编写详细的文档字符串，描述功能、参数和返回值
3. **参数命名**：使用清晰、描述性的参数名称
4. **错误处理**：妥善处理可能的异常，返回有意义的错误信息

## 通过继承Tool类创建复杂工具

对于更复杂的工具，或需要维护状态的工具，可以通过继承`Tool`类来实现。

### 基本示例

```python
from smolagents import Tool

class SearchInformationTool(Tool):
    name = "web_search"
    description = "执行网络搜索查询并返回搜索结果"
    inputs = {
        "query": {
            "type": "string", 
            "description": "要执行的网络搜索查询"
        },
        "filter_year": {
            "type": "string",
            "description": "[可选参数]: 筛选特定年份的搜索结果",
            "nullable": True
        }
    }
    output_type = "string"

    def __init__(self, browser):
        super().__init__()
        self.browser = browser  # 保存状态

    def forward(self, query: str, filter_year: int | None = None) -> str:
        # 实现搜索逻辑
        # ...
        return search_results
```

### 关键要点

1. **类属性**：直接在类中定义`name`、`description`、`inputs`和`output_type`
2. **初始化方法**：可以在`__init__`中保存状态或依赖项
3. **forward方法**：实现工具的主要逻辑，参数要与inputs定义匹配
4. **状态管理**：可以在类的不同方法之间共享状态

## 选择合适的创建方式

选择哪种方式主要取决于工具的复杂性和状态管理需求：

| 特点 | @tool装饰器 | 继承Tool类 |
|------|------------|-----------|
| 复杂度 | 简单、无状态功能 | 复杂功能或需要状态管理 |
| 代码量 | 少 | 较多 |
| 多方法支持 | 不支持 | 支持多个相关方法 |
| 状态管理 | 有限 | 灵活 |
| 推荐场景 | 简单API调用、计算等 | 浏览器操作、文件处理等 |

## 常见错误和改进示例

以下是一个获取位置天气数据的工具示例，展示了常见的错误以及如何改进。

### 存在问题的实现

```python
import datetime
from smolagents import tool

def get_weather_report_at_coordinates(coordinates, date_time):
    # Dummy function, returns a list of [Temperature in °C, risk of rain on a scale 0-1, wind speed in m/s]
    return [28.0, 0.35, 0.85]

def convert_location_to_coordinates(location):
    # Returns dummy coordinates
    return [3.3, -42.0]

@tool
def get_weather_api(location: str, date_time: str) -> str:
    """
    Returns the weather report.
    
    Args:
        location: the name of the place that you want the weather for.
        date_time: the date and time for which you want the report.
    """
    lon, lat = convert_location_to_coordinates(location)
    date_time = datetime.strptime(date_time)
    return str(get_weather_report_at_coordinates((lon, lat), date_time))
```

这个实现存在以下问题：

- 对于应该用于`date_time`的格式没有精确说明
- 对于如何指定位置没有详细说明
- 没有处理机制处理日期格式错误的情况，如果位置格式不正确或日期时间格式不正确
- 输出格式难以理解

### 改进后的实现

```python
@tool
def get_weather_api(location: str, date_time: str) -> str:
    """
    Returns the weather report.
    
    Args:
        location: the name of the place that you want the weather for. Should be a place name like "New York" or "Paris".
        date_time: the date and time for which you want the report, formatted as 'MM/DD/YY'.
    """
    try:
        lon, lat = convert_location_to_coordinates(location)
        date_time = datetime.strptime(date_time)
    except Exception as e:
        raise ValueError(f"Conversion of 'date_time' to datetime format failed, make sure to follow 'MM/DD/YY' format: {e}")
    
    temperature_celsius, risk_of_rain, wind_speed = get_weather_report_at_coordinates((lon, lat), date_time)
    return f"Weather report for {location}, {date_time}: Temperature will be {temperature_celsius}°C, with {risk_of_rain*100}% chance of rain and wind speed of {wind_speed}m/s"
```

改进的版本包含：

1. 更详细的参数说明（指定了位置应该是城市名称）
2. 明确指定了日期格式
3. 添加了错误处理，提供有用的错误信息
4. 提供了格式化的、易于阅读的输出结果

## 向代理传递额外参数

在使用代理时，你可能需要传递一些额外信息给工具，但不想通过普通的会话输入传递。这时可以使用`additional_args`参数：

```python
from smolagents import CodeAgent, InferenceClientModel

model_id = "meta-llama/llama-3.3-70B-Instruct"

agent = CodeAgent(tools=[], model=InferenceClientModel(model_id=model_id), add_base_tools=True)

agent.run(
    "Why does Mike not know many people in New York?",
    additional_args={"mp3_sound_file_url":"https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/transformers/tasks/tts_example.wav"}
)
```

使用`additional_args`参数可以传递任何类型的额外信息，例如文件URL、配置信息或其他上下文，以便你的工具能够利用这些信息执行任务。

## 将工具分享到Hub

你可以将自定义工具分享到Hugging Face Hub：

```python
my_tool.push_to_hub("username/tool-name", token="YOUR_HF_TOKEN")
```

要使推送成功，你的工具需要遵循一些规则：

1. 所有方法应该是自包含的，仅使用来自参数的变量
2. 所有导入应直接定义在工具的函数内
3. 如果重写`__init__`方法，不应有除`self`之外的参数

## 导入和使用工具

### 导入自定义工具

```python
from smolagents import load_tool

my_tool = load_tool("username/tool-name", trust_remote_code=True)
```

### 在代理中使用工具

```python
from smolagents import CodeAgent, InferenceClientModel

model = InferenceClientModel()
agent = CodeAgent(
    tools=[my_tool1, my_tool2, my_tool3],
    model=model
)

agent.run("使用相应的工具执行某个任务...")
```

## 最佳实践

1. **详细描述**：为工具提供清晰、详细的描述和参数说明
2. **错误处理**：妥善处理异常，返回有用的错误信息
3. **安全性**：避免未经过滤的用户输入直接传递到系统命令中
4. **输入验证**：验证输入参数，防止错误的参数格式
5. **命名一致性**：使用一致的命名约定，使LLM更容易理解工具功能

一般来说，为了减轻你的LLM的负担，一个好的问题是："如果我是个傻瓜，第一次使用这个工具，使用这个工具编程并知道自己的错误会容易吗？"

通过遵循这些指南，你可以创建强大、可靠的工具，显著增强代理的能力。 