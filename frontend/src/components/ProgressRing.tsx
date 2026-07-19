interface Props {
  percent: number;
  size?: number;
  stroke?: number;
  label?: string;
}

export default function ProgressRing({
  percent,
  size = 140,
  stroke = 12,
  label,
}: Props) {
  const clamped = Math.max(0, Math.min(100, percent));
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (clamped / 100) * circumference;

  return (
    <div
      className="progress-ring"
      style={{ width: size, height: size }}
      role="img"
      aria-label={`${Math.round(clamped)} percent complete`}
    >
      <svg width={size} height={size}>
        <defs>
          <linearGradient id="ring-grad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#a8492f" />
            <stop offset="55%" stopColor="#c06a4c" />
            <stop offset="100%" stopColor="#d68a63" />
          </linearGradient>
        </defs>
        <circle
          className="progress-ring__track"
          cx={size / 2}
          cy={size / 2}
          r={radius}
          strokeWidth={stroke}
          fill="none"
        />
        <circle
          className="progress-ring__fill"
          cx={size / 2}
          cy={size / 2}
          r={radius}
          strokeWidth={stroke}
          fill="none"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
          stroke="url(#ring-grad)"
        />
      </svg>
      <div className="progress-ring__center">
        <span className="progress-ring__value">{Math.round(clamped)}%</span>
        {label && <span className="progress-ring__label">{label}</span>}
      </div>
    </div>
  );
}
