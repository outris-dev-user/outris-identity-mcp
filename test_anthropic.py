import os
import anthropic
import sys

# Load env vars if needed (simple check)
key = os.getenv("ANTHROPIC_API_KEY")
if not key:
    # Try to read from .env if it exists in current dir
    try:
        from dotenv import load_dotenv
        load_dotenv()
        key = os.getenv("ANTHROPIC_API_KEY")
    except ImportError:
        pass

if not key:
    print("ERROR: ANTHROPIC_API_KEY not found in environment")
    sys.exit(1)

client = anthropic.Anthropic(api_key=key)

models_to_test = [
    "claude-3-5-sonnet-20240620", # Known stable
    "claude-sonnet-4-20250514",  # User requested
    "claude-3-5-sonnet-20241022" # The one that failed earlier
]

for model in models_to_test:
    print(f"\n--- Testing model: {model} ---")
    try:
        resp = client.messages.create(
            model=model,
            max_tokens=10,
            messages=[{"role":"user","content":"hi"}]
        )
        print("SUCCESS")
        print(resp.content[0].text)
    except anthropic.NotFoundError as e:
        print(f"FAILED (404 Not Found): {e.message}")
        print("This usually means the model name is invalid or your API Key does not have access to it.")
    except map as e:
        print(f"FAILED (Authentication Error): {e}")
    except Exception as e:
        print(f"FAILED ({type(e).__name__}): {e}")
