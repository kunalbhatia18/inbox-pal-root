// src/services/authService.js

// Local storage keys
const TOKEN_KEY = 'inboxpal_token';
const CREDENTIALS_KEY = 'inboxpal_credentials';

// Service to handle authentication
const authService = {
  // Start the login flow
  initiateLogin: async () => {
    try {
      const response = await fetch('http://localhost:8000/api/auth/login');
      const data = await response.json();
      
      // Redirect to Google's auth page
      window.location.href = data.auth_url;
    } catch (error) {
      console.error('Login initiation error:', error);
      throw error;
    }
  },
  
  // Store credentials in local storage
  setCredentials: (credentials) => {
    localStorage.setItem(CREDENTIALS_KEY, JSON.stringify(credentials));
  },
  
  // Get stored credentials
  getCredentials: () => {
    const credentials = localStorage.getItem(CREDENTIALS_KEY);
    return credentials ? JSON.parse(credentials) : null;
  },
  
  // Store token from URL
  setTokenFromUrl: async (token) => {
    localStorage.setItem(TOKEN_KEY, token);
    
    try {
      // Get credential details from backend
      const response = await fetch('http://localhost:8000/api/auth/credentials');
      if (!response.ok) {
        throw new Error(`Error fetching credentials: ${response.status}`);
      }
      
      const credentialData = await response.json();
      console.log("Received credential data:", credentialData);
      
      // Create proper credentials object
      const credentials = {
        token,
        refresh_token: null, // We don't have this in the simple flow
        token_uri: "https://oauth2.googleapis.com/token",
        client_id: credentialData.client_id,
        client_secret: credentialData.client_secret,
        scopes: [
          "https://www.googleapis.com/auth/gmail.readonly",
          "https://www.googleapis.com/auth/gmail.metadata"
        ]
      };
      
      console.log("Setting credentials:", credentials);
      authService.setCredentials(credentials);
      return true;
    } catch (error) {
      console.error("Error setting credentials:", error);
      return false;
    }
  },
  
  // Check if user is logged in
  isLoggedIn: () => {
    return !!localStorage.getItem(TOKEN_KEY);
  },
  
  // Logout user
  logout: () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(CREDENTIALS_KEY);
  }
};

export default authService;