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

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    
class GmailCredentials(BaseModel):
    token: str
    refresh_token: str = Field(default=None)
    token_uri: str
    client_id: str
    client_secret: str
    scopes: list

@app.post("/api/process-text")
async def process_text(command: TextCommand):
    try:
        logger.info(f"Received text command: {command.text}")
        return {"transcript": command.text}
    except Exception as e:
        logger.error(f"Error processing text command: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    try:
        logger.info(f"Received file: {file.filename}, content_type: {file.content_type}")
        
        content = await file.read()
        if len(content) == 0:
            logger.error("Received empty file")
            raise HTTPException(status_code=400, detail="Empty audio file received")
        
        logger.info(f"File size: {len(content)} bytes")
        
        file_ext = os.path.splitext(file.filename)[1].lower()
        if not file_ext:
            if 'webm' in file.content_type:
                file_ext = '.webm'
            elif 'mp3' in file.content_type:
                file_ext = '.mp3'
            elif 'wav' in file.content_type:
                file_ext = '.wav'
            elif 'ogg' in file.content_type:
                file_ext = '.ogg'
            else:
                file_ext = '.webm'
        
        file_location = f"temp_recording{file_ext}"
        with open(file_location, "wb") as f:
            f.write(content)
            logger.info(f"Saved file to {file_location}, size: {len(content)} bytes")
        
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
            if os.path.exists(file_location):
                os.remove(file_location)
                logger.info(f"Deleted temporary file {file_location}")
        
        return {"transcript": transcript.text}
    
    except Exception as e:
        logger.error(f"Error in transcribe_audio: {str(e)}")
        if 'file_location' in locals() and os.path.exists(file_location):
            os.remove(file_location)
        raise HTTPException(status_code=500, detail=str(e))

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
        
        creds_dict = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes
        }
        
        logger.info(f"Credentials exchanged: token={credentials.token[:10]}...")
        
        return RedirectResponse(url=f"http://localhost:5173/auth/success?token={credentials.token}")
    except Exception as e:
        logger.error(f"Auth callback error: {str(e)}")
        return RedirectResponse(url=f"http://localhost:5173/auth/error?message={str(e)}")

@app.get("/api/auth/credentials")
async def get_credentials():
    """Return the client ID and client secret for frontend use."""
    try:
        with open('oauth_credentials.json', 'r') as f:
            credentials_data = json.load(f)
        
        return {
            "client_id": credentials_data['web']['client_id'],
            "client_secret": credentials_data['web']['client_secret']
        }
    except Exception as e:
        logger.error(f"Error getting credentials: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/gmail/unread-simple")
async def get_unread_emails_simple(data: dict):
    """Get the count of unread emails using just the token."""
    try:
        token = data.get("token")
        refresh_token = data.get("refresh_token")
        
        if not token:
            raise HTTPException(status_code=400, detail="Token is required")
        
        logger.info(f"Received token for unread-simple: {token[:10]}...")
        
        service, current_token = gmail_service.build_gmail_service_with_token(token, refresh_token)
        result = gmail_service.get_unread_count(service)
        
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

@app.post("/api/gmail/recent-simple")
async def get_recent_emails_simple(data: dict):
    """Get recent emails with metadata using just the token."""
    try:
        token = data.get("token")
        refresh_token = data.get("refresh_token")
        
        if not token:
            raise HTTPException(status_code=400, detail="Token is required")
        
        service, current_token = gmail_service.build_gmail_service_with_token(token, refresh_token)
        emails = gmail_service.get_recent_emails(service)
        
        result = {"emails": emails}
        
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

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)