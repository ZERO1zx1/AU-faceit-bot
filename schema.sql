-- AU FACEIT Bot - Supabase PostgreSQL Schema
-- Run this in Supabase SQL Editor to set up all tables

-- 1. Guild Settings
CREATE TABLE IF NOT EXISTS guild_settings (
    guild_id BIGINT PRIMARY KEY,
    prefix VARCHAR(10) DEFAULT '!',
    queue_category_id BIGINT,
    match_category_id BIGINT,
    leaderboard_channel_id BIGINT,
    log_channel_id BIGINT,
    register_channel_id BIGINT,
    unverified_role_id BIGINT,
    verified_role_id BIGINT,
    level_role_ids JSONB DEFAULT '{}',
    panel_messages JSONB DEFAULT '{}',
    queue_defaults JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 2. Players
CREATE TABLE IF NOT EXISTS players (
    guild_id BIGINT NOT NULL,
    discord_user_id BIGINT NOT NULL,
    among_us_name VARCHAR(100),
    verified BOOLEAN DEFAULT FALSE,
    active BOOLEAN DEFAULT TRUE,
    au_elo INTEGER DEFAULT 0,
    level INTEGER DEFAULT 1,
    total_matches INTEGER DEFAULT 0,
    wins_as_impostor INTEGER DEFAULT 0,
    wins_as_crewmate INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    voice_seconds BIGINT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (guild_id, discord_user_id)
);

-- 3. Queues
CREATE TABLE IF NOT EXISTS queues (
    guild_id BIGINT PRIMARY KEY,
    queue_message_id BIGINT,
    status VARCHAR(20) DEFAULT 'open',
    created_at TIMESTAMP DEFAULT NOW()
);

-- 4. Queue Members
CREATE TABLE IF NOT EXISTS queue_members (
    guild_id BIGINT NOT NULL,
    discord_user_id BIGINT NOT NULL,
    joined_at TIMESTAMP DEFAULT NOW(),
    position SMALLINT,
    PRIMARY KEY (guild_id, discord_user_id)
);

-- 5. Matches
CREATE TABLE IF NOT EXISTS matches (
    match_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    guild_id BIGINT NOT NULL,
    status VARCHAR(20) DEFAULT 'open',
    text_channel_id BIGINT,
    voice_channel_id BIGINT,
    created_by BIGINT,
    closed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 6. Match Players
CREATE TABLE IF NOT EXISTS match_players (
    match_id UUID NOT NULL REFERENCES matches(match_id) ON DELETE CASCADE,
    discord_user_id BIGINT NOT NULL,
    role VARCHAR(10),
    elo_before INTEGER,
    elo_change INTEGER,
    elo_after INTEGER,
    PRIMARY KEY (match_id, discord_user_id)
);

-- 7. Match Results
CREATE TABLE IF NOT EXISTS match_results (
    match_id UUID PRIMARY KEY REFERENCES matches(match_id) ON DELETE CASCADE,
    impostors JSONB NOT NULL,
    screenshot_url TEXT,
    admin_user_id BIGINT NOT NULL,
    custom_winner_elo INTEGER,
    custom_loser_elo INTEGER,
    submitted_at TIMESTAMP DEFAULT NOW()
);

-- 8. Elo History
CREATE TABLE IF NOT EXISTS elo_history (
    id BIGSERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    discord_user_id BIGINT NOT NULL,
    match_id UUID,
    elo_before INTEGER NOT NULL,
    elo_after INTEGER NOT NULL,
    change INTEGER NOT NULL,
    reason VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

-- 9. Voice Sessions
CREATE TABLE IF NOT EXISTS voice_sessions (
    id BIGSERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    discord_user_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    joined_at TIMESTAMP DEFAULT NOW(),
    left_at TIMESTAMP,
    duration_seconds INTEGER
);

-- 10. Audit Logs
CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGSERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    action_type VARCHAR(30) NOT NULL,
    actor_id BIGINT,
    target_entity VARCHAR(50),
    details JSONB DEFAULT '{}',
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_players_guild ON players(guild_id);
CREATE INDEX IF NOT EXISTS idx_players_elo ON players(guild_id, au_elo DESC);
CREATE INDEX IF NOT EXISTS idx_queue_members_guild ON queue_members(guild_id);
CREATE INDEX IF NOT EXISTS idx_matches_guild ON matches(guild_id);
CREATE INDEX IF NOT EXISTS idx_matches_status ON matches(status);
CREATE INDEX IF NOT EXISTS idx_elo_history_user ON elo_history(guild_id, discord_user_id);
CREATE INDEX IF NOT EXISTS idx_elo_history_created ON elo_history(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_voice_sessions_user ON voice_sessions(guild_id, discord_user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_guild ON audit_logs(guild_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created ON audit_logs(created_at DESC);

-- RLS: Enable but allow service_role full access
ALTER TABLE guild_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE players ENABLE ROW LEVEL SECURITY;
ALTER TABLE queues ENABLE ROW LEVEL SECURITY;
ALTER TABLE queue_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE matches ENABLE ROW LEVEL SECURITY;
ALTER TABLE match_players ENABLE ROW LEVEL SECURITY;
ALTER TABLE match_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE elo_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE voice_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- Service role policies (full access)
CREATE POLICY "Service role full access" ON guild_settings FOR ALL USING (true);
CREATE POLICY "Service role full access" ON players FOR ALL USING (true);
CREATE POLICY "Service role full access" ON queues FOR ALL USING (true);
CREATE POLICY "Service role full access" ON queue_members FOR ALL USING (true);
CREATE POLICY "Service role full access" ON matches FOR ALL USING (true);
CREATE POLICY "Service role full access" ON match_players FOR ALL USING (true);
CREATE POLICY "Service role full access" ON match_results FOR ALL USING (true);
CREATE POLICY "Service role full access" ON elo_history FOR ALL USING (true);
CREATE POLICY "Service role full access" ON voice_sessions FOR ALL USING (true);
CREATE POLICY "Service role full access" ON audit_logs FOR ALL USING (true);
