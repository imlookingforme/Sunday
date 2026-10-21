import React, { useEffect, useState } from 'react';

interface IntelligenceModule {
  name: string;
  data: any;
  lastUpdate: number;
}

const MODULES = [
  'news', 'weather', 'stocks', 'crypto', 'github',
  'earthquakes', 'space', 'clocks', 'cve', 'screen'
];

export default function IntelligencePanel() {
  const [modules, setModules] = useState<Record<string, IntelligenceModule>>({});
  const [selectedModule, setSelectedModule] = useState<string | null>(null);

  useEffect(() => {
    // Connect to SSE endpoint
    const eventSource = new EventSource('http://localhost:8000/api/events');

    eventSource.addEventListener('intelligence', (event) => {
      const data = JSON.parse(event.data);
      setModules(prev => ({
        ...prev,
        [data.module]: {
          name: data.module,
          data: data.data,
          lastUpdate: data.timestamp
        }
      }));
    });

    eventSource.addEventListener('heartbeat', () => {
      // Keep connection alive
    });

    return () => {
      eventSource.close();
    };
  }, []);

  return (
    <div className="intelligence-panel" style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '10px', padding: '20px' }}>
      {MODULES.map(module => (
        <div
          key={module}
          className="module-card"
          onClick={() => setSelectedModule(module)}
          style={{
            border: '1px solid #333',
            borderRadius: '8px',
            padding: '15px',
            background: '#1a1a1a',
            cursor: 'pointer',
            minHeight: '100px'
          }}
        >
          <h3 style={{ margin: '0 0 10px 0', fontSize: '14px', color: '#4a90e2' }}>
            {module.toUpperCase()}
          </h3>
          {modules[module] ? (
            <div style={{ fontSize: '12px', color: '#ccc' }}>
              <pre>{JSON.stringify(modules[module].data, null, 2)}</pre>
              <div style={{ marginTop: '10px', fontSize: '10px', color: '#666' }}>
                Updated: {new Date(modules[module].lastUpdate).toLocaleTimeString()}
              </div>
            </div>
          ) : (
            <div style={{ fontSize: '12px', color: '#666' }}>Waiting for data...</div>
          )}
        </div>
      ))}

      {selectedModule && (
        <div
          className="module-detail"
          onClick={() => setSelectedModule(null)}
          style={{
            position: 'fixed',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            background: '#1a1a1a',
            border: '1px solid #4a90e2',
            borderRadius: '8px',
            padding: '20px',
            zIndex: 1000,
            minWidth: '400px',
            boxShadow: '0 4px 20px rgba(0,0,0,0.5)'
          }}
        >
          <h2 style={{ margin: '0 0 15px 0', color: '#4a90e2' }}>
            {selectedModule.toUpperCase()}
          </h2>
          {modules[selectedModule] && (
            <pre style={{ fontSize: '12px', color: '#ccc' }}>
              {JSON.stringify(modules[selectedModule].data, null, 2)}
            </pre>
          )}
          <button
            style={{
              marginTop: '15px',
              padding: '8px 16px',
              background: '#4a90e2',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            Close
          </button>
        </div>
      )}
    </div>
  );
}
