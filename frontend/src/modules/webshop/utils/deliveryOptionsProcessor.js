export const processDeliveryOptions = (optionsString) => {
  if (typeof optionsString !== 'string' || optionsString.trim() === '') {
    throw new Error('Invalid options string');
  }
  
  const sanitizedString = optionsString.replace(/[\u0000-\u001f\u007f-\u009f]/g, '');
  const rawOptions = JSON.parse(sanitizedString);
  
  if (!Array.isArray(rawOptions)) {
    throw new Error('Invalid options format');
  }
  
  if (!rawOptions.every(item => item && typeof item === 'object')) {
    throw new Error('Invalid options structure');
  }
  
  const processedOptions = [];
  const parents = rawOptions.filter(item => {
    return item && 
           typeof item === 'object' && 
           item.parent === null &&
           typeof item.id !== 'undefined' &&
           typeof item.value === 'string';
  });
  
  parents.forEach(parent => {
    if (!parent.id || typeof parent.value !== 'string') {
      return;
    }
    
    const priceItem = rawOptions.find(item => {
      return item && 
             typeof item === 'object' && 
             item.parent === parent.id &&
             typeof item.value !== 'undefined';
    });
    
    let cost = '0';
    if (priceItem && priceItem.value) {
      const sanitizedCost = String(priceItem.value).replace(/[^0-9.]/g, '');
      cost = isNaN(parseFloat(sanitizedCost)) ? '0' : sanitizedCost;
    }
    
    const sanitizedLabel = String(parent.value).replace(/[<>"'&]/g, '');
    
    processedOptions.push({
      value: String(parent.id),
      label: sanitizedLabel,
      cost: cost
    });
  });
  
  return processedOptions;
};

export const getDefaultDeliveryOptions = () => {
  const rawDefaultOptions = [
    { value: 'standard', label: 'Standaard verzending', cost: '5.95' },
    { value: 'express', label: 'Express verzending', cost: '9.95' },
    { value: 'pickup', label: 'Afhalen (gratis)', cost: '0.00' }
  ];
  
  return rawDefaultOptions.map(option => {
    if (!option || typeof option !== 'object') {
      return null;
    }
    
    const sanitizedValue = String(option.value || '').replace(/[^a-zA-Z0-9_-]/g, '');
    const sanitizedLabel = String(option.label || '').replace(/[<>"'&]/g, '');
    const sanitizedCost = String(option.cost || '0').replace(/[^0-9.]/g, '');
    
    if (!sanitizedValue || !sanitizedLabel) {
      return null;
    }
    
    return {
      value: sanitizedValue,
      label: sanitizedLabel,
      cost: sanitizedCost
    };
  }).filter(Boolean);
};