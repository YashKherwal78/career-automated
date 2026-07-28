/** Backend API base URL, e.g. "http://localhost:8000/api/v1". Single source of truth — do not re-derive elsewhere. */
export const API_BASE = (
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1"
).replace(/\/$/, "");
