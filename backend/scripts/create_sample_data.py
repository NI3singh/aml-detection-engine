"""
Sample Data Generator

Generates a CSV file with 50,000 realistic transactions for testing.

The data includes:
- Normal transactions
- Large transactions (to trigger alerts)
- High-frequency patterns
- High-risk country transactions
- Rapid movement chains

Usage:
    python scripts/create_sample_data.py
"""

import csv
import random
from datetime import datetime, timedelta
from decimal import Decimal


# ============================================================================
# Configuration
# ============================================================================

NUM_TRANSACTIONS = 50000
OUTPUT_FILE = "sample_transactions_50k.csv"

# Sample data
TRANSACTION_TYPES = ["WIRE", "ACH", "CARD", "INTERNATIONAL"]
CURRENCIES = ["USD", "EUR", "GBP"]

# Countries (mix of normal and high-risk)
NORMAL_COUNTRIES = ["US", "GB", "CA", "DE", "FR", "AU", "JP", "IT", "ES", "NL"]
HIGH_RISK_COUNTRIES = ["IR", "KP", "SY", "CU", "VE"]  # Will trigger alerts

# Account IDs
ACCOUNT_IDS = [f"ACC{str(i).zfill(4)}" for i in range(1, 201)]  # 200 accounts

# Names
FIRST_NAMES = ["John", "Jane", "Michael", "Sarah", "David", "Emily", "Robert", "Lisa", 
               "William", "Maria", "James", "Jennifer", "Richard", "Linda", "Thomas"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", 
              "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez"]


# ============================================================================
# Helper Functions
# ============================================================================

def generate_name():
    """Generate a random person name."""
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def generate_amount(transaction_type="normal"):
    """
    Generate transaction amount based on type.
    
    Types:
    - normal: $10 - $5,000
    - large: $10,000 - $100,000 (triggers alert)
    - small: $1 - $100 (for high-frequency)
    """
    if transaction_type == "large":
        return round(random.uniform(10000, 100000), 2)
    elif transaction_type == "small":
        return round(random.uniform(1, 100), 2)
    else:  # normal
        return round(random.uniform(10, 5000), 2)


def generate_timestamp(base_time, offset_minutes=0):
    """Generate timestamp with optional offset."""
    return base_time + timedelta(minutes=offset_minutes)


# ============================================================================
# Transaction Pattern Generators
# ============================================================================

def generate_normal_transaction(txn_id, timestamp):
    """Generate a normal transaction."""
    return {
        "transaction_id": f"TXN{txn_id:06d}",
        "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        "amount": generate_amount("normal"),
        "currency": random.choice(CURRENCIES),
        "sender_id": random.choice(ACCOUNT_IDS),
        "sender_name": generate_name(),
        "sender_country": random.choice(NORMAL_COUNTRIES),
        "receiver_id": random.choice(ACCOUNT_IDS),
        "receiver_name": generate_name(),
        "receiver_country": random.choice(NORMAL_COUNTRIES),
        "transaction_type": random.choice(TRANSACTION_TYPES),
        "description": "Regular transaction",
        "reference_number": f"REF{txn_id:06d}"
    }


def generate_large_transaction(txn_id, timestamp):
    """Generate a large transaction (triggers alert)."""
    txn = generate_normal_transaction(txn_id, timestamp)
    txn["amount"] = generate_amount("large")
    txn["description"] = "Large value transfer"
    return txn


def generate_high_risk_country_transaction(txn_id, timestamp):
    """Generate transaction involving high-risk country (triggers alert)."""
    txn = generate_normal_transaction(txn_id, timestamp)
    
    if random.choice([True, False]):
        txn["sender_country"] = random.choice(HIGH_RISK_COUNTRIES)
    else:
        txn["receiver_country"] = random.choice(HIGH_RISK_COUNTRIES)
    
    txn["description"] = "International transfer"
    return txn


def generate_high_frequency_pattern(start_id, timestamp, account_id):
    """Generate high-frequency transactions from same account (triggers alert)."""
    transactions = []
    
    # Generate 15 transactions in 45 minutes
    for i in range(15):
        txn_id = start_id + i
        offset = i * 3  # Every 3 minutes
        
        txn = {
            "transaction_id": f"TXN{txn_id:06d}",
            "timestamp": (timestamp + timedelta(minutes=offset)).strftime("%Y-%m-%d %H:%M:%S"),
            "amount": generate_amount("small"),
            "currency": "USD",
            "sender_id": account_id,
            "sender_name": generate_name(),
            "sender_country": random.choice(NORMAL_COUNTRIES),
            "receiver_id": random.choice(ACCOUNT_IDS),
            "receiver_name": generate_name(),
            "receiver_country": random.choice(NORMAL_COUNTRIES),
            "transaction_type": "ACH",
            "description": f"Rapid transaction {i+1}",
            "reference_number": f"REF{txn_id:06d}"
        }
        transactions.append(txn)
    
    return transactions


def generate_rapid_movement_chain(start_id, timestamp):
    """Generate rapid movement chain A→B→C→D (triggers alert)."""
    transactions = []
    
    # Create chain of 5 accounts
    chain_accounts = random.sample(ACCOUNT_IDS, 5)
    amount = 50000.00  # Start with $50K
    
    for i in range(4):  # 4 hops
        txn_id = start_id + i
        offset = i * 7  # Every 7 minutes
        
        txn = {
            "transaction_id": f"TXN{txn_id:06d}",
            "timestamp": (timestamp + timedelta(minutes=offset)).strftime("%Y-%m-%d %H:%M:%S"),
            "amount": round(amount * 0.95, 2),  # 5% fee each hop
            "currency": "USD",
            "sender_id": chain_accounts[i],
            "sender_name": generate_name(),
            "sender_country": random.choice(NORMAL_COUNTRIES),
            "receiver_id": chain_accounts[i + 1],
            "receiver_name": generate_name(),
            "receiver_country": random.choice(NORMAL_COUNTRIES),
            "transaction_type": "WIRE",
            "description": f"Chain transfer {i+1}",
            "reference_number": f"REF{txn_id:06d}"
        }
        transactions.append(txn)
        amount *= 0.95
    
    return transactions


# ============================================================================
# Main Generation
# ============================================================================

def generate_sample_data():
    """Generate 50,000 sample transactions."""
    
    print("="*60)
    print("🎲 AML Sample Data Generator")
    print("="*60)
    print(f"\n📊 Generating {NUM_TRANSACTIONS:,} transactions...")
    print(f"💾 Output file: {OUTPUT_FILE}\n")
    
    transactions = []
    base_time = datetime(2025, 1, 1, 9, 0, 0)  # Start: Jan 1, 2025, 9:00 AM
    
    txn_id = 1
    
    # Calculate distribution
    num_normal = int(NUM_TRANSACTIONS * 0.85)  # 85% normal
    num_large = int(NUM_TRANSACTIONS * 0.05)  # 5% large
    num_high_risk = int(NUM_TRANSACTIONS * 0.03)  # 3% high-risk
    num_patterns = NUM_TRANSACTIONS - num_normal - num_large - num_high_risk
    
    print(f"📈 Distribution:")
    print(f"   - Normal transactions: {num_normal:,} (85%)")
    print(f"   - Large transactions: {num_large:,} (5%)")
    print(f"   - High-risk country: {num_high_risk:,} (3%)")
    print(f"   - Suspicious patterns: {num_patterns:,} (7%)")
    print()
    
    # Generate normal transactions
    print("⏳ Generating normal transactions...")
    for _ in range(num_normal):
        timestamp = base_time + timedelta(minutes=random.randint(0, 43200))  # 30 days
        txn = generate_normal_transaction(txn_id, timestamp)
        transactions.append(txn)
        txn_id += 1
    
    # Generate large transactions
    print("⏳ Generating large transactions...")
    for _ in range(num_large):
        timestamp = base_time + timedelta(minutes=random.randint(0, 43200))
        txn = generate_large_transaction(txn_id, timestamp)
        transactions.append(txn)
        txn_id += 1
    
    # Generate high-risk country transactions
    print("⏳ Generating high-risk country transactions...")
    for _ in range(num_high_risk):
        timestamp = base_time + timedelta(minutes=random.randint(0, 43200))
        txn = generate_high_risk_country_transaction(txn_id, timestamp)
        transactions.append(txn)
        txn_id += 1
    
    # Generate high-frequency patterns
    print("⏳ Generating high-frequency patterns...")
    num_hf_patterns = num_patterns // 2
    for _ in range(num_hf_patterns // 15):  # Each pattern has 15 txns
        timestamp = base_time + timedelta(minutes=random.randint(0, 43200))
        account = random.choice(ACCOUNT_IDS)
        pattern_txns = generate_high_frequency_pattern(txn_id, timestamp, account)
        transactions.extend(pattern_txns)
        txn_id += len(pattern_txns)
    
    # Generate rapid movement chains
    print("⏳ Generating rapid movement chains...")
    remaining = NUM_TRANSACTIONS - len(transactions)
    for _ in range(remaining // 4):  # Each chain has 4 txns
        timestamp = base_time + timedelta(minutes=random.randint(0, 43200))
        chain_txns = generate_rapid_movement_chain(txn_id, timestamp)
        transactions.extend(chain_txns)
        txn_id += len(chain_txns)
    
    # Fill remaining with normal transactions
    while len(transactions) < NUM_TRANSACTIONS:
        timestamp = base_time + timedelta(minutes=random.randint(0, 43200))
        txn = generate_normal_transaction(txn_id, timestamp)
        transactions.append(txn)
        txn_id += 1
    
    # Sort by timestamp
    print("⏳ Sorting transactions by timestamp...")
    transactions.sort(key=lambda x: x["timestamp"])
    
    # Write to CSV
    print(f"⏳ Writing to {OUTPUT_FILE}...")
    
    fieldnames = [
        "transaction_id", "timestamp", "amount", "currency",
        "sender_id", "sender_name", "sender_country",
        "receiver_id", "receiver_name", "receiver_country",
        "transaction_type", "description", "reference_number"
    ]
    
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(transactions)
    
    print("\n" + "="*60)
    print("✅ Sample data generated successfully!")
    print("="*60)
    print(f"\n📁 File: {OUTPUT_FILE}")
    print(f"📊 Total transactions: {len(transactions):,}")
    print("\n💡 Next steps:")
    print(f"   1. Start the application")
    print(f"   2. Login and go to Upload page")
    print(f"   3. Upload {OUTPUT_FILE}")
    print(f"   4. Wait for processing (may take 30-60 seconds)")
    print(f"   5. View generated alerts on Dashboard")
    print("="*60 + "\n")


if __name__ == "__main__":
    generate_sample_data()