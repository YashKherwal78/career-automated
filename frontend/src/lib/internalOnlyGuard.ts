import { notFound } from "@tanstack/react-router";

/**
 * Mission Control is an internal ops/telemetry dashboard for the job-discovery
 * pipeline -- not a candidate-facing feature. It was reachable at
 * careerautomated.in/mission-control/* in production (confirmed live,
 * 2026-08-23) even though its data endpoints are operator-gated server-side;
 * the route itself still shipped to every visitor. Blocking it at the
 * production hostname keeps the code available for local/preview use
 * (Vercel preview URLs, localhost) without deleting it, while making it
 * behave as a normal 404 on the real public site.
 */
const BLOCKED_PRODUCTION_HOSTNAMES = new Set(["careerautomated.in", "www.careerautomated.in"]);

export function blockOnProductionHost(): void {
  if (typeof window === "undefined") return;
  if (BLOCKED_PRODUCTION_HOSTNAMES.has(window.location.hostname)) {
    throw notFound();
  }
}
