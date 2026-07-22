export default function Badge({ children, level = 'good', className = '' }) {
  // 'level' matches your CSS variables: good, satisfactory, moderate, poor, severe
  return (
    <span 
      className={`badge ${className}`}
      style={{
        backgroundColor: `rgba(255, 255, 255, 0.05)`, // Subtle glass background
        color: `var(--aqi-${level})`, // Pulls the exact hex color from globals.css
        border: `1px solid var(--aqi-${level})`,
        padding: '4px 12px',
        borderRadius: '20px',
        fontSize: '12px',
        fontWeight: 600,
        letterSpacing: '0.05em',
        textTransform: 'uppercase'
      }}
    >
      {children}
    </span>
  );
}