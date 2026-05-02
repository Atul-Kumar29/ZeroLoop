/**
 * Test script for the ZeroLoop API endpoint
 * 
 * Usage: node test-api.js
 * 
 * Note: Make sure Next.js dev server is running on port 3000
 */

async function testAPI() {
  const API_URL = 'http://localhost:3000/api/analyze';
  
  console.log('Testing ZeroLoop API...\n');
  
  // Test 1: GET request (documentation)
  console.log('Test 1: GET /api/analyze (documentation)');
  try {
    const response = await fetch(API_URL);
    const data = await response.json();
    console.log('✅ GET request successful');
    console.log('Response:', JSON.stringify(data, null, 2));
  } catch (error) {
    console.error('❌ GET request failed:', error.message);
  }
  
  console.log('\n' + '='.repeat(80) + '\n');
  
  // Test 2: POST request with test project
  console.log('Test 2: POST /api/analyze (test project)');
  try {
    const response = await fetch(API_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        projectPath: 'scanner/test_project'
      })
    });
    
    const data = await response.json();
    
    if (data.success) {
      console.log('✅ POST request successful');
      console.log('\nAnalysis Status:', data.analysis.status);
      console.log('Total Issues:', data.analysis.summary.total_issues);
      console.log('Bobcoins Saved:', data.savings?.total_saved || 'N/A');
      console.log('\nBob Context Preview:');
      console.log(data.bobContext?.substring(0, 500) + '...');
    } else {
      console.error('❌ POST request failed:', data.error);
      console.error('Message:', data.message);
    }
  } catch (error) {
    console.error('❌ POST request failed:', error.message);
  }
  
  console.log('\n' + '='.repeat(80) + '\n');
  
  // Test 3: POST request with current project
  console.log('Test 3: POST /api/analyze (current project)');
  try {
    const response = await fetch(API_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        projectPath: '.'
      })
    });
    
    const data = await response.json();
    
    if (data.success) {
      console.log('✅ POST request successful');
      console.log('\nAnalysis Status:', data.analysis.status);
      console.log('Total Issues:', data.analysis.summary.total_issues);
      console.log('Bobcoins Saved:', data.savings?.total_saved || 'N/A');
    } else {
      console.error('❌ POST request failed:', data.error);
      console.error('Message:', data.message);
    }
  } catch (error) {
    console.error('❌ POST request failed:', error.message);
  }
  
  console.log('\n' + '='.repeat(80) + '\n');
  
  // Test 4: POST request with missing projectPath
  console.log('Test 4: POST /api/analyze (missing projectPath - should fail)');
  try {
    const response = await fetch(API_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({})
    });
    
    const data = await response.json();
    
    if (!data.success && response.status === 400) {
      console.log('✅ Validation working correctly');
      console.log('Error:', data.error);
      console.log('Message:', data.message);
    } else {
      console.error('❌ Validation failed - should have returned 400 error');
    }
  } catch (error) {
    console.error('❌ Request failed:', error.message);
  }
  
  console.log('\n' + '='.repeat(80));
  console.log('\nAll tests completed!');
  console.log('\nTo run these tests:');
  console.log('1. Start Next.js dev server: npm run dev');
  console.log('2. Run this script: node test-api.js');
}

// Run tests
testAPI().catch(console.error);

// Made with Bob
