/** Product copy and localStorage keys for Junie AI. */

export const PRODUCT_NAME = 'Junie AI';
export const PRODUCT_SHORT = 'Junie';

/** User-facing description of what the assistant does (orchestration + AI). */
export const PRODUCT_TAGLINE =
  'Junie researches the company, runs contact discovery, drafts your outreach, and sends through your Gmail — in one flow.';

export const STORAGE_KEYS = {
  user: 'junie_user',
  profileSettings: 'junie_profile_settings',
} as const;

/** Migrated automatically on read; removed after migration. */
export const LEGACY_STORAGE_KEYS = {
  user: 'applywith_user',
  profileSettings: 'applywith_profile_settings',
  latexDraft: 'applywith_latex_source',
} as const;
