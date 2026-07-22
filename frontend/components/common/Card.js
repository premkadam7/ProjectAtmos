export default function Card({ children, className = '', title, action, style = {} }) {
  return (
    <div
      className={`card card-hover ${className}`}
      style={{
        background: 'var(--glass-bg)',
        backdropFilter: 'blur(12px)',
        WebkitBackdropFilter: 'blur(12px)',
        border: '1px solid var(--glass-border)',
        borderRadius: '16px',
        padding: '20px 24px',
        boxShadow: 'var(--shadow)',
        ...style,
      }}
      onAnimationEnd={(e) => {
        // Remove the whole stagger-in class (not just the animation name) —
        // this clears both the keyframe animation AND its base opacity:0 rule,
        // so the card settles at normal opacity and hover works cleanly.
        e.currentTarget.classList.remove('stagger-in');
      }}
    >
      {(title || action) && (
        <div
          className="card-header"
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '16px',
          }}
        >
          {title && (
            <h3
              style={{
                margin: 0,
                fontSize: '15px',
                fontWeight: 600,
                color: 'var(--text-primary)',
                letterSpacing: '-0.01em',
              }}
            >
              {title}
            </h3>
          )}
          {action && <div>{action}</div>}
        </div>
      )}
      <div className="card-content">{children}</div>
    </div>
  );
}