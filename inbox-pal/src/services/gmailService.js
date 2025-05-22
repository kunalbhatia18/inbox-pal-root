// src/services/gmailService.js
import authService from './authService';

const gmailService = {
  // Get the count of unread emails
  getUnreadCount: async () => {
    try {
      const token = localStorage.getItem('inboxpal_token');
      
      if (!token) {
        throw new Error('Not authenticated');
      }
      
      const response = await fetch('http://localhost:8000/api/gmail/unread-simple', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ token })
      });
      
      if (response.status === 401) {
        // Token expired, clear localStorage and redirect to login
        console.log('Token expired, clearing auth data');
        authService.logout();
        window.location.reload(); // This will show the login screen
        throw new Error('Session expired. Please log in again.');
      }
      
      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }
      
      const data = await response.json();
      
      // If we got a new token, store it
      if (data.new_token) {
        console.log('Received refreshed token');
        localStorage.setItem('inboxpal_token', data.new_token);
      }
      
      return data;
    } catch (error) {
      console.error('Error getting unread count:', error);
      throw error;
    }
  },
  
  // Get recent emails
  getRecentEmails: async () => {
    try {
      const token = localStorage.getItem('inboxpal_token');
      
      if (!token) {
        throw new Error('Not authenticated');
      }
      
      const response = await fetch('http://localhost:8000/api/gmail/recent-simple', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ token })
      });
      
      if (response.status === 401) {
        // Token expired, clear localStorage and redirect to login
        console.log('Token expired, clearing auth data');
        authService.logout();
        window.location.reload(); // This will show the login screen
        throw new Error('Session expired. Please log in again.');
      }
      
      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }
      
      const data = await response.json();
      
      // If we got a new token, store it
      if (data.new_token) {
        console.log('Received refreshed token');
        localStorage.setItem('inboxpal_token', data.new_token);
      }
      
      return data;
    } catch (error) {
      console.error('Error getting recent emails:', error);
      throw error;
    }
  }
};

export default gmailService;