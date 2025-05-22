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
    error: recordingError, 
    toggleRecording,
    processText
  } = useAudioRecorder();
  
  const [inputText, setInputText] = useState('');
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [emailStats, setEmailStats] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();
  
  // Check authentication status
  // Inside the Home component useEffect in App.jsx
  useEffect(() => {
    const checkAuth = async () => {
      setIsLoading(true);
      const loggedIn = authService.isLoggedIn();
      setIsAuthenticated(loggedIn);
      
      if (loggedIn) {
        try {
          const unreadData = await gmailService.getUnreadCount();
          setEmailStats(unreadData);
          setIsLoading(false);
        } catch (err) {
          console.error('Error fetching email data:', err);
          
          // Check if it's a session expiration
          if (err.message === 'SESSION_EXPIRED') {
            // Clear auth state and show login screen
            setIsAuthenticated(false);
            setEmailStats(null);
            setError('Your session has expired. Please log in again.');
          } else {
            setError(`Failed to load email data: ${err.message}`);
          }
          setIsLoading(false);
        }
      } else {
        setIsLoading(false);
      }
    };
    
    checkAuth();
  }, []);
  
  const handleLogin = () => {
    authService.initiateLogin();
  };
  
  const handleLogout = () => {
    authService.logout();
    setIsAuthenticated(false);
    setEmailStats(null);
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
        
        {isLoading ? (
          <div className="p-6 border border-gray-200 rounded-lg shadow-sm text-center">
            <p className="mb-4">Loading...</p>
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent mx-auto"></div>
          </div>
        ) : !isAuthenticated ? (
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
            <div className="flex justify-between items-center mb-4">
              <div>
                <p className="text-secondary">
                  Your voice email assistant
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  Speak or type your commands
                </p>
              </div>
              <button 
                onClick={handleLogout}
                className="text-sm text-red-600 hover:underline"
              >
                Logout
              </button>
            </div>
            
            {error && (
              <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-md">
                {error}
              </div>
            )}
            
            {emailStats && (
              <div className="mt-2 p-2 bg-blue-50 rounded-md">
                <p className="text-sm text-blue-800">
                  You have {emailStats.count} unread emails
                </p>
              </div>
            )}
            
            {recordingError && (
              <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-md">
                {recordingError}
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
  const [isLoading, setIsLoading] = useState(true);
  
  useEffect(() => {
    const processAuth = async () => {
      const params = new URLSearchParams(location.search);
      const token = params.get('token');
      
      if (token) {
        try {
          // Store the token and get credentials
          const success = await authService.setTokenFromUrl(token);
          
          if (success) {
            // Navigate to home after a short delay
            setTimeout(() => {
              navigate('/');
            }, 1500);
          } else {
            setError('Failed to set credentials');
          }
        } catch (err) {
          setError(`Failed to process authentication: ${err.message}`);
          console.error(err);
        } finally {
          setIsLoading(false);
        }
      } else {
        setError('No token received');
        setIsLoading(false);
      }
    };
    
    processAuth();
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
          <>
            <p>Authentication successful! Redirecting...</p>
            {isLoading && (
              <div className="mt-4">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent mx-auto"></div>
              </div>
            )}
          </>
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