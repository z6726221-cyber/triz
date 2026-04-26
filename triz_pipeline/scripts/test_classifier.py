import json
from triz_pipeline.tools.input_classifier import classify_input

tests = [
    ("greeting", "你好"),
    ("greeting", "在吗"),
    ("greeting", "我有一个问题"),
    ("unclear", "asdfghjkl"),
    ("invalid", "123456"),
    ("non_engineering", "今天天气怎么样"),
    ("non_engineering", "如何追女朋友"),
    ("engineering", "如何提高手术刀片耐用性"),
    ("engineering", "汽车发动机噪音大"),
    ("non_engineering", "床前明月光疑是地上霜举头望明月低头思故乡"),
]

for expected, text in tests:
    result = classify_input(text)
    ok = result["category"] == expected or (
        expected == "engineering" and result["proceed"]
    )
    status = "OK" if ok else "FAIL:" + result["category"]
    print(f'{status}: [{expected}] {text[:20]}... proceed={result["proceed"]}')
