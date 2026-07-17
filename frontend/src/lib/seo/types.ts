export interface PageImage {
  url: string;
  width?: number;
  height?: number;
  alt?: string;
}

export interface PageMeta {
  title?: string;
  description?: string;
  canonical?: string;
  robots?: {
    index: boolean;
    follow: boolean;
  };
  image?: PageImage;
  type?: "website" | "article" | "profile";
  breadcrumbs?: Array<{ name: string; item: string }>;
  faqs?: Array<{ question: string; answer: string }>;
}

export interface SitemapEntry {
  path: string;
  lastmod?: string;
  changefreq?: "always" | "hourly" | "daily" | "weekly" | "monthly" | "yearly" | "never";
  priority?: string;
}

export type SitemapProvider = () => Promise<SitemapEntry[]> | SitemapEntry[];
