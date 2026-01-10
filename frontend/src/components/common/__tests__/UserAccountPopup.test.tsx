import { isAdministrator } from '../../../utils/permissions';

// Test the administrative badge logic without UI rendering
describe('UserAccountPopup Administrative Badge Logic', () => {
  it('should identify administrative users correctly', () => {
    // Test administrative roles
    expect(isAdministrator(['Members_CRUD'])).toBe(true);
    expect(isAdministrator(['System_CRUD'])).toBe(true);
    expect(isAdministrator(['Webmaster'])).toBe(true);
    expect(isAdministrator(['National_Chairman'])).toBe(true);
    expect(isAdministrator(['Communication_CRUD'])).toBe(true);
  });

  it('should not identify regular users as administrators', () => {
    // Test regular member roles
    expect(isAdministrator(['hdcnLeden'])).toBe(false);
    expect(isAdministrator(['Members_Read'])).toBe(false);
    expect(isAdministrator(['Events_Read'])).toBe(false);
    expect(isAdministrator(['Products_Read'])).toBe(false);
  });

  it('should handle mixed roles correctly', () => {
    // Test mixed roles - should return true if any role is administrative
    expect(isAdministrator(['hdcnLeden', 'Members_CRUD'])).toBe(true);
    expect(isAdministrator(['hdcnLeden', 'Members_Read'])).toBe(false);
  });

  it('should handle empty roles array', () => {
    expect(isAdministrator([])).toBe(false);
  });

  it('should handle undefined roles', () => {
    expect(isAdministrator(undefined as any)).toBe(false);
  });
});