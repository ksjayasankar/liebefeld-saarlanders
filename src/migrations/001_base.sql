-- Run once by `navigator migrate` (spec 5.7). Dataset, caches and company requests survive every rebuild.
CREATE EXTENSION IF NOT EXISTS vector;
CREATE SCHEMA dataset;                        -- fetched pages: kept, only grows
CREATE TABLE dataset.pages (url text PRIMARY KEY, host text NOT NULL, status int NOT NULL,
                            first_fetched_at timestamptz NOT NULL, last_checked_at timestamptz NOT NULL,
                            etag text, last_modified text,      -- NULL when the server sends no such header
                            content_hash text NOT NULL, raw_path text NOT NULL, gone_at timestamptz);
CREATE SCHEMA cache;                          -- model answers: kept, keyed by input
CREATE TABLE cache.model_calls (key text PRIMARY KEY,           -- sha256 of model, settings and input
                                model text NOT NULL, input text NOT NULL, answer jsonb NOT NULL,
                                latency_ms int NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE cache.embeddings  (model_id text NOT NULL, text_hash text NOT NULL,
                                embedding vector(1024) NOT NULL, PRIMARY KEY (model_id, text_hash));
CREATE SCHEMA app;                            -- company requests: kept
CREATE TABLE app.schema_version (version int NOT NULL);
INSERT INTO app.schema_version VALUES (1);
CREATE TABLE app.requests      (id uuid PRIMARY KEY, domain text NOT NULL, build_id text NOT NULL,
                                need_card jsonb NOT NULL, leads jsonb NOT NULL, created_at timestamptz NOT NULL);
CREATE TABLE app.feedback      (request_id uuid NOT NULL REFERENCES app.requests(id), unit_id text NOT NULL,
                                need_id text NOT NULL, action text NOT NULL, reason text,
                                created_at timestamptz NOT NULL);
CREATE TABLE app.introductions (id uuid PRIMARY KEY, request_id uuid NOT NULL REFERENCES app.requests(id),
                                unit_ids text[] NOT NULL, message text NOT NULL,
                                status text NOT NULL DEFAULT 'new', created_at timestamptz NOT NULL);
