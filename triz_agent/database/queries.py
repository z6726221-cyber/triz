"""数据库查询接口"""
import sqlite3
import json
from typing import Optional, List
from triz_agent.config import DB_PATH


def _get_conn():
    return sqlite3.connect(DB_PATH)


def get_parameter_by_id(param_id: int) -> Optional[dict]:
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, name_cn, description FROM parameters WHERE id = ?", (param_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"id": row[0], "name": row[1], "name_cn": row[2], "description": row[3]}
    return None


def get_all_parameters() -> List[dict]:
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, name_cn, description, embedding_json FROM parameters ORDER BY id")
    rows = cursor.fetchall()
    conn.close()
    result = []
    for r in rows:
        d = {"id": r[0], "name": r[1], "name_cn": r[2], "description": r[3]}
        if r[4]:
            d["embedding"] = json.loads(r[4])
        result.append(d)
    return result


def query_parameters_by_similarity(keyword: str) -> List[dict]:
    """基于关键词模糊查询参数"""
    conn = _get_conn()
    cursor = conn.cursor()
    like_pattern = f"%{keyword}%"
    cursor.execute(
        "SELECT id, name, name_cn, description FROM parameters WHERE name LIKE ? OR name_cn LIKE ? OR description LIKE ? ORDER BY id",
        (like_pattern, like_pattern, like_pattern)
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "name_cn": r[2], "description": r[3]} for r in rows]


def get_matrix_principles(improve_param: int, worsen_param: int) -> List[int]:
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT principles FROM matrix WHERE improve_param = ? AND worsen_param = ?",
        (improve_param, worsen_param)
    )
    row = cursor.fetchone()
    conn.close()
    if row and row[0]:
        return json.loads(row[0])
    return []


def get_separation_principles_by_type(sep_type: str) -> List[int]:
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT principles FROM separation_rules WHERE type = ?", (sep_type,))
    row = cursor.fetchone()
    conn.close()
    if row and row[0]:
        return json.loads(row[0])
    return []


def get_all_separation_types() -> List[dict]:
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, type, condition, principles FROM separation_rules")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "type": r[1], "condition": r[2], "principles": json.loads(r[3])} for r in rows]


def query_cases(principle_ids: List[int], function: str = "", limit: int = 10) -> List[dict]:
    conn = _get_conn()
    cursor = conn.cursor()
    placeholders = ",".join("?" * len(principle_ids))
    sql = f"SELECT principle_id, function, context, source, title, description FROM cases WHERE principle_id IN ({placeholders})"
    params = list(principle_ids)
    if function:
        sql += " AND function LIKE ?"
        params.append(f"%{function}%")
    sql += f" LIMIT {limit}"
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()
    return [{"principle_id": r[0], "function": r[1], "context": r[2], "source": r[3], "title": r[4], "description": r[5]} for r in rows]
