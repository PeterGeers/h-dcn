import React, { useState, useEffect } from 'react';
import EventDashboard from './EventDashboard';
import ReportView from './ReportView';

/**
 * Admin sub-router for the PresMeet admin tab.
 *
 * Uses window.location.hash to switch between:
 * - EventDashboard (default / #/admin/presmeet)
 * - ReportView (#/admin/presmeet/reports?type=X&event_id=Y)
 *
 * Requirements: 13.3
 */
const AdminRouter: React.FC = () => {
  const [currentView, setCurrentView] = useState<'dashboard' | 'reports'>(
    getViewFromHash()
  );

  useEffect(() => {
    const handleHashChange = () => {
      setCurrentView(getViewFromHash());
    };

    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  if (currentView === 'reports') {
    return <ReportView />;
  }

  return <EventDashboard />;
};

function getViewFromHash(): 'dashboard' | 'reports' {
  const hash = window.location.hash;
  if (hash.includes('/admin/presmeet/reports')) {
    return 'reports';
  }
  return 'dashboard';
}

export default AdminRouter;
