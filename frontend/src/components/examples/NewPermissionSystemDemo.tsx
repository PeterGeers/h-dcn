import React from 'react';
import { usePermissions } from '../../utils/examples/PermissionExample';

/**
 * Demo component showing the new permission + region role system in action
 * This demonstrates how UI components should check permissions
 */
export const NewPermissionSystemDemo: React.FC = () => {
  const {
    canReadMembers,
    canWriteMembers,
    canReadEvents,
    canWriteEvents,
    canReadProducts,
    canWriteProducts,
    accessibleRegions,
    hasFullRegionalAccess,
    hasExportPermission,
    checkPermission
  } = usePermissions();

  return (
    <div style={{ padding: '20px', fontFamily: 'Arial, sans-serif' }}>
      <h1>New Permission + Region Role System Demo</h1>
      
      <div style={{ marginBottom: '20px' }}>
        <h2>Your Permissions</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '10px' }}>
          <div>
            <strong>Members:</strong>
            <ul>
              <li>Read: {canReadMembers ? '✅' : '❌'}</li>
              <li>Write: {canWriteMembers ? '✅' : '❌'}</li>
              <li>Export: {hasExportPermission ? '✅' : '❌'}</li>
            </ul>
          </div>
          
          <div>
            <strong>Events:</strong>
            <ul>
              <li>Read: {canReadEvents ? '✅' : '❌'}</li>
              <li>Write: {canWriteEvents ? '✅' : '❌'}</li>
            </ul>
          </div>
          
          <div>
            <strong>Products:</strong>
            <ul>
              <li>Read: {canReadProducts ? '✅' : '❌'}</li>
              <li>Write: {canWriteProducts ? '✅' : '❌'}</li>
            </ul>
          </div>
        </div>
      </div>

      <div style={{ marginBottom: '20px' }}>
        <h2>Regional Access</h2>
        <p><strong>Full Access:</strong> {hasFullRegionalAccess ? '✅ All Regions' : '❌ Limited'}</p>
        <p><strong>Accessible Regions:</strong> {accessibleRegions.join(', ') || 'None'}</p>
      </div>

      <div style={{ marginBottom: '20px' }}>
        <h2>Regional Permission Examples</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '10px' }}>
          {['utrecht', 'limburg', 'groningen_drenthe'].map(region => (
            <div key={region} style={{ border: '1px solid #ccc', padding: '10px', borderRadius: '5px' }}>
              <h3>{region.charAt(0).toUpperCase() + region.slice(1)}</h3>
              <ul>
                <li>Read Members: {checkPermission('members', 'read', region) ? '✅' : '❌'}</li>
                <li>Write Members: {checkPermission('members', 'write', region) ? '✅' : '❌'}</li>
                <li>Read Events: {checkPermission('events', 'read', region) ? '✅' : '❌'}</li>
                <li>Write Events: {checkPermission('events', 'write', region) ? '✅' : '❌'}</li>
              </ul>
            </div>
          ))}
        </div>
      </div>

      {/* Conditional UI based on permissions */}
      {canReadMembers && (
        <div style={{ backgroundColor: '#e8f5e8', padding: '15px', borderRadius: '5px', marginBottom: '10px' }}>
          <h3>Member Management Section</h3>
          <p>You can view member data.</p>
          {canWriteMembers && (
            <button style={{ marginRight: '10px', padding: '5px 10px' }}>
              Edit Members
            </button>
          )}
          {hasExportPermission && (
            <button style={{ padding: '5px 10px' }}>
              Export Member Data
            </button>
          )}
        </div>
      )}

      {canReadEvents && (
        <div style={{ backgroundColor: '#e8f0ff', padding: '15px', borderRadius: '5px', marginBottom: '10px' }}>
          <h3>Event Management Section</h3>
          <p>You can view events.</p>
          {canWriteEvents && (
            <button style={{ padding: '5px 10px' }}>
              Manage Events
            </button>
          )}
        </div>
      )}

      {canReadProducts && (
        <div style={{ backgroundColor: '#fff8e8', padding: '15px', borderRadius: '5px', marginBottom: '10px' }}>
          <h3>Product Management Section</h3>
          <p>You can view products.</p>
          {canWriteProducts && (
            <button style={{ padding: '5px 10px' }}>
              Manage Products
            </button>
          )}
        </div>
      )}

      {!canReadMembers && !canReadEvents && !canReadProducts && (
        <div style={{ backgroundColor: '#ffe8e8', padding: '15px', borderRadius: '5px' }}>
          <h3>No Access</h3>
          <p>You don't have permission to access any management features.</p>
        </div>
      )}
    </div>
  );
};

export default NewPermissionSystemDemo;