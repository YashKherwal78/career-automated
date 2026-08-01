const API_BASE = 'http://localhost:8002';

// Google OAuth Config — user will fill these in from GCP Console
const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || '';
const GOOGLE_REDIRECT_URI = window.location.origin + '/auth/callback';
const GOOGLE_SCOPES = [
  'openid',
  'email',
  'profile',
  'https://www.googleapis.com/auth/gmail.send',
].join(' ');

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
}

export function getGoogleAuthUrl(): string {
  const params = new URLSearchParams({
    client_id: GOOGLE_CLIENT_ID,
    redirect_uri: GOOGLE_REDIRECT_URI,
    response_type: 'code',
    scope: GOOGLE_SCOPES,
    access_type: 'offline',
    prompt: 'consent',
  });
  return `https://accounts.google.com/o/oauth2/v2/auth?${params.toString()}`;
}

export async function exchangeCodeForTokens(code: string): Promise<UserProfile> {
  const res = await fetch(`${API_BASE}/api/auth/google`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code, redirect_uri: GOOGLE_REDIRECT_URI }),
  });
  if (!res.ok) throw new Error('Failed to exchange auth code');
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
  };

  // Merge with any saved settings
  const saved = localStorage.getItem('applywith_profile_settings');
  if (saved) {
    const settings = JSON.parse(saved);
    profile.linkedin_url = settings.linkedin_url || '';
    profile.institution = settings.institution || '';
  }
  
  localStorage.setItem('applywith_user', JSON.stringify(profile));
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
    localStorage.setItem('applywith_user', JSON.stringify(user));
    return user;
  } catch {
    return null;
  }
}

export function getUser(): UserProfile | null {
  const stored = localStorage.getItem('applywith_user');
  if (!stored) return null;
  try {
    return JSON.parse(stored) as UserProfile;
  } catch {
    return null;
  }
}

export function isLoggedIn(): boolean {
  const user = getUser();
  return !!user?.access_token;
}

export function updateProfileSettings(settings: { linkedin_url: string; institution: string; name?: string }) {
  const user = getUser();
  if (!user) return;
  if (settings.name) user.name = settings.name;
  user.linkedin_url = settings.linkedin_url;
  user.institution = settings.institution;
  localStorage.setItem('applywith_user', JSON.stringify(user));
  localStorage.setItem('applywith_profile_settings', JSON.stringify({
    linkedin_url: settings.linkedin_url,
    institution: settings.institution,
    name: settings.name || user.name,
  }));
}

export function logout() {
  localStorage.removeItem('applywith_user');
  window.location.href = '/';
}
