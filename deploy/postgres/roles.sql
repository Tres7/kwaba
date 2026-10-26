-- PostgreSQL role with minimal rights for the application (API, workers, relay, consumer).
--
-- The owner role (the one that created the database) is only used for migrations. The application runs as
-- kwaba_app: read and write rows, nothing else (no creating, altering or dropping a table, no creating a role).
-- If the API is compromised, the attacker can neither destroy the schema nor grant themselves other rights.
--
-- To run once, connected with the database owner role:
--   psql "$DATABASE_URL_PROPRIETAIRE" -v mot_de_passe="'<long random password>'" -f deploy/postgres/roles.sql
-- Then:
--   - web services / workers: POSTGRES_USER=kwaba_app and this password;
--   - migration job (manage.py migrate): credentials of the owner role, which creates the new tables
--     (the default privileges below open them automatically to kwaba_app).

\set ON_ERROR_STOP on

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'kwaba_app') THEN
        CREATE ROLE kwaba_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS;
    END IF;
END $$;

ALTER ROLE kwaba_app WITH PASSWORD :mot_de_passe;
-- A blocked query must not hold locks forever
ALTER ROLE kwaba_app SET statement_timeout = '30s';
ALTER ROLE kwaba_app SET idle_in_transaction_session_timeout = '60s';

-- Nobody but the owner creates objects in the public schema
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO kwaba_app;
SELECT format('GRANT CONNECT ON DATABASE %I TO kwaba_app', current_database()) \gexec

-- Existing tables and sequences
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO kwaba_app;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO kwaba_app;

-- Tables and sequences created later by the migrations (run with the owner role)
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO kwaba_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO kwaba_app;

-- Audit log: the application adds rows but can neither change nor delete them
REVOKE UPDATE, DELETE ON securite_journal_audit FROM kwaba_app;

-- Hosts' pre-registration proofs (contrats_preinscription): same rule as the audit log.
-- The table is created by the contrats 0005 migration: run this script again after that migration.
REVOKE UPDATE, DELETE ON contrats_preinscription FROM kwaba_app;
