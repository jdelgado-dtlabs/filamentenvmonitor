import './Gauge.css';

export function Gauge({ value, min, max, unit, label, redHigh = 90, yellowHigh = 60, greenHigh = 30, yellowLow = 10 }) {
  // Ensure value is within bounds
  const clampedValue = Math.max(min, Math.min(max, value || min));
  
  // Calculate percentage (0-100)
  const percentage = ((clampedValue - min) / (max - min)) * 100;
  
  // Calculate angle for arc (starts at 180deg/left, goes through top 270deg, ends at 360deg/0deg right)
  // In SVG: 0deg is right (3 o'clock), 90deg is bottom, 180deg is left, 270deg is top
  // To go from left to right through the TOP, we go from 180° to 360° (= 0°)
  const startAngle = 180;
  const endAngle = 360; // Same as 0° but makes the math clearer
  const angle = startAngle + (percentage / 100) * (endAngle - startAngle);
  
  // SVG path parameters - viewBox needs to accommodate full semicircle height  
  const size = 140;
  const strokeWidth = 14;
  const radius = (size - strokeWidth) / 2;
  const center = size / 2;
  const viewBoxHeight = radius + strokeWidth + 30; // Radius + stroke + space for text
  
  // Create arc path
  const createArc = (startDeg, endDeg, color) => {
    const startRad = (startDeg * Math.PI) / 180;
    const endRad = (endDeg * Math.PI) / 180;
    
    const x1 = center + radius * Math.cos(startRad);
    const y1 = center + radius * Math.sin(startRad);
    const x2 = center + radius * Math.cos(endRad);
    const y2 = center + radius * Math.sin(endRad);
    
    // For arcs going from 180° through 270° (top) to 360°:
    // - Use sweep-flag=1 (clockwise through top)
    // - Use large-arc=0 since we're spanning <= 180°
    const sweepFlag = 1;
    const largeArc = 0;
    
    return (
      <path
        d={`M ${x1} ${y1} A ${radius} ${radius} 0 ${largeArc} ${sweepFlag} ${x2} ${y2}`}
        fill="none"
        stroke={color}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
      />
    );
  };
  
  // Determine color based on percentage using configurable thresholds
  const getColor = (pct) => {
    if (pct >= redHigh) return '#e74c3c'; // Red - high
    if (pct >= yellowHigh) return '#f39c12'; // Yellow - high
    if (pct >= greenHigh) return '#2ecc71'; // Green - middle
    if (pct >= yellowLow) return '#f39c12'; // Yellow - low
    return '#e74c3c'; // Red - low (0 to yellowLow)
  };
  
  const valueColor = getColor(percentage);
  
  return (
    <div className="gauge-container">
      <svg viewBox={`0 0 ${size} ${viewBoxHeight}`} preserveAspectRatio="xMidYMid meet">
        {/* Background arc */}
        {createArc(startAngle, endAngle, '#ecf0f1')}
        
        {/* Value arc */}
        {createArc(startAngle, angle, valueColor)}
        
        {/* Center text - value and unit as single centered element */}
        <text
          x={center}
          y={center + 5}
          textAnchor="middle"
          className="gauge-value"
          fill={valueColor}
        >
          {value != null ? Math.round(value * 10) / 10 : '--'}
          <tspan className="gauge-unit" fill="#7f8c8d"> {unit}</tspan>
        </text>
      </svg>
      <div className="gauge-range">
        <span>{min}</span>
        <span>{max}</span>
      </div>
      {label && <div className="gauge-label">{label}</div>}
    </div>
  );
}
