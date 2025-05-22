# inbox-pal-api/gmail_service.py
import os
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from fastapi import HTTPException
import logging
from google.auth.transport.requests import Request
from googleapiclient.errors import HttpError

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

def build_gmail_service_with_token(token, refresh_token=None):
    """Build a Gmail service with token and handle refresh if needed."""
    try:
        # Get credentials from file
        with open('oauth_credentials.json', 'r') as f:
            creds_data = json.load(f)
        
        # Create credentials object
        credentials = Credentials(
            token=token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=creds_data['web']['client_id'],
            client_secret=creds_data['web']['client_secret'],
            scopes=SCOPES
        )
        
        # Check if token is expired and refresh if possible
        if credentials.expired and credentials.refresh_token:
            logger.info("Token expired, attempting to refresh...")
            credentials.refresh(Request())
            logger.info("Token refreshed successfully")
            return build('gmail', 'v1', credentials=credentials), credentials.token
        elif credentials.expired and not credentials.refresh_token:
            logger.error("Token expired and no refresh token available")
            raise HTTPException(status_code=401, detail="Token expired. Please re-authenticate.")
        
        logger.info(f"Building Gmail service with token starting with: {token[:10]}...")
        service = build('gmail', 'v1', credentials=credentials)
        return service, token
        
    except HttpError as http_error:
        if http_error.resp.status in [401, 403]:
            logger.error(f"Gmail API authentication error: {str(http_error)}")
            raise HTTPException(status_code=401, detail="Token expired. Please re-authenticate.")
        else:
            logger.error(f"Gmail API error: {str(http_error)}")
            raise HTTPException(status_code=500, detail=f"Gmail API error: {str(http_error)}")
    except Exception as e:
        logger.error(f"Error building Gmail service with token: {str(e)}")
        if any(phrase in str(e).lower() for phrase in ["invalid_grant", "token has been expired", "invalid_token"]):
            raise HTTPException(status_code=401, detail="Token expired. Please re-authenticate.")
        raise HTTPException(status_code=500, detail=f"Error accessing Gmail API: {str(e)}")

def get_unread_count(service):
    """Get the count of unread emails."""
    try:
        results = service.users().messages().list(
            userId='me',
            labelIds=['UNREAD']
        ).execute()
        
        count = results.get('resultSizeEstimate', 0)
        logger.info(f"Successfully retrieved unread count: {count}")
        
        return {
            'count': count
        }
    except HttpError as http_error:
        if http_error.resp.status in [401, 403]:
            logger.error(f"Gmail API authentication error in get_unread_count: {str(http_error)}")
            raise HTTPException(status_code=401, detail="Token expired. Please re-authenticate.")
        else:
            logger.error(f"Gmail API error in get_unread_count: {str(http_error)}")
            raise HTTPException(status_code=500, detail=f"Gmail API error: {str(http_error)}")
    except Exception as e:
        logger.error(f"Error getting unread count: {str(e)}")
        if any(phrase in str(e).lower() for phrase in ["invalid_grant", "token has been expired", "invalid_token"]):
            raise HTTPException(status_code=401, detail="Token expired. Please re-authenticate.")
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
            
            is_unread = 'UNREAD' in msg.get('labelIds', [])
            
            headers = msg['payload']['headers']
            email_data = {
                'id': msg['id'],
                'snippet': msg.get('snippet', ''),
                'from': next((h['value'] for h in headers if h['name'] == 'From'), ''),
                'subject': next((h['value'] for h in headers if h['name'] == 'Subject'), ''),
                'date': next((h['value'] for h in headers if h['name'] == 'Date'), ''),
                'unread': is_unread
            }
            
            email_list.append(email_data)
        
        logger.info(f"Successfully retrieved {len(email_list)} recent emails")
        return email_list
    except HttpError as http_error:
        if http_error.resp.status in [401, 403]:
            logger.error(f"Gmail API authentication error in get_recent_emails: {str(http_error)}")
            raise HTTPException(status_code=401, detail="Token expired. Please re-authenticate.")
        else:
            logger.error(f"Gmail API error in get_recent_emails: {str(http_error)}")
            raise HTTPException(status_code=500, detail=f"Gmail API error: {str(http_error)}")
    except Exception as e:
        logger.error(f"Error getting recent emails: {str(e)}")
        if any(phrase in str(e).lower() for phrase in ["invalid_grant", "token has been expired", "invalid_token"]):
            raise HTTPException(status_code=401, detail="Token expired. Please re-authenticate.")
        raise HTTPException(status_code=500, detail=f"Error fetching recent emails: {str(e)}")