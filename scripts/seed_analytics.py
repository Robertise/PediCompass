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
    
    # Pre-defined clinical symptom strings
    symptom_pool = [
        "high fever and severe cough",
        "rash on arms and legs",
        "persistent vomiting and diarrhea",
        "difficulty breathing and wheezing",
        "earache and ear pain",
        "high fever and lethargy",
        "cough and runny nose",
        "vomiting and stomach ache",
        "diarrhea and fever",
        "skin rash and itching"
    ]
    
    print("Seeding 20 mock analytics records...")
    
    now = datetime.now(timezone.utc)
    
    for i in range(20):
        days_ago = random.randint(0, 6)
        fake_time = now - timedelta(days=days_ago)
        
        date_partition = fake_time.strftime('%Y-%m-%d')
        ttl = int(fake_time.timestamp()) + (90 * 24 * 60 * 60)
        intent = random.choice(intents)
        
        import uuid
        item = {
            "log_id": str(uuid.uuid4()),
            "timestamp": fake_time.isoformat(),
            "session_id": str(uuid.uuid4()),
            "user_id_hash": "mocked_user",
            "urgency_level": random.choice(urgency_levels),
            "age_group": random.choice(age_groups),
            "iterations": random.randint(1, 2),
            "intent_type": intent,
            "date_partition": date_partition,
            "ttl": ttl
        }
        
        # Only attach symptoms for triage / emergency queries
        if intent in ["triage", "emergency"]:
            item["symptoms"] = random.choice(symptom_pool)

        await db.put_item(store.table_name, item)
        print(f"Inserted record {i+1}/20 - Intent: {intent} - Date: {date_partition}")
        
    print("Seeding complete.")
    
    print("\nVerifying get_analytics_summary(7)...")
    summary = await store.get_analytics_summary(7)
    print("Result:")
    import json
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    asyncio.run(seed_data())
