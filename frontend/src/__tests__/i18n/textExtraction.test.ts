/**
 * Unit tests for text extraction completeness.
 *
 * Validates: Requirements 4.1, 4.2
 *
 * 1. Verifies no hardcoded Dutch strings remain in member-facing components
 * 2. Verifies all translation keys used in components exist in Dutch reference files
 */

import * as fs from 'fs';
import * as path from 'path';

// ---------- Configuration ----------

const FRONTEND_SRC = path.resolve(__dirname, '../..');
const LOCALES_DIR = path.resolve(FRONTEND_SRC, 'locales/nl');

/**
 * Member-facing directories to scan for Dutch text and translation key usage.
 * Admin pages are EXCLUDED per requirement 9.
 */
const MEMBER_FACING_DIRS = [
  path.resolve(FRONTEND_SRC, 'pages'),
  path.resolve(FRONTEND_SRC, 'components/auth'),
  path.resolve(FRONTEND_SRC, 'components/common'),
  path.resolve(FRONTEND_SRC, 'components/layout'),
  path.resolve(FRONTEND_SRC, 'modules/webshop'),
];

/**
 * Files/directories explicitly excluded from scanning (admin-only components).
 * These match the admin routes: /members, /products, /events, /memberships, /advanced-exports
 */
const EXCLUDED_PATTERNS = [
  /modules[\\/]advanced-exports/i,
  /modules[\\/]members/i,
  /modules[\\/]events/i,
  /modules[\\/]products/i,
  /MemberAdminTable/i,
  /MemberFilters/i,
  /MemberList/i,
  /MemberEditView/i,
  /MemberReadView/i,
  /MembershipManagement/i,
  /ExportButton/i,
  /OrdersAdmin/i,
  /__tests__/i,
  /\.test\./i,
  /\.spec\./i,
];

/**
 * Common Dutch words that indicate untranslated hardcoded text.
 * These are words that would never appear in properly internationalized code
 * unless they are inside a t() call, a comment, or a variable/key name.
 */
const DUTCH_PATTERNS: { pattern: RegExp; description: string }[] = [
  { pattern: /['"`](?:[^'"`]*\b(?:Geen|geen)\s+(?:toegang|gegevens|data|resultaten|leden|producten|items)\b[^'"`]*)['"`]/, description: 'Dutch "Geen ..." phrase' },
  { pattern: /['"`](?:[^'"`]*\b(?:Fout|fout)\s+bij\s+\w+\b[^'"`]*)['"`]/, description: 'Dutch "Fout bij ..." error phrase' },
  { pattern: /['"`](?:[^'"`]*\b(?:Laden|laden)\.\.\.[^'"`]*)['"`]/, description: 'Dutch "Laden..." loading text' },
  { pattern: /['"`](?:[^'"`]*\b(?:Opslaan|Verwijderen|Annuleren|Bewerken|Toevoegen|Zoeken)\b[^'"`]*)['"`]/, description: 'Dutch button labels' },
  { pattern: /['"`](?:[^'"`]*\b(?:Welkom|welkom)\s+(?:bij|terug)\b[^'"`]*)['"`]/, description: 'Dutch "Welkom" greeting' },
  { pattern: /['"`](?:[^'"`]*\bProbeer\s+(?:het\s+)?(?:opnieuw|later)\b[^'"`]*)['"`]/, description: 'Dutch "Probeer opnieuw" retry text' },
  { pattern: /['"`](?:[^'"`]*\bSuccesvol\s+\w+\b[^'"`]*)['"`]/, description: 'Dutch "Succesvol" success message' },
  { pattern: /['"`](?:[^'"`]*\bWeet\s+(?:je|u)\s+zeker\b[^'"`]*)['"`]/, description: 'Dutch confirmation dialog' },
  { pattern: /['"`](?:[^'"`]*\bVul\s+(?:een|je|uw)\b[^'"`]*)['"`]/, description: 'Dutch form validation "Vul ..."' },
  { pattern: /['"`](?:[^'"`]*\bVerplicht\s+veld\b[^'"`]*)['"`]/, description: 'Dutch "Verplicht veld" required field' },
];

/**
 * Patterns to skip when checking for Dutch text (legitimate uses).
 * These include comments, translation function calls, imports, etc.
 */
const SKIP_LINE_PATTERNS = [
  /^\s*\/\//, // single-line comments
  /^\s*\*/, // block comment content
  /^\s*\/\*/, // block comment start
  /^\s*import\s/, // import statements
  /^\s*export\s/, // export statements
  /console\.(log|warn|error|debug)/, // console logging
  /^\s*\/\/ ?eslint/, // eslint directives
];

// ---------- Utility Functions ----------

/**
 * Recursively collects .tsx and .ts files from a directory,
 * excluding test files and admin components.
 */
function collectSourceFiles(dir: string): string[] {
  const files: string[] = [];

  if (!fs.existsSync(dir)) return files;

  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);

    // Check if this path matches an exclusion pattern
    if (EXCLUDED_PATTERNS.some((p) => p.test(fullPath))) continue;

    if (entry.isDirectory()) {
      files.push(...collectSourceFiles(fullPath));
    } else if (entry.isFile() && /\.(tsx?|jsx?)$/.test(entry.name)) {
      files.push(fullPath);
    }
  }

  return files;
}

/**
 * Checks if a line contains a Dutch text string that should have been extracted.
 * Returns the match description or null if no Dutch text found.
 */
function findDutchTextInLine(
  line: string
): { description: string; match: string } | null {
  // Skip lines that are comments, imports, or console statements
  if (SKIP_LINE_PATTERNS.some((p) => p.test(line))) return null;

  // Skip lines that are inside t() calls (already translated)
  // This is a heuristic: if the line has t(' or t(" it's likely a translation call
  if (/\bt\s*\(/.test(line)) return null;

  // Skip lines that are translation key definitions or JSON imports
  if (/^\s*['"`]\w+[\w.]*['"`]\s*:/.test(line)) return null;

  for (const { pattern, description } of DUTCH_PATTERNS) {
    const match = line.match(pattern);
    if (match) {
      // Additional check: skip if this is inside a comment block or part of
      // admin-only code (cards with admin routes)
      const matchedText = match[0];

      // Skip admin card labels (these are intentionally Dutch per requirement 9)
      if (
        /Ledenadministratie|Evenementenadministratie|Product Management|Geavanceerde Exports|Lidmaatschap Beheer/.test(
          matchedText
        )
      ) {
        continue;
      }

      // Skip if it's a title/description for an admin FunctionGuard card
      // (checking surrounding context would need multi-line, so we check common admin labels)
      if (/Beheer\s+(leden|evenementen|webshop|producten|lidmaatschap)/.test(matchedText)) {
        continue;
      }

      return { description, match: matchedText };
    }
  }

  return null;
}

/**
 * Extracts all t('key') and t("key") translation key references from source code.
 * Handles both simple keys and namespaced keys (e.g., t('common.nav.title') or t('key', { ns: 'webshop' })).
 */
function extractTranslationKeys(content: string): { key: string; namespace?: string }[] {
  const keys: { key: string; namespace?: string }[] = [];

  // Match t('key') or t("key") — captures the first argument string
  const tCallRegex = /\bt\s*\(\s*['"]([^'"]+)['"]/g;
  let match;

  while ((match = tCallRegex.exec(content)) !== null) {
    const fullKey = match[1];

    // Check if there's a namespace option in the immediate options object.
    // We look for the closing of the key string and then a comma followed by an object
    // containing ns: 'namespace'. We limit search to avoid picking up nested t() calls.
    const afterKey = content.slice(match.index + match[0].length);
    let namespace: string | undefined;

    // Only look for ns: within the same function call's options object.
    // Find the matching closing paren, tracking depth to avoid nested calls.
    let depth = 1;
    let searchEnd = 0;
    for (let i = 0; i < Math.min(afterKey.length, 200); i++) {
      if (afterKey[i] === '(') depth++;
      if (afterKey[i] === ')') {
        depth--;
        if (depth === 0) {
          searchEnd = i;
          break;
        }
      }
      // If we hit another t( call, stop searching for ns:
      if (afterKey.slice(i).match(/^\bt\s*\(/)) break;
    }

    if (searchEnd > 0) {
      const optionsSlice = afterKey.slice(0, searchEnd);
      // Only match ns: if it appears before any nested t() call
      const nestedTIndex = optionsSlice.search(/\bt\s*\(/);
      const nsSearchSlice = nestedTIndex > 0 ? optionsSlice.slice(0, nestedTIndex) : optionsSlice;
      const nsMatch = nsSearchSlice.match(/ns:\s*['"]([^'"]+)['"]/);
      namespace = nsMatch ? nsMatch[1] : undefined;
    }

    keys.push({
      key: fullKey,
      namespace,
    });
  }

  return keys;
}

/**
 * Extracts the namespace from a useTranslation() call in source code.
 */
function extractUseTranslationNamespace(content: string): string | null {
  const match = content.match(/useTranslation\s*\(\s*['"]([^'"]+)['"]/);
  return match ? match[1] : null;
}

/**
 * Loads all Dutch translation files and returns a map of namespace -> flat keys.
 * Flattens nested keys using dot notation.
 */
function loadDutchTranslations(): Map<string, Set<string>> {
  const translations = new Map<string, Set<string>>();

  const files = fs.readdirSync(LOCALES_DIR).filter((f) => f.endsWith('.json'));
  for (const file of files) {
    const namespace = file.replace('.json', '');
    const filePath = path.join(LOCALES_DIR, file);
    const content = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
    const keys = flattenKeys(content);
    translations.set(namespace, new Set(keys));
  }

  return translations;
}

/**
 * Flattens a nested object into dot-notation keys.
 */
function flattenKeys(obj: Record<string, unknown>, prefix = ''): string[] {
  const keys: string[] = [];

  for (const [key, value] of Object.entries(obj)) {
    const fullKey = prefix ? `${prefix}.${key}` : key;
    if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
      keys.push(...flattenKeys(value as Record<string, unknown>, fullKey));
    } else {
      keys.push(fullKey);
    }
  }

  return keys;
}

/**
 * Checks if a translation key exists in the Dutch translation files.
 * Handles namespace prefixed keys and bare keys.
 */
function keyExistsInTranslations(
  key: string,
  namespace: string | undefined,
  defaultNamespace: string | null,
  translations: Map<string, Set<string>>
): boolean {
  // If key has explicit namespace via ns option
  if (namespace) {
    const nsKeys = translations.get(namespace);
    return nsKeys ? nsKeys.has(key) : false;
  }

  // If key contains a namespace prefix like 'common:nav.title'
  if (key.includes(':')) {
    const [ns, actualKey] = key.split(':', 2);
    const nsKeys = translations.get(ns);
    return nsKeys ? nsKeys.has(actualKey) : false;
  }

  // Use the default namespace from useTranslation
  if (defaultNamespace) {
    const nsKeys = translations.get(defaultNamespace);
    if (nsKeys && nsKeys.has(key)) return true;
  }

  // Fallback: check if key exists in any namespace
  for (const [, nsKeys] of translations) {
    if (nsKeys.has(key)) return true;
  }

  return false;
}

// ---------- Tests ----------

describe('Text Extraction Completeness', () => {
  let sourceFiles: string[];
  let translations: Map<string, Set<string>>;

  beforeAll(() => {
    sourceFiles = [];
    for (const dir of MEMBER_FACING_DIRS) {
      sourceFiles.push(...collectSourceFiles(dir));
    }
    translations = loadDutchTranslations();
  });

  describe('No hardcoded Dutch strings in member-facing components', () => {
    /**
     * **Validates: Requirements 4.1**
     *
     * Scans member-facing component source files for common Dutch text patterns
     * that should have been extracted to translation files.
     */
    it('should not contain hardcoded Dutch text in member-facing components', () => {
      const violations: { file: string; line: number; description: string; text: string }[] = [];

      for (const filePath of sourceFiles) {
        const content = fs.readFileSync(filePath, 'utf-8');
        const lines = content.split('\n');

        for (let i = 0; i < lines.length; i++) {
          const result = findDutchTextInLine(lines[i]);
          if (result) {
            violations.push({
              file: path.relative(FRONTEND_SRC, filePath),
              line: i + 1,
              description: result.description,
              text: result.match,
            });
          }
        }
      }

      if (violations.length > 0) {
        const report = violations
          .map((v) => `  ${v.file}:${v.line} - ${v.description}\n    Found: ${v.text}`)
          .join('\n');
        throw new Error(
          `Found ${violations.length} hardcoded Dutch string(s) in member-facing components:\n${report}`
        );
      }
    });
  });

  describe('All translation keys used in components exist in Dutch reference files', () => {
    /**
     * **Validates: Requirements 4.2**
     *
     * Extracts all t('...') calls from member-facing source files and verifies
     * that each referenced key exists in the corresponding Dutch translation file.
     */
    it('should have all referenced translation keys present in Dutch locale files', () => {
      expect(translations.size).toBeGreaterThan(0);

      const missingKeys: { file: string; key: string; namespace: string | null }[] = [];

      for (const filePath of sourceFiles) {
        const content = fs.readFileSync(filePath, 'utf-8');
        const defaultNamespace = extractUseTranslationNamespace(content);
        const keys = extractTranslationKeys(content);

        for (const { key, namespace } of keys) {
          // Skip interpolation-only keys that are template expressions
          if (key.includes('${') || key.includes('{{')) continue;

          if (!keyExistsInTranslations(key, namespace, defaultNamespace, translations)) {
            missingKeys.push({
              file: path.relative(FRONTEND_SRC, filePath),
              key,
              namespace: namespace || defaultNamespace,
            });
          }
        }
      }

      if (missingKeys.length > 0) {
        const report = missingKeys
          .map((m) => `  ${m.file} - t('${m.key}') [namespace: ${m.namespace || 'unknown'}]`)
          .join('\n');
        throw new Error(
          `Found ${missingKeys.length} translation key(s) used in components but missing from Dutch locale files:\n${report}`
        );
      }
    });

    /**
     * **Validates: Requirements 4.2**
     *
     * Verifies that at least some source files use translation functions,
     * confirming the i18n extraction has been applied.
     */
    it('should have member-facing components that use translation functions', () => {
      let filesWithTranslations = 0;

      for (const filePath of sourceFiles) {
        const content = fs.readFileSync(filePath, 'utf-8');
        if (/useTranslation|withTranslation|\bt\s*\(/.test(content)) {
          filesWithTranslations++;
        }
      }

      // At minimum, we expect several member-facing files to use translations
      expect(filesWithTranslations).toBeGreaterThan(0);
    });
  });
});
