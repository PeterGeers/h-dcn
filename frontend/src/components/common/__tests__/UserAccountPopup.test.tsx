import { isAdministrator } from '../../../utils/permissions';

// Test the administrative badge logic without UI rendering
describe('UserAccountPopup Administrative Badge Logic', () => {
  it('should identify administrative users correctly', () => {
    // Test administrative roles
    expect(isAdministrator(['Members_CRUD_All'])).toBe(true);
    expect(isAdministrator(['System_CRUD_All'])).toBe(true);
    expect(isAdministrator(['Webmaster'])).toBe(true);
    expect(isAdministrator(['hdcnAdmins'])).toBe(true);
    expect(isAdministrator(['National_Chairman'])).toBe(true);
    expect(isAdministrator(['Communication_CRUD_All'])).toBe(true);
  });

  it('should not identify regular users as administrators', () => {
    // Test regular member roles
    expect(isAdministrator(['hdcnLeden'])).toBe(false);
    expect(isAdministrator(['Members_Read_All'])).toBe(false);
    expect(isAdministrator(['Events_Read_All'])).toBe(false);
    expect(isAdministrator(['Products_Read_All'])).toBe(false);
  });

  it('should handle mixed roles correctly', () => {
    // Test mixed roles - should return true if any role is administrative
    expect(isAdministrator(['hdcnLeden', 'Members_CRUD_All'])).toBe(true);
    expect(isAdministrator(['hdcnLeden', 'Members_Read_All'])).toBe(false);
  });

  it('should handle empty roles array', () => {
    expect(isAdministrator([])).toBe(false);
  });

  it('should handle undefined roles', () => {
    expect(isAdministrator(undefined as any)).toBe(false);
  });
});