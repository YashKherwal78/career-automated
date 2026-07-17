import { SITE_URL } from "../../seo.config";

export function getCanonicalUrl(path: string): string {
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  const formattedPath = cleanPath === "/" ? "" : cleanPath.replace(/\/$/, "");
  return `${SITE_URL}${formattedPath}`;
}
