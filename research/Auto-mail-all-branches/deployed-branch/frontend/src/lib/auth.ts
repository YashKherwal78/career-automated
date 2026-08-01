const API_BASE = 'http://127.0.0.1:8001';

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
  onboarded?: boolean;
  groq_api_1: string;
  hunter_api_key: string;
  getprospect_api_key: string;
  resume_text: string;
  latex_source: string;
  resume_pdf_base64: string;
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
    resume_text: '',
    latex_source: '',
    resume_pdf_base64: '',
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
        if (p.resume_text) profile.resume_text = p.resume_text;
        if (p.latex_source) profile.latex_source = p.latex_source;
        if (p.resume_pdf_base64) profile.resume_pdf_base64 = p.resume_pdf_base64;

        // Check if required fields exist to consider onboarded
        if (p.linkedin_url && p.groq_api_1) profile.onboarded = true;
      }
    }
  } catch (e) {
    console.error("Could not fetch DB profile", e);
  }

  // Merge with any saved fallback settings
  const saved = localStorage.getItem('applywith_profile_settings');
  if (saved) {
    const settings = JSON.parse(saved);
    if (!profile.linkedin_url) profile.linkedin_url = settings.linkedin_url || '';
    if (!profile.institution) profile.institution = settings.institution || '';
    if (profile.linkedin_url) profile.onboarded = true;
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

export async function updateProfileSettings(settings: { 
  linkedin_url: string; 
  institution: string; 
  name?: string;
  groq_api_1?: string;
  hunter_api_key?: string;
  getprospect_api_key?: string;
  resume_text?: string;
  latex_source?: string;
  resume_pdf_base64?: string;
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
  if (settings.resume_pdf_base64 !== undefined) user.resume_pdf_base64 = settings.resume_pdf_base64;
  user.onboarded = true;
  
  localStorage.setItem('applywith_user', JSON.stringify(user));
  localStorage.setItem('applywith_profile_settings', JSON.stringify({
    linkedin_url: settings.linkedin_url,
    institution: settings.institution,
    name: settings.name || user.name,
  }));
  
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
        resume_pdf_base64: settings.resume_pdf_base64 !== undefined ? settings.resume_pdf_base64 : user.resume_pdf_base64,
      })
    });
  } catch (e) {
    console.error("Failed to sync profile to Database", e);
  }
}

export function logout() {
  localStorage.removeItem('applywith_user');
  window.location.href = '/';
}
