#!/bin/bash
# Session init hook para project-memory
# Executa summary automaticamente ao iniciar sessão

SCRIPT_DIR="$(dirname "$0")"
RESULT=$(python3 "$SCRIPT_DIR/memory_api.py" summary 2>/dev/null)

# Verifica se foi pulado (não é git repo)
if echo "$RESULT" | grep -q '"status": "skipped"'; then
    exit 0
fi

# Verifica se teve sucesso
if echo "$RESULT" | grep -q '"status": "success"'; then
    # Extrai informações do JSON
    REPO=$(echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('repo',''))" 2>/dev/null)
    BRANCH=$(echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('branch',''))" 2>/dev/null)
    DECISIONS=$(echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('total_decisions',0))" 2>/dev/null)
    TODOS=$(echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('total_todos',0))" 2>/dev/null)
    HIGH_TODOS=$(echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('high_priority_todos',0))" 2>/dev/null)
    LAST_DECISION=$(echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); ld=d.get('last_decision'); print(ld.get('title','') if ld else '')" 2>/dev/null)

    # Output para o Claude ver
    cat << EOF
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "📚 Project Memory carregado para $REPO (branch: $BRANCH)\n- $DECISIONS decisões técnicas ativas\n- $TODOS TODOs pendentes ($HIGH_TODOS alta prioridade)\n- Última decisão: \"$LAST_DECISION\"\n\nUse 'python3 ~/.claude/skills/project-memory/scripts/memory_api.py' para gerenciar memória."
  }
}
EOF
fi

exit 0
