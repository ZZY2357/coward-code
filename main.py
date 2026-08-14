from openai import OpenAI
import os
import json
import subprocess
from rich import print
from rich.markdown import Markdown
from rich.panel import Panel

# 配置模型
config = {}

if os.path.exists('model.json'):
    with open('model.json', 'r') as f:
        config = json.load(f)
else:
    config['base_url'] = input('请输入 base url：')
    config['api_key'] = input('请输入 api key：')
    config['model'] = input('请输入模型：')
    with open('model.json', 'w') as f:
        json.dump(config, f)

tools = [
    {
        'type': 'function',
        'function': {
            'name': 'read',
            'description': 'Read a text file',
            'parameters': {
                'type': 'object',
                'properties': {
                    'path': {
                        'type': 'string',
                        'description': 'File path'
                    }
                },
                'required': ['path'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'write',
            'description': 'Write a new text file',
            'parameters': {
                'type': 'object',
                'properties': {
                    'path': {
                        'type': 'string',
                        'description': 'File path'
                    },
                    'content': {
                        'type': 'string',
                        'description': 'Content'
                    },
                },
                'required': ['path', 'content'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'bash',
            'description': 'Execute a bash command.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'command': {
                        'type': 'string',
                        'description': 'Command'
                    }
                },
                'required': ['command'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'edit',
            'description': 'Edit multiple files',
            'parameters': {
                'type': 'object',
                'properties': {
                    'path': {
                        'type': 'string',
                        'description': 'Path to the file to edit'
                    },
                    'edits': {
                        'type': 'array',
                        'description': 'One or more targeted replacements',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'old': {
                                    'type':
                                        'string',
                                    'description':
                                        'Exact text for one targeted replacement',
                                },
                                'new': {
                                    'type':
                                        'string',
                                    'description':
                                        'Replacement text for this targeted edit',
                                },
                            },
                            'required': ['old', 'new'],
                        },
                    },
                },
                'required': ['path', 'edits'],
            }
        },
    },
]


def read(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f'Failed to read: { e }'


def write(path, content):
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return 'OK'
    except Exception as e:
        return f'Failed to write: { e }'


def bash(command):
    try:
        result = subprocess.run(
            ['pwsh', '-Command', command],
            shell=True,
            capture_output=True, # 捕获输出，而不是直接打印到屏幕上
            text=True # 文本而不是字节
        )
        return f'stdout:\n{ result.stdout }\nstderr:\n{ result.stderr }'
    except Exception as e:
        return f'Failed to execute: { e }'


def edit(path, edits):
    try:
        content = read(path)
        for edit in edits:
            old = edit['old']
            new = edit['new']
            if old not in content:
                return f'"{ old }" not found in { path }'
            content = content.replace(old, new)

        write_result = write(path, content)
        if write_result != 'OK':
            return write_result
        return 'OK'
    except Exception as e:
        return f'Failed to edit: { e }'


TOOL_CALL_MAP = {'read': read, 'write': write, 'bash': bash, 'edit': edit}

messages = [{
    'role': 'system',
    'content': 'You are a useful assistant running in Coward Code.'
}]

client = OpenAI(api_key=config['api_key'], base_url=config['base_url'])

print(Panel('Welcome to Coward Code!', subtitle='Made by zzy2357.'))

while True:
    user_input = input('> ')
    if user_input.startswith('/quit'):
        break
    messages.append({'role': 'user', 'content': user_input})

    # 循环处理工具调用
    while True:
        response = client.chat.completions.create(
            model=config['model'],
            messages=messages,
            tools=tools,
            reasoning_effort="high",
            extra_body={"thinking": {
                "type": "enabled"
            }},
        )

        messages.append(response.choices[0].message)
        reasoning_content = response.choices[0].message.reasoning_content
        content = response.choices[0].message.content
        tool_calls = response.choices[0].message.tool_calls

        if reasoning_content:
            print(f'[italic grey42]Thinking: { reasoning_content }[/italic grey42]'[:200], flush=True)
        if content:
            print(Markdown(content), flush=True)

        if tool_calls is None:
            break
        for tool in tool_calls:
            tool_function = TOOL_CALL_MAP[tool.function.name]
            tool_result = tool_function(**json.loads(tool.function.arguments))
            print(f"[grey42]{ tool.function.name }: { tool_result }[/grey42]"[:20])
            messages.append({
                "role": "tool",
                "tool_call_id": tool.id,
                "content": tool_result,
            })
