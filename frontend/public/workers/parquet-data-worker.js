/**
 * Parquet Data Processing Web Worker
 * 
 * This worker handles CPU-intensive data processing tasks in the background
 * to prevent blocking the main UI thread. It processes member data including:
 * - Calculated field computation
 * - Regional filtering
 * - Data transformations
 * - Large dataset processing
 */

// Import calculated fields utilities (we'll need to handle this differently in worker context)
// Since we can't import ES modules directly in a web worker, we'll need to inline the logic

// ============================================================================
// CALCULATED FIELDS LOGIC (Inlined from calculatedFields.ts)
// ============================================================================

/**
 * Calculate age from birth date
 */
function calculateAge(geboortedatum) {
  if (!geboortedatum) return null;
  
  try {
    const birthDate = new Date(geboortedatum);
    if (isNaN(birthDate.getTime())) return null;
    
    const today = new Date();
    let age = today.getFullYear() - birthDate.getFullYear();
    const monthDiff = today.getMonth() - birthDate.getMonth();
    
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthDate.getDate())) {
      age--;
    }
    
    return age >= 0 ? age : null;
  } catch (error) {
    return null;
  }
}

/**
 * Calculate years of membership
 */
function calculateMembershipYears(ingangsdatum) {
  if (!ingangsdatum) return null;
  
  try {
    const startDate = new Date(ingangsdatum);
    if (isNaN(startDate.getTime())) return null;
    
    const today = new Date();
    let years = today.getFullYear() - startDate.getFullYear();
    const monthDiff = today.getMonth() - startDate.getMonth();
    
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < startDate.getDate())) {
      years--;
    }
    
    return years >= 0 ? years : null;
  } catch (error) {
    return null;
  }
}

/**
 * Extract birthday in Dutch format
 */
function extractBirthday(geboortedatum) {
  if (!geboortedatum) return null;
  
  try {
    const birthDate = new Date(geboortedatum);
    if (isNaN(birthDate.getTime())) return null;
    
    const months = [
      'januari', 'februari', 'maart', 'april', 'mei', 'juni',
      'juli', 'augustus', 'september', 'oktober', 'november', 'december'
    ];
    
    const day = birthDate.getDate();
    const month = months[birthDate.getMonth()];
    
    return `${month} ${day}`;
  } catch (error) {
    return null;
  }
}

/**
 * Extract year from date
 */
function extractYear(dateString) {
  if (!dateString) return null;
  
  try {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return null;
    
    return date.getFullYear();
  } catch (error) {
    return null;
  }
}

/**
 * Concatenate name parts
 */
function concatenateName(voornaam, tussenvoegsel, achternaam) {
  const parts = [voornaam, tussenvoegsel, achternaam].filter(part => 
    part && typeof part === 'string' && part.trim().length > 0
  );
  return parts.length > 0 ? parts.join(' ') : null;
}

/**
 * Apply calculated fields to a single member
 */
function applyCalculatedFieldsToMember(member) {
  return {
    ...member,
    korte_naam: concatenateName(member.voornaam, member.tussenvoegsel, member.achternaam),
    leeftijd: calculateAge(member.geboortedatum),
    verjaardag: extractBirthday(member.geboortedatum),
    jaren_lid: calculateMembershipYears(member.ingangsdatum || member.tijdstempel),
    aanmeldingsjaar: extractYear(member.ingangsdatum || member.tijdstempel)
  };
}

// ============================================================================
// REGIONAL FILTERING LOGIC
// ============================================================================

/**
 * Apply regional filtering to member data
 */
function applyRegionalFiltering(members, options) {
  if (!options || !options.userRoles || !Array.isArray(options.userRoles)) {
    return members;
  }
  
  // Check if user has full access roles
  const fullAccessRoles = ['Members_CRUD_All', 'System_CRUD_All', 'System_User_Management'];
  const hasFullAccess = options.userRoles.some(role => fullAccessRoles.includes(role));
  
  if (hasFullAccess) {
    return members;
  }
  
  // Extract regional roles (format: hdcnRegio_RegionName)
  const regionalRoles = options.userRoles.filter(role => role.startsWith('hdcnRegio_'));
  
  if (regionalRoles.length === 0) {
    return members;
  }
  
  // Extract allowed regions from roles
  const allowedRegions = regionalRoles.map(role => role.replace('hdcnRegio_', ''));
  
  // Filter members by region
  return members.filter(member => {
    const memberRegion = member.regio || member.region;
    return memberRegion && allowedRegions.includes(memberRegion);
  });
}

// ============================================================================
// BATCH PROCESSING UTILITIES
// ============================================================================

/**
 * Process data in batches to prevent blocking and allow progress updates
 */
function processBatch(data, batchSize, processingFunction, progressCallback) {
  return new Promise((resolve, reject) => {
    const results = [];
    let currentIndex = 0;
    
    function processNextBatch() {
      try {
        const batch = data.slice(currentIndex, currentIndex + batchSize);
        if (batch.length === 0) {
          resolve(results);
          return;
        }
        
        // Process the batch
        const processedBatch = batch.map(processingFunction);
        results.push(...processedBatch);
        
        currentIndex += batchSize;
        
        // Report progress
        const progress = Math.min((currentIndex / data.length) * 100, 100);
        if (progressCallback) {
          progressCallback(progress);
        }
        
        // Schedule next batch processing to avoid blocking
        setTimeout(processNextBatch, 0);
        
      } catch (error) {
        reject(error);
      }
    }
    
    processNextBatch();
  });
}

// ============================================================================
// MESSAGE HANDLERS
// ============================================================================

/**
 * Handle calculated fields processing
 */
async function handleCalculatedFields(data, requestId) {
  try {
    const batchSize = 100; // Process 100 members at a time
    
    const processedData = await processBatch(
      data,
      batchSize,
      applyCalculatedFieldsToMember,
      (progress) => {
        // Send progress update
        self.postMessage({
          type: 'PROGRESS',
          payload: {
            progress: Math.round(progress),
            message: `Processing calculated fields: ${Math.round(progress)}%`
          },
          requestId
        });
      }
    );
    
    // Send success response
    self.postMessage({
      type: 'SUCCESS',
      payload: {
        data: processedData,
        stats: {
          totalRecords: data.length,
          processedRecords: processedData.length,
          calculatedFieldsComputed: processedData.length,
          processingTime: Date.now()
        }
      },
      requestId
    });
    
  } catch (error) {
    self.postMessage({
      type: 'ERROR',
      payload: {
        error: error.message || 'Failed to process calculated fields'
      },
      requestId
    });
  }
}

/**
 * Handle regional filtering
 */
async function handleRegionalFilter(data, options, requestId) {
  try {
    const filteredData = applyRegionalFiltering(data, options);
    
    self.postMessage({
      type: 'SUCCESS',
      payload: {
        data: filteredData,
        stats: {
          totalRecords: data.length,
          processedRecords: filteredData.length,
          regionallyFiltered: data.length - filteredData.length,
          processingTime: Date.now()
        }
      },
      requestId
    });
    
  } catch (error) {
    self.postMessage({
      type: 'ERROR',
      payload: {
        error: error.message || 'Failed to apply regional filtering'
      },
      requestId
    });
  }
}

/**
 * Handle combined data processing (calculated fields + regional filtering)
 */
async function handleProcessData(data, options, requestId) {
  try {
    const batchSize = 100;
    let processedData = data;
    
    // Step 1: Apply calculated fields if requested
    if (options.applyCalculatedFields !== false) {
      self.postMessage({
        type: 'PROGRESS',
        payload: {
          progress: 10,
          message: 'Starting calculated fields processing...'
        },
        requestId
      });
      
      processedData = await processBatch(
        processedData,
        batchSize,
        applyCalculatedFieldsToMember,
        (progress) => {
          self.postMessage({
            type: 'PROGRESS',
            payload: {
              progress: 10 + Math.round(progress * 0.7), // 10-80% for calculated fields
              message: `Processing calculated fields: ${Math.round(progress)}%`
            },
            requestId
          });
        }
      );
    }
    
    // Step 2: Apply regional filtering if requested
    if (options.applyRegionalFiltering && options.regionalFilterOptions) {
      self.postMessage({
        type: 'PROGRESS',
        payload: {
          progress: 85,
          message: 'Applying regional filtering...'
        },
        requestId
      });
      
      processedData = applyRegionalFiltering(processedData, options.regionalFilterOptions);
    }
    
    // Send final success response
    self.postMessage({
      type: 'SUCCESS',
      payload: {
        data: processedData,
        stats: {
          totalRecords: data.length,
          processedRecords: processedData.length,
          calculatedFieldsComputed: options.applyCalculatedFields !== false ? processedData.length : 0,
          regionallyFiltered: options.applyRegionalFiltering ? data.length - processedData.length : 0,
          processingTime: Date.now()
        }
      },
      requestId
    });
    
  } catch (error) {
    self.postMessage({
      type: 'ERROR',
      payload: {
        error: error.message || 'Failed to process data'
      },
      requestId
    });
  }
}

// ============================================================================
// MAIN MESSAGE HANDLER
// ============================================================================

self.addEventListener('message', async function(event) {
  const { type, payload, requestId } = event.data;
  
  if (!requestId) {
    self.postMessage({
      type: 'ERROR',
      payload: {
        error: 'Missing requestId in message'
      },
      requestId: 'unknown'
    });
    return;
  }
  
  try {
    switch (type) {
      case 'PROCESS_DATA':
        await handleProcessData(payload.data, payload.options || {}, requestId);
        break;
        
      case 'APPLY_CALCULATED_FIELDS':
        await handleCalculatedFields(payload.data, requestId);
        break;
        
      case 'APPLY_REGIONAL_FILTER':
        await handleRegionalFilter(payload.data, payload.options, requestId);
        break;
        
      default:
        self.postMessage({
          type: 'ERROR',
          payload: {
            error: `Unknown message type: ${type}`
          },
          requestId
        });
    }
  } catch (error) {
    self.postMessage({
      type: 'ERROR',
      payload: {
        error: error.message || 'Unexpected error in worker'
      },
      requestId
    });
  }
});

// Send ready message when worker is loaded
self.postMessage({
  type: 'READY',
  payload: {
    message: 'Parquet data worker is ready'
  },
  requestId: 'init'
});