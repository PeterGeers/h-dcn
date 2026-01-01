/**
 * Utility to block password manager extensions from interfering with the application
 */

export const blockPasswordManagers = () => {
  // Block common password manager selectors
  const passwordManagerSelectors = [
    'div[data-lastpass-icon-root]',
    'div[data-lastpass-root]',
    'div[id*="bitwarden"]',
    'div[class*="bitwarden"]',
    'div[id*="lastpass"]',
    'div[class*="lastpass"]',
    'div[id*="1password"]',
    'div[class*="1password"]',
    'div[id*="dashlane"]',
    'div[class*="dashlane"]',
    'div[id*="keeper"]',
    'div[class*="keeper"]',
    'iframe[src*="bitwarden"]',
    'iframe[src*="lastpass"]',
    'iframe[src*="1password"]',
    'iframe[src*="dashlane"]',
    'iframe[src*="keeper"]'
  ];

  // Function to remove password manager elements
  const removePasswordManagerElements = () => {
    passwordManagerSelectors.forEach(selector => {
      const elements = document.querySelectorAll(selector);
      elements.forEach(element => {
        if (element && element.parentNode) {
          element.parentNode.removeChild(element);
        }
      });
    });
  };

  // Initial cleanup
  removePasswordManagerElements();

  // Set up mutation observer to continuously block password managers
  const observer = new MutationObserver((mutations) => {
    let shouldCleanup = false;
    
    mutations.forEach((mutation) => {
      if (mutation.type === 'childList') {
        mutation.addedNodes.forEach((node) => {
          if (node.nodeType === Node.ELEMENT_NODE) {
            const element = node as Element;
            
            // Check if the added node matches password manager patterns
            const isPasswordManager = passwordManagerSelectors.some(selector => {
              try {
                return element.matches && element.matches(selector.replace(/\[.*?\]/g, ''));
              } catch (e) {
                return false;
              }
            });

            if (isPasswordManager || 
                element.id?.includes('bitwarden') ||
                element.id?.includes('lastpass') ||
                element.id?.includes('1password') ||
                element.className?.includes('bitwarden') ||
                element.className?.includes('lastpass') ||
                element.className?.includes('1password')) {
              shouldCleanup = true;
            }
          }
        });
      }
    });

    if (shouldCleanup) {
      setTimeout(removePasswordManagerElements, 0);
    }
  });

  // Start observing
  observer.observe(document.body, {
    childList: true,
    subtree: true
  });

  // Periodic cleanup as backup
  const intervalId = setInterval(removePasswordManagerElements, 1000);

  // Return cleanup function
  return () => {
    observer.disconnect();
    clearInterval(intervalId);
  };
};

// Add attributes to prevent password managers from targeting inputs
export const addPasswordManagerBlockingAttributes = (element: HTMLInputElement) => {
  element.setAttribute('data-1p-ignore', 'true');
  element.setAttribute('data-lpignore', 'true');
  element.setAttribute('data-form-type', 'other');
  element.setAttribute('autocomplete', 'off');
  element.setAttribute('data-bitwarden-watching', 'false');
};

// Global function to disable password managers on all inputs
export const disablePasswordManagersOnInputs = () => {
  const inputs = document.querySelectorAll('input[type="text"], input[type="email"], input[type="password"], input[type="search"], textarea');
  inputs.forEach((input) => {
    if (input instanceof HTMLInputElement || input instanceof HTMLTextAreaElement) {
      addPasswordManagerBlockingAttributes(input as HTMLInputElement);
    }
  });
};