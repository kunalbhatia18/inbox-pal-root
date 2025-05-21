// src/hooks/useSpeechRecognition.jsx
import { useState, useEffect, useCallback, useRef } from 'react';

const useSpeechRecognition = () => {
  const [transcript, setTranscript] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [error, setError] = useState(null);
  
  const recognitionRef = useRef(null);
  
  useEffect(() => {
    // Check if browser supports speech recognition
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
      setError('Speech recognition is not supported in this browser.');
      return;
    }
    
    // Initialize speech recognition
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognitionRef.current = new SpeechRecognition();
    
    // Configure settings
    recognitionRef.current.continuous = true;
    recognitionRef.current.interimResults = true;
    recognitionRef.current.lang = 'en-US';
    
    // Set up event handlers
    recognitionRef.current.onresult = (event) => {
      const currentTranscript = Array.from(event.results)
        .map(result => result[0].transcript)
        .join('');
      
      setTranscript(currentTranscript);
    };
    
    recognitionRef.current.onerror = (event) => {
      setError(`Speech recognition error: ${event.error}`);
      setIsListening(false);
    };
    
    recognitionRef.current.onend = () => {
      if (isListening) {
        // If still set to listening, restart recognition
        // (this handles the auto-stop after inactivity)
        recognitionRef.current.start();
      }
    };
    
    return () => {
      // Cleanup
      if (recognitionRef.current) {
        recognitionRef.current.onresult = null;
        recognitionRef.current.onerror = null;
        recognitionRef.current.onend = null;
        
        if (isListening) {
          recognitionRef.current.stop();
        }
      }
    };
  }, [isListening]);
  
  const startListening = useCallback(() => {
    setTranscript('');
    setError(null);
    setIsListening(true);
    
    if (recognitionRef.current) {
      try {
        recognitionRef.current.start();
      } catch (err) {
        // Handle the case where start() is called when already started
        console.error('Speech recognition error:', err);
      }
    }
  }, []);
  
  const stopListening = useCallback(() => {
    setIsListening(false);
    
    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }
  }, []);
  
  const toggleListening = useCallback(() => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  }, [isListening, startListening, stopListening]);
  
  return {
    transcript,
    isListening,
    error,
    startListening,
    stopListening,
    toggleListening,
  };
};

export default useSpeechRecognition;