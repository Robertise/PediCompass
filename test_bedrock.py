import boto3
import os
from dotenv import load_dotenv

load_dotenv()

client = boto3.client('bedrock-runtime', region_name='ap-southeast-1')

def test_model(model_id):
    try:
        response = client.invoke_model(
            modelId=model_id,
            body=b'{"anthropic_version": "bedrock-2023-05-31", "max_tokens": 10, "messages": [{"role": "user", "content": "hi"}]}',
            contentType="application/json"
        )
        print(f"SUCCESS: {model_id} works!")
    except Exception as e:
        print(f"FAILED {model_id}: {e}")

test_model("anthropic.claude-haiku-4-5-20251001-v1:0")
test_model("ap.anthropic.claude-haiku-4-5-20251001-v1:0")
test_model("ap.global.anthropic.claude-haiku-4-5-20251001-v1:0")
test_model("anthropic.claude-3-5-haiku-20241022-v1:0")
test_model("ap.anthropic.claude-3-5-haiku-20241022-v1:0")
