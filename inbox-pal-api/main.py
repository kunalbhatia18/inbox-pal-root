# inbox-pal-api/main.py
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import os
import logging
from dotenv import load_dotenv
from pydantic import BaseModel, Field
import json
from fastapi.responses import RedirectResponse
import gmail_service


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get API key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    logger.error("OPENAI_API_KEY not found in environment variables")
    raise ValueError("OPENAI_API_KEY not set. Please set it in your .env file")

# Initialize OpenAI client
client = OpenAI(api_key=api_key)

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TextCommand(BaseModel):
    text: str

# Add these models - note the Field with default=None
class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    
class GmailCredentials(BaseModel):
    token: str
    refresh_token: str = Field(default=None)  # Make it truly optional
    token_uri: str
    client_id: str
    client_secret: str
    scopes: list

@app.post("/api/process-text")
async def process_text(command: TextCommand):
    try:
        logger.info(f"Received text command: {command.text}")
        
        # Here we would process the command
        # For now, just return the text as-is
        # Later this will be integrated with Gmail commands
        
        return {"transcript": command.text}
    
    except Exception as e:
        logger.error(f"Error processing text command: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    try:
        logger.info(f"Received file: {file.filename}, content_type: {file.content_type}")
        
        # Check file size first
        content = await file.read()
        if len(content) == 0:
            logger.error("Received empty file")
            raise HTTPException(status_code=400, detail="Empty audio file received")
        
        logger.info(f"File size: {len(content)} bytes")
        
        # Determine file extension based on content type or filename
        file_ext = os.path.splitext(file.filename)[1].lower()
        if not file_ext:
            # Try to get extension from content type
            if 'webm' in file.content_type:
                file_ext = '.webm'
            elif 'mp3' in file.content_type:
                file_ext = '.mp3'
            elif 'wav' in file.content_type:
                file_ext = '.wav'
            elif 'ogg' in file.content_type:
                file_ext = '.ogg'
            else:
                file_ext = '.webm'  # Default to webm
        
        # Save the uploaded file temporarily with proper extension
        file_location = f"temp_recording{file_ext}"
        with open(file_location, "wb") as f:
            f.write(content)
            logger.info(f"Saved file to {file_location}, size: {len(content)} bytes")
        
        # Transcribe with Whisper API
        try:
            with open(file_location, "rb") as f:
                logger.info(f"Sending file to Whisper API with extension: {file_ext}")
                transcript = client.audio.transcriptions.create(
                    model="whisper-1", 
                    file=f
                )
                logger.info(f"Received transcript: {transcript.text}")
        except Exception as whisper_error:
            logger.error(f"Whisper API error: {str(whisper_error)}")
            raise whisper_error
        finally:
            # Clean up the temporary file
            if os.path.exists(file_location):
                os.remove(file_location)
                logger.info(f"Deleted temporary file {file_location}")
        
        return {"transcript": transcript.text}
    
    except Exception as e:
        logger.error(f"Error in transcribe_audio: {str(e)}")
        if 'file_location' in locals() and os.path.exists(file_location):
            os.remove(file_location)
        raise HTTPException(status_code=500, detail=str(e))
    
# Add these routes after your existing routes
@app.get("/api/auth/login")
async def login():
    """Start the OAuth process by redirecting to Google's auth page."""
    try:
        auth_url = gmail_service.get_authorization_url()
        return {"auth_url": auth_url}
    except Exception as e:
        logger.error(f"Error getting auth URL: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/auth/callback")
async def auth_callback(code: str):
    """Handle the OAuth callback and exchange code for token."""
    try:
        credentials = gmail_service.exchange_code_for_token(code)
        
        # Convert credentials to dict for storage
        creds_dict = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes
        }
        
        # Log the actual credentials (for debugging, remove in production)
        logger.info(f"Credentials exchanged: {creds_dict}")
        
        # In a real app, you would store these credentials securely
        # For now, we'll just redirect to the frontend with a success message
        return RedirectResponse(url=f"http://localhost:5173/auth/success?token={credentials.token}")
    except Exception as e:
        logger.error(f"Auth callback error: {str(e)}")
        return RedirectResponse(url=f"http://localhost:5173/auth/error?message={str(e)}")

@app.get("/api/auth/credentials")
async def get_credentials():
    """Return the client ID and client secret for frontend use."""
    try:
        # Read from oauth_credentials.json
        with open('oauth_credentials.json', 'r') as f:
            credentials_data = json.load(f)
        
        return {
            "client_id": credentials_data['web']['client_id'],
            "client_secret": credentials_data['web']['client_secret']
        }
    except Exception as e:
        logger.error(f"Error getting credentials: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/gmail/unread")
async def get_unread_emails(credentials: GmailCredentials):
    """Get the count of unread emails."""
    try:
        # Log the received credentials for debugging
        logger.info(f"Received credentials for unread: token={credentials.token[:10]}..., client_id={credentials.client_id[:10]}..., client_secret={credentials.client_secret[:5]}...")
        
        # Check if credentials are properly populated
        if credentials.client_id == "YOUR_CLIENT_ID" or credentials.client_secret == "YOUR_CLIENT_SECRET":
            logger.error("Placeholder values detected in credentials")
            # Get proper credentials from the file
            with open('oauth_credentials.json', 'r') as f:
                creds_data = json.load(f)
                credentials.client_id = creds_data['web']['client_id']
                credentials.client_secret = creds_data['web']['client_secret']
        
        service = gmail_service.build_gmail_service(credentials.dict())
        result = gmail_service.get_unread_count(service)
        return result
    except Exception as e:
        logger.error(f"Error getting unread emails: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Add this endpoint to main.py
@app.post("/api/gmail/unread-simple")
async def get_unread_emails_simple(data: dict):
    """Get the count of unread emails using just the token."""
    try:
        token = data.get("token")
        refresh_token = data.get("refresh_token")  # Optional
        
        if not token:
            raise HTTPException(status_code=400, detail="Token is required")
        
        logger.info(f"Received token for unread-simple: {token[:10]}...")
        
        service, current_token = gmail_service.build_gmail_service_with_token(token, refresh_token)
        result = gmail_service.get_unread_count(service)
        
        # If token was refreshed, return the new token
        if current_token != token:
            result['new_token'] = current_token
            logger.info("Token was refreshed, returning new token")
        
        return result
    except HTTPException as http_error:
        logger.error(f"HTTP Error in unread-simple: {str(http_error)}")
        raise http_error
    except Exception as e:
        logger.error(f"Unexpected error getting unread emails: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching unread emails: {str(e)}")

@app.post("/api/gmail/recent")
async def get_recent_emails(credentials: GmailCredentials):
    """Get recent emails with metadata."""
    try:
        service = gmail_service.build_gmail_service(credentials.dict())
        emails = gmail_service.get_recent_emails(service)
        return {"emails": emails}
    except Exception as e:
        logger.error(f"Error getting recent emails: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    

@app.post("/api/gmail/recent-simple")
async def get_recent_emails_simple(data: dict):
    """Get recent emails with metadata using just the token."""
    try:
        token = data.get("token")
        refresh_token = data.get("refresh_token")  # Optional
        
        if not token:
            raise HTTPException(status_code=400, detail="Token is required")
        
        service, current_token = gmail_service.build_gmail_service_with_token(token, refresh_token)
        emails = gmail_service.get_recent_emails(service)
        
        result = {"emails": emails}
        
        # If token was refreshed, return the new token
        if current_token != token:
            result['new_token'] = current_token
            logger.info("Token was refreshed, returning new token")
        
        return result
    except HTTPException as http_error:
        logger.error(f"HTTP Error in recent-simple: {str(http_error)}")
        raise http_error
    except Exception as e:
        logger.error(f"Unexpected error getting recent emails: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching recent emails: {str(e)}")
    
@app.post("/api/process-command")
async def process_command(command: TextCommand):
    """Process voice/text commands and route to appropriate handlers."""
    try:
        logger.info(f"Processing command: {command.text}")
        
        # Use GPT to understand the intent
        intent_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system", 
                    "content": """You are an email assistant. Classify user commands into these categories:
                    - SUMMARIZE_EMAILS: User wants email summaries (e.g., "summarize my emails", "tell me about my emails")
                    - NEXT_EMAIL: User wants the next email (e.g., "next", "next email", "continue")
                    - SKIP_EMAIL: User wants to skip current email (e.g., "skip", "skip this")
                    - MORE_DETAILS: User wants more details about current email (e.g., "tell me more", "read the full email")
                    - STOP: User wants to stop (e.g., "stop", "that's enough", "done")
                    - OTHER: Anything else
                    
                    Respond with just the category name, nothing else."""
                },
                {"role": "user", "content": command.text}
            ],
            max_tokens=10,
            temperature=0
        )
        
        intent = intent_response.choices[0].message.content.strip()
        logger.info(f"Detected intent: {intent}")
        
        return {
            "intent": intent,
            "original_command": command.text,
            "response": f"I understand you want to: {intent.lower().replace('_', ' ')}"
        }
        
    except Exception as e:
        logger.error(f"Error processing command: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/api/gmail/ranked-emails")
async def get_ranked_emails(data: dict):
    """Get emails ranked by importance."""
    try:
        token = data.get("token")
        if not token:
            raise HTTPException(status_code=400, detail="Token is required")
        
        service, current_token = gmail_service.build_gmail_service_with_token(token)
        ranked_emails = gmail_service.rank_emails_by_importance(service)
        
        result = {"emails": ranked_emails}
        if current_token != token:
            result['new_token'] = current_token
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting ranked emails: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/gmail/summarize-email")
async def summarize_email(data: dict):
    """Summarize a specific email."""
    try:
        email_content = data.get("email_content")
        if not email_content:
            raise HTTPException(status_code=400, detail="Email content is required")
        
        # Use GPT to summarize the email
        summary_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are an email assistant. Summarize emails concisely in 2-3 sentences, focusing on key actions needed, important information, and deadlines. Speak naturally as if talking to the user."
                },
                {
                    "role": "user", 
                    "content": f"Summarize this email:\n\nFrom: {email_content.get('from', '')}\nSubject: {email_content.get('subject', '')}\nContent: {email_content.get('body', '')}"
                }
            ],
            max_tokens=150,
            temperature=0.3
        )
        
        summary = summary_response.choices[0].message.content.strip()
        
        return {
            "summary": summary,
            "email_id": email_content.get('id'),
            "subject": email_content.get('subject')
        }
        
    except Exception as e:
        logger.error(f"Error summarizing email: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)