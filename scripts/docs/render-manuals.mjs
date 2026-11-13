#!/usr/bin/env node
/*
 * render-manuals.mjs
 * ------------------
 * Rendert de Nederlandse eindgebruiker-handleidingen van Markdown naar
 * standalone HTML. Nul npm-dependencies: dit script bevat een kleine
 * Markdown-subset-renderer die precies de constructies aankan die in de
 * handleidingen voorkomen (koppen, alinea's, geordende/ongeordende lijsten,
 * tabellen, blockquotes, inline/blok-code, links, afbeeldingen, nadruk en
 * horizontale lijnen).
 *
 * Elke handleidingenset heeft een eigen map met een `style.css` en een
 * `assets/`-map. De gegenereerde HTML bakt de CSS inline mee, zodat elk
 * HTML-bestand op zichzelf te openen, te mailen en als PDF op te slaan is via
 * "Afdrukken -> Opslaan als PDF". Screenshot-placeholders worden automatisch
 * vervangen door een echte afbeelding zodra het bestand in `assets/` bestaat.
 *
 * Gebruik:
 *   node scripts/docs/render-manuals.mjs
 *
 * Uitvoer (per set):
 *   docs/webshop/handleiding-winkel.html
 *   docs/webshop/handleiding-beheer.html
 *   docs/events/handleiding-evenementen.html
 *   docs/events/handleiding-evenementen-beheer.html
 */

import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = join(__dirname, '..', '..');

/**
 * Doc sets to render. Each set has a `dir` (relative to repo root) containing a
 * `style.css` + `assets/`, and a list of markdown -> html manuals.
 */
const DOC_SETS = [
  {
    label: 'Webwinkel-handleidingen',
    dir: join('docs', 'webshop'),
    manuals: [
      { md: 'handleiding-winkel.md', html: 'handleiding-winkel.html' },
      { md: 'handleiding-beheer.md', html: 'handleiding-beheer.html' },
    ],
  },
  {
    label: 'Evenementen-handleidingen',
    dir: join('docs', 'events'),
    manuals: [
      { md: 'handleiding-evenementen.md', html: 'handleiding-evenementen.html' },
      { md: 'handleiding-evenementen-beheer.md', html: 'handleiding-evenementen-beheer.html' },
    ],
  },
];

/* ------------------------------------------------------------------ *
 * Helpers
 * ------------------------------------------------------------------ */

function escapeHtml(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function slugify(text) {
  return text
    .toLowerCase()
    .replace(/[^\w\s-]/g, '')
    .trim()
    .replace(/\s+/g, '-');
}

/**
 * Inline markdown: code spans, links, images, bold, italic.
 * Code spans are processed first and protected so their contents are not
 * re-parsed for other inline syntax.
 */
function renderInline(text) {
  const codeTokens = [];
  // Protect inline code `...`
  let out = text.replace(/`([^`]+)`/g, (_m, code) => {
    const token = `\u0000CODE${codeTokens.length}\u0000`;
    codeTokens.push(`<code>${escapeHtml(code)}</code>`);
    return token;
  });

  out = escapeHtml(out);

  // Images: ![alt](src)
  out = out.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, (_m, alt, src) => {
    return `<img src="${src}" alt="${alt}">`;
  });

  // Links: [text](href)
  out = out.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_m, label, href) => {
    return `<a href="${href}">${label}</a>`;
  });

  // Bold: **text**
  out = out.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

  // Italic: *text* (avoid matching ** which is already consumed)
  out = out.replace(/(^|[^*])\*([^*\n]+)\*(?!\*)/g, '$1<em>$2</em>');

  // Restore code spans
  out = out.replace(/\u0000CODE(\d+)\u0000/g, (_m, i) => codeTokens[Number(i)]);

  return out;
}

/** Classify a blockquote by its leading marker emoji for styled callouts. */
function classifyBlockquote(firstLine) {
  if (firstLine.includes('📷')) return 'screenshot';
  if (firstLine.includes('💡')) return 'tip';
  if (firstLine.includes('⚠️') || firstLine.includes('⚠')) return 'warn';
  if (firstLine.includes('ℹ️') || firstLine.includes('ℹ')) return 'info';
  return '';
}

/* ------------------------------------------------------------------ *
 * Block-level renderer
 * ------------------------------------------------------------------ */

/**
 * @param {string} md       markdown source
 * @param {string} baseDir  absolute directory the manual lives in (for resolving
 *                          screenshot `assets/...` paths)
 */
function renderMarkdown(md, baseDir) {
  const lines = md.replace(/\r\n/g, '\n').split('\n');
  const html = [];
  const headings = [];
  let i = 0;

  const flushParagraph = (buf) => {
    if (buf.length) {
      html.push(`<p>${renderInline(buf.join(' '))}</p>`);
      buf.length = 0;
    }
  };

  const paragraphBuf = [];

  while (i < lines.length) {
    const line = lines[i];

    // Blank line -> paragraph break
    if (line.trim() === '') {
      flushParagraph(paragraphBuf);
      i++;
      continue;
    }

    // Fenced code block ```
    if (/^```/.test(line.trim())) {
      flushParagraph(paragraphBuf);
      const codeLines = [];
      i++;
      while (i < lines.length && !/^```/.test(lines[i].trim())) {
        codeLines.push(lines[i]);
        i++;
      }
      i++; // skip closing fence
      html.push(`<pre><code>${escapeHtml(codeLines.join('\n'))}</code></pre>`);
      continue;
    }

    // Horizontal rule
    if (/^---+\s*$/.test(line.trim())) {
      flushParagraph(paragraphBuf);
      html.push('<hr>');
      i++;
      continue;
    }

    // Heading
    const headingMatch = /^(#{1,4})\s+(.*)$/.exec(line);
    if (headingMatch) {
      flushParagraph(paragraphBuf);
      const level = headingMatch[1].length;
      const rawText = headingMatch[2].trim();
      const id = slugify(rawText);
      if (level === 2) {
        headings.push({ id, text: rawText });
      }
      html.push(`<h${level} id="${id}">${renderInline(rawText)}</h${level}>`);
      i++;
      continue;
    }

    // Blockquote (one or more consecutive "> " lines)
    if (/^>\s?/.test(line)) {
      flushParagraph(paragraphBuf);
      const quoteLines = [];
      while (i < lines.length && /^>\s?/.test(lines[i])) {
        quoteLines.push(lines[i].replace(/^>\s?/, ''));
        i++;
      }
      const cls = classifyBlockquote(quoteLines[0] || '');
      const joined = quoteLines.filter((l) => l.trim() !== '').join(' ');

      // Screenshot placeholder: if the referenced image exists in assets/,
      // render it as a real figure; otherwise keep the styled placeholder box.
      if (cls === 'screenshot') {
        const srcMatch = /`([^`]+\.(?:png|jpe?g|gif|webp))`/i.exec(joined);
        const captionMatch = /\[Screenshot:\s*([^\]]+)\]/i.exec(joined);
        const caption = captionMatch ? captionMatch[1].trim() : '';
        const src = srcMatch ? srcMatch[1].trim() : '';
        if (src && existsSync(join(baseDir, src))) {
          const captionHtml = caption
            ? `<figcaption>${renderInline(caption)}</figcaption>`
            : '';
          html.push(
            `<figure class="screenshot-figure"><img src="${src}" alt="${escapeHtml(caption)}">${captionHtml}</figure>`
          );
          continue;
        }
      }

      const inner = quoteLines
        .filter((l) => l.trim() !== '')
        .map((l) => renderInline(l))
        .join('<br>');
      const classAttr = cls ? ` class="${cls}"` : '';
      html.push(`<blockquote${classAttr}><p>${inner}</p></blockquote>`);
      continue;
    }

    // Table (header row followed by a separator row of ---/:--)
    if (
      line.includes('|') &&
      i + 1 < lines.length &&
      /^\s*\|?[\s:|-]+\|?\s*$/.test(lines[i + 1]) &&
      lines[i + 1].includes('-')
    ) {
      flushParagraph(paragraphBuf);
      const splitRow = (row) =>
        row
          .trim()
          .replace(/^\|/, '')
          .replace(/\|$/, '')
          .split('|')
          .map((c) => c.trim());

      const headerCells = splitRow(line);
      i += 2; // skip header + separator
      const bodyRows = [];
      while (i < lines.length && lines[i].includes('|') && lines[i].trim() !== '') {
        bodyRows.push(splitRow(lines[i]));
        i++;
      }

      let table = '<table><thead><tr>';
      table += headerCells.map((c) => `<th>${renderInline(c)}</th>`).join('');
      table += '</tr></thead><tbody>';
      for (const row of bodyRows) {
        table += '<tr>' + row.map((c) => `<td>${renderInline(c)}</td>`).join('') + '</tr>';
      }
      table += '</tbody></table>';
      html.push(table);
      continue;
    }

    // Unordered list
    if (/^\s*[-*]\s+/.test(line)) {
      flushParagraph(paragraphBuf);
      const items = [];
      while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) {
        // Support simple soft-wrapped continuation lines (indented, non-blank,
        // not a new list item).
        let item = lines[i].replace(/^\s*[-*]\s+/, '');
        i++;
        while (
          i < lines.length &&
          lines[i].trim() !== '' &&
          !/^\s*[-*]\s+/.test(lines[i]) &&
          !/^\s*\d+\.\s+/.test(lines[i]) &&
          !/^#{1,4}\s/.test(lines[i]) &&
          !/^>\s?/.test(lines[i]) &&
          /^\s+/.test(lines[i])
        ) {
          item += ' ' + lines[i].trim();
          i++;
        }
        items.push(`<li>${renderInline(item)}</li>`);
      }
      html.push(`<ul>${items.join('')}</ul>`);
      continue;
    }

    // Ordered list
    if (/^\s*\d+\.\s+/.test(line)) {
      flushParagraph(paragraphBuf);
      const items = [];
      while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i])) {
        let item = lines[i].replace(/^\s*\d+\.\s+/, '');
        i++;
        while (
          i < lines.length &&
          lines[i].trim() !== '' &&
          !/^\s*\d+\.\s+/.test(lines[i]) &&
          !/^\s*[-*]\s+/.test(lines[i]) &&
          !/^#{1,4}\s/.test(lines[i]) &&
          !/^>\s?/.test(lines[i]) &&
          /^\s+/.test(lines[i])
        ) {
          item += ' ' + lines[i].trim();
          i++;
        }
        items.push(`<li>${renderInline(item)}</li>`);
      }
      html.push(`<ol>${items.join('')}</ol>`);
      continue;
    }

    // Default: accumulate into a paragraph
    paragraphBuf.push(line.trim());
    i++;
  }

  flushParagraph(paragraphBuf);

  return { body: html.join('\n'), headings };
}

/* ------------------------------------------------------------------ *
 * Page assembly
 * ------------------------------------------------------------------ */

function buildToc(headings) {
  if (headings.length === 0) return '';
  const items = headings
    .map((h) => `<li><a href="#${h.id}">${renderInline(h.text)}</a></li>`)
    .join('');
  return `<nav class="toc"><div class="toc-title">Inhoud</div><ul>${items}</ul></nav>`;
}

function buildPage(title, css, body, headings) {
  const toc = buildToc(headings);
  return `<!DOCTYPE html>
<html lang="nl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${escapeHtml(title)}</title>
<style>
${css}
</style>
</head>
<body>
<main class="page">
${toc}
${body}
<p class="footer-note">H-DCN — automatisch gegenereerd uit Markdown. Gebruik je browser (Afdrukken &rarr; Opslaan als PDF) voor een PDF-versie.</p>
</main>
</body>
</html>
`;
}

/* ------------------------------------------------------------------ *
 * Main
 * ------------------------------------------------------------------ */

function main() {
  for (const set of DOC_SETS) {
    const baseDir = join(REPO_ROOT, set.dir);
    const css = readFileSync(join(baseDir, 'style.css'), 'utf8');
    const results = [];

    for (const manual of set.manuals) {
      const md = readFileSync(join(baseDir, manual.md), 'utf8');

      // Derive the page title from the first H1, fall back to the filename.
      const h1Match = /^#\s+(.*)$/m.exec(md);
      const title = h1Match ? h1Match[1].trim() : manual.md;

      const { body, headings } = renderMarkdown(md, baseDir);
      const page = buildPage(title, css, body, headings);
      writeFileSync(join(baseDir, manual.html), page, 'utf8');
      results.push({ html: manual.html, title, headings: headings.length });
    }

    console.log(`${set.label} gerenderd:`);
    for (const r of results) {
      console.log(`  - ${set.dir.replace(/\\/g, '/')}/${r.html}  ("${r.title}", ${r.headings} secties)`);
    }
  }

  console.log('\nOpen een bestand in de browser en kies Afdrukken -> Opslaan als PDF voor een PDF.');
}

main();
