export const SITE_NAME = "CareerAutomated";

export const SITE_URL =
  (typeof process !== "undefined" ? process.env?.VITE_SITE_URL : undefined) ??
  (import.meta.env?.VITE_SITE_URL) ??
  "https://careerautomated.in";

export const DEFAULT_TITLE = "CareerAutomated — The AI career operating system";
export const DEFAULT_DESCRIPTION =
  "Spend less time applying, more time interviewing. CareerAutomated finds matching jobs, tailors your resume, and drafts applications — you stay in control and approve every send.";

export const DEFAULT_OG_IMAGE = "/og/default.png";
export const THEME_COLOR = "#E85D2C"; // Peach accent
export const TWITTER_HANDLE = "@CareerAutomated";
export const LOCALE = "en_US";

export const SOCIAL_LINKS = [
  "https://linkedin.com",
  "https://twitter.com",
  "https://github.com/YashKherwal78/career-automated"
];
