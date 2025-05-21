// src/App.jsx
import { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom';
import { MicrophoneIcon, PaperAirplaneIcon } from '@heroicons/react/24/solid';
import useAudioRecorder from './hooks/useAudioRecorder';
import authService from './services/authService';
import gmailService from './services/gmailService';

// Home component with voice assistant
function Home() {
  const { 
    isRecording, 
    isProcessing,
    transcript, 
    error, 
    toggleRecording,
    processText
  } = useAudioRecorder();
  
  const [inputText, setInputText] = useState('');
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [emailStats, setEmailStats] = useState(null);
  const navigate = useNavigate();
  
  // Check authentication status
  useEffect(() => {
    const checkAuth = async () => {
      const loggedIn = authService.isLoggedIn();
      setIsAuthenticated(loggedIn);
      
      if (loggedIn) {
        try {
          // Fetch email stats
          const unreadData = await gmailService.getUnreadCount();
          setEmailStats(unreadData);
        } catch (err) {
          console.error('Error fetching email data:', err);
        }
      }
    };
    
    checkAuth();
  }, []);
  
  const handleLogin = () => {
    authService.initiateLogin();
  };
  
  const handleSubmitText = (e) => {
    e.preventDefault();
    if (inputText.trim()) {
      processText(inputText);
      setInputText('');
    }
  };
  
  return (
    <div className="min-h-screen bg-background text-primary font-sans">
      <div className="container-center py-8">
        <h1 className="text-3xl font-bold mb-6">InboxPal</h1>
        
        {!isAuthenticated ? (
          <div className="p-6 border border-gray-200 rounded-lg shadow-sm text-center">
            <p className="mb-4">Connect your Gmail account to get started</p>
            <button 
              onClick={handleLogin}
              className="btn btn-primary"
            >
              Login with Google
            </button>
          </div>
        ) : (
          <div className="p-6 border border-gray-200 rounded-lg shadow-sm">
            <div className="mb-4">
              <p className="text-secondary">
                Your voice email assistant
              </p>
              <p className="text-xs text-gray-500 mt-1">
                Speak or type your commands
              </p>
              
              {emailStats && (
                <div className="mt-2 p-2 bg-blue-50 rounded-md">
                  <p className="text-sm text-blue-800">
                    You have {emailStats.count} unread emails
                  </p>
                </div>
              )}
            </div>
            
            {error && (
              <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-md">
                {error}
              </div>
            )}
            
            <div className="mt-4 mb-6 min-h-20 p-4 bg-gray-50 rounded-md text-left">
              {isProcessing ? (
                <p className="text-gray-400 italic">Processing...</p>
              ) : transcript ? (
                <p>{transcript}</p>
              ) : (
                <p className="text-gray-400 italic">
                  {isRecording 
                    ? 'Recording in progress... Speak now' 
                    : 'Tap the microphone button to speak or type below...'}
                </p>
              )}
            </div>
            
            {/* Text Input Form */}
            <form onSubmit={handleSubmitText} className="flex gap-2 mb-4">
              <input
                type="text"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                placeholder="Type your command here..."
                className="flex-1 p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-accent"
                disabled={isRecording || isProcessing}
              />
              <button 
                type="submit"
                disabled={isRecording || isProcessing || !inputText.trim()}
                className="btn btn-primary p-2 rounded-md"
                aria-label="Send text command"
              >
                <PaperAirplaneIcon className="h-5 w-5 text-white" />
              </button>
            </form>
            
            {/* Voice Button */}
            <div className="flex justify-center mt-4">
              <button 
                className={`btn ${isRecording ? 'bg-red-500' : 'btn-primary hover:opacity-90'} p-4 rounded-full`}
                onClick={toggleRecording}
                disabled={isProcessing}
              >
                <MicrophoneIcon className="h-6 w-6 text-white" />
              </button>
            </div>
            
            <div className="mt-4 text-center text-secondary">
              {isProcessing ? 'Processing...' : isRecording ? 'Recording - Tap to stop' : 'Tap to speak'}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// Auth Success Component
function AuthSuccess() {
  const location = useLocation();
  const navigate = useNavigate();
  const [error, setError] = useState(null);
  
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const token = params.get('token');
    
    if (token) {
      try {
        // Store the token
        authService.setTokenFromUrl(token);
        
        // Redirect to home
        navigate('/');
      } catch (err) {
        setError('Failed to process authentication');
        console.error(err);
      }
    } else {
      setError('No token received');
    }
  }, [location, navigate]);
  
  return (
    <div className="min-h-screen bg-background text-primary font-sans flex items-center justify-center">
      <div className="p-6 border border-gray-200 rounded-lg shadow-sm text-center">
        {error ? (
          <>
            <p className="text-red-600 mb-4">{error}</p>
            <button 
              onClick={() => navigate('/')}
              className="btn btn-primary"
            >
              Go back to home
            </button>
          </>
        ) : (
          <p>Authenticating... Please wait.</p>
        )}
      </div>
    </div>
  );
}

// Auth Error Component
function AuthError() {
  const location = useLocation();
  const navigate = useNavigate();
  
  // Get error message from URL
  const errorMessage = new URLSearchParams(location.search).get('message') || 'Authentication failed';
  
  return (
    <div className="min-h-screen bg-background text-primary font-sans flex items-center justify-center">
      <div className="p-6 border border-gray-200 rounded-lg shadow-sm text-center">
        <p className="text-red-600 mb-4">{errorMessage}</p>
        <button 
          onClick={() => navigate('/')}
          className="btn btn-primary"
        >
          Go back to home
        </button>
      </div>
    </div>
  );
}

// Main App with Router
function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/auth/success" element={<AuthSuccess />} />
        <Route path="/auth/error" element={<AuthError />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}

export default App;