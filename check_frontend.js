const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  
  // Capture console logs
  page.on('console', msg => console.log('BROWSER CONSOLE:', msg.text()));
  
  // Capture errors
  page.on('pageerror', error => {
    console.log('PAGE ERROR:', error.message);
  });
  
  // Navigate to the page
  await page.goto('http://localhost:3000', {
    waitUntil: 'networkidle2',
    timeout: 30000
  });
  
  // Take a screenshot
  await page.screenshot({path: 'frontend_screenshot.png'});
  
  // Get page title
  const title = await page.title();
  console.log('Page title:', title);
  
  // Check for Docker Monitor text
  const bodyText = await page.evaluate(() => document.body.textContent);
  if (bodyText.includes('Docker Monitor')) {
    console.log('Found "Docker Monitor" text on the page');
  } else {
    console.log('Did NOT find "Docker Monitor" text on the page');
  }
  
  // Check for error text
  if (bodyText.includes('Error:')) {
    console.log('Found error message on the page');
  }
  
  await browser.close();
})();