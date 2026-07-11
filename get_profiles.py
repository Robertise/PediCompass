import boto3
from dotenv import load_dotenv

load_dotenv()
client = boto3.client('bedrock', region_name='ap-southeast-1')

print("--- INFERENCE PROFILES ---")
try:
    response = client.list_inference_profiles()
    for profile in response.get('inferenceProfileSummaries', []):
        name = profile.get('inferenceProfileName', '').lower()
        if 'haiku' in name:
            print(f"Profile: {profile.get('inferenceProfileId')} | Name: {profile.get('inferenceProfileName')}")
except Exception as e:
    print(f"Error: {e}")
