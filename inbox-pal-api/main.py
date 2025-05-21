# inbox-pal-api/main.py
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import os
import logging
from dotenv import load_dotenv
from pydantic import BaseModel


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
        if os.path.exists(file_location):
            os.remove(file_location)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)