# Schema do Banco de Dados

## Tabela: entries

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| id | UUID | Identificador único |
| git_repo | TEXT | Repositório git (ex: github.com/user/repo) |
| git_branch | TEXT | Branch atual (ex: main) |
| type | TEXT | Tipo: decision, todo, context, pattern, note |
| title | TEXT | Título curto |
| content | TEXT | Conteúdo detalhado |
| priority | TEXT | low, medium, high, critical |
| status | TEXT | active, completed, archived, deprecated |
| related_files | TEXT[] | Arquivos relacionados |
| created_by | TEXT | Quem criou (claude, usuário) |
| created_at | TIMESTAMPTZ | Data de criação |
| updated_at | TIMESTAMPTZ | Data de atualização |
| search_vector | TSVECTOR | Índice de busca textual |

## Tabela: entry_tags

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| entry_id | UUID | FK para entries |
| tag | TEXT | Nome da tag |

## Índices

- `idx_entries_repo_branch`: Busca por repo + branch
- `idx_entries_type`: Busca por tipo
- `idx_entries_status`: Busca por status
- `idx_entries_search`: Full-text search (GIN)
- `idx_tags_tag`: Busca por tag

## Exemplos de Queries

### Buscar decisões do projeto atual
```sql
SELECT * FROM entries
WHERE git_repo = 'github.com/user/repo'
  AND git_branch = 'main'
  AND type = 'decision'
  AND status = 'active'
ORDER BY created_at DESC;
```

### Busca textual
```sql
SELECT *, ts_rank(search_vector, query) as rank
FROM entries, plainto_tsquery('portuguese', 'autenticação') query
WHERE search_vector @@ query
ORDER BY rank DESC;
```

### TODOs de alta prioridade
```sql
SELECT * FROM entries
WHERE type = 'todo'
  AND priority IN ('high', 'critical')
  AND status = 'active'
ORDER BY priority DESC, created_at DESC;
```
