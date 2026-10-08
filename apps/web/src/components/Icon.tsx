/** Inline SVG icon set (stroke icons, currentColor). No external icon font or CDN. */
import type { SVGProps } from "react";

const P: Record<string, string> = {
  home: "M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z",
  rooms: "M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z",
  devices: "M9 3v2M15 3v2M9 19v2M15 19v2M3 9h2M3 15h2M19 9h2M19 15h2M7 5h10a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2zM9.5 9.5h5v5h-5z",
  energy: "M13 2 4 14h7l-1 8 9-12h-7z",
  camera: "M3 8a2 2 0 0 1 2-2h2l2-2h6l2 2h2a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2zM12 17a4 4 0 1 0 0-8 4 4 0 0 0 0 8z",
  hub: "M4 14h16a1 1 0 0 1 1 1v4a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-4a1 1 0 0 1 1-1zM7 17h.01M11 17h.01M8.5 10.5a5 5 0 0 1 7 0M6 8a8.5 8.5 0 0 1 12 0",
  settings: "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z",
  members: "M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM22 21v-2a4 4 0 0 0-3-3.9M16 3.1a4 4 0 0 1 0 7.8",
  more: "M5 12h.01M12 12h.01M19 12h.01",
  bulb: "M9 18h6M10 21h4M12 3a6 6 0 0 0-3.5 10.9c.6.4 1 1.1 1 1.8V16h5v-.3c0-.7.4-1.4 1-1.8A6 6 0 0 0 12 3z",
  gate: "M3 21V7l4-3 4 3v14M13 21V7l4-3 4 3v14M7 10v8M17 10v8M3 13h18",
  ac: "M3 5h18v8H3zM6 9h12M7 17c0 1.5-1 2-1 3M12 16v5M17 17c0 1.5 1 2 1 3",
  fan: "M12 12c0-3 1-7 4-7s2 4 0 5.5M12 12c3 0 7 1 7 4s-4 2-5.5 0M12 12c0 3-1 7-4 7s-2-4 0-5.5M12 12c-3 0-7-1-7-4s4-2 5.5 0",
  drop: "M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11z",
  meter: "M12 14l3-3M4.9 19a9 9 0 1 1 14.2 0zM12 14h.01",
  motion: "M12 12m-2 0a2 2 0 1 0 4 0 2 2 0 1 0-4 0M7.8 7.8a6 6 0 0 0 0 8.4M16.2 16.2a6 6 0 0 0 0-8.4M5 5a10 10 0 0 0 0 14M19 19a10 10 0 0 0 0-14",
  lock: "M6 11h12v10H6zM8 11V7a4 4 0 0 1 8 0v4",
  unlock: "M6 11h12v10H6zM8 11V7a4 4 0 0 1 7.5-2",
  leak: "M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11zM12 10v4M12 17h.01",
  thermo: "M14 14.8V5a2 2 0 0 0-4 0v9.8a4 4 0 1 0 4 0z",
  power: "M12 3v9M6.3 6.3a8 8 0 1 0 11.4 0",
  door: "M6 3h10v18H6zM13 12h.01M16 21h3",
  check: "M5 12.5 10 17 19 7",
  clock: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 7v5l3 2",
  alert: "M12 9v4M12 17h.01M10.3 3.9 2.4 18a2 2 0 0 0 1.7 3h15.8a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z",
  offline: "M2 2l20 20M8.5 16.5a5 5 0 0 1 7 0M5 13a10 10 0 0 1 5.2-2.8M19 13a10 10 0 0 0-2-1.5M2 8.8a15 15 0 0 1 4.2-2.7M22 8.8A15 15 0 0 0 10.7 5M12 20h.01",
  wifi: "M5 13a10 10 0 0 1 14 0M8.5 16.5a5 5 0 0 1 7 0M2 8.8a15 15 0 0 1 20 0M12 20h.01",
  star: "M12 3l2.8 5.7 6.2.9-4.5 4.4 1.1 6.2L12 17.3 6.4 20.2l1.1-6.2L3 9.6l6.2-.9z",
  chevron: "M9 6l6 6-6 6",
  plus: "M12 5v14M5 12h14",
  logout: "M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9",
  play: "M7 4v16l13-8z",
  sun: "M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10zM12 1v2M12 21v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M1 12h2M21 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4",
  moon: "M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z",
  shield: "M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z",
  // ---- devices
  lamp: "M8 3h8l3 8H5zM12 11v8M8 21h8",
  ceiling: "M12 2v4M4 12a8 6 0 0 1 16 0zM9 16l-1 3M12 16v4M15 16l1 3",
  socket: "M5 3h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2zM12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10zM10 11v1.5M14 11v1.5",
  plug: "M9 2v6M15 2v6M6 8h12v4a6 6 0 0 1-12 0zM12 18v4",
  tv: "M3 5h18v12H3zM8 21h8M12 17v4",
  fridge: "M6 2h12v20H6zM6 10h12M9 5v2M9 13v3",
  washer: "M4 2h16v20H4zM4 7h16M7 4.5h.01M10 4.5h.01M12 18a4 4 0 1 0 0-8 4 4 0 0 0 0 8z",
  boiler: "M7 2h10a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2zM9 22v-2M15 22v-2M12 7c-2 2-2 3.5 0 5s2 3 0 5",
  heater: "M5 5v14M9.5 5v14M14.5 5v14M19 5v14M3 8h18M3 16h18",
  pump: "M3 12h4M17 12h4M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10zM12 7V3M9 3h6M12 12l2.5-2.5",
  sprinkler: "M12 22V12M8 22h8M12 12 6 6M12 12l6-6M12 12V4M4 9h.01M20 9h.01M3 4h.01M21 4h.01M12 2h.01",
  garage: "M3 21V9l9-6 9 6v12M7 21v-9h10v9M7 15h10M7 18h10",
  curtain: "M3 3h18M6 3c0 7 1 13 4 18H5M18 3c0 7-1 13-4 18h5",
  window: "M4 3h16v18H4zM12 3v18M4 12h16",
  speaker: "M6 2h12v20H6zM12 18a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM12 6h.01",
  send: "M22 2 11 13M22 2l-7 20-4-9-9-4z",
  breaker: "M7 2h10v20H7zM10 5h4M10 9h4v6h-4zM12 18h.01",
  phone: "M7 2h10v20H7zM11 18h2",
  bell: "M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9M10.3 21a1.9 1.9 0 0 0 3.4 0",
  siren: "M7 18v-6a5 5 0 0 1 10 0v6M5 21h14v-3H5zM12 2v2M4.2 5.2l1.4 1.4M19.8 5.2l-1.4 1.4",
  car: "M5 17h14v-5l-2-5H7l-2 5zM5 12h14M7.5 17v2M16.5 17v2M8 14.5h.01M16 14.5h.01",
  charger: "M5 3h9v18H5zM10 7l-2 4h3l-2 4M14 9h2a2 2 0 0 1 2 2v5a1.5 1.5 0 0 0 3 0V8l-2-2",
  solar: "M4 14h16l-2-9H6zM4 14l-1 4h18l-1-4M12 5v13M5 9.5h14M9 22h6M12 18v4",
  // ---- rooms
  sofa: "M4 11V8a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v3M2 13a2 2 0 0 1 4 0v2h12v-2a2 2 0 0 1 4 0v5H2zM5 18v2M19 18v2",
  bed: "M3 5v15M3 15h18v5M21 15v-3a3 3 0 0 0-3-3h-7v6M6.5 12a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3z",
  kitchen: "M4 10h16v7a3 3 0 0 1-3 3H7a3 3 0 0 1-3-3zM2 10h2M20 10h2M9 6c0-1 1-1 1-2M14 6c0-1 1-1 1-2",
  bath: "M3 12h18v3a5 5 0 0 1-5 5H8a5 5 0 0 1-5-5zM6 12V5a2 2 0 0 1 3.5-1.3M7 20l-1 2M17 20l1 2",
  office: "M4 5h16v10H4zM2 19h20",
  kids: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM9 10h.01M15 10h.01M9.5 14.5a3.5 3.5 0 0 0 5 0",
  dining: "M7 2v20M4 2v6a3 3 0 0 0 6 0V2M17 22V2c-2 2-3 5-3 8h3",
  gym: "M6 7v10M3 9v6M18 7v10M21 9v6M6 12h12",
  pool: "M2 19c2 0 2-1.5 4-1.5s2 1.5 4 1.5 2-1.5 4-1.5 2 1.5 4 1.5 2-1.5 4-1.5M8 15V5a2 2 0 0 1 4 0M16 15V5a2 2 0 0 0-4 0M8 9h8M8 12h8",
  stairs: "M3 20h5v-5h5v-5h5V5h3",
  storage: "M3 7l9-4 9 4v10l-9 4-9-4zM3 7l9 4 9-4M12 11v10",
  plant: "M12 22V11M12 11c0-4 3-7 8-7 0 5-3 8-8 7zM12 14c0-3-2-5-6-5 0 4 2 6 6 5M7 22h10",
  balcony: "M3 12h18M5 12v8M9 12v8M15 12v8M19 12v8M3 20h18M7 12V4h10v8",
  // ---- ui
  edit: "M4 20h4L19 9l-4-4L4 16zM14 6l4 4",
  trash: "M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3",
  close: "M6 6l12 12M18 6 6 18",
  back: "M15 6l-6 6 6 6",
  up: "M12 19V5M5 12l7-7 7 7",
  down: "M12 5v14M19 12l-7 7-7-7",
  stop: "M7 7h10v10H7z",
  minus: "M5 12h14",
  snow: "M12 2v20M4.9 7l14.2 10M4.9 17 19.1 7M9 4l3 2 3-2M9 20l3-2 3 2",
};

export type IconName = keyof typeof P;
export const hasIcon = (name?: string | null): name is string => !!name && name in P;

export function Icon({ name, size = 22, ...rest }: { name: string; size?: number } & SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor"
      strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false" {...rest}>
      <path d={P[name] ?? P.devices} />
    </svg>
  );
}
