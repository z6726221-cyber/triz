"""一次性迁移：为39个工程参数预计算embedding并存入数据库。

用法: python scripts/migrate_embeddings.py
"""
import sys
import json
sys.path.insert(0, '.')

import sqlite3
from triz_pipeline.config import DB_PATH


def migrate():
    print(f"数据库路径: {DB_PATH}")

    # 1. 加载模型
    print("加载 sentence-transformers 模型...")
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2", local_files_only=True)
    print(f"模型加载完成，维度: {model.get_sentence_embedding_dimension()}")

    # 2. 读取参数
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, name_cn, description FROM parameters ORDER BY id")
    params = cursor.fetchall()
    print(f"读取到 {len(params)} 个参数")

    # 3. 计算 embedding 并更新
    updated = 0
    for pid, name, name_cn, desc in params:
        text = f"{name} {name_cn} {desc}"
        embedding = model.encode(text).tolist()
        embedding_json = json.dumps(embedding)

        cursor.execute(
            "UPDATE parameters SET embedding_json = ? WHERE id = ?",
            (embedding_json, pid)
        )
        updated += 1
        print(f"  [{pid:2d}] {name_cn}: 维度 {len(embedding)}")

    conn.commit()

    # 4. 验证
    cursor.execute("SELECT id, embedding_json FROM parameters ORDER BY id")
    rows = cursor.fetchall()
    verified = 0
    for pid, emb_json in rows:
        assert emb_json is not None, f"参数 {pid} embedding 为空"
        emb = json.loads(emb_json)
        assert len(emb) == 384, f"参数 {pid} 维度错误: {len(emb)}"
        verified += 1

    conn.close()
    print(f"\n完成！更新 {updated} 个参数，验证通过 {verified} 个")


if __name__ == "__main__":
    migrate()
