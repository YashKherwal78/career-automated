import React from "react";
import { LucideIcon } from "lucide-react";

export function StatCard({
  title,
  value,
  detail,
  icon: Icon,
  className = ""
}: {
  title: string;
  value: string | number;
  detail?: string;
  icon?: LucideIcon;
  className?: string;
}) {
  return (
    <div className={`glass-card rounded-2xl p-5 border border-white/40 shadow-sm hover:shadow-md transition-all duration-300 ${className}`}>
      <div className="flex items-start justify-between">
        <div>
          <span className="text-[13px] font-medium tracking-tight text-ink-soft">{title}</span>
          <h3 className="mt-2 text-3xl font-semibold tracking-tight text-ink">{value}</h3>
          {detail && <p className="mt-1 text-xs text-ink-soft">{detail}</p>}
        </div>
        {Icon && (
          <div className="rounded-lg bg-[color:var(--peach-soft)] p-2">
            <Icon className="h-4.5 w-4.5 text-[color:var(--peach-deep)]" />
          </div>
        )}
      </div>
    </div>
  );
}

export function EmptyState({
  title,
  description,
  actionText,
  onAction,
  icon: Icon
}: {
  title: string;
  description: string;
  actionText?: string;
  onAction?: () => void;
  icon?: LucideIcon;
}) {
  return (
    <div className="flex min-h-[300px] flex-col items-center justify-center rounded-2xl border border-dashed border-white/50 bg-white/30 p-8 text-center backdrop-blur">
      {Icon && (
        <div className="rounded-2xl bg-[color:var(--peach-soft)] p-3 text-[color:var(--peach-deep)]">
          <Icon className="h-6 w-6" />
        </div>
      )}
      <h3 className="mt-4 text-base font-semibold text-ink">{title}</h3>
      <p className="mt-2 max-w-sm text-xs leading-relaxed text-ink-soft">{description}</p>
      {actionText && onAction && (
        <button onClick={onAction} className="btn-peach mt-5 text-xs">
          {actionText}
        </button>
      )}
    </div>
  );
}

export function LoadingSkeleton({ type = "table", count = 3 }: { type?: "table" | "cards" | "stats"; count?: number }) {
  if (type === "stats") {
    return (
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="glass-card rounded-2xl p-5 border border-white/40 shadow-sm animate-pulse">
            <div className="h-4 w-24 rounded bg-white/80" />
            <div className="mt-3 h-8 w-16 rounded bg-white/80" />
            <div className="mt-2 h-3 w-32 rounded bg-white/80" />
          </div>
        ))}
      </div>
    );
  }

  if (type === "cards") {
    return (
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: count }).map((_, i) => (
          <div key={i} className="glass-card rounded-2xl p-5 border border-white/40 shadow-sm animate-pulse space-y-3">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-lg bg-white/80" />
              <div className="space-y-1">
                <div className="h-4 w-28 rounded bg-white/80" />
                <div className="h-3 w-20 rounded bg-white/80" />
              </div>
            </div>
            <div className="h-16 rounded bg-white/80" />
            <div className="flex gap-2">
              <div className="h-6 w-16 rounded bg-white/80" />
              <div className="h-6 w-16 rounded bg-white/80" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="w-full space-y-4 animate-pulse">
      <div className="h-8 rounded bg-white/80" />
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="flex gap-4 h-12 items-center border-b border-white/20 px-2">
          <div className="h-4 w-4 rounded bg-white/80" />
          <div className="h-4 w-1/4 rounded bg-white/80" />
          <div className="h-4 w-1/3 rounded bg-white/80" />
          <div className="h-4 w-1/6 rounded bg-white/80" />
          <div className="h-4 w-12 rounded bg-white/80 ml-auto" />
        </div>
      ))}
    </div>
  );
}

export function StatusBadge({ status }: { status: string | null }) {
  const normalized = (status || "").toLowerCase();
  
  if (normalized === "success" || normalized === "active" || normalized === "verified" || normalized === "healthy") {
    return (
      <span className="inline-flex items-center rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-medium text-emerald-700 ring-1 ring-inset ring-emerald-600/20">
        Active
      </span>
    );
  }

  if (normalized === "running" || normalized === "discovered") {
    return (
      <span className="inline-flex items-center rounded-full bg-blue-50 px-2 py-0.5 text-[10px] font-medium text-blue-700 ring-1 ring-inset ring-blue-700/10">
        {status}
      </span>
    );
  }

  if (normalized === "failed" || normalized === "dead") {
    return (
      <span className="inline-flex items-center rounded-full bg-red-50 px-2 py-0.5 text-[10px] font-medium text-red-700 ring-1 ring-inset ring-red-600/10">
        Failed
      </span>
    );
  }

  return (
    <span className="inline-flex items-center rounded-full bg-gray-50 px-2 py-0.5 text-[10px] font-medium text-gray-600 ring-1 ring-inset ring-gray-500/10">
      {status || "Unknown"}
    </span>
  );
}
