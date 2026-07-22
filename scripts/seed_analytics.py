import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../backend'))

from db.dynamodb_client import get_dynamodb_client
from db.analytics_store import AnalyticsStore
import random
from datetime import datetime, timedelta, timezone

async def seed_data():
    db = get_dynamodb_client()
    # Wait for tables just in case
    await db.ensure_tables_exist()
    
    store = AnalyticsStore(db)
    
    urgency_levels = ["emergency", "consult_hcp", "self_care", "routine"]
    age_groups = ["newborn", "young_infant", "infant", "toddler", "preschool"]
    intents = ["triage", "triage", "general", "greeting", "confirmation"]
    
    # Pre-defined symptom strings with common words that aren't stop words
    symptom_pool = [
        "high fever and severe cough",
        "mild rash on the arms and legs",
        "vomiting and diarrhea since yesterday",
        "difficulty breathing and wheezing",
        "ear pain and crying",
        "high fever and no appetite",
        "cough and runny nose",
        "vomiting and stomach ache",
        "diarrhea and fever",
        "rash and itching"
    ]
    
    print("Seeding 20 mock analytics records...")
    
    now = datetime.now(timezone.utc)
    
    for i in range(20):
        # Fake a time in the last 7 days
        days_ago = random.randint(0, 6)
        fake_time = now - timedelta(days=days_ago)
        
        date_partition = fake_time.strftime('%Y-%m-%d')
        ttl = int(fake_time.timestamp()) + (90 * 24 * 60 * 60)
        
        import uuid
        item = {
            "log_id": str(uuid.uuid4()),
            "timestamp": fake_time.isoformat(),
            "session_id": str(uuid.uuid4()),
            "user_id_hash": "mocked_user",
            "urgency_level": random.choice(urgency_levels),
            "age_group": random.choice(age_groups),
            "iterations": random.randint(1, 2),
            "intent_type": random.choice(intents),
            "date_partition": date_partition,
            "ttl": ttl,
            "symptoms": random.choice(symptom_pool)
        }
        await db.put_item(store.table_name, item)
        print(f"Inserted record {i+1}/20 - Date: {date_partition}")
        
    print("Seeding complete.")
    
    print("\nVerifying get_analytics_summary(7)...")
    summary = await store.get_analytics_summary(7)
    print("Result:")
    import json
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    asyncio.run(seed_data())
