import { BASE_URL } from '@/lib/api';

/**
 * Error state for failed API requests. `compact` renders inside a card;
 * otherwise it fills the page and shows which API address was tried.
 */
export default function LoadError({ title = "Couldn't load data", error, onRetry, compact = false, note }) {
  const message = error?.message || String(error || 'Unknown error');
  return (
    <div className={compact ? 'load-error-inline' : 'api-error'} role="alert">
      <p className={compact ? 'load-error-title' : 'api-error-title'}>{title}</p>
      <p>{message}</p>
      {!compact && (
        <p>
          Tried <code>{BASE_URL}{error?.path || ''}</code>
          {note ? ` · ${note}` : ''}
        </p>
      )}
      {onRetry && (
        <button className="api-error-retry" onClick={onRetry}>Retry now</button>
      )}
    </div>
  );
}
