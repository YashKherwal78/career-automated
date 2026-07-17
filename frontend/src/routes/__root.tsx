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

function NotFoundComponent() {
  return (
    <div className="flex min-h-screen flex-col">
      <SiteNav />
      <div className="flex flex-1 items-center justify-center px-4">
        <div className="max-w-md text-center">
          <h1 className="font-display text-7xl">404</h1>
          <h2 className="mt-4 text-xl font-medium">Page not found</h2>
          <p className="mt-2 text-sm text-ink-soft">
            The page you're looking for doesn't exist or has been moved.
          </p>
          <div className="mt-6">
            <Link to="/" className="btn-peach text-sm">Go home</Link>
          </div>
        </div>
      </div>
      <SiteFooter />
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
            onClick={() => { router.invalidate(); reset(); }}
            className="btn-peach text-sm"
          >Try again</button>
          <a href="/" className="btn-ghost-ink text-sm">Go home</a>
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
      { name: "google-site-verification", content: (import.meta.env?.VITE_GOOGLE_SITE_VERIFICATION || "") },
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

function RootComponent() {
  const { queryClient } = Route.useRouteContext();
  const router = useRouter();
  const isDashboard = router.state.location.pathname.startsWith("/dashboard");

  if (isDashboard) {
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
