/**
 * Field Registry Test Component
 * 
 * Comprehensive test component to validate field resolution, rendering, and permissions
 * Use this to validate the complete field registry system before full UI integration
 */

import React, { useState } from 'react';
import { resolveFieldsForContext, canViewField, canEditField } from '../utils/fieldResolver';
import { renderFieldValue, getFieldInputComponent, validateFieldValue } from '../utils/fieldRenderers';
import { canPerformAction, hasRegionalAccess, getRoleName } from '../utils/permissionHelpers';
import { HDCNGroup } from '../config/memberFields';

const FieldRegistryTest: React.FC = () => {
  const [selectedContext, setSelectedContext] = useState('memberOverview');
  const [selectedRole, setSelectedRole] = useState<HDCNGroup>('Members_CRUD');
  const [userRegion, setUserRegion] = useState('Noord-Holland');
  const [memberData] = useState({
    lidmaatschap: 'Gewoon lid',
    status: 'Actief',
    geboortedatum: '1990-05-15',
    regio: 'Noord-Holland',
    voornaam: 'Jan',
    achternaam: 'de Vries',
    email: 'jan@example.com',
    telefoon: '06-12345678',
    bankrekeningnummer: 'NL91ABNA0417164300',
    motormerk: 'Harley-Davidson',
    bouwjaar: 2020,
    privacy: 'Ja',
    clubblad: 'Digitaal'
  });

  const contexts = [
    'memberOverview',
    'memberCompact', 
    'motorView',
    'communicationView',
    'financialView',
    'memberView',
    'memberQuickView',
    'memberRegistration',
    'membershipApplication'
  ];

  const roles: HDCNGroup[] = [
    'Members_CRUD',
    'Members_Read', 
    'Members_Export',
    'Events_CRUD',
    'Events_Read',
    'Products_CRUD',
    'Products_Read',
    'Communication_CRUD',
    'Communication_Read',
    'System_User_Management',
    'System_Logs_Read',
    'Webshop_Management',
    'hdcnLeden'
  ];

  const regions = [
    'Noord-Holland',
    'Zuid-Holland', 
    'Friesland',
    'Utrecht',
    'Oost',
    'Limburg',
    'Groningen/Drenthe',
    'Noord-Brabant',
    'Zeeland'
  ];

  const resolvedFields = resolveFieldsForContext(selectedContext, selectedRole, memberData);

  return (
    <div style={{ padding: '20px', fontFamily: 'Arial, sans-serif', maxWidth: '1400px' }}>
      <h2>Field Registry Test Dashboard</h2>
      
      {/* Controls */}
      <div style={{ marginBottom: '20px', display: 'flex', gap: '20px', flexWrap: 'wrap' }}>
        <label>
          Context: 
          <select 
            value={selectedContext} 
            onChange={(e) => setSelectedContext(e.target.value)}
            style={{ marginLeft: '10px', padding: '5px' }}
          >
            {contexts.map(context => (
              <option key={context} value={context}>{context}</option>
            ))}
          </select>
        </label>
        
        <label>
          Role: 
          <select 
            value={selectedRole} 
            onChange={(e) => setSelectedRole(e.target.value as HDCNGroup)}
            style={{ marginLeft: '10px', padding: '5px' }}
          >
            {roles.map(role => (
              <option key={role} value={role}>{getRoleName(role)}</option>
            ))}
          </select>
        </label>

        <label>
          User Region: 
          <select 
            value={userRegion} 
            onChange={(e) => setUserRegion(e.target.value)}
            style={{ marginLeft: '10px', padding: '5px' }}
          >
            {regions.map(region => (
              <option key={region} value={region}>{region}</option>
            ))}
          </select>
        </label>
      </div>

      {/* Permission Summary */}
      <div style={{ marginBottom: '20px', padding: '15px', backgroundColor: '#f0f8ff', borderRadius: '5px' }}>
        <h3>Permission Summary</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '10px' }}>
          <div>
            <strong>Can View Member:</strong> {canPerformAction('view', selectedRole, memberData, userRegion) ? '✅' : '❌'}
          </div>
          <div>
            <strong>Can Edit Member:</strong> {canPerformAction('edit', selectedRole, memberData, userRegion) ? '✅' : '❌'}
          </div>
          <div>
            <strong>Can Delete Member:</strong> {canPerformAction('delete', selectedRole, memberData, userRegion) ? '✅' : '❌'}
          </div>
          <div>
            <strong>Can Approve Status:</strong> {canPerformAction('approve', selectedRole, memberData, userRegion) ? '✅' : '❌'}
          </div>
          <div>
            <strong>Regional Access:</strong> {hasRegionalAccess(selectedRole, memberData.regio, userRegion) ? '✅' : '❌'}
          </div>
          <div>
            <strong>Resolved Fields:</strong> {resolvedFields.length}
          </div>
        </div>
      </div>

      {/* Field Details Table */}
      <div>
        <h3>Field Resolution Results</h3>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: '14px' }}>
            <thead>
              <tr style={{ backgroundColor: '#f0f0f0' }}>
                <th style={{ border: '1px solid #ccc', padding: '8px', minWidth: '120px' }}>Field Key</th>
                <th style={{ border: '1px solid #ccc', padding: '8px', minWidth: '120px' }}>Label</th>
                <th style={{ border: '1px solid #ccc', padding: '8px', minWidth: '80px' }}>Group</th>
                <th style={{ border: '1px solid #ccc', padding: '8px', minWidth: '80px' }}>Type</th>
                <th style={{ border: '1px solid #ccc', padding: '8px', minWidth: '60px' }}>View</th>
                <th style={{ border: '1px solid #ccc', padding: '8px', minWidth: '60px' }}>Edit</th>
                <th style={{ border: '1px solid #ccc', padding: '8px', minWidth: '150px' }}>Sample Value</th>
                <th style={{ border: '1px solid #ccc', padding: '8px', minWidth: '100px' }}>Input Type</th>
                <th style={{ border: '1px solid #ccc', padding: '8px', minWidth: '100px' }}>Validation</th>
              </tr>
            </thead>
            <tbody>
              {resolvedFields.map(field => {
                const sampleValue = memberData[field.key as keyof typeof memberData];
                const renderedValue = renderFieldValue(field, sampleValue);
                const inputComponent = getFieldInputComponent(field);
                const validation = validateFieldValue(field, sampleValue, memberData);
                
                return (
                  <tr key={field.key}>
                    <td style={{ border: '1px solid #ccc', padding: '8px' }}>
                      <code>{field.key}</code>
                    </td>
                    <td style={{ border: '1px solid #ccc', padding: '8px' }}>{field.label}</td>
                    <td style={{ border: '1px solid #ccc', padding: '8px' }}>
                      <span style={{ 
                        padding: '2px 6px', 
                        borderRadius: '3px', 
                        fontSize: '12px',
                        backgroundColor: getGroupColor(field.group),
                        color: 'white'
                      }}>
                        {field.group}
                      </span>
                    </td>
                    <td style={{ border: '1px solid #ccc', padding: '8px' }}>{field.dataType}</td>
                    <td style={{ border: '1px solid #ccc', padding: '8px', textAlign: 'center' }}>
                      {canViewField(field, selectedRole, memberData) ? '✅' : '❌'}
                    </td>
                    <td style={{ border: '1px solid #ccc', padding: '8px', textAlign: 'center' }}>
                      {canEditField(field, selectedRole, memberData) ? '✅' : '❌'}
                    </td>
                    <td style={{ border: '1px solid #ccc', padding: '8px' }}>
                      <span style={{ 
                        fontFamily: 'monospace', 
                        backgroundColor: '#f5f5f5', 
                        padding: '2px 4px',
                        borderRadius: '3px'
                      }}>
                        {renderedValue}
                      </span>
                    </td>
                    <td style={{ border: '1px solid #ccc', padding: '8px' }}>
                      <span style={{ fontSize: '12px' }}>
                        {inputComponent.component} ({inputComponent.type})
                      </span>
                    </td>
                    <td style={{ border: '1px solid #ccc', padding: '8px' }}>
                      <span style={{ 
                        color: validation.isValid ? 'green' : 'red',
                        fontSize: '12px'
                      }}>
                        {validation.isValid ? '✅ Valid' : `❌ ${validation.errors.length} errors`}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Test Member Data */}
      <div style={{ marginTop: '20px' }}>
        <h3>Test Member Data</h3>
        <pre style={{ 
          backgroundColor: '#f5f5f5', 
          padding: '15px', 
          borderRadius: '5px',
          fontSize: '12px',
          overflow: 'auto'
        }}>
          {JSON.stringify(memberData, null, 2)}
        </pre>
      </div>

      {/* Field Groups Summary */}
      <div style={{ marginTop: '20px' }}>
        <h3>Fields by Group</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px' }}>
          {['personal', 'address', 'membership', 'motor', 'financial', 'administrative'].map(group => {
            const groupFields = resolvedFields.filter(f => f.group === group);
            return (
              <div key={group} style={{ 
                padding: '10px', 
                border: '1px solid #ddd', 
                borderRadius: '5px',
                backgroundColor: '#fafafa'
              }}>
                <h4 style={{ 
                  margin: '0 0 10px 0',
                  color: getGroupColor(group),
                  textTransform: 'capitalize'
                }}>
                  {group} ({groupFields.length})
                </h4>
                <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '12px' }}>
                  {groupFields.map(field => (
                    <li key={field.key}>{field.label}</li>
                  ))}
                </ul>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

function getGroupColor(group: string): string {
  const colors: Record<string, string> = {
    personal: '#3b82f6',
    address: '#10b981',
    membership: '#f59e0b',
    motor: '#ef4444',
    financial: '#8b5cf6',
    administrative: '#6b7280'
  };
  return colors[group] || '#6b7280';
}

export default FieldRegistryTest;