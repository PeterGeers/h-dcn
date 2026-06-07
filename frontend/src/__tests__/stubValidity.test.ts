/**
 * Property-Based Test: Generated frontend test stubs are valid
 *
 * Verifies each stub file is valid TypeScript that can be parsed without errors
 * and contains at least one `it()` or `test()` block.
 *
 * Testing framework: Jest + fast-check
 * **Validates: Requirements 5.4**
 */

import * as fc from 'fast-check';
import * as fs from 'fs';
import * as path from 'path';
import * as ts from 'typescript';

// ============================================================================
// Constants
// ============================================================================

const STUB_FILES = [
  'src/components/__tests__/MemberAdminTable.test.tsx',
  'src/components/__tests__/MemberEditView.test.tsx',
  'src/components/__tests__/NewMemberApplicationForm.test.tsx',
  'src/components/auth/__tests__/CustomAuthenticator.test.tsx',
  'src/modules/webshop/__tests__/WebshopPage.test.tsx',
];

const PROJECT_ROOT = path.resolve(__dirname, '../..');

// ============================================================================
// Helpers
// ============================================================================

function readStubFile(relativePath: string): string {
  const fullPath = path.join(PROJECT_ROOT, relativePath);
  return fs.readFileSync(fullPath, 'utf-8');
}

function hasTestBlocks(content: string): boolean {
  // Check for it( or test( patterns that indicate test blocks
  const itPattern = /\bit\s*\(/;
  const testPattern = /\btest\s*\(/;
  return itPattern.test(content) || testPattern.test(content);
}

function isValidTypeScript(content: string, fileName: string): { valid: boolean; errors: string[] } {
  const sourceFile = ts.createSourceFile(
    fileName,
    content,
    ts.ScriptTarget.ES2015,
    true,
    fileName.endsWith('.tsx') ? ts.ScriptKind.TSX : ts.ScriptKind.TS
  );

  // Check for parse diagnostics (syntax errors)
  const errors: string[] = [];
  // parseDiagnostics is available on the source file
  const diagnostics = (sourceFile as any).parseDiagnostics as ts.Diagnostic[] | undefined;

  if (diagnostics && diagnostics.length > 0) {
    for (const diag of diagnostics) {
      const message = ts.flattenDiagnosticMessageText(diag.messageText, '\n');
      errors.push(message);
    }
  }

  return { valid: errors.length === 0, errors };
}

// ============================================================================
// Property 6: Generated frontend test stubs are valid
// **Validates: Requirements 5.4**
// ============================================================================

describe('Property 6: Generated frontend test stubs are valid', () => {
  const stubFileArbitrary = fc.constantFrom(...STUB_FILES);

  it('all stub files exist on disk', () => {
    fc.assert(
      fc.property(stubFileArbitrary, (relativePath) => {
        const fullPath = path.join(PROJECT_ROOT, relativePath);
        return fs.existsSync(fullPath);
      }),
      { numRuns: 20 }
    );
  });

  it('each stub file contains it() or test() blocks', () => {
    fc.assert(
      fc.property(stubFileArbitrary, (relativePath) => {
        const content = readStubFile(relativePath);
        return hasTestBlocks(content);
      }),
      { numRuns: 20 }
    );
  });

  it('each stub file is valid TypeScript (parses without syntax errors)', () => {
    fc.assert(
      fc.property(stubFileArbitrary, (relativePath) => {
        const content = readStubFile(relativePath);
        const fileName = path.basename(relativePath);
        const result = isValidTypeScript(content, fileName);
        return result.valid;
      }),
      { numRuns: 20 }
    );
  });

  it('each stub file imports a component (has import statement)', () => {
    fc.assert(
      fc.property(stubFileArbitrary, (relativePath) => {
        const content = readStubFile(relativePath);
        return /\bimport\b/.test(content);
      }),
      { numRuns: 20 }
    );
  });

  it('each stub file has a describe() block', () => {
    fc.assert(
      fc.property(stubFileArbitrary, (relativePath) => {
        const content = readStubFile(relativePath);
        return /\bdescribe\s*\(/.test(content);
      }),
      { numRuns: 20 }
    );
  });
});
