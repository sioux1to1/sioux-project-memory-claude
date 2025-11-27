# Sioux Project Memory for Claude Code

Skill para Claude Code que armazena memória persistente de projetos em PostgreSQL.

## Funcionalidades

- Armazena decisões técnicas, TODOs, contexto e padrões
- Identificação automática do projeto via git repo + branch
- Full-text search em português
- Comportamento 100% automático

## Instalação

### 1. Clonar para ~/.claude/skills/

```bash
git clone https://github.com/sioux1to1/sioux-project-memory-claude.git ~/.claude/skills/project-memory
```

### 2. Instalar dependências

```bash
pip install psycopg2-binary
```

### 3. Criar banco de dados PostgreSQL

```bash
createdb sioux_project_memory
psql sioux_project_memory < ~/.claude/skills/project-memory/scripts/setup_db.sql
```

### 4. Configurar conexão

Edite `~/.claude/skills/project-memory/config.json`:

```json
{
  "database_url": "postgresql://usuario:senha@host:5432/sioux_project_memory"
}
```

## Uso

A skill funciona automaticamente quando você usa Claude Code em um repositório git.

### Comandos disponíveis

```bash
# Resumo do projeto (início de sessão)
python scripts/memory_api.py summary

# Adicionar decisão
python scripts/memory_api.py add --type decision --title "Usar FastAPI" --content "..."

# Listar decisões
python scripts/memory_api.py decisions

# Listar TODOs
python scripts/memory_api.py todos

# Buscar
python scripts/memory_api.py search "autenticação"
```

### Tipos de entrada

- `decision`: Decisões técnicas
- `todo`: Melhorias futuras
- `context`: Contexto do projeto
- `pattern`: Padrões de código
- `note`: Anotações gerais

## Comportamento Automático

O Claude deve:

1. **Ao iniciar sessão**: Carregar contexto automaticamente
2. **Durante uso**: Salvar decisões importantes automaticamente
3. **Ao consultar**: Verificar memória antes de sugerir tecnologias

## Estrutura

```
project-memory/
├── SKILL.md              # Instruções para Claude
├── config.json           # Configuração do banco
├── scripts/
│   ├── memory_api.py     # Script principal
│   └── setup_db.sql      # Schema do banco
└── references/
    └── schema.md         # Documentação do schema
```

## Licença

MIT
