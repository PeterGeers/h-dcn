import React from 'react';
import { Flex, Image, Text } from '@chakra-ui/react';

export default function Header(): React.ReactElement {
  return (
    <Flex bg="brand.gray" p={4} align="center" justify="space-between">
      <Image src="https://my-hdcn-bucket.s3.eu-west-1.amazonaws.com/imagesWebsite/hdcnFavico.png" boxSize="60px"/>
      <Text fontSize="2xl" color="orange.400" fontWeight="bold">Artikelen Clubsjop</Text>
      <Image src="https://my-hdcn-bucket.s3.eu-west-1.amazonaws.com/imagesWebsite/hdcnFavico.png"  boxSize="60px"/>
    </Flex>
  );
}