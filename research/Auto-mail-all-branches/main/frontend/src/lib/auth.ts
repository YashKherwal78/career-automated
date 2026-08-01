import { LEGACY_STORAGE_KEYS, STORAGE_KEYS } from './branding';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8001';

// Google OAuth Config — user will fill these in from GCP Console
const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || '';
const GOOGLE_REDIRECT_URI = window.location.origin + '/auth/callback';
const GOOGLE_SCOPES = [
  'openid',
  'email',
  'profile',
  'https://www.googleapis.com/auth/gmail.send',
].join(' ');

const TOKEN_SKEW_MS = 60_000;

export interface UserProfile {
  email: string;
  name: string;
  picture: string;
  access_token: string;
  refresh_token?: string;
  expires_at: number;
  // User-configurable fields
  linkedin_url: string;
  institution: string;
  onboarded?: boolean;
  groq_api_1: string;
  hunter_api_key: string;
  getprospect_api_key: string;
  apollo_api_key: string;
  snov_api_key: string;
  fireworks_api_key: string;
  resume_text: string;
  latex_source: string;
  resume_bucket_uri: string;
}

function readRawUser(): string | null {
  return (
    localStorage.getItem(STORAGE_KEYS.user) ??
    localStorage.getItem(LEGACY_STORAGE_KEYS.user)
  );
}

function writeUser(profile: UserProfile): void {
  const json = JSON.stringify(profile);
  localStorage.setItem(STORAGE_KEYS.user, json);
  localStorage.removeItem(LEGACY_STORAGE_KEYS.user);
}

function readProfileSettingsRaw(): string | null {
  return (
    localStorage.getItem(STORAGE_KEYS.profileSettings) ??
    localStorage.getItem(LEGACY_STORAGE_KEYS.profileSettings)
  );
}

function migrateProfileSettingsIfNeeded(): void {
  const legacy = localStorage.getItem(LEGACY_STORAGE_KEYS.profileSettings);
  const primary = localStorage.getItem(STORAGE_KEYS.profileSettings);
  if (legacy && !primary) {
    localStorage.setItem(STORAGE_KEYS.profileSettings, legacy);
    localStorage.removeItem(LEGACY_STORAGE_KEYS.profileSettings);
  }
}

export function getGoogleAuthUrl(): string {
  const params = new URLSearchParams({
    client_id: GOOGLE_CLIENT_ID,
    redirect_uri: GOOGLE_REDIRECT_URI,
    response_type: 'code',
    scope: GOOGLE_SCOPES,
    access_type: 'offline',
  });

  // Force consent only when we still need a refresh token; otherwise avoid re-prompting.
  const raw = readRawUser();
  if (raw) {
    try {
      const u = JSON.parse(raw) as UserProfile;
      if (!u.refresh_token?.trim()) params.set('prompt', 'consent');
    } catch {
      params.set('prompt', 'consent');
    }
  } else {
    params.set('prompt', 'consent');
  }

  return `https://accounts.google.com/o/oauth2/v2/auth?${params.toString()}`;
}

function isAccessTokenValid(user: UserProfile): boolean {
  if (!user.access_token?.trim()) return false;
  if (!user.expires_at) return true;
  return Date.now() < user.expires_at - TOKEN_SKEW_MS;
}

/** True if stored session can be used without visiting Google (valid or refreshable). */
export function hasRefreshableSession(): boolean {
  const user = getUser();
  if (!user) return false;
  if (isAccessTokenValid(user)) return true;
  return !!user.refresh_token?.trim();
}

/**
 * Ensures a usable access token: refreshes when expired if possible.
 * On failure, clears session. Call from landing / route guards.
 */
export async function ensureValidSession(): Promise<boolean> {
  const user = getUser();
  if (!user?.access_token?.trim()) return false;
  if (isAccessTokenValid(user)) return true;
  if (!user.refresh_token?.trim()) {
    logout();
    return false;
  }
  const refreshed = await refreshAccessToken();
  if (refreshed?.access_token) return true;
  logout();
  return false;
}

export async function exchangeCodeForTokens(code: string): Promise<UserProfile> {
  const res = await fetch(`${API_BASE}/api/auth/google`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code, redirect_uri: GOOGLE_REDIRECT_URI }),
  });
  if (!res.ok) {
     const errorText = await res.text();
     throw new Error(`Server returned ${res.status}: ${errorText}`);
  }
  const data = await res.json();

  const profile: UserProfile = {
    email: data.email,
    name: data.name,
    picture: data.picture,
    access_token: data.access_token,
    refresh_token: data.refresh_token,
    expires_at: Date.now() + (data.expires_in || 3600) * 1000,
    linkedin_url: '',
    institution: '',
    onboarded: false,
    groq_api_1: '',
    hunter_api_key: '',
    getprospect_api_key: '',
    apollo_api_key: '',
    snov_api_key: '',
    fireworks_api_key: '',
    resume_text: '',
    latex_source: '',
    resume_bucket_uri: '',
  };

  try {
    const pRes = await fetch(`${API_BASE}/api/profile?email=${encodeURIComponent(data.email)}`);
    if (pRes.ok) {
      const pData = await pRes.json();
      const p = pData.profile;
      if (p && Object.keys(p).length > 0) {
        if (p.linkedin_url) profile.linkedin_url = p.linkedin_url;
        if (p.name) profile.name = p.name;
        if (p.institution) profile.institution = p.institution;
        if (p.groq_api_1) profile.groq_api_1 = p.groq_api_1;
        if (p.hunter_api_key) profile.hunter_api_key = p.hunter_api_key;
        if (p.getprospect_api_key) profile.getprospect_api_key = p.getprospect_api_key;
        if (p.apollo_api_key) profile.apollo_api_key = p.apollo_api_key;
        if (p.snov_api_key) profile.snov_api_key = p.snov_api_key;
        if (p.fireworks_api_key) profile.fireworks_api_key = p.fireworks_api_key;
        if (p.resume_text) profile.resume_text = p.resume_text;
        if (p.latex_source) profile.latex_source = p.latex_source;
        if (p.resume_bucket_uri) profile.resume_bucket_uri = p.resume_bucket_uri;

        if (p.linkedin_url && p.groq_api_1 && p.hunter_api_key) profile.onboarded = true;
      }
    }
  } catch (e) {
    console.error("Could not fetch DB profile", e);
  }

  migrateProfileSettingsIfNeeded();
  const saved = readProfileSettingsRaw();
  if (saved) {
    const settings = JSON.parse(saved);
    if (!profile.linkedin_url) profile.linkedin_url = settings.linkedin_url || '';
    if (!profile.institution) profile.institution = settings.institution || '';
  }

  writeUser(profile);
  return profile;
}

export async function refreshAccessToken(): Promise<UserProfile | null> {
  const user = getUser();
  if (!user?.refresh_token) return null;

  try {
    const res = await fetch(`${API_BASE}/api/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: user.refresh_token }),
    });
    if (!res.ok) return null;
    const data = await res.json();
    user.access_token = data.access_token;
    user.expires_at = Date.now() + (data.expires_in || 3600) * 1000;
    writeUser(user);
    return user;
  } catch {
    return null;
  }
}

export function getUser(): UserProfile | null {
  const raw = readRawUser();
  if (!raw) return null;
  try {
    const profile = JSON.parse(raw) as UserProfile;
    if (localStorage.getItem(LEGACY_STORAGE_KEYS.user)) {
      writeUser(profile);
    }
    return profile;
  } catch {
    return null;
  }
}

/** Persist profile to primary storage (use after merging server fields). */
export function persistUser(profile: UserProfile): void {
  writeUser(profile);
}

export function isLoggedIn(): boolean {
  const user = getUser();
  return !!user?.access_token?.trim();
}

export async function updateProfileSettings(settings: {
  linkedin_url: string;
  institution: string;
  name?: string;
  groq_api_1?: string;
  hunter_api_key?: string;
  getprospect_api_key?: string;
  mailmeteor_api_key?: string;
  salesql_api_key?: string;
  resume_text?: string;
  latex_source?: string;
  resume_bucket_uri?: string;
}) {
  const user = getUser();
  if (!user) return;
  if (settings.name) user.name = settings.name;
  user.linkedin_url = settings.linkedin_url;
  user.institution = settings.institution;
  if (settings.groq_api_1 !== undefined) user.groq_api_1 = settings.groq_api_1;
  if (settings.hunter_api_key !== undefined) user.hunter_api_key = settings.hunter_api_key;
  if (settings.getprospect_api_key !== undefined) user.getprospect_api_key = settings.getprospect_api_key;
  if (settings.resume_text !== undefined) user.resume_text = settings.resume_text;
  if (settings.latex_source !== undefined) user.latex_source = settings.latex_source;
  if (settings.resume_bucket_uri !== undefined) user.resume_bucket_uri = settings.resume_bucket_uri;
  user.onboarded = true;

  writeUser(user);
  localStorage.setItem(STORAGE_KEYS.profileSettings, JSON.stringify({
    linkedin_url: settings.linkedin_url,
    institution: settings.institution,
    name: settings.name || user.name,
  }));
  localStorage.removeItem(LEGACY_STORAGE_KEYS.profileSettings);

  // Persist to DB
  try {
    await fetch(`${API_BASE}/api/profile`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: user.email,
        name: user.name,
        linkedin_url: settings.linkedin_url,
        groq_api_1: settings.groq_api_1 !== undefined ? settings.groq_api_1 : user.groq_api_1,
        hunter_api_key: settings.hunter_api_key !== undefined ? settings.hunter_api_key : user.hunter_api_key,
        getprospect_api_key: settings.getprospect_api_key !== undefined ? settings.getprospect_api_key : user.getprospect_api_key,
        resume_text: settings.resume_text !== undefined ? settings.resume_text : user.resume_text,
        latex_source: settings.latex_source !== undefined ? settings.latex_source : user.latex_source,
        resume_bucket_uri: settings.resume_bucket_uri !== undefined ? settings.resume_bucket_uri : user.resume_bucket_uri,
      })
    });
  } catch (e) {
    console.error("Failed to sync profile to Database", e);
  }
}

export function logout() {
  localStorage.removeItem(STORAGE_KEYS.user);
  localStorage.removeItem(LEGACY_STORAGE_KEYS.user);
  localStorage.removeItem(STORAGE_KEYS.profileSettings);
  localStorage.removeItem(LEGACY_STORAGE_KEYS.profileSettings);
  window.location.href = '/';
}

export { API_BASE };
