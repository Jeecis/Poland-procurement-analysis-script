import os
import json
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def find_procurements():
    keyword = os.getenv("KEYWORD")
    date_from = os.getenv("DATE")

    if not keyword or not date_from:
        print("Error: KEYWORD or DATE environment variables are not set.")
        return

    # 1. Search for tenders
    search_url = (
        f"https://ezamowienia.gov.pl/mp-readmodels/api/Search/SearchTenders"
        f"?title={keyword}&initiationDateFrom={date_from}"
        f"&SortingColumnName=InitiationDate&SortingDirection=DESC&PageNumber=1&PageSize=10"
    )

    print(f"Searching for tenders with keyword '{keyword}' since '{date_from}'...")
    
    try:
        response = requests.get(search_url)
        response.raise_for_status()
        search_results = response.json()
    except requests.RequestException as e:
        print(f"Error searching tenders: {e}")
        return

    tenders_found = []
    print(f"Found {len(search_results)} tenders. Fetching details...")

    # 2. Get details for each tender
    for tender in search_results:
        object_id = tender.get("objectId")
        if not object_id:
            continue
            
        details_url = f"https://ezamowienia.gov.pl/mp-readmodels/api/Search/GetTender?id={object_id}"
        
        try:
            details_response = requests.get(details_url)
            details_response.raise_for_status()
            tender_details = details_response.json()
            tenders_found.append(tender_details)
            print(f"Fetched details for tender: {object_id}")
        except requests.RequestException as e:
            print(f"Error fetching details for tender {object_id}: {e}")

    # 3. Save results to JSON
    output_filename = "procurement_results.json"
    try:
        with open(output_filename, "w", encoding="utf-8") as f:
            json.dump(tenders_found, f, ensure_ascii=False, indent=4)
        print(f"Successfully saved {len(tenders_found)} procurement records to {output_filename}")
    except IOError as e:
        print(f"Error saving results: {e}")

if __name__ == "__main__":
    find_procurements()
