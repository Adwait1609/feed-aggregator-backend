"""
Migration to create APScheduler job storage table

This migration creates the table needed for APScheduler to persist jobs in the database.
"""

from sqlalchemy import Column, String, DateTime, LargeBinary, Integer, text
from sqlalchemy.ext.declarative import declarative_base
from alembic import op

def upgrade():
    """Create the scheduler_jobs table for APScheduler"""
    op.execute(text("""
        CREATE TABLE IF NOT EXISTS scheduler_jobs (
            id VARCHAR(191) NOT NULL PRIMARY KEY,
            next_run_time DOUBLE PRECISION,
            job_state BYTEA NOT NULL
        );
    """))
    
    # Create index for better performance
    op.execute(text("""
        CREATE INDEX IF NOT EXISTS ix_scheduler_jobs_next_run_time 
        ON scheduler_jobs(next_run_time);
    """))

def downgrade():
    """Drop the scheduler_jobs table"""
    op.execute(text("DROP TABLE IF EXISTS scheduler_jobs CASCADE;"))
