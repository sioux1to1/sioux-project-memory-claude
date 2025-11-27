-- Schema para sioux_project_memory
-- Execute: psql sioux_project_memory < setup_db.sql

-- Entradas de memória (identificação por git repo + branch)
CREATE TABLE IF NOT EXISTS entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Identificação automática via git
    git_repo TEXT NOT NULL,              -- ex: "github.com/user/repo"
    git_branch TEXT NOT NULL,            -- ex: "main", "feature/auth"

    -- Dados da entrada
    type TEXT NOT NULL CHECK (type IN ('decision', 'todo', 'context', 'pattern', 'note')),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    priority TEXT DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'critical')),
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'completed', 'archived', 'deprecated')),
    related_files TEXT[],
    created_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Full-text search
    search_vector TSVECTOR GENERATED ALWAYS AS (
        setweight(to_tsvector('portuguese', coalesce(title, '')), 'A') ||
        setweight(to_tsvector('portuguese', coalesce(content, '')), 'B')
    ) STORED
);

-- Tags
CREATE TABLE IF NOT EXISTS entry_tags (
    entry_id UUID REFERENCES entries(id) ON DELETE CASCADE,
    tag TEXT NOT NULL,
    PRIMARY KEY (entry_id, tag)
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_entries_repo_branch ON entries(git_repo, git_branch);
CREATE INDEX IF NOT EXISTS idx_entries_type ON entries(git_repo, git_branch, type);
CREATE INDEX IF NOT EXISTS idx_entries_status ON entries(git_repo, git_branch, status);
CREATE INDEX IF NOT EXISTS idx_entries_search ON entries USING GIN(search_vector);
CREATE INDEX IF NOT EXISTS idx_tags_tag ON entry_tags(tag);

-- Trigger para updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS entries_updated_at ON entries;
CREATE TRIGGER entries_updated_at
    BEFORE UPDATE ON entries
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Mensagem de sucesso
DO $$
BEGIN
    RAISE NOTICE 'Schema sioux_project_memory criado com sucesso!';
END $$;
