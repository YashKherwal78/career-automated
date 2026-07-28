import * as React from "react";

export interface DsAvatarProps {
  initial: string;
  color?: string;
  size?: number;
  radius?: number;
  className?: string;
}

export function DsAvatar({
  initial,
  color = "#635BFF",
  size = 34,
  radius = 9,
  className,
}: DsAvatarProps) {
  return (
    <div
      className={`flex items-center justify-center flex-shrink-0 text-white font-bold ${className ?? ""}`}
      style={{
        width: size,
        height: size,
        borderRadius: radius,
        background: color,
        fontSize: size * 0.4,
      }}
    >
      {initial}
    </div>
  );
}
