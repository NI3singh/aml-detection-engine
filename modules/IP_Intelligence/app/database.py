# app/database.py

from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class Database:
    client: AsyncIOMotorClient = None
    
    def connect(self):
        """Establish connection to MongoDB."""
        try:
            self.client = AsyncIOMotorClient(settings.MONGODB_URL)
            # Motor is "lazy" - it doesn't actually connect until the first query.
            # We force a connection check on startup to fail fast if DB is down.
            logger.info("✅ MongoDB Client initialized")
        except Exception as e:
            logger.error(f"❌ Could not connect to MongoDB: {e}")
            raise e

    def close(self):
        """Close the connection."""
        if self.client:
            self.client.close()
            logger.info("🛑 MongoDB connection closed")

    def get_db(self):
        """Get the database instance."""
        return self.client[settings.DB_NAME]

# Create a global instance
db_client = Database()

# --- Collection Helpers ---
# These functions ensure we always use the correct DB and Collection names
# Usage in other files: from app.database import get_vpn_collection

def get_vpn_collection():
    """Returns the 'vpn_ips' collection object."""
    return db_client.get_db()["vpn_ips"]

def get_clean_collection():
    """Returns the 'clean_ips' collection object."""
    return db_client.get_db()["clean_ips"]

def get_tor_collection():
    """Returns the 'tor_ips' collection object."""
    return db_client.get_db()["tor_ips"]