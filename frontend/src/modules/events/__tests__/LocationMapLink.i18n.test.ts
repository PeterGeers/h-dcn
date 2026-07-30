import path from 'path';
import fs from 'fs';

const LANGUAGES = ['nl', 'en', 'de', 'fr', 'es', 'it', 'da', 'sv'];
const SRC_LOCALES_DIR = path.resolve(__dirname, '../../../locales');
const PUBLIC_LOCALES_DIR = path.resolve(__dirname, '../../../../public/locales');

describe('LocationMapLink i18n - translation key presence', () => {
  describe('src/locales', () => {
    LANGUAGES.forEach((lang) => {
      describe(`${lang}/eventBooking.json`, () => {
        const filePath = path.join(SRC_LOCALES_DIR, lang, 'eventBooking.json');
        let data: any;

        beforeAll(() => {
          const raw = fs.readFileSync(filePath, 'utf-8');
          data = JSON.parse(raw);
        });

        it('has a location object', () => {
          expect(data.location).toBeDefined();
          expect(typeof data.location).toBe('object');
        });

        it('has an openInMaps key', () => {
          expect(data.location.openInMaps).toBeDefined();
        });

        it('value is a non-empty string', () => {
          expect(typeof data.location.openInMaps).toBe('string');
          expect(data.location.openInMaps.trim().length).toBeGreaterThan(0);
        });

        it('value contains {{location}} interpolation variable', () => {
          expect(data.location.openInMaps).toContain('{{location}}');
        });
      });
    });
  });

  describe('public/locales', () => {
    LANGUAGES.forEach((lang) => {
      describe(`${lang}/eventBooking.json`, () => {
        const filePath = path.join(PUBLIC_LOCALES_DIR, lang, 'eventBooking.json');
        let data: any;

        beforeAll(() => {
          const raw = fs.readFileSync(filePath, 'utf-8');
          data = JSON.parse(raw);
        });

        it('has a location object', () => {
          expect(data.location).toBeDefined();
          expect(typeof data.location).toBe('object');
        });

        it('has an openInMaps key', () => {
          expect(data.location.openInMaps).toBeDefined();
        });

        it('value is a non-empty string', () => {
          expect(typeof data.location.openInMaps).toBe('string');
          expect(data.location.openInMaps.trim().length).toBeGreaterThan(0);
        });

        it('value contains {{location}} interpolation variable', () => {
          expect(data.location.openInMaps).toContain('{{location}}');
        });
      });
    });
  });
});
