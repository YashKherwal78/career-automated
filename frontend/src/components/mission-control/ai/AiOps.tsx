import React from 'react';
import { NotInstrumented } from '../shared/NotInstrumented';

export const AiOps: React.FC = () => {
  return (
    <NotInstrumented
      title="AI Operations Telemetry"
      description="Token usage, resume tailoring queues, and embedding throughput."
    />
  );
};
