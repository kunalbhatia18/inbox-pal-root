// src/App.jsx
import { useState } from 'react';
import { MicrophoneIcon, PaperAirplaneIcon } from '@heroicons/react/24/solid';
import useAudioRecorder from './hooks/useAudioRecorder';

function App() {
  const { 
    isRecording, 
    isProcessing,
    transcript, 
    error, 
    toggleRecording,
    processText // We'll add this function to the hook
  } = useAudioRecorder();
  
  const [inputText, setInputText] = useState('');
  
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
        
        <div className="p-6 border border-gray-200 rounded-lg shadow-sm">
          <div className="mb-4">
            <p className="text-secondary">
              Your voice email assistant
            </p>
            <p className="text-xs text-gray-500 mt-1">
              Speak or type your commands
            </p>
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
      </div>
    </div>
  );
}

export default App;