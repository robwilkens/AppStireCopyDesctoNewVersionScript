#!/opt/anaconda3/bin/python3
import os
import json
import jwt
import requests
import time
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# App Store Connect API credentials
ISSUER_ID = "<insert issuer id here>"  # Team ID
KEY_ID = "<insert key id here>"  # Key ID
APPSTORE_PRIVATE_KEY = """-----BEGIN PRIVATE KEY-----
<insert key here>
-----END PRIVATE KEY-----"""

# Ensure the private key is properly formatted (remove extra whitespace, ensure newlines)
PRIVATE_KEY = "\n".join(line.strip() for line in APPSTORE_PRIVATE_KEY.splitlines() if line.strip())

# Generate JWT for raw requests
def generate_jwt():
    now = int(time.time())
    payload = {
        "iss": ISSUER_ID,
        "iat": now,
        "exp": now + 900,  # 15 minutes expiration
        "aud": "appstoreconnect-v1",
        "kid": KEY_ID
    }
    # Ensure the token is a string (some pyjwt versions return bytes)
    token = jwt.encode(payload, PRIVATE_KEY, algorithm="ES256", headers={"kid": KEY_ID})
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token

# Set up a requests session with retry logic
session = requests.Session()
retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
session.mount("https://", HTTPAdapter(max_retries=retries))

# Fetch apps using raw requests
print("Fetching apps...")
jwt_token = generate_jwt()
headers = {
    "Authorization": f"Bearer {jwt_token}"
}
apps_url = "https://api.appstoreconnect.apple.com/v1/apps?limit=50"
response = session.get(apps_url, headers=headers)
response.raise_for_status()
apps_data = response.json()
apps = apps_data.get("data", [])

# Iterate through each app
for app in apps:
    app_id = app["id"]
    app_name = app["attributes"]["name"]
    print(f"\nApp ID: {app_id}")
    print(f"App Name: {app_name}")
    
    # Fetch app store versions for the app
    try:
        # Fetch all app store versions
        versions_url = f"https://api.appstoreconnect.apple.com/v1/apps/{app_id}/appStoreVersions"
        versions = []
        next_url = versions_url
        while next_url:
            versions_response = session.get(next_url, headers=headers)
            versions_response.raise_for_status()
            versions_data = versions_response.json()
            versions.extend(versions_data.get("data", []))
            next_url = versions_data.get("links", {}).get("next")

        # Find the released version ("READY_FOR_SALE")
        released_version = None
        for version in versions:
            if version["attributes"].get("appStoreState") == "READY_FOR_SALE":
                released_version = version
                break
        
        # Check if a released version was found
        if not released_version:
            print("  No released version (Ready for Sale) found for this app. Skipping.")
            continue
        
        # Get the released version ID and fetch its localizations
        released_version_id = released_version["id"]
        localizations_url = f"https://api.appstoreconnect.apple.com/v1/appStoreVersions/{released_version_id}/appStoreVersionLocalizations"
        localizations_response = session.get(localizations_url, headers=headers)
        localizations_response.raise_for_status()
        localizations_data = localizations_response.json()
        released_localizations = localizations_data.get("data", [])
        
        # Store the descriptions from the released version
        descriptions = {}
        for localization in released_localizations:
            locale = localization["attributes"]["locale"]
            descriptions[locale] = {
                "promotionalText": localization["attributes"].get("promotionalText", "Not set"),
                "whatsNew": localization["attributes"].get("whatsNew", "Not set")
            }
        
        # Print the descriptions being copied
        print("  Descriptions from Released Version (Ready for Sale):")
        for locale, desc in descriptions.items():
            print(f"    Locale: {locale}")
            print(f"      Promotional Text: {desc['promotionalText']}")
            print(f"      Update Description: {desc['whatsNew']}")
        
        # Find the "Prepare for Submission" version
        prepare_version = None
        for version in versions:
            if version["attributes"].get("appStoreState") == "PREPARE_FOR_SUBMISSION":
                prepare_version = version
                break
        
        # Check if a "Prepare for Submission" version was found
        if not prepare_version:
            print("  No version in Prepare for Submission found for this app. Skipping.")
            continue
        
        # Get the "Prepare for Submission" version ID
        prepare_version_id = prepare_version["id"]
        print(f"  Found Prepare for Submission version (ID: {prepare_version_id}). Copying descriptions...")
        
        # Fetch existing localizations for the "Prepare for Submission" version
        prepare_localizations_url = f"https://api.appstoreconnect.apple.com/v1/appStoreVersions/{prepare_version_id}/appStoreVersionLocalizations"
        prepare_localizations_response = session.get(prepare_localizations_url, headers=headers)
        prepare_localizations_response.raise_for_status()
        prepare_localizations_data = prepare_localizations_response.json()
        prepare_localizations = prepare_localizations_data.get("data", [])
        
        # Map existing localizations by locale for easier lookup
        existing_localizations = {loc["attributes"]["locale"]: loc for loc in prepare_localizations}
        
        # Copy descriptions to the "Prepare for Submission" version
        for locale, desc in descriptions.items():
            if locale in existing_localizations:
                # Update existing localization with a PATCH request
                localization_id = existing_localizations[locale]["id"]
                update_url = f"https://api.appstoreconnect.apple.com/v1/appStoreVersionLocalizations/{localization_id}"
                update_data = {
                    "data": {
                        "type": "appStoreVersionLocalizations",
                        "id": localization_id,
                        "attributes": {
                            "promotionalText": desc["promotionalText"],
                            "whatsNew": desc["whatsNew"]
                        }
                    }
                }
                update_response = session.patch(update_url, headers=headers, json=update_data)
                update_response.raise_for_status()
                print(f"    Updated localization for locale {locale} in Prepare for Submission version.")
            else:
                # Create new localization with a POST request
                create_url = f"https://api.appstoreconnect.apple.com/v1/appStoreVersions/{prepare_version_id}/appStoreVersionLocalizations"
                create_data = {
                    "data": {
                        "type": "appStoreVersionLocalizations",
                        "attributes": {
                            "locale": locale,
                            "promotionalText": desc["promotionalText"],
                            "whatsNew": desc["whatsNew"]
                        }
                    }
                }
                create_response = session.post(create_url, headers=headers, json=create_data)
                create_response.raise_for_status()
                print(f"    Created new localization for locale {locale} in Prepare for Submission version.")
        
    except requests.exceptions.HTTPError as http_err:
        print(f"  Error processing app {app_id}: {http_err}")
        print(f"  Response: {http_err.response.text}")
    except Exception as err:
        print(f"  Error processing app {app_id}: {err}")

# Write the full response to a JSON file for debugging
with open('app_descriptions.json', 'w') as out:
    apps_response = response.json()
    out.write(json.dumps(apps_response, indent=4))
print("\nFull API response written to app_descriptions.json")
