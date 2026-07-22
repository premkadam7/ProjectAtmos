export default function Button({ children, variant = 'primary', className = '', onClick, ...props }) {
  const isPrimary = variant === 'primary';
  
  return (
    <button 
      className={`btn ${className}`} 
      onClick={onClick}
      style={{
        background: isPrimary ? 'var(--accent-gradient)' : 'transparent',
        color: isPrimary ? '#0f1724' : 'var(--text-primary)',
        border: isPrimary ? 'none' : '1px solid var(--glass-border)',
        padding: '10px 20px',
        borderRadius: '8px',
        fontWeight: 600,
        cursor: 'pointer',
        transition: 'all 0.2s ease',
        ...props.style
      }}
      {...props}
    >
      {children}
    </button>
  );
}