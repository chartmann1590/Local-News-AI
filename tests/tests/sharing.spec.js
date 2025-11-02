const { test, expect } = require('@playwright/test');

test.describe('Sharing Feature', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the app
    await page.goto('/');
    
    // Wait for splash screen to disappear - same approach as other tests
    try {
      await page.waitForSelector('input[placeholder*="Search articles"]', { 
        timeout: 10000,
        state: 'visible'
      });
    } catch {
      // Fallback: wait for Settings button in header
      await page.waitForSelector('header button:has-text("Settings")', { 
        timeout: 10000,
        state: 'visible'
      });
    }
    
    // Additional small wait to ensure everything is settled
    await page.waitForTimeout(500);
    
    // Wait for the app header to be visible (non-splash version)
    await expect(page.locator('header').locator('text=Local News & Weather')).toBeVisible({ timeout: 5000 });
    
    // Wait for articles section to load
    const hasArticles = await page.locator('article').count() > 0;
    const hasNoArticles = await page.locator('text=No articles yet').isVisible().catch(() => false);
    const hasNewsSection = await page.locator('text=Latest Local News').isVisible().catch(() => false);
    
    // Wait up to 15 seconds for one of these to be true
    let waited = 0;
    while (!hasArticles && !hasNoArticles && !hasNewsSection && waited < 15000) {
      await page.waitForTimeout(500);
      const articleCount = await page.locator('article').count();
      const hasNoArticlesNow = await page.locator('text=No articles yet').isVisible().catch(() => false);
      const hasNewsSectionNow = await page.locator('text=Latest Local News').isVisible().catch(() => false);
      if (articleCount > 0 || hasNoArticlesNow || hasNewsSectionNow) break;
      waited += 500;
    }
  });

  test('share button is visible on articles', async ({ page }) => {
    // Check if there are articles
    const articleCount = await page.locator('article').count();
    
    if (articleCount > 0) {
      // Get first article and check for share button
      const firstArticle = page.locator('article').first();
      const shareButton = firstArticle.locator('button').filter({ hasText: /📤/ });
      
      // Share button should exist
      await expect(shareButton.first()).toBeVisible({ timeout: 3000 });
    } else {
      // Skip if no articles
      test.skip();
    }
  });

  test('share button is clickable', async ({ page }) => {
    const articleCount = await page.locator('article').count();
    
    if (articleCount === 0) {
      test.skip();
      return;
    }
    
    // Get first article
    const firstArticle = page.locator('article').first();
    const shareButton = firstArticle.locator('button').filter({ hasText: /📤/ }).first();
    
    // Verify button exists and is visible
    await expect(shareButton).toBeVisible({ timeout: 3000 });
    
    // Click share button
    await shareButton.click();
    
    // Wait a moment for share dialog or clipboard operation
    await page.waitForTimeout(1000);
    
    // On browsers that support Web Share API, the share dialog will appear
    // On others, clipboard copy should work (we can't directly test clipboard in Playwright without permissions)
    // So we just verify the button click doesn't throw an error
    // The button should remain visible after click
    await expect(shareButton).toBeVisible({ timeout: 1000 });
  });

  test('share functionality handles Web Share API', async ({ page, context }) => {
    // Grant clipboard permissions if needed
    await context.grantPermissions(['clipboard-read', 'clipboard-write']);
    
    const articleCount = await page.locator('article').count();
    
    if (articleCount === 0) {
      test.skip();
      return;
    }
    
    // Monitor console for share-related errors only
    const shareErrors = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        const text = msg.text().toLowerCase();
        // Only capture errors that are specifically about sharing functionality
        if (text.includes('share') || text.includes('clipboard') || 
            (text.includes('failed to') && (text.includes('share') || text.includes('copy')))) {
          shareErrors.push(msg.text());
        }
      }
    });
    
    // Get first article
    const firstArticle = page.locator('article').first();
    const shareButton = firstArticle.locator('button').filter({ hasText: /📤/ }).first();
    
    // Verify button is visible before clicking
    await expect(shareButton).toBeVisible({ timeout: 3000 });
    
    // Click share button
    await shareButton.click();
    
    // Wait a moment for share dialog or clipboard operation to complete
    await page.waitForTimeout(1500);
    
    // Check that no share-specific errors occurred
    // The share function should either:
    // 1. Open the native share dialog (Web Share API)
    // 2. Copy to clipboard silently
    // 3. Show an alert (fallback)
    // All of these should work without throwing share-related errors
    expect(shareErrors.length).toBe(0);
  });

  test('share button appears alongside bookmark button', async ({ page }) => {
    const articleCount = await page.locator('article').count();
    
    if (articleCount === 0) {
      test.skip();
      return;
    }
    
    // Get first article
    const firstArticle = page.locator('article').first();
    
    // Both buttons should be present
    const shareButton = firstArticle.locator('button').filter({ hasText: /📤/ });
    const bookmarkButton = firstArticle.locator('button').filter({ hasText: /⭐|☆/ });
    
    await expect(shareButton.first()).toBeVisible({ timeout: 3000 });
    await expect(bookmarkButton.first()).toBeVisible({ timeout: 3000 });
  });
});

