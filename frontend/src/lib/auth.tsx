import React, { createContext, useContext, useEffect, useRef, useState } from "react";
import { User, Session } from "@supabase/supabase-js";
import { supabase } from "./supabase";
import { API_BASE } from "./api";

interface UserProfile {
  user_id: string;
  email: string;
  full_name: string | null;
  avatar_url: string | null;
  onboarding_complete: boolean;
}

interface AuthContextType {
  user: User | null;
  session: Session | null;
  profile: UserProfile | null;
  isLoading: boolean;
  loginWithEmail: (email: string, password: string) => Promise<any>;
  signUpWithEmail: (email: string, password: string) => Promise<any>;
  loginWithGoogle: () => Promise<any>;
  logout: () => Promise<any>;
  refreshProfile: () => Promise<void>;
  markOnboardingComplete: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Once true, onboarding_complete can never be set back to false on this
  // profile for the rest of the session — it's a one-way transition in
  // reality, and stale/out-of-order profile fetches (e.g. Supabase's own
  // onAuthStateChange listener firing independently of an explicit
  // refreshProfile() call) must not be able to undo a completed onboarding
  // just because they resolve later with an older snapshot.
  const onboardingCompletedRef = useRef(false);

  const applyProfile = (p: UserProfile | null) => {
    if (p && onboardingCompletedRef.current) {
      p = { ...p, onboarding_complete: true };
    }
    setProfile(p);
  };

  const fetchProfile = async (token: string, fallbackUser?: User | null): Promise<UserProfile | null> => {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 1200);
      const response = await fetch(`${API_BASE}/users/me`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
        signal: controller.signal,
      });
      clearTimeout(timeoutId);
      if (response.ok) {
        return await response.json();
      }
    } catch (e) {
      console.warn("Backend profile API slow/unreachable, falling back to Supabase auth:", e);
    }
    if (fallbackUser) {
      try {
        const { data: spData } = await supabase
          .from("user_profiles")
          .select("*")
          .eq("user_id", fallbackUser.id)
          .maybeSingle();

        if (spData) {
          return {
            user_id: spData.user_id,
            email: spData.email || fallbackUser.email || "",
            full_name: spData.full_name || fallbackUser.user_metadata?.full_name || null,
            avatar_url: spData.avatar_url || fallbackUser.user_metadata?.avatar_url || null,
            onboarding_complete: Boolean(spData.onboarding_complete),
          };
        }
      } catch (err) {
        console.warn("Supabase user_profiles direct query error:", err);
      }

      return {
        user_id: fallbackUser.id,
        email: fallbackUser.email ?? "",
        full_name: fallbackUser.user_metadata?.full_name || fallbackUser.user_metadata?.name || null,
        avatar_url: fallbackUser.user_metadata?.avatar_url || fallbackUser.user_metadata?.picture || null,
        onboarding_complete: false,
      };
    }
    return null;
  };

  const refreshProfile = async () => {
    if (session?.access_token) {
      const p = await fetchProfile(session.access_token, user);
      applyProfile(p);
    }
  };

  // Sets onboarding_complete locally without a refetch, so the Dashboard's
  // redirect guard can't lose a race against a concurrent onAuthStateChange
  // profile fetch that resolves with a stale (pre-onboarding) snapshot.
  const markOnboardingComplete = () => {
    onboardingCompletedRef.current = true;
    setProfile((prev) => (prev ? { ...prev, onboarding_complete: true } : prev));
  };

  useEffect(() => {
    // 1. Get initial session from Supabase (synchronous from localStorage)
    supabase.auth.getSession().then(({ data: { session: initialSession } }) => {
      setSession(initialSession);
      const currentUser = initialSession?.user ?? null;
      setUser(currentUser);
      setIsLoading(false); // Unblock UI instantly (0ms)
      
      if (initialSession?.access_token) {
        fetchProfile(initialSession.access_token, currentUser).then(applyProfile);
      }
    });

    // 2. Listen for auth changes (login, logout, token refresh)
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event, currentSession) => {
      setSession(currentSession);
      const currentUser = currentSession?.user ?? null;
      setUser(currentUser);
      setIsLoading(false); // Unblock UI instantly (0ms)
      
      if (currentSession?.access_token) {
        fetchProfile(currentSession.access_token, currentUser).then(applyProfile);
      } else {
        setProfile(null);
      }
    });

    return () => {
      subscription.unsubscribe();
    };
  }, []);

  const loginWithEmail = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const { data, error } = await supabase.auth.signInWithPassword({ email, password });
      if (error) throw error;
      return data;
    } finally {
      setIsLoading(false);
    }
  };

  const signUpWithEmail = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const { data, error } = await supabase.auth.signUp({ email, password });
      if (error) throw error;
      return data;
    } finally {
      setIsLoading(false);
    }
  };

  const loginWithGoogle = async () => {
    const { data, error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: window.location.origin,
      },
    });
    if (error) throw error;
    return data;
  };

  const logout = async () => {
    setIsLoading(true);
    try {
      const { error } = await supabase.auth.signOut();
      if (error) throw error;
      setUser(null);
      setSession(null);
      setProfile(null);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        session,
        profile,
        isLoading,
        loginWithEmail,
        signUpWithEmail,
        loginWithGoogle,
        logout,
        refreshProfile,
        markOnboardingComplete,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
