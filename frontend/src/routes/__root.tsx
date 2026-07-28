import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  Outlet,
  Link,
  createRootRouteWithContext,
  useRouter,
  HeadContent,
  Scripts,
} from "@tanstack/react-router";
import { useEffect, type ReactNode } from "react";

import appCss from "../styles.css?url";
import { reportLovableError } from "../lib/lovable-error-reporting";
import { SiteNav } from "../components/site-nav";
import { SiteFooter } from "../components/site-footer";
import { DsLogo } from "../components/ds/Logo";

function NotFoundComponent() {
  return (
    <div
      className="flex min-h-screen flex-col items-center justify-center text-center px-6"
      style={{ fontFamily: "var(--ds-font-body)", color: "var(--ds-text-primary)" }}
    >
      <div className="mb-10">
        <DsLogo box={30} wordmark={16} weight={700} />
      </div>
      <div
        className="font-[var(--ds-font-display)] font-bold mb-2"
        style={{ fontSize: 56, color: "var(--ds-ink-300)" }}
      >
        404
      </div>
      <h1 className="font-[var(--ds-font-display)] font-semibold text-[22px] mb-2.5">
        This page wandered off.
      </h1>
      <p
        className="text-[14.5px] mb-7"
        style={{ color: "var(--ds-ink-500)", maxWidth: 360, lineHeight: 1.6 }}
      >
        Nothing to worry about — your applications and matches are all still being tracked. Let's
        get you back to it.
      </p>
      <Link
        to="/dashboard"
        className="font-bold text-sm"
        style={{
          padding: "12px 24px",
          borderRadius: "var(--ds-radius-md)",
          background: "var(--ds-accent-primary)",
          color: "var(--ds-text-on-brand)",
          boxShadow: "0 10px 22px -8px rgba(226,116,72,0.45)",
        }}
      >
        Back to dashboard
      </Link>
    </div>
  );
}

function ErrorComponent({ error, reset }: { error: Error; reset: () => void }) {
  console.error(error);
  const router = useRouter();
  useEffect(() => {
    reportLovableError(error, { boundary: "tanstack_root_error_component" });
  }, [error]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="max-w-md text-center">
        <h1 className="text-xl font-semibold tracking-tight">This page didn't load</h1>
        <p className="mt-2 text-sm text-ink-soft">
          Something went wrong on our end. You can try refreshing or head back home.
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-2">
          <button
            onClick={() => {
              router.invalidate();
              reset();
            }}
            className="btn-peach text-sm"
          >
            Try again
          </button>
          <a href="/" className="btn-ghost-ink text-sm">
            Go home
          </a>
        </div>
      </div>
    </div>
  );
}

import {
  generateMetadata,
  generateOrganizationSchema,
  generateWebSiteSchema,
  generateSoftwareApplicationSchema,
} from "../lib/seo";

const defaultSEO = generateMetadata("/");

export const Route = createRootRouteWithContext<{ queryClient: QueryClient }>()({
  head: () => ({
    meta: [
      { charSet: "utf-8" },
      { name: "viewport", content: "width=device-width, initial-scale=1, shrink-to-fit=no" },
      { name: "theme-color", content: "#E85D2C" },
      { name: "application-name", content: "CareerAutomated" },
      { name: "apple-mobile-web-app-title", content: "CareerAutomated" },
      { name: "format-detection", content: "telephone=no" },
      {
        name: "google-site-verification",
        content: import.meta.env?.VITE_GOOGLE_SITE_VERIFICATION || "",
      },
      ...defaultSEO.meta,
    ],
    links: [
      { rel: "stylesheet", href: appCss },
      { rel: "icon", href: "/favicon.ico", type: "image/x-icon" },
      { rel: "icon", href: "/favicon.svg", type: "image/svg+xml" },
      { rel: "apple-touch-icon", href: "/apple-touch-icon.png" },
      { rel: "manifest", href: "/manifest.webmanifest" },
      { rel: "preconnect", href: "https://fonts.googleapis.com" },
      { rel: "preconnect", href: "https://fonts.gstatic.com", crossOrigin: "anonymous" },
      { rel: "preconnect", href: "https://api.fontshare.com" },
      {
        rel: "stylesheet",
        href: "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap",
      },
      {
        rel: "stylesheet",
        href: "https://api.fontshare.com/v2/css?f[]=general-sans@400,500,600,700&display=swap",
      },
      ...defaultSEO.links,
    ],
  }),

  shellComponent: RootShell,
  component: RootComponent,
  notFoundComponent: NotFoundComponent,
  errorComponent: ErrorComponent,
});

function RootShell({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <head>
        <HeadContent />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify(generateOrganizationSchema()),
          }}
        />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify(generateWebSiteSchema()),
          }}
        />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify(generateSoftwareApplicationSchema()),
          }}
        />
      </head>
      <body>
        {children}
        <Scripts />
      </body>
    </html>
  );
}

import { AuthProvider } from "../lib/auth";

// Routes that own their full page chrome (own header/logo, no shared marketing nav/footer)
// per the CareerAutomated design handoff — see design_handoff_careerautomated/*.dc.html.
const FULL_BLEED_PATHS = new Set([
  "/",
  "/signin",
  "/signup",
  "/forgot-password",
  "/legal",
  "/onboarding",
  "/pricing",
  "/checkout",
  "/payment-success",
  "/upgrade",
]);

function RootComponent() {
  const { queryClient } = Route.useRouteContext();
  const router = useRouter();
  const pathname = router.state.location.pathname;
  const isDashboard = pathname.startsWith("/dashboard");
  const isNotFound =
    router.state.statusCode === 404 ||
    router.state.matches.some((m) => m.status === "notFound" || m.globalNotFound);
  const isFullBleed = FULL_BLEED_PATHS.has(pathname) || isNotFound;

  if (isDashboard || isFullBleed) {
    return (
      <AuthProvider>
        <QueryClientProvider client={queryClient}>
          <Outlet />
        </QueryClientProvider>
      </AuthProvider>
    );
  }

  return (
    <AuthProvider>
      <QueryClientProvider client={queryClient}>
        <div className="flex min-h-screen flex-col">
          <SiteNav />
          <main className="flex-1">
            <Outlet />
          </main>
          <SiteFooter />
        </div>
      </QueryClientProvider>
    </AuthProvider>
  );
}
