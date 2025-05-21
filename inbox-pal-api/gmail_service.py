# inbox-pal-api/gmail_service.py
import os
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

# Scopes required for the Gmail API
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.metadata'
]

# Load the credentials from file
try:
    with open('oauth_credentials.json', 'r') as f:
        credentials_data = json.load(f)
    
    CLIENT_ID = credentials_data['web']['client_id']
    CLIENT_SECRET = credentials_data['web']['client_secret']
    REDIRECT_URI = 'http://localhost:8000/api/auth/callback'
except Exception as e:
    logger.error(f"Error loading OAuth credentials: {str(e)}")
    raise

def create_oauth_flow():
    """Create a new OAuth flow instance."""
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI]
            }
        },
        scopes=SCOPES
    )
    flow.redirect_uri = REDIRECT_URI
    return flow

def get_authorization_url():
    """Get the authorization URL for the OAuth flow."""
    flow = create_oauth_flow()
    auth_url, _ = flow.authorization_url(
        access_type='offline',
        prompt='consent',
        include_granted_scopes='true'
    )
    return auth_url

def exchange_code_for_token(code):
    """Exchange the authorization code for an access token."""
    try:
        flow = create_oauth_flow()
        flow.fetch_token(code=code)
        return flow.credentials
    except Exception as e:
        logger.error(f"Error exchanging code for token: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error getting access token: {str(e)}")

def build_gmail_service(credentials_dict):
    """Build and return a Gmail service object."""
    try:
        credentials = Credentials(
            token=credentials_dict["token"],
            refresh_token=credentials_dict.get("refresh_token"),
            token_uri=credentials_dict["token_uri"],
            client_id=credentials_dict["client_id"],
            client_secret=credentials_dict["client_secret"],
            scopes=credentials_dict["scopes"]
        )
        
        return build('gmail', 'v1', credentials=credentials)
    except Exception as e:
        logger.error(f"Error building Gmail service: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error accessing Gmail API: {str(e)}")

def get_unread_count(service):
    """Get the count of unread emails."""
    try:
        results = service.users().messages().list(
            userId='me',
            q='is:unread'
        ).execute()
        
        return {
            'count': results.get('resultSizeEstimate', 0)
        }
    except Exception as e:
        logger.error(f"Error getting unread count: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching unread emails: {str(e)}")

def get_recent_emails(service, max_results=5):
    """Get recent emails with basic metadata."""
    try:
        results = service.users().messages().list(
            userId='me',
            maxResults=max_results
        ).execute()
        
        messages = results.get('messages', [])
        email_list = []
        
        for message in messages:
            msg = service.users().messages().get(
                userId='me',
                id=message['id'],
                format='metadata',
                metadataHeaders=['From', 'Subject', 'Date']
            ).execute()
            
            headers = msg['payload']['headers']
            email_data = {
                'id': msg['id'],
                'snippet': msg.get('snippet', ''),
                'from': next((h['value'] for h in headers if h['name'] == 'From'), ''),
                'subject': next((h['value'] for h in headers if h['name'] == 'Subject'), ''),
                'date': next((h['value'] for h in headers if h['name'] == 'Date'), ''),
                'unread': 'UNREAD' in msg.get('labelIds', [])
            }
            
            email_list.append(email_data)
        
        return email_list
    except Exception as e:
        logger.error(f"Error getting recent emails: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching recent emails: {str(e)}")