# AppStoreCopyDesctoNewVersionScript
For app store API: Copies "Promo description" and "Update Description" from "READY FOR SALE" version to "PREPARE FOR SUBMISSION" version for all locales for all apps

This takes any apps that are in a "PREPARE FOR SUBMISSION" state and copies all locale descriptions for PROMO and UPDATE which are blank by default, and replaces them with the READY FOR SALE version of these fields.   Suggest you update them after copying them, but this is a start without a lot of copy and pasting.  Also, if you have a lot of translations, this makes life easier if you don't normally ranslate the update or promo text for each language, for example, but they have to be filled in.
---

Insert your:
-Issuer ID
-Key ID
-App store private key

into the file where it has:

# App Store Connect API credentials
ISSUER_ID = "<insert issuer id here>"  # Team ID
KEY_ID = "<insert key id here>"  # Key ID
APPSTORE_PRIVATE_KEY = """-----BEGIN PRIVATE KEY-----
<insert key here>
-----END PRIVATE KEY-----"""

Then run it from python (pyinstaller works to install it for launching with double click on mac too)

This script is not copyrightable as it was generated by an AI tool (SuperGrok 3 from xAI) with hours of prompting to get a working script just right (there were initially errors getting the key to work, but for me it's working now).
