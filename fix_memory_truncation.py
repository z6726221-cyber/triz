"""修复 agent.py 中的内存截断逻辑（P3-18）和拼写错误。"""
import re

filepath = "D:/code/triz/triz_agent/agent/agent.py"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# 定位并替换内存显示部分
old_code = (
    '        lines.append("")\n'
    '        lines.append("=== 已完成的分析（详细）===")\n'
    '\n'
    '        # 展示完整的 Skill Markdown 输出\n'
    '        for mem in self.memory:\n'
    '            if mem.get("role") == "assitant":\n'
    '                lines.append(f"\\n### 执行了 {mem.get(\'skill\', \'unknown\')}")\n'
    '                lines.append(f"思考: {mem.get(\'thought\', \'\')}")\n'
    '            elif mem.get("role") == "system" and "skill_result" in mem:\n'
    '                lines.append(f"\\n#### {mem[\'skill_result\']} 输出：")\n'
    '                lines.append(mem["content"])\n'
    '            elif mem.get("role") == "system" and "tool_result" in mem:\n'
    '                lines.append(f"\\n#### {mem[\'tool_result\']} 输出：")\n'
    '                lines.append(mem["content"])\n'
    '            elif mem.get("role") == "system" and "content" in mem:\n'
    '                lines.append(f"\\n> {mem[\'content\']}")\n'
)

new_code = (
    '        lines.append("")\n'
    '        lines.append("=== 已完成的分析（详细）===")\n'
    '\n'
    '        # 展示 Skill/Tool 输出，对超长内容做截断\n'
    '        MAX_CONTENT_LEN = 800\n'
    '        MAX_MEMORY_ITEMS = 15\n'
    '        memory_to_show = self.memory[-MAX_MEMORY_ITEMS:] if len(self.memory) > MAX_MEMORY_ITEMS else self.memory\n'
    '        if len(self.memory) > MAX_MEMORY_ITEMS:\n'
    '            lines.append(f"\\n...(较早的 {len(self.memory) - MAX_MEMORY_ITEMS} 条记忆已折叠，仅展示最近 {MAX_MEMORY_ITEMS} 条)")\n'
    '\n'
    '        for mem in memory_to_show:\n'
    '            if mem.get("role") == "assistant":\n'
    '                lines.append(f"\\n### 执行了 {mem.get(\'skill\', \'unknown\')}")\n'
    '                thought = mem.get("thought", "")\n'
    '                if len(thought) > 200:\n'
    '                    thought = thought[:200] + "...(思考已截断)"\n'
    '                lines.append(f"思考: {thought}")\n'
    '            elif mem.get("role") == "system" and "skill_result" in mem:\n'
    '                lines.append(f"\\n#### {mem[\'skill_result\']} 输出：")\n'
    '                content = str(mem["content"])\n'
    '                if len(content) > MAX_CONTENT_LEN:\n'
    '                    content = content[:MAX_CONTENT_LEN] + f"...(已截断，共 {len(mem[\'content\'])} 字)"\n'
    '                lines.append(content)\n'
    '            elif mem.get("role") == "system" and "tool_result" in mem:\n'
    '                lines.append(f"\\n#### {mem[\'tool_result\']} 输出：")\n'
    '                content = str(mem["content"])\n'
    '                if len(content) > MAX_CONTENT_LEN:\n'
    '                    content = content[:MAX_CONTENT_LEN] + f"...(已截断，共 {len(mem[\'content\'])} 字)"\n'
    '                lines.append(content)\n'
    '            elif mem.get("role") == "system" and "content" in mem:\n'
    '                content = str(mem["content"])\n'
    '                if len(content) > 300:\n'
    '                    content = content[:300] + "...(已截断)"\n'
    '                lines.append(f"\\n> {content}")\n'
)

if old_code in content:
    content = content.replace(old_code, new_code, 1)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print("P3-18 修复完成：内存截断逻辑已写入，同时修复了 'assitant' 拼写错误。")
else:
    print("未找到匹配内容，尝试用正则方式...")
    # 用正则匹配（更宽松）
    pattern = r'(\s+)# 展示完整的 Skill Markdown 输出.*?elif mem\.get\("role"\) == "system" and "content" in mem:.*?lines\.append\(f"\\n> \{mem\[\'content\'\]}"\)'
    match = re.search(pattern, content, re.DOTALL)
    if match:
        indent = match.group(1)
        replacement = (
            f'{indent}# 展示 Skill/Tool 输出，对超长内容做截断\n'
            f'{indent}MAX_CONTENT_LEN = 800\n'
            f'{indent}MAX_MEMORY_ITEMS = 15\n'
            f'{indent}memory_to_show = self.memory[-MAX_MEMORY_ITEMS:] if len(self.memory) > MAX_MEMORY_ITEMS else self.memory\n'
            f'{indent}if len(self.memory) > MAX_MEMORY_ITEMS:\n'
            f'{indent}    lines.append(f"\\n...(较早的 {{len(self.memory) - MAX_MEMORY_ITEMS}} 条记忆已折叠，仅展示最近 {{MAX_MEMORY_ITEMS}} 条)")\n'
            f'\n'
            f'{indent}for mem in memory_to_show:\n'
            f'{indent}    if mem.get("role") == "assistant":\n'
            f'{indent}        lines.append(f"\\n### 执行了 {{mem.get(\'skill\', \'unknown\')}}")\n'
            f'{indent}        thought = mem.get("thought", "")\n'
            f'{indent}        if len(thought) > 200:\n'
            f'{indent}            thought = thought[:200] + "...(思考已截断)"\n'
            f'{indent}        lines.append(f"思考: {{thought}}")\n'
            f'{indent}    elif mem.get("role") == "system" and "skill_result" in mem:\n'
            f'{indent}        lines.append(f"\\n#### {{{{mem[\'skill_result\']}}}} 输出：")\n'
            f'{indent}        content = str(mem["content"])\n'
            f'{indent}        if len(content) > MAX_CONTENT_LEN:\n'
            f'{indent}            content = content[:MAX_CONTENT_LEN] + f"...(已截断，共 {{len(mem[\'content\'])}} 字)"\n'
            f'{indent}        lines.append(content)\n'
            f'{indent}    elif mem.get("role") == "system" and "tool_result" in mem:\n'
            f'{indent}        lines.append(f"\\n#### {{{{mem[\'tool_result\']}}}} 输出：")\n'
            f'{indent}        content = str(mem["content"])\n'
            f'{indent}        if len(content) > MAX_CONTENT_LEN:\n'
            f'{indent}            content = content[:MAX_CONTENT_LEN] + f"...(已截断，共 {{len(mem[\'content\'])}} 字)"\n'
            f'{indent}        lines.append(content)\n'
            f'{indent}    elif mem.get("role") == "system" and "content" in mem:\n'
            f'{indent}        content = str(mem["content"])\n'
            f'{indent}        if len(content) > 300:\n'
            f'{indent}            content = content[:300] + "...(已截断)"\n'
            f'{indent}        lines.append(f"\\n> {{content}}")\n'
        )
        # 正则替换太复杂，直接报错
        print("正则方式也不够精确，请手动检查。")
    else:
        print("正则未匹配到内容。")
