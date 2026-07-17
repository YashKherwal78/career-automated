import {
  DEFAULT_TITLE,
  DEFAULT_DESCRIPTION,
  DEFAULT_OG_IMAGE,
  TWITTER_HANDLE,
  SITE_NAME,
  LOCALE,
} from "../../seo.config";
import { getCanonicalUrl } from "./canonical";
import { PageMeta } from "./types";

export function generateMetadata(path: string, options: PageMeta = {}) {
  const isDefaultTitle = !options.title;
  const title = isDefaultTitle ? DEFAULT_TITLE : `${options.title} | ${SITE_NAME}`;
  const description = options.description || DEFAULT_DESCRIPTION;
  const canonical = options.canonical || getCanonicalUrl(path);

  const robotsDirective = options.robots
    ? `${options.robots.index ? "index" : "noindex"}, ${options.robots.follow ? "follow" : "nofollow"}`
    : "index, follow";

  const imageUrl = options.image?.url || DEFAULT_OG_IMAGE;
  const absoluteImageUrl = imageUrl.startsWith("http") ? imageUrl : getCanonicalUrl(imageUrl);

  const metaList: any[] = [
    { title },
    { name: "description", content: description },
    { name: "robots", content: robotsDirective },
    { name: "author", content: SITE_NAME },

    // Open Graph
    { property: "og:title", content: options.title || DEFAULT_TITLE },
    { property: "og:description", content: description },
    { property: "og:url", content: canonical },
    { property: "og:type", content: options.type || "website" },
    { property: "og:site_name", content: SITE_NAME },
    { property: "og:locale", content: LOCALE },
    { property: "og:image", content: absoluteImageUrl },
  ];

  if (options.image?.width) {
    metaList.push({ property: "og:image:width", content: String(options.image.width) });
  }
  if (options.image?.height) {
    metaList.push({ property: "og:image:height", content: String(options.image.height) });
  }
  if (options.image?.alt) {
    metaList.push({ property: "og:image:alt", content: options.image.alt });
  }

  // Twitter
  metaList.push(
    { name: "twitter:card", content: "summary_large_image" },
    { name: "twitter:title", content: options.title || DEFAULT_TITLE },
    { name: "twitter:description", content: description },
    { name: "twitter:image", content: absoluteImageUrl },
    { name: "twitter:creator", content: TWITTER_HANDLE }
  );

  const linksList: any[] = [
    { rel: "canonical", href: canonical }
  ];

  return {
    meta: metaList,
    links: linksList,
  };
}
