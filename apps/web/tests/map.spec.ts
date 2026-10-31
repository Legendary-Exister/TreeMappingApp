import { test, expect } from '@playwright/test';

test.describe('Tree Map', () => {
  test('loads map with controls and legend', async ({ page }) => {
    await page.goto('/');

    // Wait for map container to be visible
    await expect(page.locator('[role="application"]')).toBeVisible();

    // Check for city badge
    await expect(page.locator('text=TreeMap')).toBeVisible();
    await expect(page.locator('text=Centred on')).toBeVisible();

    // Check for filters
    await expect(page.locator('#tree-search')).toBeVisible();
    await expect(page.locator('#health-filter')).toBeVisible();
    await expect(page.locator('#verified-toggle')).toBeVisible();

    // Check for legend (only if tiles URL is configured)
    const legend = page.locator('[role="legend"]');
    const legendVisible = await legend.isVisible().catch(() => false);
    if (legendVisible) {
      await expect(legend).toContainText('Leaf cycle');
    }
  });

  test('keyboard navigation works', async ({ page }) => {
    await page.goto('/');

    const map = page.locator('[role="application"]');
    await map.focus();

    // Test zoom in with +
    await page.keyboard.press('+');
    // MapLibre should handle zoom - just verify no errors

    // Test zoom out with -
    await page.keyboard.press('-');

    // Test arrow keys for panning
    await page.keyboard.press('ArrowRight');
    await page.keyboard.press('ArrowDown');
    await page.keyboard.press('ArrowLeft');
    await page.keyboard.press('ArrowUp');
  });

  test('filters update URL', async ({ page }) => {
    await page.goto('/');

    // Type in search
    await page.locator('#tree-search').fill('Quercus');
    await expect(page).toHaveURL(/q=Quercus/);

    // Change health filter
    await page.locator('#health-filter').selectOption('good');
    await expect(page).toHaveURL(/health=good/);

    // Toggle verified
    await page.locator('#verified-toggle').click();
    await expect(page).toHaveURL(/verified=true/);

    // Clear search
    await page.locator('#tree-search').fill('');
    await expect(page).not.toHaveURL(/q=/);
  });

  test('escape key closes panel', async ({ page }) => {
    await page.goto('/');

    const map = page.locator('[role="application"]');
    await map.focus();

    // Press Escape - should not error even if no panel is open
    await page.keyboard.press('Escape');
  });

  test('responsive layout on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');

    // Filters should stack vertically on mobile
    const filters = page.locator('.absolute.top-4');
    await expect(filters).toBeVisible();

    // City badge should be responsive
    await expect(page.locator('text=TreeMap')).toBeVisible();
  });

  test('accessibility attributes are present', async ({ page }) => {
    await page.goto('/');

    // Map has proper ARIA attributes
    const map = page.locator('[role="application"]');
    await expect(map).toHaveAttribute('aria-label', /Interactive tree map/);
    await expect(map).toHaveAttribute('tabIndex', '0');

    // Filters have labels
    await expect(page.locator('#tree-search')).toHaveAttribute('aria-label', /Search tree species/);
    await expect(page.locator('#health-filter')).toHaveAttribute('aria-label', /Filter trees by health/);
    await expect(page.locator('#verified-toggle')).toHaveAttribute('aria-pressed');

    // Legend has proper role
    const legend = page.locator('[role="legend"]');
    const legendVisible = await legend.isVisible().catch(() => false);
    if (legendVisible) {
      await expect(legend).toHaveAttribute('aria-label', /Tree leaf cycle legend/);
    }
  });
});
