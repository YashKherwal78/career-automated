import { PageImage } from "./types";

export function getSocialImage(url: string, alt?: string, width?: number, height?: number): PageImage {
  return { url, alt, width, height };
}
