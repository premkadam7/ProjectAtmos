export default function Loader({ size = '24px', text = 'Loading...' }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px', padding: '24px' }}>
      <div 
        className="spinner" 
        style={{ 
          width: size, 
          height: size,
          border: '3px solid var(--glass-border)',
          borderTopColor: 'var(--accent-primary)', // Teal spinning top
          borderRadius: '50%',
          animation: 'spin 1s linear infinite'
        }}
      />
      {text && <span style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>{text}</span>}
      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}