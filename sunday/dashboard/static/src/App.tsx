import TechnoOrb, { PersonaType } from './TechnoOrb';
import IntelligencePanel from './IntelligencePanel';
import Chat from './Chat';

export default function App() {
  const [orbState, setOrbState] = useState('idle');
  const [persona, setPersona] = useState<PersonaType>('senpai');
  const [activeTab, setActiveTab] = useState('orb');
  const [forestData, setForestData] = useState<any>(null);

  useEffect(() => {
    // Fetch live forest status
    const fetchForest = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/forest/summary');
        if (res.ok) {
          const data = await res.json();
          setForestData(data);
        }
      } catch (e) {
        // offline fallback
      }
    };
    fetchForest();
  }, []);

  return (
    <div className="app" style={{ minHeight: '100vh', background: '#0a0a0f', color: 'white' }}>
      <header style={{ padding: '20px', borderBottom: '1px solid #222', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
          <h1 style={{ margin: 0, color: persona === 'senpai' ? '#ffb7c5' : '#00ff88', fontSize: '20px' }}>
            ⚡ Sunday Techno Dashboard
          </h1>
          <select
            value={persona}
            onChange={(e) => setPersona(e.target.value as PersonaType)}
            style={{
              background: '#151824',
              color: 'white',
              border: '1px solid #333',
              borderRadius: '6px',
              padding: '6px 12px',
              fontSize: '12px',
              cursor: 'pointer'
            }}
          >
            <option value="senpai">🌸 Sunday Senpai</option>
            <option value="genz">👾 Sunday GenZ</option>
            <option value="jarvis">💠 JARVIS</option>
            <option value="friday">🔥 FRIDAY</option>
            <option value="reflective">🌌 Reflective</option>
            <option value="sunday">⚡ Sunday</option>
          </select>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            onClick={() => setActiveTab('orb')}
            style={{
              padding: '8px 16px',
              background: activeTab === 'orb' ? (persona === 'senpai' ? '#ffb7c5' : '#00ff88') : '#222',
              color: activeTab === 'orb' ? '#0a0a0f' : 'white',
              border: 'none',
              borderRadius: '6px',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            Techno Orb
          </button>
          <button
            onClick={() => setActiveTab('intelligence')}
            style={{
              padding: '8px 16px',
              background: activeTab === 'intelligence' ? '#4a90e2' : '#333',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            Intelligence
          </button>
          <button
            onClick={() => setActiveTab('chat')}
            style={{
              padding: '8px 16px',
              background: activeTab === 'chat' ? '#4a90e2' : '#333',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            Chat
          </button>
        </div>
      </header>

      <main style={{ padding: '20px' }}>
        {activeTab === 'orb' && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
              <div>
                <h2 style={{ color: persona === 'senpai' ? '#ffb7c5' : '#00ff88', margin: '0 0 5px 0' }}>
                  {persona === 'senpai' ? '🌸 Senpai Focus Orb' : '⚡ World-Class Techno Orb'}
                </h2>
                <p style={{ color: '#888', margin: 0, fontSize: '13px' }}>Mode: {persona.toUpperCase()} // State: {orbState}</p>
              </div>
              {forestData && (
                <div style={{ display: 'flex', gap: '20px', background: 'rgba(255,255,255,0.05)', padding: '8px 16px', borderRadius: '8px', border: '1px solid #333' }}>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '11px', color: '#888' }}>MATURE TREES</div>
                    <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#00ff88' }}>{forestData.mature_trees || 0}</div>
                  </div>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '11px', color: '#888' }}>WILTED</div>
                    <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#ff4444' }}>{forestData.wilted_trees || 0}</div>
                  </div>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '11px', color: '#888' }}>SUCCESS RATE</div>
                    <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#ffb7c5' }}>{forestData.success_rate || 100}%</div>
                  </div>
                </div>
              )}
            </div>
            <div style={{ height: '480px', background: '#07090e', borderRadius: '12px', overflow: 'hidden', border: '1px solid #222' }}>
              <TechnoOrb persona={persona} state={orbState as any} />
            </div>
          </div>
        )}

        {activeTab === 'intelligence' && (
          <div>
            <h2 style={{ color: '#4a90e2' }}>Intelligence Panel</h2>
            <IntelligencePanel />
          </div>
        )}

        {activeTab === 'chat' && (
          <div style={{ height: '600px' }}>
            <h2 style={{ color: '#4a90e2' }}>Chat</h2>
            <Chat />
          </div>
        )}
      </main>
    </div>
  );
}
