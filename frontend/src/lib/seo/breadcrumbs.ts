import { getCanonicalUrl } from "./canonical";

export function buildBreadcrumbs(path: string) {
  const parts = path.split("/").filter(Boolean);
  const items = [{ name: "Home", item: "/" }];

  let currentPath = "";
  for (const part of parts) {
    currentPath += `/${part}`;
    const name = part.charAt(0).toUpperCase() + part.slice(1).replace(/-/g, " ");
    items.push({ name, item: currentPath });
  }

  return items;
}
