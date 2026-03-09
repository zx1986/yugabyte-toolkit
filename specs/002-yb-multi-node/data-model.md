# Data Model: yb-multi-node

For the performance comparison, we define two tables with identical schema but different primary key sharding configurations.

## Entities

### `users_hash`
A table sharded by a hash of its primary key, resulting in even data distribution across all tablets/nodes regardless of write order. This is the default YugabyteDB behavior.

**Fields**:
- `id` (UUID): Unique identifier, defaults to `gen_random_uuid()`. **HASH PRIMARY KEY**.
- `email` (VARCHAR(255)): User email address, UNIQUE, NOT NULL.
- `name` (VARCHAR(255)): User full name, NOT NULL.
- `created_at` (TIMESTAMPTZ): Timestamp of creation, defaults to `NOW()`.

### `users_range`
A table sharded by range order of its primary key. Range sharding is efficient for range scans (e.g., querying a continuous block of IDs or dates) but can lead to hotspotting during sequential inserts.

**Fields**:
- `id` (UUID): Unique identifier, defaults to `gen_random_uuid()`. **ASC PRIMARY KEY** (forces range sharding).
- `email` (VARCHAR(255)): User email address, UNIQUE, NOT NULL.
- `name` (VARCHAR(255)): User full name, NOT NULL.
- `created_at` (TIMESTAMPTZ): Timestamp of creation, defaults to `NOW()`.

## Validation Rules
- `email` field must enforce uniqueness for data integrity across the distributed cluster.
- All non-nullable fields must be enforced at the schema level.

## State Transitions
- No complex state transitions modeled. Simple CRUD behavior for performance measurement.
