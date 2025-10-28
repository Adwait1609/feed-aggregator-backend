#!/usr/bin/env python3
"""
Script to drop all existing tables and reinitialize the database with the new normalized schema.
"""
import asyncio
import sys
from sqlalchemy import text
from loguru import logger

from database.connection import engine, init_database
from models.base import Base

async def drop_all_tables():
    """Drop all existing tables from the database"""
    try:
        # Drop all tables
        Base.metadata.drop_all(bind=engine)
        logger.info("All tables dropped successfully")
        
        # Also drop the scheduler_jobs table since it's created separately
        with engine.connect() as conn:
            conn.execute(text("DROP TABLE IF EXISTS scheduler_jobs"))
            conn.commit()
            logger.info("Scheduler jobs table dropped")
        
        return True
    except Exception as e:
        logger.error(f"Error dropping tables: {e}")
        return False

async def reset_database():
    """Reset the database by dropping all tables and recreating them"""
    # Drop all existing tables
    success = await drop_all_tables()
    if not success:
        logger.error("Failed to drop tables. Aborting database reset.")
        return False
    
    # Initialize database with new schema
    try:
        await init_database()
        logger.success("Database reset completed successfully. New schema initialized.")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize new database schema: {e}")
        return False

if __name__ == "__main__":
    print("WARNING: This will delete ALL data in the database and recreate the schema.")
    confirmation = input("Type 'yes' to confirm: ")
    
    if confirmation.lower() != "yes":
        print("Operation cancelled.")
        sys.exit(0)
    
    success = asyncio.run(reset_database())
    if success:
        print("Database successfully reset with the new normalized schema!")
    else:
        print("Failed to reset database. Check the logs for details.")
        sys.exit(1)
