/**
 * Derives a display name from an email local-part when full_name isn't set
 * yet (e.g. signed up with email/password, no name captured at signup).
 * "yash.kherwal78@gmail.com" -> "Yash Kherwal78"
 */
function deriveNameFromEmail(email?: string | null): string {
  if (!email) return "";
  const local = email.split("@")[0] || "";
  const cleaned = local.replace(/[._-]+/g, " ").trim();
  if (!cleaned) return "";
  return cleaned
    .split(" ")
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export function getDisplayName(
  fullName?: string | null,
  email?: string | null,
  fallback = "there"
): string {
  if (fullName && fullName.trim()) return fullName.trim();
  return deriveNameFromEmail(email) || fallback;
}

export function getInitial(
  fullName?: string | null,
  email?: string | null,
  fallback = "?"
): string {
  const name = getDisplayName(fullName, email, "");
  return (name || fallback).charAt(0).toUpperCase();
}
