import React, { useState } from 'react';
import {
  Box, VStack, Button, Input, Text, Progress, useToast,
  Table, Thead, Tbody, Tr, Th, Td, Alert, AlertIcon
} from '@chakra-ui/react';
import { AddIcon } from '@chakra-ui/icons';
import cognitoService from '../services/cognitoService';

interface CsvUser {
  username: string;
  email: string;
  given_name: string;
  family_name: string;
  phone_number: string;
  groups: string;
  rowIndex: number;
  voornaam?: string;
  achternaam?: string;
  telefoon?: string;
}

interface UploadResult {
  row: number;
  username: string;
  email: string;
  status: 'success' | 'error';
  message: string;
}

interface CsvUploadProps {
  onUsersCreated?: () => void;
}

function CsvUpload({ onUsersCreated }: CsvUploadProps) {
  const [file, setFile] = useState<File | null>(null);
  const [users, setUsers] = useState<CsvUser[]>([]);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [results, setResults] = useState<UploadResult[]>([]);
  const toast = useToast();

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files[0];
    if (selectedFile && selectedFile.type === 'text/csv') {
      setFile(selectedFile);
      parseCSV(selectedFile);
    } else {
      toast({
        title: 'Ongeldig bestand',
        description: 'Selecteer een CSV bestand',
        status: 'error',
        duration: 3000,
      });
    }
  };

  const parseCSV = (file: File) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const csv = e.target?.result as string;
      const lines = csv.split('\n');
      const headers = lines[0].split(',').map(h => h.trim());
      
      console.log('CSV Headers:', headers); // Debug
      
      const parsedUsers = lines.slice(1)
        .filter(line => line.trim())
        .map((line, index) => {
          const values = line.split(',').map(v => v.trim());
          const user: CsvUser = {} as CsvUser;
          
          // Map CSV columns to user object
          user.username = values[0] || '';
          user.email = values[1] || '';
          user.given_name = values[2] || '';
          user.family_name = values[3] || '';
          user.phone_number = values[4] || '';
          user.groups = values[5] || '';
          user.rowIndex = index + 2;
          
          console.log('Parsed user:', user); // Debug
          return user;
        });
      
      setUsers(parsedUsers);
    };
    reader.readAsText(file);
  };

  const uploadUsers = async () => {
    if (users.length === 0) return;
    
    setUploading(true);
    setProgress(0);
    setResults([]);
    
    const uploadResults: UploadResult[] = [];
    
    for (let i = 0; i < users.length; i++) {
      const user = users[i];
      
      try {
        // Validate required fields
        if (!user.email || !user.username) {
          throw new Error('Email en username zijn verplicht');
        }
        
        // Create user with correct API format
        await cognitoService.createUser(
          user.username,
          user.email, 
          {
            given_name: user.given_name || user.voornaam || '',
            family_name: user.family_name || user.achternaam || '',
            phone_number: user.phone_number || user.telefoon || ''
          },
          user.groups || ''
        );
        
        // Groups are now passed directly to createUser
        
        uploadResults.push({
          row: user.rowIndex,
          username: user.username,
          email: user.email,
          status: 'success',
          message: 'Gebruiker aangemaakt'
        });
        
      } catch (error: any) {
        uploadResults.push({
          row: user.rowIndex,
          username: user.username || 'Onbekend',
          email: user.email || 'Onbekend',
          status: 'error',
          message: error.message
        });
      }
      
      setProgress(((i + 1) / users.length) * 100);
    }
    
    setResults(uploadResults);
    setUploading(false);
    
    const successCount = uploadResults.filter(r => r.status === 'success').length;
    const errorCount = uploadResults.filter(r => r.status === 'error').length;
    
    toast({
      title: 'Upload voltooid',
      description: `${successCount} gebruikers aangemaakt, ${errorCount} fouten`,
      status: successCount > 0 ? 'success' : 'error',
      duration: 5000,
    });
    
    if (successCount > 0 && onUsersCreated) {
      onUsersCreated();
    }
  };

  return (
    <VStack spacing={6} align="stretch">
      <Box bg="gray.800" p={4} borderRadius="md" border="1px" borderColor="orange.400">
        <VStack spacing={4}>
          <Text color="orange.400" fontWeight="bold">CSV Upload voor Cognito Gebruikers</Text>
          
          <Alert status="info" bg="blue.900" color="white">
            <AlertIcon />
            <Text fontSize="sm">
              CSV formaat: username,email,given_name,family_name,phone_number,groups
              <br />
              Groepen scheiden met ; (bijv: hdcnLeden;hdcnRegio_Utrecht)
            </Text>
          </Alert>
          
          <Input
            type="file"
            accept=".csv"
            onChange={handleFileChange}
            bg="gray.700"
            borderColor="orange.400"
          />
          
          {users.length > 0 && (
            <Text color="white">
              {users.length} gebruikers gevonden in CSV
            </Text>
          )}
          
          <Button
            leftIcon={<AddIcon />}
            colorScheme="orange"
            onClick={uploadUsers}
            isDisabled={users.length === 0 || uploading}
            isLoading={uploading}
          >
            Upload Gebruikers
          </Button>
          
          {uploading && (
            <Box w="full">
              <Text color="white" mb={2}>Uploading... {Math.round(progress)}%</Text>
              <Progress value={progress} colorScheme="orange" />
            </Box>
          )}
        </VStack>
      </Box>

      {users.length > 0 && (
        <Box bg="gray.800" borderRadius="md" border="1px" borderColor="orange.400" overflow="hidden">
          <Text color="orange.400" p={4} fontWeight="bold">Preview (eerste 5 rijen)</Text>
          <Table variant="simple" size="sm">
            <Thead bg="gray.700">
              <Tr>
                <Th color="orange.300">Username</Th>
                <Th color="orange.300">Email</Th>
                <Th color="orange.300">Naam</Th>
                <Th color="orange.300">Groepen</Th>
              </Tr>
            </Thead>
            <Tbody>
              {users.slice(0, 5).map((user, index) => (
                <Tr key={index}>
                  <Td color="white">{String(user.username || '').replace(/[<>"'&]/g, '')}</Td>
                  <Td color="white">{String(user.email || '').replace(/[<>"'&]/g, '')}</Td>
                  <Td color="white">{`${String(user.given_name || user.voornaam || '').replace(/[<>"'&]/g, '')} ${String(user.family_name || user.achternaam || '').replace(/[<>"'&]/g, '')}`.trim()}</Td>
                  <Td color="white">{String(user.groups || '-').replace(/[<>"'&]/g, '')}</Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        </Box>
      )}

      {results.length > 0 && (
        <Box bg="gray.800" borderRadius="md" border="1px" borderColor="orange.400" overflow="hidden">
          <Text color="orange.400" p={4} fontWeight="bold">Upload Resultaten</Text>
          <Table variant="simple" size="sm">
            <Thead bg="gray.700">
              <Tr>
                <Th color="orange.300">Rij</Th>
                <Th color="orange.300">Username</Th>
                <Th color="orange.300">Email</Th>
                <Th color="orange.300">Status</Th>
                <Th color="orange.300">Bericht</Th>
              </Tr>
            </Thead>
            <Tbody>
              {results.map((result, index) => (
                <Tr key={index}>
                  <Td color="white">{result.row}</Td>
                  <Td color="white">{String(result.username || '').replace(/[<>"'&]/g, '')}</Td>
                  <Td color="white">{String(result.email || '').replace(/[<>"'&]/g, '')}</Td>
                  <Td>
                    <Text color={result.status === 'success' ? 'green.400' : 'red.400'}>
                      {result.status === 'success' ? '✅' : '❌'}
                    </Text>
                  </Td>
                  <Td color="white" fontSize="sm">{String(result.message || '').replace(/[<>"'&]/g, '')}</Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        </Box>
      )}
    </VStack>
  );
}

export default CsvUpload;