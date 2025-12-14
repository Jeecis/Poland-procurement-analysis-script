import os
import json
import time
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

# Initialize OpenAI client after loading env
api_key = os.environ.get("OPENAI_API_KEY")
if api_key:
    client = OpenAI(api_key=api_key)
else:
    client = None

# Paths
SCRIPT_DIR = Path(__file__).parent
DOWNLOADS_DIR = SCRIPT_DIR / "downloads"
RESPONSES_DIR = SCRIPT_DIR / "responses"
PROMPT_FILE = SCRIPT_DIR / "Prompt.md"
PROCUREMENT_JSON = SCRIPT_DIR / "procurement_results.json"

# Read system prompt from file
with open(PROMPT_FILE, 'r', encoding='utf-8') as f:
    SYSTEM_PROMPT = f.read()

# Read procurement results
# Creates a lookup dictionary to find tender details by the short ID used in folder names
tender_lookup = {}
if PROCUREMENT_JSON.exists():
    with open(PROCUREMENT_JSON, 'r', encoding='utf-8') as f:
        try:
            raw_data = json.load(f)
            # raw_data should be a list of tenders
            for tender in raw_data:
                obj_id = tender.get("objectId", "")
                if obj_id:
                    # Map the first 8 characters to the full tender object
                    short_id = obj_id[:8]
                    tender_lookup[short_id] = tender
        except json.JSONDecodeError:
            print("Error parsing procurement_results.json")


def upload_file_to_openai(file_path):
    """
    Upload a file to OpenAI for use with the Responses API.
    Files are uploaded with purpose='user_data' as per docs.
    Returns the file_id on success, or None on failure.
    """
    try:
        uploaded_file = client.files.create(
            file=open(file_path, "rb"),
            purpose="user_data",
        )
        return uploaded_file.id
    except Exception as e:
        print(f"⚠ Error uploading {file_path.name}: {e}")
        return None


def call_gpt_for_procurement(year, procurement_id, files):
    """
    Call GPT-5-mini via the Responses API for a single procurement.
    All files for that procurement are uploaded and passed as input_file items.
    """
    print(f"\n📞 Calling GPT-5-mini for {procurement_id}...")
    print(f"   Files to process: {len(files)}")

    if client is None:
        err = "OpenAI client not initialized - OPENAI_API_KEY missing"
        print(f"   ❌ Error calling GPT-5-mini: {err}")
        return {
            "error": err,
            "procurement_id": procurement_id,
            "year": year,
        }

    # 1) Upload all files and collect file_ids
    file_ids = []
    for file_path in files:
        if not file_path.is_file():
            continue
        
        # Skip report files or hidden files
        if file_path.name.startswith('.') or file_path.suffix == '.md':
            continue

        file_id = upload_file_to_openai(file_path)
        if file_id:
            file_ids.append(file_id)
            print(f"   📤 Uploaded: {file_path.name} -> {file_id}")
        else:
            print(f"   ⚠ Skipping (upload failed): {file_path.name}")

    if not file_ids:
        err = "No files could be uploaded for this procurement"
        print(f"   ❌ {err}")
        return {
            "error": err,
            "procurement_id": procurement_id,
            "year": year,
        }

    # 2) Build the input for Responses API
    user_content = [
        {
            "type": "input_text",
            "text": (
                SYSTEM_PROMPT
                + "\n\n"
                + f"Now analyze the following tender documents for procurement ID {procurement_id} "
                f"in year {year}. Use all attached files as context and return ONLY the JSON "
                f"""object as specified in the instructions (no extra text, no explanations)."""
            ),
        }
    ]

    # Attach all files
    for fid in file_ids:
        user_content.append({
            "type": "input_file",
            "file_id": fid,
        })

    messages = [
        {
            "role": "user",
            "content": user_content,
        }
    ]

    try:
        # 3) Call the Responses API
        response = client.responses.create(
            model="gpt-5-mini",
            input=messages,
        )

        # Prefer the convenience helper if present
        text_out = getattr(response, "output_text", None)

        if not text_out:
            # Fallback: try to dig into output[0].content[...]
            text_out = ""
            if getattr(response, "output", None):
                for item in response.output:
                    if not getattr(item, "content", None):
                        continue
                    for c in item.content:
                        if getattr(c, "type", None) == "output_text":
                            if isinstance(c.text, str):
                                text_out += c.text
                            else:
                                value = getattr(c.text, "value", None)
                                if isinstance(value, str):
                                    text_out += value

        if not text_out:
            raise ValueError("No text output in response")

        text_out = text_out.strip()

        # 4) Try to parse JSON; fallback to raw text
        try:
            json_result = json.loads(text_out)
        except Exception:
            json_result = {"text": text_out}

        print(f"   ✅ Successfully processed {procurement_id}")
        return json_result

    except Exception as e:
        print(f"   ❌ Error calling GPT-5-mini: {e}")
        return {
            "error": str(e),
            "procurement_id": procurement_id,
            "year": year,
        }


def process_all_procurements():
    """Main function to process all procurements from downloads/ into responses/"""
    print("🚀 Starting procurement processing...")
    print(f"📁 Downloads directory: {DOWNLOADS_DIR}")
    print(f"💾 Responses directory: {RESPONSES_DIR}")

    # Create responses directory
    RESPONSES_DIR.mkdir(exist_ok=True)

    if not DOWNLOADS_DIR.exists():
        print(f"❌ Downloads directory not found: {DOWNLOADS_DIR}")
        return

    # Iterate through all subdirectories in downloads/
    for procurement_dir in sorted(DOWNLOADS_DIR.iterdir()):
        if not procurement_dir.is_dir():
            continue

        folder_name = procurement_dir.name
        
        # Try to extract the short ID from the folder name (format: {8chars}_{title})
        parts = folder_name.split('_')
        short_id = parts[0] if parts else folder_name
        
        # Look up year/details from JSON if possible
        year = "Unknown"
        full_id = folder_name
        
        tender_info = tender_lookup.get(short_id)
        if tender_info:
            full_id = tender_info.get('objectId', full_id)
            init_date = tender_info.get('initiationDate')
            if init_date:
                year = init_date[:4]

        print(f"\n{'=' * 60}")
        print(f"📦 Processing: {folder_name} (ID: {short_id}, Year: {year})")
        
        # Check if already processed
        # We use the folder name as the filename for the response to keep it safe
        response_file = RESPONSES_DIR / f"{folder_name}.json"
        
        if response_file.exists():
            print(f"   ⏭ Skipping (already processed)")
            continue

        # Gather all files in procurement directory (recursively not needed usually, but just iterate top level)
        files = []
        for file_path in procurement_dir.iterdir():
            if file_path.is_file():
                files.append(file_path)
                print(f"   📄 Found: {file_path.name}")

        if not files:
            print(f"   ⚠ No files found in directory")
            continue

        # Call GPT for this procurement
        result = call_gpt_for_procurement(year, full_id, files)

        # Save response
        with open(response_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"   💾 Saved to: {response_file}")

        # Simple rate limiting between requests
        time.sleep(2)

    print("\n" + "=" * 60)
    print("✅ Processing complete!")
    print("=" * 60)


if __name__ == "__main__":
    # Check for API key
    if not os.environ.get("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY environment variable not set")
        print("Please set it with: $env:OPENAI_API_KEY='your-api-key-here'")
        exit(1)

    process_all_procurements()
