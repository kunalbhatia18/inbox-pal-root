// src/hooks/useAudioRecorder.jsx
import { useState, useRef, useCallback } from 'react';

const useAudioRecorder = () => {
  const [isRecording, setIsRecording] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [error, setError] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  
  const streamRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  
  // Simple toggle function
  const toggleRecording = useCallback(() => {
    if (isRecording) {
      // Stop recording
      console.log("Stopping recording");
      setIsRecording(false);
      
      if (mediaRecorderRef.current) {
        try {
          mediaRecorderRef.current.stop();
          // MediaRecorder.stop() will trigger the onstop event handler
        } catch (e) {
          console.error("Error stopping recorder:", e);
        }
      }
      
      // Stop all tracks
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
    } else {
      // Start recording
      console.log("Starting recording");
      setError(null);
      setTranscript('');
      chunksRef.current = [];
      
      // Request microphone access
      navigator.mediaDevices.getUserMedia({ audio: true })
        .then(stream => {
          streamRef.current = stream;
          
          // Create a simple recorder
          const recorder = new MediaRecorder(stream);
          mediaRecorderRef.current = recorder;
          
          // Handle data available events
          recorder.ondataavailable = (e) => {
            console.log("Data available:", e.data.size);
            if (e.data.size > 0) {
              chunksRef.current.push(e.data);
            }
          };
          
          // Handle stop event
          recorder.onstop = () => {
            console.log("Recorder stopped, chunks:", chunksRef.current.length);
            
            if (chunksRef.current.length === 0) {
              setError("No audio recorded");
              return;
            }
            
            // Create blob and send to server
            const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
            console.log("Audio blob created:", blob.size);
            
            // Send to server
            sendAudioToServer(blob);
          };
          
          // Start the recorder
          recorder.start(100); // Collect data every 100ms
          setIsRecording(true);
          
          // Automatically stop after 15 seconds (for testing)
          setTimeout(() => {
            if (recorder.state === 'recording') {
              console.log("Auto-stopping after timeout");
              setIsRecording(false);
              recorder.stop();
              
              // Stop tracks
              stream.getTracks().forEach(track => track.stop());
            }
          }, 15000);
        })
        .catch(err => {
          console.error("Microphone access error:", err);
          setError(`Microphone access error: ${err.message}`);
        });
    }
  }, [isRecording]);
  
  // Function to send audio to server
  const sendAudioToServer = async (blob) => {
    if (!blob || blob.size === 0) {
      setError("No audio to transcribe");
      return;
    }
    
    setIsProcessing(true);
    
    try {
      // Create form data
      const formData = new FormData();
      formData.append('file', blob, 'recording.webm');
      
      // Send to server
      console.log("Sending to server, blob size:", blob.size);
      const response = await fetch('http://localhost:8000/api/transcribe', {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }
      
      // Process response
      const data = await response.json();
      console.log("Transcript received:", data);
      setTranscript(data.transcript);
    } catch (err) {
      console.error("Transcription error:", err);
      setError(`Transcription error: ${err.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  // New function to process text input directly
  const processText = async (text) => {
    if (!text || text.trim() === '') {
      return;
    }
    
    setIsProcessing(true);
    setTranscript('');
    setError(null);
    
    try {
      // Send text to backend for processing
      const response = await fetch('http://localhost:8000/api/process-text', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text }),
      });
      
      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }
      
      const data = await response.json();
      setTranscript(data.transcript);
      
    } catch (err) {
      console.error("Text processing error:", err);
      setError(`Text processing error: ${err.message}`);
    } finally {
      setIsProcessing(false);
    }
  };
  
  
  return {
    isRecording,
    isProcessing,
    transcript,
    error,
    toggleRecording,
    processText
  };
};

export default useAudioRecorder;