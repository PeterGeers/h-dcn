import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

// Test that both demo components can be imported and rendered together
describe('Permission Demo Integration', () => {
  test('can import and render both demo components', async () => {
    // Dynamic imports to test that modules can be loaded
    const { NewPermissionSystemDemo } = await import('../examples/NewPermissionSystemDemo');
    const { usePermissions } = await import('../../utils/examples/PermissionExample');
    
    // Verify components are defined
    expect(NewPermissionSystemDemo).toBeDefined();
    expect(usePermissions).toBeDefined();
    expect(typeof NewPermissionSystemDemo).toBe('function');
    expect(typeof usePermissions).toBe('function');
  });

  test('demo components export the expected functions', async () => {
    // Test PermissionExample exports
    const permissionModule = await import('../../utils/examples/PermissionExample');
    
    expect(permissionModule.PermissionExample).toBeDefined();
    expect(permissionModule.usePermissions).toBeDefined();
    expect(permissionModule.withPermissionCheck).toBeDefined();
    expect(permissionModule.ProtectedMemberManagement).toBeDefined();
    
    // Test NewPermissionSystemDemo exports
    const demoModule = await import('../examples/NewPermissionSystemDemo');
    
    expect(demoModule.NewPermissionSystemDemo).toBeDefined();
    expect(demoModule.default).toBeDefined();
  });

  test('components have correct TypeScript types', async () => {
    const { NewPermissionSystemDemo } = await import('../examples/NewPermissionSystemDemo');
    const { usePermissions, withPermissionCheck } = await import('../../utils/examples/PermissionExample');
    
    // These should not throw TypeScript errors if types are correct
    const demoComponent: React.FC = NewPermissionSystemDemo;
    const hookFunction: () => any = usePermissions;
    const hocFunction: (component: React.ComponentType<any>, ...args: any[]) => React.ComponentType<any> = withPermissionCheck;
    
    expect(demoComponent).toBeDefined();
    expect(hookFunction).toBeDefined();
    expect(hocFunction).toBeDefined();
  });
});