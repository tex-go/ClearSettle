/**
 * MarketplaceHub — the central Marketplace Integrations page.
 *
 * Layout
 * ------
 * ┌─ Header (title + stats bar) ─────────────────────────────────────────┐
 * │ Connected: N  |  Available: N  |  Coming Soon: N                      │
 * ├─ Filter tabs: All | Connected | Manual Upload | OAuth | API Key ──────┤
 * ├─ Grid of MarketplaceCards ────────────────────────────────────────────┤
 * └── ConnectModal (rendered in portal) ──────────────────────────────────┘
 */
import React, { useEffect, useState, useCallback } from 'react';
import { Globe, CheckCircle, AlertCircle, Clock, RefreshCw } from 'lucide-react';
import useMarketplaceStore from '../store/marketplaceStore';
import MarketplaceCard from '../components/marketplace/MarketplaceCard';
import ConnectModal from '../components/marketplace/ConnectModal';

const FILTER_TABS = [
  { key: 'all',           label: 'All' },
  { key: 'connected',     label: 'Connected' },
  { key: 'manual_upload', label: 'Manual Upload' },
  { key: 'oauth',         label: 'OAuth' },
  { key: 'api_key',       label: 'API Key' },
];

export default function MarketplaceHub() {
  const {
    marketplaces,
    connections,
    fetchMarketplaces,
    fetchConnections,
    connectManual,
    disconnect,
    triggerSync,
    isLoading,
    getError,
  } = useMarketplaceStore();

  const [activeFilter,  setActiveFilter]  = useState('all');
  const [modalMarket,   setModalMarket]   = useState(null); // marketplace object to connect
  const [confirmSlug,   setConfirmSlug]   = useState(null); // slug awaiting disconnect confirm

  useEffect(() => {
    fetchMarketplaces();
    fetchConnections();
  }, []);

  const getConnection = useCallback(
    (slug) => connections.find(c => c.marketplace?.slug === slug),
    [connections]
  );

  // ── Filter logic ───────────────────────────────────────────────────────────
  const filtered = marketplaces.filter(m => {
    if (activeFilter === 'all')           return true;
    if (activeFilter === 'connected')     return getConnection(m.slug)?.status === 'connected';
    if (activeFilter === 'manual_upload') return m.connection_type === 'manual_upload';
    if (activeFilter === 'oauth')         return m.connection_type === 'oauth';
    if (activeFilter === 'api_key')       return ['api_key', 'api_key_secret'].includes(m.connection_type);
    return true;
  });

  // ── Stats ──────────────────────────────────────────────────────────────────
  const totalConnected = connections.filter(c => c.status === 'connected').length;
  const totalError     = connections.filter(c => c.status === 'error').length;
  const totalAvailable = marketplaces.filter(m => m.is_live).length;
  const totalSoon      = marketplaces.filter(m => !m.is_live).length;

  const isPageLoading = isLoading('marketplaces') || isLoading('connections');

  const handleConnect = (marketplace) => {
    if (marketplace.connection_type === 'manual_upload') {
      // One-click for manual upload
      connectManual(marketplace.slug);
    } else {
      setModalMarket(marketplace);
    }
  };

  const handleDisconnect = (slug) => setConfirmSlug(slug);

  const handleSync = (connectionId, slug) => triggerSync(connectionId);

  return (
    <div style={{ padding: '24px 28px', maxWidth: 1200, margin: '0 auto' }}>
      {/* ── Page header ─────────────────────────────────────────────────────── */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
          <Globe size={22} color="#1A3A5C" />
          <h1 style={{ fontSize: 22, fontWeight: 700, color: '#1A2B4A', margin: 0 }}>
            Marketplace Integrations
          </h1>
          {isPageLoading && <RefreshCw size={16} color="#6B7897" style={{ animation: 'spin 1s linear infinite' }} />}
        </div>
        <p style={{ color: '#6B7897', fontSize: 14, margin: 0 }}>
          Connect your seller accounts to automatically sync orders, settlements, fees and taxes.
        </p>
      </div>

      {/* ── Stats bar ───────────────────────────────────────────────────────── */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 24, flexWrap: 'wrap' }}>
        <StatChip icon={<CheckCircle size={14} />} label="Connected" value={totalConnected} color="#00C896" />
        {totalError > 0 && (
          <StatChip icon={<AlertCircle size={14} />} label="Error" value={totalError} color="#E53935" />
        )}
        <StatChip icon={<Globe size={14} />} label="Available" value={totalAvailable} color="#1A3A5C" />
        <StatChip icon={<Clock size={14} />} label="Coming Soon" value={totalSoon} color="#F5A623" />
      </div>

      {/* ── Filter tabs ─────────────────────────────────────────────────────── */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20, flexWrap: 'wrap' }}>
        {FILTER_TABS.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveFilter(tab.key)}
            style={{
              padding:      '6px 16px',
              borderRadius:  20,
              border:       activeFilter === tab.key ? 'none' : '1px solid #E2E8F0',
              background:   activeFilter === tab.key ? '#1A3A5C' : 'transparent',
              color:        activeFilter === tab.key ? '#fff' : '#6B7897',
              fontSize:      13,
              fontWeight:    activeFilter === tab.key ? 600 : 400,
              cursor:       'pointer',
              transition:   'all 0.15s',
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* ── Marketplace grid ─────────────────────────────────────────────────── */}
      {filtered.length === 0 ? (
        <div style={{ textAlign: 'center', color: '#6B7897', padding: '48px 0', fontSize: 15 }}>
          No marketplaces match this filter.
        </div>
      ) : (
        <div style={{
          display:             'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
          gap:                  20,
        }}>
          {filtered.map(market => {
            const conn = getConnection(market.slug);
            const slug = market.slug;
            return (
              <MarketplaceCard
                key={slug}
                marketplace={market}
                connection={conn}
                onConnect={() => handleConnect(market)}
                onDisconnect={() => handleDisconnect(slug)}
                onSync={conn ? () => handleSync(conn.id, slug) : undefined}
                isLoading={
                  isLoading(`connect_${slug}`) ||
                  isLoading(`disconnect_${slug}`) ||
                  isLoading(`sync_${conn?.id}`)
                }
                error={getError(`connect_${slug}`) || getError(`disconnect_${slug}`)}
              />
            );
          })}
        </div>
      )}

      {/* ── Connect modal ────────────────────────────────────────────────────── */}
      {modalMarket && (
        <ConnectModal
          marketplace={modalMarket}
          onClose={() => setModalMarket(null)}
          onConnected={() => {
            setModalMarket(null);
            fetchConnections();
          }}
        />
      )}

      {/* ── Disconnect confirmation ───────────────────────────────────────────── */}
      {confirmSlug && (
        <div style={overlayStyle} onClick={() => setConfirmSlug(null)}>
          <div style={confirmModalStyle} onClick={e => e.stopPropagation()}>
            <h3 style={{ margin: '0 0 10px', color: '#1A2B4A' }}>
              Disconnect {confirmSlug.charAt(0).toUpperCase() + confirmSlug.slice(1)}?
            </h3>
            <p style={{ color: '#6B7897', fontSize: 14, margin: '0 0 20px' }}>
              This will remove your connection. Previously synced data will be retained.
            </p>
            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
              <button
                onClick={() => setConfirmSlug(null)}
                style={{ ...btnStyle, background: '#F0F4F8', color: '#1A2B4A' }}
              >
                Cancel
              </button>
              <button
                onClick={async () => {
                  await disconnect(confirmSlug);
                  setConfirmSlug(null);
                }}
                disabled={isLoading(`disconnect_${confirmSlug}`)}
                style={{ ...btnStyle, background: '#E53935', color: '#fff' }}
              >
                {isLoading(`disconnect_${confirmSlug}`) ? 'Disconnecting…' : 'Disconnect'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

function StatChip({ icon, label, value, color }) {
  return (
    <div style={{
      display:      'flex',
      alignItems:   'center',
      gap:           6,
      background:   color + '18',
      borderRadius:  20,
      padding:      '5px 14px',
      color,
      fontSize:      13,
      fontWeight:    600,
    }}>
      {icon} {value} {label}
    </div>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const overlayStyle = {
  position:  'fixed', inset: 0,
  background: 'rgba(0,0,0,0.4)',
  display:   'flex', alignItems: 'center', justifyContent: 'center',
  zIndex:    1000,
};

const confirmModalStyle = {
  background:   '#fff',
  borderRadius:  14,
  padding:       28,
  width:         400,
  boxShadow:    '0 20px 60px rgba(0,0,0,0.2)',
};

const btnStyle = {
  padding:      '9px 20px',
  borderRadius:  8,
  border:       'none',
  fontSize:      14,
  fontWeight:    600,
  cursor:       'pointer',
};
