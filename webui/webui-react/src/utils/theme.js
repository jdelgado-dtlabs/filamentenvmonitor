/**
 * Theme utility for managing dark/light mode with OS preference detection
 */

const THEME_KEY = 'app-theme';
const THEME_LIGHT = 'light';
const THEME_DARK = 'dark';
const THEME_AUTO = 'auto';

/**
 * Get the system's preferred color scheme
 * @returns {'light' | 'dark'}
 */
export function getSystemTheme() {
  // Try multiple methods to detect system theme
  if (window.matchMedia) {
    // Check prefers-color-scheme
    if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return THEME_DARK;
    }
    if (window.matchMedia('(prefers-color-scheme: light)').matches) {
      return THEME_LIGHT;
    }
  }
  
  // Check if document has dark mode class (some systems set this)
  if (document.documentElement.classList.contains('dark')) {
    return THEME_DARK;
  }
  
  // Default to dark for better visibility on kiosk displays
  return THEME_DARK;
}

/**
 * Get the saved theme preference from localStorage
 * @returns {'light' | 'dark' | 'auto' | null}
 */
export function getSavedTheme() {
  try {
    return localStorage.getItem(THEME_KEY);
  } catch (e) {
    console.warn('Failed to read theme from localStorage:', e);
    return null;
  }
}

/**
 * Save the theme preference to localStorage
 * @param {'light' | 'dark' | 'auto'} theme
 */
export function saveTheme(theme) {
  try {
    localStorage.setItem(THEME_KEY, theme);
  } catch (e) {
    console.warn('Failed to save theme to localStorage:', e);
  }
}

/**
 * Get the actual theme to apply (resolves 'auto' to system preference)
 * @param {'light' | 'dark' | 'auto' | null} preference
 * @returns {'light' | 'dark'}
 */
export function resolveTheme(preference) {
  if (preference === THEME_AUTO || preference === null) {
    return getSystemTheme();
  }
  return preference;
}

/**
 * Apply the theme to the document
 * @param {'light' | 'dark'} theme
 */
export function applyTheme(theme) {
  if (theme === THEME_DARK) {
    document.documentElement.setAttribute('data-theme', 'dark');
  } else {
    document.documentElement.removeAttribute('data-theme');
  }
}

/**
 * Set and apply a theme preference
 * @param {'light' | 'dark' | 'auto'} preference
 */
export function setTheme(preference) {
  saveTheme(preference);
  const actualTheme = resolveTheme(preference);
  applyTheme(actualTheme);
}

/**
 * Toggle between light and dark mode
 * @returns {'light' | 'dark'} The new theme
 */
export function toggleTheme() {
  const currentPreference = getSavedTheme() || THEME_AUTO;
  const currentActual = resolveTheme(currentPreference);
  const newTheme = currentActual === THEME_DARK ? THEME_LIGHT : THEME_DARK;
  setTheme(newTheme);
  return newTheme;
}

/**
 * Initialize the theme on app load
 * Sets up the initial theme and system preference listener
 * @returns {'light' | 'dark'} The applied theme
 */
export function initializeTheme() {
  const savedPreference = getSavedTheme();
  const actualTheme = resolveTheme(savedPreference);
  applyTheme(actualTheme);

  // Listen for system theme changes (only if preference is auto or not set)
  if (window.matchMedia) {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    mediaQuery.addEventListener('change', (e) => {
      const currentPreference = getSavedTheme();
      if (currentPreference === THEME_AUTO || currentPreference === null) {
        applyTheme(e.matches ? THEME_DARK : THEME_LIGHT);
      }
    });
  }

  return actualTheme;
}

/**
 * Get the current applied theme
 * @returns {'light' | 'dark'}
 */
export function getCurrentTheme() {
  return document.documentElement.getAttribute('data-theme') === 'dark' ? THEME_DARK : THEME_LIGHT;
}
