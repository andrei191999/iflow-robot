from google.cloud import firestore

# Single shared client (Cloud Run uses ADC; local uses Application Default Credentials)
_client = firestore.Client()

def get_db() -> firestore.Client:
    return _client
