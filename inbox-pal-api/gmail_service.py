# inbox-pal-api/gmail_service.py
import os
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from fastapi import HTTPException
import logging
from google.auth.transport.requests import Request

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
        
    except Exception as e:
        logger.error(f"Error building Gmail service with token: {str(e)}")
        if "invalid_grant" in str(e) or "Token has been expired" in str(e) or "invalid_token" in str(e):
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
    except Exception as e:
        logger.error(f"Error getting unread count: {str(e)}")
        if "invalid_grant" in str(e) or "Token has been expired" in str(e) or "invalid_token" in str(e):
            raise HTTPException(status_code=401, detail="Token expired. Please re-authenticate.")
        raise HTTPException(status_code=500, detail=f"Error fetching unread emails: {str(e)}")

def get_recent_emails(service, max_results=5):
    """Get recent emails with basic metadata."""
    try:
        # First get list of messages (without using q parameter)
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
            
            # Check if 'UNREAD' is in the labelIds
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
    except Exception as e:
        logger.error(f"Error getting recent emails: {str(e)}")
        if "invalid_grant" in str(e) or "Token has been expired" in str(e):
            raise HTTPException(status_code=401, detail="Token expired. Please re-authenticate.")
        raise HTTPException(status_code=500, detail=f"Error fetching recent emails: {str(e)}")
    
# Add this function to gmail_service.py
def rank_emails_by_importance(service, max_results=10):
    """Get emails and rank them by importance using AI."""
    try:
        # Get recent emails
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
                format='full'  # Get full content for better analysis
            ).execute()
            
            # Extract email content
            headers = msg['payload'].get('headers', [])
            from_email = next((h['value'] for h in headers if h['name'].lower() == 'from'), '')
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), '')
            date = next((h['value'] for h in headers if h['name'].lower() == 'date'), '')
            
            # Get email body
            body = extract_email_body(msg['payload'])
            
            email_data = {
                'id': msg['id'],
                'from': from_email,
                'subject': subject,
                'date': date,
                'body': body[:500],  # First 500 chars for analysis
                'full_body': body,
                'unread': 'UNREAD' in msg.get('labelIds', []),
                'importance_score': 0  # Will be set by AI
            }
            
            email_list.append(email_data)
        
        # Use AI to rank importance
        ranked_emails = rank_with_ai(email_list)
        
        logger.info(f"Successfully ranked {len(ranked_emails)} emails by importance")
        return ranked_emails
        
    except Exception as e:
        logger.error(f"Error ranking emails: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error ranking emails: {str(e)}")

def extract_email_body(payload):
    """Extract text content from email payload."""
    body = ""
    
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                data = part['body']['data']
                body = base64.urlsafe_b64decode(data).decode('utf-8')
                break
    elif payload['mimeType'] == 'text/plain':
        data = payload['body']['data']
        body = base64.urlsafe_b64decode(data).decode('utf-8')
    
    return body

def rank_with_ai(emails):
    """Use AI to rank emails by importance."""
    import openai
    import os
    
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    # Create email summaries for AI analysis
    email_summaries = []
    for i, email in enumerate(emails):
        summary = f"Email {i+1}: From: {email['from']}, Subject: {email['subject']}, Preview: {email['body'][:200]}..."
        email_summaries.append(summary)
    
    prompt = f"""Rank these emails from most important (1) to least important based on:
- Urgency keywords (urgent, asap, deadline, etc.)
- Sender importance (boss, client, important domains)
- Subject matter (meetings, deadlines, questions, etc.)
- Content urgency

Emails:
{chr(10).join(email_summaries)}

Respond with just the numbers in order of importance (e.g., "3,1,5,2,4"):"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=50,
            temperature=0
        )
        
        # Parse the ranking
        ranking_str = response.choices[0].message.content.strip()
        rankings = [int(x.strip()) - 1 for x in ranking_str.split(',')]
        
        # Reorder emails based on AI ranking
        ranked_emails = [emails[i] for i in rankings if i < len(emails)]
        
        return ranked_emails
        
    except Exception as e:
        logger.error(f"Error in AI ranking: {str(e)}")
        # Fallback: return emails sorted by unread status
        return sorted(emails, key=lambda x: x['unread'], reverse=True)