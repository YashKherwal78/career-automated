import React from 'react';
import { NotInstrumented } from '../shared/NotInstrumented';

export const Tracing: React.FC = () => {
  return (
    <NotInstrumented
      title="Distributed Trace Explorer"
      description="Select and trace any job or company's lifecycle journey."
    />
  );
};
