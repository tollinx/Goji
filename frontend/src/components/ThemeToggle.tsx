import type { Theme } from '../hooks/useTheme';
import './ThemeToggle.css';

interface ThemeToggleProps {
  theme: Theme;
  onToggle: () => void;
}

/**
 * Geometry only — every stroke, fill and opacity comes from ThemeToggle.css.
 */
export default function ThemeToggle({ theme, onToggle }: ThemeToggleProps) {
  const nextTheme = theme === 'dark' ? 'light' : 'dark';

  return (
    <button
      className="theme-toggle"
      type="button"
      onClick={onToggle}
      aria-label={`Switch to ${nextTheme} theme`}
      title={`Switch to ${nextTheme} theme`}
    >
      {theme === 'dark' ? (
        <svg className="theme-toggle__icon" viewBox="0 0 24 24" aria-hidden="true">
          <circle className="theme-toggle__body" cx="12" cy="12" r="5" />
          <g className="theme-toggle__rays">
            <path d="M12 1.5 L12 4" />
            <path d="M12 20 L12 22.5" />
            <path d="M1.5 12 L4 12" />
            <path d="M20 12 L22.5 12" />
            <path d="M4.5 4.5 L6.3 6.3" />
            <path d="M17.7 17.7 L19.5 19.5" />
            <path d="M19.5 4.5 L17.7 6.3" />
            <path d="M6.3 17.7 L4.5 19.5" />
          </g>
        </svg>
      ) : (
        <svg className="theme-toggle__icon" viewBox="0 0 24 24" aria-hidden="true">
          <path
            className="theme-toggle__body"
            d="M20 14.5 A8.5 8.5 0 1 1 9.5 4 A6.6 6.6 0 0 0 20 14.5 Z"
          />
        </svg>
      )}
    </button>
  );
}
