import { SitemapEntry, SitemapProvider } from "./types";

const sitemapProviders: Set<SitemapProvider> = new Set();

export function registerSitemapProvider(provider: SitemapProvider) {
  sitemapProviders.add(provider);
}

export function unregisterSitemapProvider(provider: SitemapProvider) {
  sitemapProviders.delete(provider);
}

export async function getSitemapEntries(): Promise<SitemapEntry[]> {
  const allEntries: SitemapEntry[] = [];
  
  const staticRoutes: SitemapEntry[] = [
    { path: "/", changefreq: "weekly", priority: "1.0" },
    { path: "/pricing", changefreq: "monthly", priority: "0.9" },
    { path: "/about", changefreq: "monthly", priority: "0.8" },
    { path: "/about/product", changefreq: "monthly", priority: "0.8" },
    { path: "/faq", changefreq: "weekly", priority: "0.7" },
    { path: "/contact", changefreq: "monthly", priority: "0.7" },
    { path: "/privacy", changefreq: "yearly", priority: "0.3" },
    { path: "/terms", changefreq: "yearly", priority: "0.3" },
  ];

  allEntries.push(...staticRoutes);

  for (const provider of sitemapProviders) {
    try {
      const entries = await provider();
      allEntries.push(...entries);
    } catch (error) {
      console.error("Error fetching sitemap entries from provider:", error);
    }
  }

  return allEntries;
}
