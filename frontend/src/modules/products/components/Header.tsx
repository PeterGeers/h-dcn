import React from 'react';
import { Flex, Image, Text } from '@chakra-ui/react';

export default function Header(): React.ReactElement {
  return (
    <Flex bg="brand.gray" p={4} align="center" justify="space-between">
      <Image src="https://h-dcn-data-506221081911.s3.eu-west-1.amazonaws.com/imagesWebsite/hdcnFavico.png" boxSize="60px"/>
      <Text fontSize="2xl" color="orange.400" fontWeight="bold">Export gegevens</Text>
      <Image src="https://h-dcn-data-506221081911.s3.eu-west-1.amazonaws.com/imagesWebsite/hdcnFavico.png"  boxSize="60px"/>
    </Flex>
  );
}