import { useState } from "react";

const AVATAR_COLORS = ["#635BFF", "#2F2A26", "#5E5CE6", "#8B7BC0", "#6B8F5E", "#D9A441"];

function colorForName(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
}

/**
 * Hotlinks the company's logo from a free logo API keyed by domain — no
 * storage of images for ~69k companies. Falls back to the existing colored
 * initial avatar if there's no domain on file or the image fails to load.
 */
export function CompanyLogo({
  name,
  domain,
  size = 24,
  radius = 6,
  fontSize = 11,
}: {
  name: string;
  domain?: string | null;
  size?: number;
  radius?: number;
  fontSize?: number;
}) {
  const [failed, setFailed] = useState(false);
  const initial = (name || "?").charAt(0).toUpperCase();

  if (domain && !failed) {
    return (
      <img
        src={`https://unavatar.io/${domain}?fallback=false`}
        alt=""
        onError={() => setFailed(true)}
        className="flex-shrink-0 object-cover"
        style={{ width: size, height: size, borderRadius: radius, background: "#fff" }}
      />
    );
  }

  return (
    <div
      className="flex items-center justify-center flex-shrink-0 text-white font-bold"
      style={{
        width: size,
        height: size,
        borderRadius: radius,
        background: colorForName(name || "?"),
        fontSize,
      }}
    >
      {initial}
    </div>
  );
}
