const fs = require('fs');
const path = require('path');

const FRONTEND_DIR = path.resolve(__dirname, '..');

class SEOValidator {
  constructor(name) {
    this.name = name;
  }
  validate() {
    throw new Error('Not implemented');
  }
}

class AssetValidator extends SEOValidator {
  constructor() {
    super('Asset Validator');
  }
  validate() {
    const assets = [
      'public/favicon.ico',
      'public/robots.txt',
      'public/manifest.webmanifest'
    ];
    for (const asset of assets) {
      const fullPath = path.join(FRONTEND_DIR, asset);
      if (!fs.existsSync(fullPath)) {
        throw new Error(`Missing required asset: ${asset}`);
      }
    }
    console.log('✓ Assets validated.');
  }
}

class ConfigValidator extends SEOValidator {
  constructor() {
    super('Config Validator');
  }
  validate() {
    const configPath = path.join(FRONTEND_DIR, 'src/seo.config.ts');
    if (!fs.existsSync(configPath)) {
      throw new Error('Missing src/seo.config.ts configuration file.');
    }
    const content = fs.readFileSync(configPath, 'utf8');
    const requiredKeys = ['SITE_NAME', 'SITE_URL', 'DEFAULT_TITLE', 'DEFAULT_DESCRIPTION', 'THEME_COLOR'];
    for (const key of requiredKeys) {
      if (!content.includes(key)) {
        throw new Error(`Missing configuration key: ${key} in seo.config.ts`);
      }
    }
    console.log('✓ Config validated.');
  }
}

class AccessibilityValidator extends SEOValidator {
  constructor() {
    super('Accessibility Validator');
  }
  validate() {
    const routes = [
      'src/routes/index.tsx',
      'src/routes/pricing.tsx',
      'src/routes/about.tsx',
      'src/routes/about/product.tsx'
    ];
    for (const route of routes) {
      const fullPath = path.join(FRONTEND_DIR, route);
      if (!fs.existsSync(fullPath)) continue;
      const content = fs.readFileSync(fullPath, 'utf8');
      
      if (!content.includes('generateMetadata')) {
        throw new Error(`Missing generateMetadata integration in route: ${route}`);
      }
      
      const h1Count = (content.match(/<h1[\s>]/g) || []).length;
      if (h1Count > 1) {
        throw new Error(`Multiple <h1> tags found in route: ${route}. Exactly one h1 required per page.`);
      }
    }
    console.log('✓ Accessibility and headings validated.');
  }
}

const registry = [
  new AssetValidator(),
  new ConfigValidator(),
  new AccessibilityValidator()
];

console.log('Running SEO Validation Suite...');
try {
  for (const validator of registry) {
    console.log(`Running ${validator.name}...`);
    validator.validate();
  }
  console.log('🎉 All SEO validation checks passed successfully!');
  // TODO: Integrate Lighthouse CI gates in future GitHub Actions configurations
} catch (error) {
  console.error(`❌ SEO Validation Failed: ${error.message}`);
  process.exit(1);
}
