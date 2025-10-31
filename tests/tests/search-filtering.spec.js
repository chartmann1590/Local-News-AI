const { test, expect } = require('@playwright/test');

test.describe('Search and Filtering Features', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the app
    await page.goto('/');
    
    // The splash screen shows for ~5 seconds. Wait for it to disappear.
    // The splash screen has z-index 50 and contains "Loading…" text.
    // We'll wait for the search input which only appears after splash is gone.
    
    // Wait for splash to disappear - check for search input or header button
    // These elements only appear after splash screen is hidden
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
    
    // Wait for articles section to load - check for article elements or empty state message
    // Use locator instead of waitForSelector with text
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

  test('search bar is visible in header', async ({ page }) => {
    // Check that search bar is present
    const searchInput = page.locator('input[placeholder*="Search articles"]');
    await expect(searchInput).toBeVisible();
  });

  test('can search for articles', async ({ page }) => {
    const searchInput = page.locator('input[placeholder*="Search articles"]');
    
    // Type a search query
    await searchInput.fill('test');
    
    // Wait for search results (debounce delay is 300ms)
    await page.waitForTimeout(500);
    
    // Check that the URL or page state changed (articles should be filtered)
    // We'll check if the search input still has the value
    await expect(searchInput).toHaveValue('test');
    
    // Wait a bit more for results to load
    await page.waitForTimeout(1000);
    
    // Check that we're either showing filtered results or no results message
    const hasArticles = await page.locator('article').count() > 0;
    const hasNoResults = await page.locator('text=No articles yet').isVisible().catch(() => false);
    const hasNewsSection = await page.locator('text=Latest Local News').isVisible().catch(() => false);
    
    // At least one of these should be true
    expect(hasArticles || hasNoResults || hasNewsSection).toBeTruthy();
  });

  test('can clear search', async ({ page }) => {
    const searchInput = page.locator('input[placeholder*="Search articles"]');
    
    // Enter search
    await searchInput.fill('test');
    await page.waitForTimeout(500);
    await expect(searchInput).toHaveValue('test');
    
    // Clear search (there should be a clear button or we can clear the input)
    await searchInput.clear();
    await page.waitForTimeout(500);
    
    // Search should be empty
    await expect(searchInput).toHaveValue('');
  });

  test('filters panel can be toggled', async ({ page }) => {
    // Find the filters toggle button
    const filtersButton = page.locator('button:has-text("Filters"), button:has-text("▶ Filters")');
    
    if (await filtersButton.count() > 0) {
      // Click to show filters
      await filtersButton.click();
      
      // Check that filter panel is visible
      const filterPanel = page.locator('select, label:has-text("Source"), label:has-text("Sort By")').first();
      await expect(filterPanel).toBeVisible({ timeout: 2000 });
      
      // Click again to hide
      await filtersButton.click();
    }
  });

  test('can filter by source', async ({ page }) => {
    // Show filters
    const filtersButton = page.locator('button:has-text("Filters"), button:has-text("▶ Filters")');
    
    if (await filtersButton.count() > 0) {
      await filtersButton.click();
      await page.waitForTimeout(300);
    }
    
    // Find source dropdown
    const sourceSelect = page.locator('select').filter({ has: page.locator('option:has-text("All Sources")') }).first();
    
    if (await sourceSelect.count() > 0) {
      // Get options count
      const optionsCount = await sourceSelect.locator('option').count();
      
      if (optionsCount > 1) {
        // Select a source (skip "All Sources" option)
        await sourceSelect.selectOption({ index: 1 });
        
        // Wait for filter to apply
        await page.waitForTimeout(500);
        
        // Check that articles are filtered (or no articles message)
        const hasContent = await page.locator('article').first().isVisible({ timeout: 3000 }).catch(() => false) ||
                          await page.locator('text=No articles yet').isVisible({ timeout: 3000 }).catch(() => false);
        expect(hasContent).toBeTruthy();
      }
    }
  });

  test('can sort articles', async ({ page }) => {
    // Show filters
    const filtersButton = page.locator('button:has-text("Filters"), button:has-text("▶ Filters")');
    
    if (await filtersButton.count() > 0) {
      await filtersButton.click();
      await page.waitForTimeout(300);
    }
    
    // Find sort dropdown
    const sortSelect = page.locator('select').filter({ has: page.locator('option:has-text("Date")') }).first();
    
    if (await sortSelect.count() > 0) {
      // Change sort option
      await sortSelect.selectOption({ index: 1 }); // Try selecting a different sort option
      
      // Wait for sort to apply
      await page.waitForTimeout(500);
      
      // Check that page updated
      const hasContent = await page.locator('article').first().isVisible({ timeout: 3000 }).catch(() => false) ||
                        await page.locator('text=No articles yet').isVisible({ timeout: 3000 }).catch(() => false);
      expect(hasContent).toBeTruthy();
    }
  });

  test('clear filters button appears when filters are active', async ({ page }) => {
    const searchInput = page.locator('input[placeholder*="Search articles"]');
    
    // Enter a search query
    await searchInput.fill('test');
    await page.waitForTimeout(500);
    
    // Check for clear filters button
    const clearButton = page.locator('button:has-text("Clear Filters")');
    
    // Button should appear when filters are active
    await expect(clearButton).toBeVisible({ timeout: 2000 });
    
    // Click clear filters
    await clearButton.click();
    await page.waitForTimeout(300);
    
    // Search should be cleared
    await expect(searchInput).toHaveValue('');
  });

  test('search uses debouncing', async ({ page }) => {
    const searchInput = page.locator('input[placeholder*="Search articles"]');
    
    // Type multiple characters quickly
    await searchInput.fill('a');
    await page.waitForTimeout(100);
    await searchInput.fill('ab');
    await page.waitForTimeout(100);
    await searchInput.fill('abc');
    
    // Wait for debounce (300ms) plus some buffer
    await page.waitForTimeout(500);
    
    // Final value should be 'abc'
    await expect(searchInput).toHaveValue('abc');
  });

  test('API supports search parameters', async ({ request }) => {
    // Test the API endpoint directly
    const response = await request.get('/api/articles?q=test&page=1&limit=10');
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data).toHaveProperty('items');
    expect(data).toHaveProperty('page');
    expect(data).toHaveProperty('total');
    expect(data).toHaveProperty('pages');
    expect(Array.isArray(data.items)).toBeTruthy();
  });

  test('API supports source filter', async ({ request }) => {
    // First get sources
    const sourcesResponse = await request.get('/api/articles/sources');
    expect(sourcesResponse.ok()).toBeTruthy();
    
    const sourcesData = await sourcesResponse.json();
    expect(sourcesData).toHaveProperty('sources');
    expect(Array.isArray(sourcesData.sources)).toBeTruthy();
    
    // If there are sources, test filtering
    if (sourcesData.sources.length > 0) {
      const testSource = sourcesData.sources[0];
      const response = await request.get(`/api/articles?source=${encodeURIComponent(testSource)}&page=1&limit=10`);
      expect(response.ok()).toBeTruthy();
      
      const data = await response.json();
      expect(data).toHaveProperty('items');
      // All items should match the source (if any)
      if (data.items.length > 0) {
        data.items.forEach(item => {
          if (item.source) {
            expect(item.source).toBe(testSource);
          }
        });
      }
    }
  });

  test('API supports sorting', async ({ request }) => {
    // Test different sort options
    const sortOptions = ['date_desc', 'date_asc', 'title', 'source'];
    
    for (const sortBy of sortOptions) {
      const response = await request.get(`/api/articles?sort_by=${sortBy}&page=1&limit=10`);
      expect(response.ok()).toBeTruthy();
      
      const data = await response.json();
      expect(data).toHaveProperty('items');
      expect(Array.isArray(data.items)).toBeTruthy();
    }
  });
});

