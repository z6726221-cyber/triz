"""输入分类器：在 M1 之前判断问题类型，过滤非工程输入。"""
import json
import re

from triz_pipeline.utils.api_client import OpenAIClient

# ---------------------------------------------------------------------------
# 第一层：打招呼/寒暄 关键词
# ---------------------------------------------------------------------------
_GREETING_PATTERNS = [
    r"^(你好|在吗|在么|有人吗|哈喽|嗨|hi|hello|hey)\s*[!.。]?\s*$",
    r"^(您好|早上好|下午好|晚上好)\s*[!.。]?\s*$",
    r"^(老师|专家|助手|小哥|小姐姐)\s*[好]?\s*$",
    r"^(我有一个问题|想问一下|请教一下|咨询一下|问个问题)\s*$",
    r"^(能问个问题吗|可以问个问题吗|能帮我个忙吗)\s*$",
]

_GREETING_RESPONSE = (
    "你好！我是 TRIZ 智能系统，专门帮助解决工程技术矛盾。"
    "请直接描述你遇到的技术问题，例如：「如何提高手术刀片的耐用性」。"
)

# ---------------------------------------------------------------------------
# 第二层：无效输入检测
# ---------------------------------------------------------------------------
_INVALID_RESPONSE = "请输入一个具体的技术问题描述。"

# 明显的非工程关键词（第三层快速拦截）
_NON_ENGINEERING_KEYWORDS = [
    "天气", "温度", "下雨", "下雪", "晴天", "阴天",
    "女朋友", "男朋友", "追", "恋爱", "分手", "结婚", "离婚",
    "减肥", "增肥", "健身", "美容", "化妆", "穿搭",
    "做饭", "做菜", "烘焙", "食谱", "美食", "好吃",
    "股票", "基金", "彩票", "赌博", "投资", "赚钱",
    "心情", "情绪", "抑郁", "焦虑", "压力", "开心",
    "考试", "分数", "成绩", "挂科", "考研", "高考",
    "小说", "电影", "音乐", "游戏", "旅游", "风景",
    "星座", "运势", "塔罗", "算命", "风水",
    "宠物", "猫", "狗", "养鱼", "养花",
    "法律", "合同", "纠纷", "赔偿", "律师",
]

_NON_ENG_RESPONSE_TEMPLATE = (
    "您的问题「{question}」不涉及工程技术矛盾，TRIZ 方法可能无法提供有效帮助。"
    "请描述一个具体的技术问题，例如：「如何提高手术刀片的耐用性」。"
)

# 明显的工程关键词（快速放行，不调用 LLM）
_ENGINEERING_KEYWORDS = [
    "耐用", "磨损", "强度", "硬度", "韧性", "腐蚀", "疲劳",
    "效率", "损耗", "能耗", "功耗", "散热", "噪音", "振动",
    "精度", "误差", "偏差", "间隙", "公差",
    "断裂", "变形", "裂纹", "泄漏", "堵塞", "卡死",
    "老化", "氧化", "退化", "失效", "故障",
    "成本", "重量", "体积", "尺寸", "速度", "压力",
    "结构", "材料", "工艺", "焊接", "铸造", "锻造",
    "电路", "信号", "电磁", "干扰", "延迟", "带宽",
    "手术", "医疗", "器械", "植入", "药物", "靶向",
    "电池", "充电", "续航", "电机", "发动机", "轴承",
]


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _is_greeting(text: str) -> bool:
    """检测是否是打招呼/寒暄。"""
    t = text.strip().lower()
    for pattern in _GREETING_PATTERNS:
        if re.match(pattern, t, re.IGNORECASE):
            return True
    return False


def _is_invalid_input(text: str) -> bool:
    """检测是否是无效输入（空、emoji、纯数字、纯乱码）。"""
    t = text.strip()
    if len(t) < 3:
        return True
    # 纯数字
    if t.isdigit():
        return True
    # 纯 emoji（去除所有非 emoji 字符后为空）
    # 简单判断：如果只有 Unicode emoji 范围内的字符
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"  # dingbats
        "\U0001F900-\U0001F9FF"  # supplemental symbols
        "\U0001FA00-\U0001FA6F"  # chess symbols
        "\U0001FA70-\U0001FAFF"  # symbols and pictographs extended-a
        "]+",
        flags=re.UNICODE,
    )
    remaining = emoji_pattern.sub("", t).strip()
    if not remaining:
        return True
    # 纯乱码：无中文字符且无常见英文单词，且字符熵高
    has_chinese = bool(re.search(r"[一-鿿]", t))
    has_english_word = bool(re.search(r"[a-zA-Z]{2,}", t))
    if not has_chinese and not has_english_word:
        # 检查是否全是重复字符（如 "aaaaa"）
        unique_chars = len(set(t.lower()))
        if unique_chars <= 3:
            return True
    return False


def _has_keyword(text: str, keywords: list[str]) -> bool:
    """检查文本是否包含关键词列表中的词。"""
    t = text.lower()
    for kw in keywords:
        if kw.lower() in t:
            return True
    return False


# ---------------------------------------------------------------------------
# 第三层：LLM 语义分类
# ---------------------------------------------------------------------------

_LLM_SYSTEM_PROMPT = """你是工程技术问题分类器。

将用户输入分类为以下之一：
- non_engineering: 非工程技术问题（天气、情感、数学计算、健康咨询、烹饪、生活琐事、法律等）
- engineering: 工程技术问题（涉及具体的技术、设备、材料、工艺、结构、性能参数等矛盾）
- unclear: 无法判断

判断标准：
- 是否包含具体的技术对象（如设备、材料、结构）？
- 是否涉及性能参数的冲突（如既要轻又要强）？
- 是否可以通过工程技术手段解决？

只输出 JSON，不要其他内容：
{"category": "non_engineering|engineering|unclear", "confidence": "high|medium|low"}"""


def _llm_classify(text: str) -> dict:
    """调用 LLM 进行语义分类。"""
    client = OpenAIClient()
    prompt = f'问题："{text}"\n\n请分类：'
    try:
        response = client.chat(
            prompt=prompt,
            system_prompt=_LLM_SYSTEM_PROMPT,
            temperature=0.1,
        )
        data = json.loads(response.strip())
        return {
            "category": data.get("category", "unclear"),
            "confidence": data.get("confidence", "low"),
        }
    except (json.JSONDecodeError, Exception):
        # LLM 调用失败时，保守处理：放过
        return {"category": "unclear", "confidence": "low"}


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def classify_input(text: str) -> dict:
    """分类用户输入，返回决策结果。

    Returns:
        {
            "category": "greeting|invalid|non_engineering|engineering",
            "proceed": True/False,
            "response": "用户提示消息（如果不 proceed）",
        }
    """
    # 第一层：打招呼
    if _is_greeting(text):
        return {
            "category": "greeting",
            "proceed": False,
            "response": _GREETING_RESPONSE,
        }

    # 第二层：无效输入
    if _is_invalid_input(text):
        return {
            "category": "invalid",
            "proceed": False,
            "response": _INVALID_RESPONSE,
        }

    # 快速关键词检查
    if _has_keyword(text, _NON_ENGINEERING_KEYWORDS):
        return {
            "category": "non_engineering",
            "proceed": False,
            "response": _NON_ENG_RESPONSE_TEMPLATE.format(question=text),
        }

    if _has_keyword(text, _ENGINEERING_KEYWORDS):
        return {
            "category": "engineering",
            "proceed": True,
            "response": None,
        }

    # 第三层：LLM 语义分类
    result = _llm_classify(text)
    category = result.get("category", "unclear")
    confidence = result.get("confidence", "low")

    if category == "non_engineering" and confidence == "high":
        return {
            "category": "non_engineering",
            "proceed": False,
            "response": _NON_ENG_RESPONSE_TEMPLATE.format(question=text),
        }

    # 其他情况（engineering / unclear / confidence 不高）→ 放过
    return {
        "category": category,
        "proceed": True,
        "response": None,
    }
