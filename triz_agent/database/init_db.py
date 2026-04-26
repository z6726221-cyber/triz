"""数据库初始化：建表、插入TRIZ标准数据"""

import sqlite3
import json
from pathlib import Path
from triz_agent.config import DB_PATH, DATA_DIR
from triz_agent.database.triz_data import (
    get_parameters,
    get_principles,
    get_separation_rules,
    MATRIX,
)


def ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def init_database():
    ensure_data_dir()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS parameters (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            name_cn TEXT NOT NULL,
            description TEXT NOT NULL,
            embedding_json TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS principles (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            name_cn TEXT NOT NULL,
            description TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS matrix (
            improve_param INTEGER,
            worsen_param INTEGER,
            principles TEXT,
            PRIMARY KEY (improve_param, worsen_param)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS separation_rules (
            id INTEGER PRIMARY KEY,
            type TEXT NOT NULL,
            condition TEXT NOT NULL,
            principles TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cases (
            id INTEGER PRIMARY KEY,
            principle_id INTEGER,
            function TEXT NOT NULL,
            context TEXT,
            source TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL
        )
    """)

    cursor.execute("SELECT COUNT(*) FROM parameters")
    if cursor.fetchone()[0] == 0:
        for p in get_parameters():
            cursor.execute(
                "INSERT INTO parameters (id, name, name_cn, description, embedding_json) VALUES (?, ?, ?, ?, ?)",
                (p["id"], p["name"], p["name_cn"], p["description"], None),
            )

    cursor.execute("SELECT COUNT(*) FROM principles")
    if cursor.fetchone()[0] == 0:
        for p in get_principles():
            cursor.execute(
                "INSERT INTO principles (id, name, name_cn, description) VALUES (?, ?, ?, ?)",
                (p["id"], p["name"], p["name_cn"], p["description"]),
            )

    cursor.execute("SELECT COUNT(*) FROM matrix")
    if cursor.fetchone()[0] == 0:
        for (imp, wor), prins in MATRIX.items():
            cursor.execute(
                "INSERT INTO matrix (improve_param, worsen_param, principles) VALUES (?, ?, ?)",
                (imp, wor, json.dumps(prins)),
            )

    cursor.execute("SELECT COUNT(*) FROM separation_rules")
    if cursor.fetchone()[0] == 0:
        for r in get_separation_rules():
            cursor.execute(
                "INSERT INTO separation_rules (id, type, condition, principles) VALUES (?, ?, ?, ?)",
                (r["id"], r["type"], r["condition"], json.dumps(r["principles"])),
            )

    cursor.execute("SELECT COUNT(*) FROM cases")
    if cursor.fetchone()[0] == 0:
        sample_cases = [
            (
                15,
                "切割",
                "医疗",
                "本地库",
                "手术刀动态压力调节",
                "根据组织密度实时调整刀片接触压力",
            ),
            (
                28,
                "切割",
                "医疗",
                "本地库",
                "超声波手术刀",
                "使用超声波振动代替机械切割",
            ),
            (
                1,
                "固定",
                "医疗",
                "本地库",
                "可拆卸手术支架",
                "将支架分成多个独立部分便于取出",
            ),
            (
                35,
                "加热",
                "航天",
                "本地库",
                "航天器温控涂层",
                "根据日照角度改变涂层颜色调节温度",
            ),
            (
                14,
                "支撑",
                "汽车",
                "本地库",
                "F1赛车悬挂",
                "用曲面结构分散冲击力提高强度",
            ),
        ]
        for case in sample_cases:
            cursor.execute(
                "INSERT INTO cases (principle_id, function, context, source, title, description) VALUES (?, ?, ?, ?, ?, ?)",
                case,
            )

    conn.commit()
    conn.close()
    return DB_PATH
