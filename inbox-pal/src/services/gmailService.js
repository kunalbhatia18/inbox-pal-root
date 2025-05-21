// src/services/gmailService.js
import authService from './authService';

const gmailService = {
  // Get the count of unread emails
  getUnreadCount: async () => {
    try {
      const credentials = authService.getCredentials();
      
      if (!credentials) {
        throw new Error('Not authenticated');
      }
      
      const response = await fetch('http://localhost:8000/api/gmail/unread', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(credentials)
      });
      
      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error getting unread count:', error);
      throw error;
    }
  },
  
  // Get recent emails
  getRecentEmails: async () => {
    try {
      const credentials = authService.getCredentials();
      
      if (!credentials) {
        throw new Error('Not authenticated');
      }
      
      const response = await fetch('http://localhost:8000/api/gmail/recent', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(credentials)
      });
      
      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error getting recent emails:', error);
      throw error;
    }
  }
};

export default gmailService;