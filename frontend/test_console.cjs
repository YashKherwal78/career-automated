const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  
  page.on('console', msg => console.log('BROWSER CONSOLE:', msg.type(), msg.text()));
  page.on('pageerror', err => console.log('BROWSER ERROR:', err.toString()));
  
  try {
    await page.goto('http://localhost:8080/mission-control', { waitUntil: 'networkidle0', timeout: 15000 });
    console.log("SUCCESS: Page loaded without crashing the puppeteer navigation.");
  } catch (e) {
    console.log("FAILED:", e.message);
  }
  
  await browser.close();
})();
