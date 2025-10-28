"""
Database Initialization Script

This script:
1. Creates all database tables
2. Can optionally create a test user
3. Creates default rules for organizations

Usage:
    python scripts/init_db.py
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import engine, Base
from app.db.base import Base as BaseModel
from app.core.config import settings


async def init_database():
    """
    Initialize the database.
    
    Creates all tables defined in the models.
    """
    print("🔧 Initializing database...")
    print(f"📍 Database URL: {settings.DATABASE_URL}")
    
    try:
        # Create all tables
        async with engine.begin() as conn:
            print("📊 Creating tables...")
            await conn.run_sync(BaseModel.metadata.create_all)
        
        print("✅ Database initialized successfully!")
        print("\n📋 Tables created:")
        print("   - organizations")
        print("   - users")
        print("   - transactions")
        print("   - rules")
        print("   - alerts")
        print("   - file_uploads")
        print("   - audit_logs")
        
        return True
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        return False


async def create_test_user():
    """
    Create a test user for development.
    
    Email: admin@test.com
    Password: password123
    Organization: Test Corporation
    """
    from app.db.session import AsyncSessionLocal
    from app.crud.user import create_organization, create_user, email_exists
    from app.crud.rule import create_default_rules_for_organization
    from app.utils.constants import UserRole
    
    print("\n🧪 Creating test user...")
    
    async with AsyncSessionLocal() as db:
        try:
            # Check if user already exists
            if await email_exists(db, "admin@test.com"):
                print("⚠️  Test user already exists (admin@test.com)")
                return
            
            # Create organization
            org = await create_organization(
                db=db,
                name="Test Corporation",
                contact_email="admin@test.com"
            )
            print(f"✅ Created organization: {org.name}")
            
            # Create user
            user = await create_user(
                db=db,
                email="admin@test.com",
                password="password123",
                full_name="Test Admin",
                organization_id=org.id,
                role=UserRole.ADMIN
            )
            print(f"✅ Created user: {user.email}")
            
            # Create default rules
            rules = await create_default_rules_for_organization(
                db=db,
                organization_id=org.id
            )
            print(f"✅ Created {len(rules)} default rules")
            
            print("\n" + "="*50)
            print("🎉 Test user created successfully!")
            print("="*50)
            print("\n📝 Login Credentials:")
            print("   Email: admin@test.com")
            print("   Password: password123")
            print("\n🌐 Access the system at:")
            print("   http://localhost:8000/login")
            print("="*50 + "\n")
            
        except Exception as e:
            print(f"❌ Error creating test user: {e}")
            import traceback
            traceback.print_exc()


async def drop_all_tables():
    """
    Drop all tables (DANGER: This deletes all data!)
    
    Only use in development.
    """
    print("⚠️  WARNING: This will delete ALL data!")
    response = input("Are you sure you want to drop all tables? (yes/no): ")
    
    if response.lower() != "yes":
        print("❌ Operation cancelled")
        return
    
    print("🗑️  Dropping all tables...")
    
    try:
        async with engine.begin() as conn:
            await conn.run_sync(BaseModel.metadata.drop_all)
        
        print("✅ All tables dropped")
        
    except Exception as e:
        print(f"❌ Error dropping tables: {e}")


async def main():
    """Main function."""
    
    print("="*60)
    print("🛡️  AML Transaction Monitoring - Database Setup")
    print("="*60)
    print()
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "drop":
            await drop_all_tables()
            return
        elif command == "reset":
            await drop_all_tables()
            await init_database()
            await create_test_user()
            return
    
    # Default: Initialize database
    success = await init_database()
    
    if success:
        # Ask if user wants to create test data
        print("\n" + "="*60)
        response = input("Do you want to create a test user? (yes/no): ")
        
        if response.lower() == "yes":
            await create_test_user()
        else:
            print("\n💡 You can create a test user later by running:")
            print("   python scripts/init_db.py test")
    
    print("\n✨ Setup complete!")
    print("\n📚 Next steps:")
    print("   1. Start the application: uvicorn app.main:app --reload")
    print("   2. Visit: http://localhost:8000/login")
    print("   3. Register a new account or use test credentials")
    print()


if __name__ == "__main__":
    asyncio.run(main())