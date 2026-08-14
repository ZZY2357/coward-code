# Coward Code 🐤

> 教学项目：手写一个简单的 Claude Code / Cursor 式终端 AI 编程助手。

一个用 **Python + OpenAI SDK + DeepSeek** 从零实现的命令行 AI Agent。核心只有 200 行代码，却实现了 Claude Code 最精髓的能力——**让模型自主调用工具（读文件 / 写文件 / 执行命令 / 修改代码）并循环执行**。

名字叫 *Coward*（胆小鬼），是因为它只敢做最基础的事：模型说一步，它做一步——但教学的目的正是拆掉黑盒，让你看清 Agent 的每一步。

---

## ✨ 功能特性

- 💬 终端交互式对话，支持 Markdown 渲染（rich）
- 🛠️ 四个内置工具：`read` / `write` / `bash` / `edit`
- 🔁 完整的工具调用循环：模型请求工具 → 本地执行 → 结果回填 → 继续推理，直到给出最终答案
- 🧠 支持 DeepSeek 的推理过程（reasoning_content）实时展示
- ⚙️ 模型配置外置，可切换任意 OpenAI 兼容接口

## 📦 依赖

- Python 3.10+
- [openai](https://pypi.org/project/openai/)
- [rich](https://pypi.org/project/rich/)

```bash
pip install openai rich
```

## 🚀 快速开始

### 1. 配置模型

在项目根目录创建 `model.json`（已加入 `.gitignore`，不会提交）：

```json
{
    "base_url": "https://api.deepseek.com",
    "api_key": "sk-你的key",
    "model": "deepseek-chat"
}
```

如果不存在该文件，首次运行会交互式询问你输入三项配置。

> ⚠️ 安全提醒：`api_key` 是敏感信息，请勿提交到 Git 或分享给他人。生产环境建议改用环境变量。

### 2. 运行

```bash
python main.py
```

看到欢迎面板后即可对话，例如：

```
> 帮我看看当前目录有哪些文件
> 新建一个 hello.py，打印 "Hello, Coward!"
> 用 bash 运行一下 hello.py
> /quit   # 退出
```

## 🧠 工作原理：Agent 的核心循环

Claude Code 的本质是一个 **「模型 + 工具 + 循环」** 的 Agent。本项目完整复现了这个模式：

```
┌─────────────────────────────────────────────────────────────┐
│                     Agent 主循环（while True）                │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────▼─────────────────────┐
        │   1. 把完整对话历史 + 工具定义发给模型        │
        │      messages + tools                      │
        └─────────────────────┬─────────────────────┘
                              │
        ┌─────────────────────▼─────────────────────┐
        │   2. 模型返回：                             │
        │      ・普通文本回复  → 打印，结束本轮         │
        │      ・tool_calls    → 解析出工具名和参数    │
        └─────────────────────┬─────────────────────┘
                              │
        ┌─────────────────────▼─────────────────────┐
        │   3. 本地执行工具（read/write/bash/edit）   │
        │      把结果转成字符串                        │
        └─────────────────────┬─────────────────────┘
                              │
        ┌─────────────────────▼─────────────────────┐
        │   4. 把工具结果以 role="tool" 回填给模型     │
        │      带着新信息重新走第 1 步                │
        └─────────────────────┬─────────────────────┘
                              │
             直到模型不再请求工具 → 本轮对话结束
```

### 关键代码解读

**工具定义（JSON Schema）**——告诉模型"你能用什么"：

```python
tools = [{
    'type': 'function',
    'function': {
        'name': 'read',
        'description': 'Read a text file',
        'parameters': {...},  # 参数 schema
    },
}]
```

**执行分发**——模型返回的工具调用，映射到本地函数：

```python
TOOL_CALL_MAP = {'read': read, 'write': write, 'bash': bash, 'edit': edit}
...
for tool in tool_calls:
    result = TOOL_CALL_MAP[tool.function.name](**json.loads(tool.function.arguments))
    messages.append({"role": "tool", "tool_call_id": tool.id, "content": result})
```

**循环终止条件**——模型不再返回 `tool_calls` 时，本轮结束：

```python
if tool_calls is None:
    break
```

## 📁 项目结构

```
coward-code/
├── main.py          # 全部代码：配置、工具定义、Agent 主循环（约 200 行）
├── model.json       # 模型配置（已 gitignore，需自行创建）
├── .gitignore
└── README.md
```

## 🔒 安全注意

- `bash` 工具会直接执行模型生成的命令——**请只在自己信任的模型和环境中使用**
- 本项目刻意保持极简，未做沙箱/白名单/权限控制，仅适合学习演示

## 🎯 扩展思路（留给你的作业）

- 增加 `glob` / `grep` 等只读工具
- 用环境变量替代 `model.json` 存放 API key
- 会话历史持久化（保存/恢复对话）
- 限制 `bash` 命令白名单，防止危险操作
- 支持多轮任务拆解与计划展示

---

**Made with 🐤 by ZZY2357** — 学习 Agent 原理，从自己手写一个开始。
