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
    config['shell'] = input('请选择 shell(bash/pwsh/powershell)[bash]：')
    if config['shell'].strip() == '':
        config['shell'] = 'bash'
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
            [config['shell'], '-c', command],  # 交给 shell 解析，支持 ls -la 这类带参数命令
            capture_output=True, # 捕获输出，而不是直接打印到屏幕上
            text=True, # 文本而不是字节
            encoding='utf-8',
            errors='replace' # 解码失败不抛异常（输出可能混 GBK/UTF-8）
        )
        output = result.stdout + result.stderr
        return output if output.strip() else '(no output)'
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
    'content': f'You are a useful assistant running in Coward Code. Your shell environment is { config["shell"] }.'
}]

client = OpenAI(api_key=config['api_key'], base_url=config['base_url'])

print(Panel(f'Model: { config["model"] }\nShell: { config["shell"] }', title='Welcome to Coward Code!', subtitle='Made by zzy2357.'))

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
            stream=True,
            reasoning_effort="high",
            extra_body={"thinking": {
                "type": "enabled"
            }},
        )

        # 流式累积 delta：thinking 即时打印，content / tool_calls 拼完整再处理
        reasoning_content = ""
        content = ""
        tool_calls = []  # 按 delta.tool_calls 的 index 对齐
        for chunk in response:
            if not chunk.choices:
                continue  # 末尾 usage 空块
            delta = chunk.choices[0].delta
            rc = getattr(delta, 'reasoning_content', None)  # DeepSeek 扩展字段，SDK 的 ChoiceDelta 未声明
            if rc:
                reasoning_content += rc
                print(rc, end='', flush=True)
            if delta.content:
                content += delta.content
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    while len(tool_calls) <= tc.index:
                        tool_calls.append({'id': '', 'type': 'function', 'function': {'name': '', 'arguments': ''}})
                    entry = tool_calls[tc.index]
                    if tc.id:
                        entry['id'] = tc.id
                    if tc.function:
                        if tc.function.name:
                            entry['function']['name'] = tc.function.name
                        if tc.function.arguments:
                            entry['function']['arguments'] += tc.function.arguments

        if reasoning_content:
            print(flush=True)  # 收尾 thinking 行
        if content:
            print(Markdown(content), flush=True)

        assistant_msg = {'role': 'assistant', 'content': content or None}
        if tool_calls:
            assistant_msg['tool_calls'] = tool_calls
            # 文档要求：带 tools 的请求必须回传 reasoning_content，否则 API 400
            assistant_msg['reasoning_content'] = reasoning_content
        if content or tool_calls:
            messages.append(assistant_msg)  # 无工具调用时不回传 reasoning_content

        if not tool_calls:
            break
        for tool in tool_calls:
            fn = tool['function']
            args = json.loads(fn['arguments'])
            tool_function = TOOL_CALL_MAP[fn['name']]
            tool_result = tool_function(**args)
            body = tool_result
            if len(body) > 2000:
                body = body[:2000] + '\n...'
            header = f"$ { args['command'] }" if fn['name'] == 'bash' else fn['name']
            print(f"[grey42]{ header }\n{ body }[/grey42]")
            messages.append({
                "role": "tool",
                "tool_call_id": tool['id'],
                "content": tool_result,
            })
