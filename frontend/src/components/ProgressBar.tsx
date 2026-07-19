interface Props {
  percent: number;
  showValue?: boolean;
}

export default function ProgressBar({ percent, showValue = false }: Props) {
  const clamped = Math.max(0, Math.min(100, percent));
  return (
    <div className="progress-bar" role="progressbar" aria-valuenow={Math.round(clamped)} aria-valuemin={0} aria-valuemax={100}>
      <div className="progress-bar__track">
        <div className="progress-bar__fill" style={{ width: `${clamped}%` }} />
      </div>
      {showValue && (
        <span className="progress-bar__value">{Math.round(clamped)}%</span>
      )}
    </div>
  );
}
