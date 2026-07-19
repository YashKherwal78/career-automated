import React from 'react';
import { NotInstrumented } from '../shared/NotInstrumented';

export const LogViewer: React.FC = () => {
  return (
    <NotInstrumented
      title="Live streaming logs"
      description="Direct syslog connection and real-time text query logs."
    />
  );
};
