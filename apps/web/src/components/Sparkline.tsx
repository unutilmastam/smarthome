import type { TelemetryPoint } from "../api/types";

/** Minimal SVG line of 1-minute averages. Gaps (missing minutes) break the line:
 *  no interpolation, nothing invented. */
export function Sparkline({ points, unit, height = 64 }: { points: TelemetryPoint[]; unit?: string; height?: number }) {
  if (points.length < 2) return null;
  const xs = points.map((p) => new Date(p.ts).getTime());
  const ys = points.map((p) => p.avg);
  const [x0, x1] = [Math.min(...xs), Math.max(...xs)];
  const [y0, y1] = [Math.min(...points.map((p) => p.min)), Math.max(...points.map((p) => p.max))];
  const W = 300, H = height, span = y1 - y0 || 1;
  const px = (x: number) => ((x - x0) / (x1 - x0 || 1)) * W;
  const py = (y: number) => H - 4 - ((y - y0) / span) * (H - 8);
  let d = "";
  points.forEach((_p, i) => {
    const gap = i > 0 && xs[i] - xs[i - 1] > 90_000;
    d += `${i === 0 || gap ? "M" : "L"}${px(xs[i]).toFixed(1)},${py(ys[i]).toFixed(1)} `;
  });
  return (
    <figure style={{ margin: 0 }}>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} role="img" aria-label={`${y0.toFixed(0)}–${y1.toFixed(0)} ${unit ?? ""}`}>
        <path d={d} fill="none" stroke="var(--accent)" strokeWidth="2" vectorEffect="non-scaling-stroke" />
      </svg>
      <figcaption className="muted row spread"><span>{y0.toFixed(0)} {unit}</span><span>{y1.toFixed(0)} {unit}</span></figcaption>
    </figure>
  );
}
