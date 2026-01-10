/**
 * Address Label Generator Component Tests
 * 
 * Tests for the address label generator React component
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { ChakraProvider } from '@chakra-ui/react';
import AddressLabelGenerator from '../AddressLabelGenerator';
import { Member } from '../../../types/index';

// Mock the address label service
jest.mock('../../../services/AddressLabelService', () => ({
  addressLabelService: {
    processMembers: jest.fn((members) => members.filter(m => m.korte_naam && m.straat)),
    getAvailableCountries: jest.fn(() => ['Nederland', 'België']),
    formatAddress: jest.fn((member) => [member.korte_naam, member.straat, `${member.postcode} ${member.woonplaats}`]),
    generateLabelsPDF: jest.fn(() => Promise.resolve({
      success: true,
      filename: 'test-labels.pdf',
      labelCount: 2,
      pageCount: 1
    }))
  },
  STANDARD_LABEL_FORMATS: [
    {
      id: 'test-format',
      name: 'Test Format',
      description: 'Test format for testing',
      columns: 2,
      rows: 2,
      labelWidth: 50,
      labelHeight: 25,
      marginTop: 10,
      marginLeft: 5,
      marginRight: 5,
      marginBottom: 10,
      gapHorizontal: 2,
      gapVertical: 2,
      pageWidth: 210,
      pageHeight: 297
    }
  ],
  DEFAULT_LABEL_STYLE: {
    fontSize: 10,
    fontFamily: 'Arial',
    lineHeight: 1.2,
    padding: 2,
    alignment: 'left',
    includeBorder: false,
    borderWidth: 0.1
  }
}));

// Mock member export service
jest.mock('../../../services/MemberExportService', () => ({
  memberExportService: {
    exportCustomColumns: jest.fn(() => Promise.resolve({ success: true }))
  }
}));

const mockMembers: Member[] = [
  {
    member_id: '1',
    korte_naam: 'Jan van der Berg',
    straat: 'Hoofdstraat 123',
    postcode: '1234AB',
    woonplaats: 'Amsterdam',
    land: 'Nederland',
    regio: 'Noord-Holland',
    status: 'Actief'
  } as Member,
  {
    member_id: '2',
    korte_naam: 'Marie Dubois',
    straat: 'Rue de la Paix 45',
    postcode: '75001',
    woonplaats: 'Paris',
    land: 'België',
    regio: 'Overig',
    status: 'Actief'
  } as Member
];

const renderComponent = (props = {}) => {
  return render(
    <ChakraProvider>
      <AddressLabelGenerator
        members={mockMembers}
        viewName="addressStickersRegional"
        {...props}
      />
    </ChakraProvider>
  );
};

describe('AddressLabelGenerator', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should render the component with header', () => {
    renderComponent();
    
    expect(screen.getByText('🏷️ Adreslabels Generator')).toBeInTheDocument();
    expect(screen.getByText('Genereer adreslabels voor mailings en distributie')).toBeInTheDocument();
  });

  it('should display member statistics', () => {
    renderComponent();
    
    expect(screen.getByText('2 labels')).toBeInTheDocument();
    expect(screen.getByText('1 pagina\'s')).toBeInTheDocument();
  });

  it('should show configuration options', () => {
    renderComponent();
    
    expect(screen.getByText('Configuratie')).toBeInTheDocument();
    expect(screen.getByText('Label Formaat')).toBeInTheDocument();
    expect(screen.getByText('Sortering')).toBeInTheDocument();
    expect(screen.getByText('Land Filter')).toBeInTheDocument();
  });

  it('should have action buttons', () => {
    renderComponent();
    
    expect(screen.getByText('PDF Genereren')).toBeInTheDocument();
    expect(screen.getByText('Toon Preview')).toBeInTheDocument();
    expect(screen.getByText('Export Excel')).toBeInTheDocument();
    expect(screen.getByText('Export CSV')).toBeInTheDocument();
  });

  it('should show close button when onClose prop is provided', () => {
    const mockOnClose = jest.fn();
    renderComponent({ onClose: mockOnClose });
    
    const closeButton = screen.getByText('Sluiten');
    expect(closeButton).toBeInTheDocument();
  });

  it('should show warning when no valid addresses found', () => {
    const emptyMembers: Member[] = [
      {
        member_id: '1',
        korte_naam: '',
        straat: '',
        postcode: '',
        woonplaats: '',
        status: 'Actief'
      } as Member
    ];
    
    render(
      <ChakraProvider>
        <AddressLabelGenerator
          members={emptyMembers}
          viewName="addressStickersRegional"
        />
      </ChakraProvider>
    );
    
    expect(screen.getByText('Geen geldige adressen gevonden')).toBeInTheDocument();
  });
});