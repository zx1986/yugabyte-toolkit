-- Schema initialization for hash vs range sharding benchmark
-- See: specs/002-yb-multi-node/data-model.md

-- Drop existing tables if present (ensures clean state on re-run)
DROP TABLE IF EXISTS users_hash;
DROP TABLE IF EXISTS users_range;

-- Hash-sharded table (default YugabyteDB behavior)
-- Rows are evenly distributed across all tablets regardless of insert order.
CREATE TABLE users_hash (
    id         UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    email      VARCHAR(255) UNIQUE NOT NULL,
    name       VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Range-sharded table (ASC primary key forces range sharding)
-- Rows are ordered by primary key, enabling efficient range scans but
-- potentially causing hotspots during high-throughput sequential inserts.
CREATE TABLE users_range (
    id         UUID        DEFAULT gen_random_uuid(),
    email      VARCHAR(255) UNIQUE NOT NULL,
    name       VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (created_at ASC, id ASC)
);
