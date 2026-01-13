import React, { useState, useEffect } from 'react';
import { setMaintenanceScreenCallback, ApiError } from '../utils/errorHandler';
import MaintenanceScreen from './MaintenanceScreen';

interface MaintenanceProviderProps {
  children: React.ReactNode;
}

export const MaintenanceProvider: React.FC<MaintenanceProviderProps> = ({ children }) => {
  const [showMaintenance, setShowMaintenance] = useState(false);
  const [maintenanceError, setMaintenanceError] = useState<ApiError | null>(null);

  useEffect(() => {
    // Set up the global callback for showing/hiding maintenance screen
    setMaintenanceScreenCallback((show: boolean, error?: ApiError) => {
      setShowMaintenance(show);
      setMaintenanceError(error || null);
    });

    // Cleanup on unmount
    return () => {
      setMaintenanceScreenCallback(() => {});
    };
  }, []);

  const handleRetry = () => {
    try {
      window.location.reload();
      // Only reset state if reload succeeds
      setShowMaintenance(false);
      setMaintenanceError(null);
    } catch (error) {
      // If reload fails, keep maintenance screen visible
      console.error('Error reloading page:', error);
      // Don't reset the maintenance state
    }
  };

  if (showMaintenance) {
    return (
      <MaintenanceScreen
        message={maintenanceError?.message}
        onRetry={handleRetry}
        showRetry={true}
      />
    );
  }

  return <>{children}</>;
};

export default MaintenanceProvider;