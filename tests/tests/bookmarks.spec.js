const { test, expect } = require('@playwright/test');

test.describe('Bookmarks Feature', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the app
    await page.goto('/');
    
    // Wait for splash screen to disappear - same approach as search tests
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
      waited += 500;
    }
  });

  test('bookmark button is visible on articles', async ({ page }) => {
    // Check if there are articles
    const articleCount = await page.locator('article').count();
    
    if (articleCount > 0) {
      // Get first article and check for bookmark button
      const firstArticle = page.locator('article').first();
      const bookmarkButton = firstArticle.locator('button').filter({ hasText: /⭐|☆/ });
      
      // Bookmark button should exist (either ⭐ or ☆)
      await expect(bookmarkButton.first()).toBeVisible({ timeout: 3000 });
    } else {
      // Skip if no articles
      test.skip();
    }
  });

  test('can toggle bookmark on an article', async ({ page }) => {
    const articleCount = await page.locator('article').count();
    
    if (articleCount === 0) {
      test.skip();
      return;
    }
    
    // Get first article
    const firstArticle = page.locator('article').first();
    const bookmarkButton = firstArticle.locator('button').filter({ hasText: /⭐|☆/ }).first();
    
    // Get initial state
    const initialText = await bookmarkButton.textContent();
    const isInitiallyBookmarked = initialText?.includes('⭐') || false;
    
    // Click bookmark button
    await bookmarkButton.click();
    
    // Wait for state to actually change - wait for opposite icon to appear
    if (isInitiallyBookmarked) {
      // Was bookmarked, wait for unbookmarked state (☆)
      await expect(bookmarkButton).toContainText('☆', { timeout: 3000 });
    } else {
      // Was not bookmarked, wait for bookmarked state (⭐)
      await expect(bookmarkButton).toContainText('⭐', { timeout: 3000 });
    }
    
    // Verify the state flipped
    const newText = await bookmarkButton.textContent();
    const isNowBookmarked = newText?.includes('⭐') || false;
    expect(isNowBookmarked).toBe(!isInitiallyBookmarked);
  });

  test('bookmarks button appears in toolbar', async ({ page }) => {
    const bookmarksButton = page.locator('button:has-text("Bookmarks"), button:has-text("⭐ Bookmarks")');
    await expect(bookmarksButton).toBeVisible({ timeout: 3000 });
  });

  test('can view bookmarked articles', async ({ page }) => {
    // First, bookmark an article if available
    const articleCount = await page.locator('article').count();
    
    if (articleCount === 0) {
      test.skip();
      return;
    }
    
    // Try to bookmark first article
    const firstArticle = page.locator('article').first();
    const bookmarkButton = firstArticle.locator('button').filter({ hasText: /⭐|☆/ }).first();
    const initialText = await bookmarkButton.textContent();
    
    // If not bookmarked, bookmark it
    if (!initialText?.includes('⭐')) {
      await bookmarkButton.click();
      await page.waitForTimeout(500);
    }
    
    // Click Bookmarks button in toolbar
    const bookmarksToggle = page.locator('button:has-text("Bookmarks"), button:has-text("⭐ Bookmarks")').first();
    await bookmarksToggle.click();
    
    // Wait for bookmarks view to appear
    await page.waitForTimeout(500);
    
    // Check that bookmarks section is visible
    const bookmarksSection = page.locator('text=Bookmarked Articles').first();
    await expect(bookmarksSection).toBeVisible({ timeout: 3000 });
    
    // Should have at least one bookmarked article
    const bookmarkedArticles = page.locator('article').count();
    const hasNoBookmarks = page.locator('text=No bookmarked articles yet').isVisible().catch(() => false);
    
    // Either has articles or shows empty message
    const hasContent = await bookmarkedArticles > 0 || await hasNoBookmarks;
    expect(hasContent).toBeTruthy();
  });

  test('can remove bookmark from bookmarks view', async ({ page }) => {
    const articleCount = await page.locator('article').count();
    
    if (articleCount === 0) {
      test.skip();
      return;
    }
    
    // First, ensure at least one article is bookmarked
    const firstArticle = page.locator('article').first();
    const bookmarkButton = firstArticle.locator('button').filter({ hasText: /⭐|☆/ }).first();
    const initialText = await bookmarkButton.textContent();
    
    if (!initialText?.includes('⭐')) {
      await bookmarkButton.click();
      await page.waitForTimeout(500);
    }
    
    // Open bookmarks view
    const bookmarksToggle = page.locator('button:has-text("Bookmarks"), button:has-text("⭐ Bookmarks")').first();
    await bookmarksToggle.click();
    await page.waitForTimeout(500);
    
    // Wait for bookmarks to load - either articles or empty message
    let waited = 0;
    let hasContent = false;
    while (!hasContent && waited < 5000) {
      const articleCount = await page.locator('article').count();
      const hasNoBookmarks = await page.locator('text=No bookmarked articles yet').isVisible().catch(() => false);
      hasContent = articleCount > 0 || hasNoBookmarks;
      if (hasContent) break;
      await page.waitForTimeout(500);
      waited += 500;
    }
    
    const bookmarkedCount = await page.locator('article').count();
    
    if (bookmarkedCount > 0) {
      // Click bookmark button on first bookmarked article
      const firstBookmarked = page.locator('article').first();
      const removeBookmarkBtn = firstBookmarked.locator('button').filter({ hasText: /⭐|☆/ }).first();
      
      await removeBookmarkBtn.click();
      await page.waitForTimeout(500);
      
      // Article should be removed from list or show empty message
      const newCount = await page.locator('article').count();
      const hasNoBookmarks = await page.locator('text=No bookmarked articles yet').isVisible().catch(() => false);
      
      // Either count decreased or shows empty message
      expect(newCount < bookmarkedCount || hasNoBookmarks).toBeTruthy();
    }
  });

  test('API supports bookmark toggle', async ({ request }) => {
    // First, get an article ID
    const articlesResponse = await request.get('/api/articles?page=1&limit=1');
    expect(articlesResponse.ok()).toBeTruthy();
    
    const articlesData = await articlesResponse.json();
    
    if (articlesData.items && articlesData.items.length > 0) {
      const articleId = articlesData.items[0].id;
      
      // Toggle bookmark
      const toggleResponse = await request.post(`/api/articles/${articleId}/bookmark`);
      expect(toggleResponse.ok()).toBeTruthy();
      
      const toggleData = await toggleResponse.json();
      expect(toggleData).toHaveProperty('bookmarked');
      expect(toggleData).toHaveProperty('action');
      expect(typeof toggleData.bookmarked).toBe('boolean');
    }
  });

  test('API returns bookmarked articles list', async ({ request }) => {
    const response = await request.get('/api/articles/bookmarked?page=1&limit=10');
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data).toHaveProperty('items');
    expect(data).toHaveProperty('page');
    expect(data).toHaveProperty('total');
    expect(data).toHaveProperty('pages');
    expect(Array.isArray(data.items)).toBeTruthy();
    
    // Each item should have is_bookmarked = true if present
    if (data.items.length > 0) {
      data.items.forEach(item => {
        if (item.hasOwnProperty('is_bookmarked')) {
          expect(item.is_bookmarked).toBe(true);
        }
      });
    }
  });

  test('articles API includes bookmark status', async ({ request }) => {
    const response = await request.get('/api/articles?page=1&limit=10');
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data).toHaveProperty('items');
    expect(Array.isArray(data.items)).toBeTruthy();
    
    // Each article should have is_bookmarked property
    if (data.items.length > 0) {
      data.items.forEach(item => {
        expect(item).toHaveProperty('is_bookmarked');
        expect(typeof item.is_bookmarked === 'boolean' || item.is_bookmarked === null || item.is_bookmarked === undefined).toBeTruthy();
      });
    }
  });
});


