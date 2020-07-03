GRANT CONNECT ON DATABASE cliahub TO cliahub_staging; -- readonly account
GRANT CONNECT, CREATE ON DATABASE cliahub TO cliahub_staging_rw; -- read/write account

-- create schema temporarily so we can set up permissions
CREATE SCHEMA qpcr_processing;
CREATE SCHEMA ngs_sample_tracking;

-- grant read permissions for public schema to readonly account
GRANT USAGE ON SCHEMA public TO cliahub_staging;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO cliahub_staging; 
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO cliahub_staging; 

-- grant read/write for public schema to rw account
GRANT USAGE, CREATE ON SCHEMA public TO cliahub_staging_rw;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO cliahub_staging_rw;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO cliahub_staging_rw;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO cliahub_staging_rw;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE ON SEQUENCES TO cliahub_staging_rw;

-- same for qpcr_processing
GRANT USAGE ON SCHEMA qpcr_processing TO cliahub_staging;
GRANT SELECT ON ALL TABLES IN SCHEMA qpcr_processing TO cliahub_staging; 
ALTER DEFAULT PRIVILEGES IN SCHEMA qpcr_processing GRANT SELECT ON TABLES TO cliahub_staging; 

GRANT USAGE, CREATE ON SCHEMA qpcr_processing TO cliahub_staging_rw;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA qpcr_processing TO cliahub_staging_rw;
ALTER DEFAULT PRIVILEGES IN SCHEMA qpcr_processing GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO cliahub_staging_rw;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA qpcr_processing TO cliahub_staging_rw;
ALTER DEFAULT PRIVILEGES IN SCHEMA qpcr_processing GRANT USAGE ON SEQUENCES TO cliahub_staging_rw;

-- same for ngs_sample_tracking
GRANT USAGE ON SCHEMA ngs_sample_tracking TO cliahub_staging;
GRANT SELECT ON ALL TABLES IN SCHEMA ngs_sample_tracking TO cliahub_staging; 
ALTER DEFAULT PRIVILEGES IN SCHEMA ngs_sample_tracking GRANT SELECT ON TABLES TO cliahub_staging; 

GRANT USAGE, CREATE ON SCHEMA ngs_sample_tracking TO cliahub_staging_rw;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA ngs_sample_tracking TO cliahub_staging_rw;
ALTER DEFAULT PRIVILEGES IN SCHEMA ngs_sample_tracking GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO cliahub_staging_rw;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA ngs_sample_tracking TO cliahub_staging_rw;
ALTER DEFAULT PRIVILEGES IN SCHEMA ngs_sample_tracking GRANT USAGE ON SEQUENCES TO cliahub_staging_rw;

-- drop the schema, otherwise cliahub_staging_rw won't have the permission to drop/create
DROP SCHEMA qpcr_processing;
DROP SCHEMA ngs_sample_tracking;
