// Simple test to check API connectivity
const backendUrl = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

console.log('Testing API connectivity...');
console.log('Backend URL:', backendUrl);

fetch(`${backendUrl}/api/docker/status`)
  .then(response => {
    console.log('Response status:', response.status);
    return response.json();
  })
  .then(data => {
    console.log('Response data:', data);
  })
  .catch(error => {
    console.error('API Error:', error);
  });