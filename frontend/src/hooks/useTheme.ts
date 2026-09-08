import { useCallback, useEffect, useState } from 'react';

export type Theme = 'light' | 'dark';

/** null means "follow the OS", which is the default until someone chooses. */
type ThemePreference = Theme | null;

const STORAGE_KEY = 'goji-theme';

function readStoredPreference(): ThemePreference {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored === 'light' || stored === 'dark' ? stored : null;
  } catch {
    // Private mode and blocked site data both throw on access.
    return null;
  }
}

function systemTheme(): Theme {
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

/**
 * Resolves the active theme and stamps it on <html> for theme.css to read.
 *
 * Kept as a hook rather than context: only the toggle needs to write, and
 * only <html> needs to know, so there is nothing to share down the tree.
 */
export function useTheme() {
  const [preference, setPreference] = useState<ThemePreference>(readStoredPreference);
  const [resolved, setResolved] = useState<Theme>(() => readStoredPreference() ?? systemTheme());

  // Follow the OS for as long as the user hasn't made an explicit choice.
  useEffect(() => {
    if (preference !== null) {
      setResolved(preference);
      return;
    }

    const media = window.matchMedia('(prefers-color-scheme: dark)');
    const sync = () => setResolved(media.matches ? 'dark' : 'light');

    sync();
    media.addEventListener('change', sync);
    return () => media.removeEventListener('change', sync);
  }, [preference]);

  // The attribute is what theme.css actually selects on.
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', resolved);
  }, [resolved]);

  const toggle = useCallback(() => {
    setPreference((current) => {
      const next: Theme = (current ?? systemTheme()) === 'dark' ? 'light' : 'dark';
      try {
        localStorage.setItem(STORAGE_KEY, next);
      } catch {
        // Preference just won't survive a reload; not worth failing the click.
      }
      return next;
    });
  }, []);

  return { theme: resolved, toggle };
}
