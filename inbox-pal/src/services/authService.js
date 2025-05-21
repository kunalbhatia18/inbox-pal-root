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
  setTokenFromUrl: (token) => {
    localStorage.setItem(TOKEN_KEY, token);
    
    // Also store as credentials (simplified version for now)
    const credentials = {
      token: token,
      // These would come from a proper token exchange in a real app
      refresh_token: null,
      token_uri: "https://oauth2.googleapis.com/token",
      client_id: "YOUR_CLIENT_ID", // This will be replaced with actual value
      client_secret: "YOUR_CLIENT_SECRET", // This will be replaced with actual value
      scopes: [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.metadata"
      ]
    };
    
    authService.setCredentials(credentials);
    return credentials;
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