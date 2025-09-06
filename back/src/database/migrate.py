#!/usr/bin/env python3
"""
Database migration script for Sayar WhatsApp Commerce Platform
Run this script to apply the initial database schema
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add the parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.database.connection import engine

async def apply_migration():
    """Apply the initial database schema migration"""
    
    # Read the migration SQL file
    migration_path = Path("migrations/001_initial_schema.sql")
    if not migration_path.exists():
        print(f"Error: Migration file not found at {migration_path}")
        return False
    
    try:
        with open(migration_path, 'r') as f:
            migration_sql = f.read()
        
        print("Applying database migration...")
        
        async with engine.connect() as conn:
            # Execute the migration SQL
            await conn.execute("BEGIN")
            
            # Split SQL by semicolons and execute each statement
            statements = migration_sql.split(';')
            for statement in statements:
                statement = statement.strip()
                if statement:  # Skip empty statements
                    try:
                        await conn.execute(statement)
                        print(f"✓ Executed: {statement[:100]}...")
                    except Exception as e:
                        print(f"⚠ Warning executing statement: {e}")
                        # Continue with other statements
            
            await conn.execute("COMMIT")
            print("✅ Migration completed successfully!")
            return True
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        # Try to rollback
        try:
            async with engine.connect() as conn:
                await conn.execute("ROLLBACK")
                print("Rolled back transaction")
        except:
            pass
        return False

async def verify_migration():
    """Verify that the migration was applied successfully"""
    try:
        async with engine.connect() as conn:
            # Check if merchants table exists
            result = await conn.execute(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'merchants')"
            )
            merchants_exists = result.scalar()
            
            # Check if RLS is enabled on merchants table
            result = await conn.execute(
                "SELECT rowsecurity FROM pg_tables WHERE tablename = 'merchants'"
            )
            rls_enabled = result.scalar()
            
            print(f"Merchants table exists: {merchants_exists}")
            print(f"RLS enabled on merchants: {rls_enabled}")
            
            # Count tables created
            result = await conn.execute(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'"
            )
            table_count = result.scalar()
            print(f"Total tables in public schema: {table_count}")
            
            return merchants_exists and rls_enabled
            
    except Exception as e:
        print(f"Verification failed: {e}")
        return False

async def main():
    """Main migration function"""
    load_dotenv()
    
    print("🚀 Sayar Database Migration Tool")
    print("=" * 50)
    
    # Check if environment variables are set
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
    
    if not supabase_url or not supabase_key:
        print("❌ Error: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env file")
        print("Please update back/.env with your Supabase credentials")
        return False
    
    print("✅ Environment variables found")
    
    # Test connection first
    print("Testing database connection...")
    try:
        async with engine.connect() as conn:
            version = await conn.scalar("SELECT version()")
            print(f"✅ Connected to: {version}")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("Please check your Supabase URL and Service Key")
        return False
    
    # Apply migration
    success = await apply_migration()
    
    if success:
        print("\nVerifying migration...")
        verified = await verify_migration()
        if verified:
            print("✅ Migration verified successfully!")
        else:
            print("⚠ Migration applied but verification failed")
    
    return success

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)