#!/usr/bin/env python3
"""
Project Memory API Client
Gerencia memória de projetos em PostgreSQL centralizado
Identifica projetos automaticamente via git repo + branch
"""

import json
import sys
import subprocess
import argparse
from datetime import datetime
from pathlib import Path

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print(json.dumps({"error": "psycopg2 não instalado. Execute: pip install psycopg2-binary"}))
    sys.exit(1)


def get_config():
    """Carrega configuração do arquivo config.json"""
    config_path = Path(__file__).parent.parent / "config.json"
    if not config_path.exists():
        return {"database_url": "postgresql://localhost:5432/sioux_project_memory"}

    with open(config_path) as f:
        return json.load(f)


def get_connection():
    """Conecta ao banco de dados"""
    config = get_config()
    return psycopg2.connect(config["database_url"])


def get_git_info():
    """Obtém repo e branch do diretório atual"""
    try:
        # Obter remote URL
        remote = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, check=True
        ).stdout.strip()

        # Normalizar URL (remover .git, https://, git@)
        repo = remote.replace("https://", "").replace("git@", "")
        repo = repo.replace(":", "/").replace(".git", "")

        # Obter branch atual
        branch = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True, text=True, check=True
        ).stdout.strip()

        return {"repo": repo, "branch": branch}
    except subprocess.CalledProcessError:
        return {"repo": "local", "branch": "unknown"}


def add_entry(entry_type, title, content, tags=None, priority="medium",
              related_files=None, created_by="claude"):
    """Adiciona nova entrada de memória"""
    git_info = get_git_info()

    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute("""
        INSERT INTO entries (git_repo, git_branch, type, title, content, priority, related_files, created_by)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (git_info["repo"], git_info["branch"], entry_type, title, content, priority, related_files, created_by))

    entry_id = cursor.fetchone()["id"]

    # Adicionar tags
    if tags:
        for tag in tags.split(","):
            tag = tag.strip()
            if tag:
                cursor.execute(
                    "INSERT INTO entry_tags (entry_id, tag) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (entry_id, tag)
                )

    conn.commit()
    conn.close()

    return {"status": "success", "id": str(entry_id), "repo": git_info["repo"], "branch": git_info["branch"]}


def search(query, limit=20, all_branches=False):
    """Busca textual usando Full-Text Search do PostgreSQL"""
    git_info = get_git_info()

    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    if all_branches:
        cursor.execute("""
            SELECT e.*, array_agg(t.tag) FILTER (WHERE t.tag IS NOT NULL) as tags,
                   ts_rank(search_vector, plainto_tsquery('portuguese', %s)) as rank
            FROM entries e
            LEFT JOIN entry_tags t ON e.id = t.entry_id
            WHERE e.git_repo = %s
              AND e.search_vector @@ plainto_tsquery('portuguese', %s)
              AND e.status = 'active'
            GROUP BY e.id
            ORDER BY rank DESC
            LIMIT %s
        """, (query, git_info["repo"], query, limit))
    else:
        cursor.execute("""
            SELECT e.*, array_agg(t.tag) FILTER (WHERE t.tag IS NOT NULL) as tags,
                   ts_rank(search_vector, plainto_tsquery('portuguese', %s)) as rank
            FROM entries e
            LEFT JOIN entry_tags t ON e.id = t.entry_id
            WHERE e.git_repo = %s AND e.git_branch = %s
              AND e.search_vector @@ plainto_tsquery('portuguese', %s)
              AND e.status = 'active'
            GROUP BY e.id
            ORDER BY rank DESC
            LIMIT %s
        """, (query, git_info["repo"], git_info["branch"], query, limit))

    results = cursor.fetchall()
    conn.close()

    return {"status": "success", "count": len(results), "entries": results,
            "repo": git_info["repo"], "branch": git_info["branch"]}


def list_entries(entry_type=None, tag=None, status="active", limit=50, all_branches=False):
    """Lista entradas com filtros"""
    git_info = get_git_info()

    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    if all_branches:
        query = """
            SELECT DISTINCT e.*, array_agg(t.tag) FILTER (WHERE t.tag IS NOT NULL) as tags
            FROM entries e
            LEFT JOIN entry_tags t ON e.id = t.entry_id
            WHERE e.git_repo = %s AND e.status = %s
        """
        params = [git_info["repo"], status]
    else:
        query = """
            SELECT DISTINCT e.*, array_agg(t.tag) FILTER (WHERE t.tag IS NOT NULL) as tags
            FROM entries e
            LEFT JOIN entry_tags t ON e.id = t.entry_id
            WHERE e.git_repo = %s AND e.git_branch = %s AND e.status = %s
        """
        params = [git_info["repo"], git_info["branch"], status]

    if entry_type:
        query += " AND e.type = %s"
        params.append(entry_type)

    if tag:
        query += " AND e.id IN (SELECT entry_id FROM entry_tags WHERE tag = %s)"
        params.append(tag)

    query += " GROUP BY e.id ORDER BY e.priority DESC, e.created_at DESC LIMIT %s"
    params.append(limit)

    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()

    return {"status": "success", "count": len(results), "entries": results,
            "repo": git_info["repo"], "branch": git_info["branch"]}


def get_todos():
    """Retorna TODOs pendentes ordenados por prioridade"""
    return list_entries(entry_type="todo", status="active")


def get_decisions():
    """Retorna decisões técnicas ativas"""
    return list_entries(entry_type="decision", status="active")


def get_context():
    """Retorna contexto do projeto"""
    return list_entries(entry_type="context", status="active")


def get_summary():
    """Retorna resumo do projeto para início de sessão"""
    git_info = get_git_info()

    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    # Contar por tipo
    cursor.execute("""
        SELECT type, COUNT(*) as count
        FROM entries
        WHERE git_repo = %s AND git_branch = %s AND status = 'active'
        GROUP BY type
    """, (git_info["repo"], git_info["branch"]))
    counts = {row["type"]: row["count"] for row in cursor.fetchall()}

    # Contar TODOs por prioridade
    cursor.execute("""
        SELECT priority, COUNT(*) as count
        FROM entries
        WHERE git_repo = %s AND git_branch = %s AND status = 'active' AND type = 'todo'
        GROUP BY priority
    """, (git_info["repo"], git_info["branch"]))
    todo_priorities = {row["priority"]: row["count"] for row in cursor.fetchall()}

    # Última decisão
    cursor.execute("""
        SELECT title, created_at
        FROM entries
        WHERE git_repo = %s AND git_branch = %s AND status = 'active' AND type = 'decision'
        ORDER BY created_at DESC
        LIMIT 1
    """, (git_info["repo"], git_info["branch"]))
    last_decision = cursor.fetchone()

    conn.close()

    return {
        "status": "success",
        "repo": git_info["repo"],
        "branch": git_info["branch"],
        "counts": counts,
        "todo_priorities": todo_priorities,
        "last_decision": last_decision,
        "total_decisions": counts.get("decision", 0),
        "total_todos": counts.get("todo", 0),
        "high_priority_todos": todo_priorities.get("high", 0) + todo_priorities.get("critical", 0)
    }


def update_entry(entry_id, status=None, title=None, content=None):
    """Atualiza uma entrada"""
    conn = get_connection()
    cursor = conn.cursor()

    updates = []
    params = []

    if status:
        updates.append("status = %s")
        params.append(status)
    if title:
        updates.append("title = %s")
        params.append(title)
    if content:
        updates.append("content = %s")
        params.append(content)

    if not updates:
        return {"status": "error", "message": "Nada para atualizar"}

    params.append(entry_id)
    cursor.execute(f"UPDATE entries SET {', '.join(updates)} WHERE id = %s", params)

    conn.commit()
    conn.close()

    return {"status": "success", "updated_id": entry_id}


def main():
    parser = argparse.ArgumentParser(description="Project Memory API")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Comando: add
    add_parser = subparsers.add_parser("add", help="Adicionar entrada")
    add_parser.add_argument("--type", "-t", required=True,
                           choices=["decision", "todo", "context", "pattern", "note"])
    add_parser.add_argument("--title", required=True)
    add_parser.add_argument("--content", "-c", required=True)
    add_parser.add_argument("--tags", default=None)
    add_parser.add_argument("--priority", default="medium",
                           choices=["low", "medium", "high", "critical"])
    add_parser.add_argument("--files", nargs="*", default=None)
    add_parser.add_argument("--by", default="claude")

    # Comando: search
    search_parser = subparsers.add_parser("search", help="Buscar")
    search_parser.add_argument("query")
    search_parser.add_argument("--limit", "-l", type=int, default=20)
    search_parser.add_argument("--all-branches", action="store_true")

    # Comando: list
    list_parser = subparsers.add_parser("list", help="Listar")
    list_parser.add_argument("--type", "-t", default=None)
    list_parser.add_argument("--tag", default=None)
    list_parser.add_argument("--status", "-s", default="active")
    list_parser.add_argument("--limit", "-l", type=int, default=50)
    list_parser.add_argument("--all-branches", action="store_true")

    # Comando: todos
    subparsers.add_parser("todos", help="Listar TODOs")

    # Comando: decisions
    subparsers.add_parser("decisions", help="Listar decisões")

    # Comando: context
    subparsers.add_parser("context", help="Obter contexto")

    # Comando: summary (para início de sessão)
    subparsers.add_parser("summary", help="Resumo do projeto")

    # Comando: update
    update_parser = subparsers.add_parser("update", help="Atualizar")
    update_parser.add_argument("--id", required=True)
    update_parser.add_argument("--status", default=None)
    update_parser.add_argument("--title", default=None)
    update_parser.add_argument("--content", default=None)

    args = parser.parse_args()

    try:
        if args.command == "add":
            result = add_entry(args.type, args.title, args.content,
                              args.tags, args.priority, args.files, args.by)
        elif args.command == "search":
            result = search(args.query, args.limit, args.all_branches)
        elif args.command == "list":
            result = list_entries(args.type, args.tag, args.status, args.limit, args.all_branches)
        elif args.command == "todos":
            result = get_todos()
        elif args.command == "decisions":
            result = get_decisions()
        elif args.command == "context":
            result = get_context()
        elif args.command == "summary":
            result = get_summary()
        elif args.command == "update":
            result = update_entry(args.id, args.status, args.title, args.content)
        else:
            result = {"error": f"Comando desconhecido: {args.command}"}

        print(json.dumps(result, indent=2, default=str))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
