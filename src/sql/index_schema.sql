-- Run into staging_<domain> at the start of every build (spec 5.7).
CREATE TABLE build    (id text PRIMARY KEY, domain text NOT NULL, model_id text NOT NULL,
                       dim int NOT NULL CHECK (dim = 1024), created_at timestamptz NOT NULL, counts jsonb NOT NULL);
CREATE TABLE units    (id text PRIMARY KEY, name text NOT NULL, kind text NOT NULL,
                       parent_id text REFERENCES units(id), host text NOT NULL,
                       category text NOT NULL CHECK (category IN ('research_partner','facility','clinical_validation','licensing','support','talent')),
                       summary text NOT NULL CHECK (summary <> ''), summary_sources text[] NOT NULL CHECK (cardinality(summary_sources) > 0),
                       terms text[] NOT NULL,                   -- English terms from enrichment: the unit's fields of expertise
                       page_count int NOT NULL CHECK (page_count > 0), embedding vector(1024) NOT NULL);
CREATE TABLE pages    (url text PRIMARY KEY, host text NOT NULL, lang text NOT NULL CHECK (lang IN ('en','de','fr')),
                       page_type text NOT NULL, title text NOT NULL, page_date date,
                       text_hash text NOT NULL UNIQUE, translation_of text REFERENCES pages(url));
CREATE TABLE unit_pages (unit_id text REFERENCES units(id), url text REFERENCES pages(url),
                         PRIMARY KEY (unit_id, url));
CREATE TABLE unit_items (unit_id text NOT NULL REFERENCES units(id),
                         kind text NOT NULL CHECK (kind IN ('project', 'facility')),
                         name text NOT NULL, url text NOT NULL REFERENCES pages(url));
CREATE TABLE people   (unit_id text NOT NULL REFERENCES units(id), name text NOT NULL, titles text NOT NULL,
                       function text, affiliation text NOT NULL, email text, phone text,   -- contact data lives only here (D-26)
                       profile_url text REFERENCES dataset.pages(url), source_url text NOT NULL REFERENCES pages(url),
                       contact boolean NOT NULL, position int NOT NULL);
CREATE INDEX ON people (unit_id);
CREATE TABLE chunks   (id text PRIMARY KEY, unit_id text NOT NULL REFERENCES units(id),
                       url text REFERENCES pages(url),          -- NULL only for a unit's term chunk
                       lang text NOT NULL, text text NOT NULL, is_terms boolean NOT NULL,
                       tsv tsvector NOT NULL, embedding vector(1024) NOT NULL,
                       CHECK (is_terms = (url IS NULL)));
CREATE INDEX ON chunks USING gin (tsv);
CREATE INDEX ON chunks USING hnsw (embedding vector_cosine_ops);
CREATE TABLE concepts       (id text PRIMARY KEY, source text NOT NULL);
CREATE TABLE concept_labels (concept_id text NOT NULL REFERENCES concepts(id), lang text NOT NULL,
                             label text NOT NULL, match_key text NOT NULL);
CREATE INDEX ON concept_labels (match_key);
CREATE TABLE chunk_concepts (chunk_id text REFERENCES chunks(id), concept_id text REFERENCES concepts(id),
                             PRIMARY KEY (chunk_id, concept_id));
CREATE TABLE report_sentences (section text NOT NULL, position int NOT NULL, sentence text NOT NULL,
                               url text NOT NULL REFERENCES pages(url), source_sentence text NOT NULL,
                               PRIMARY KEY (section, position));
