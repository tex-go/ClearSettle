/**
 * MarketplaceCard — displays a single marketplace with connection status,
 * connect/disconnect buttons, and sync trigger.
 *
 * Props
 * -----
 * marketplace   : MarketplaceOut from API
 * connection    : MarketplaceConnection | null (null = not connected)
 * onConnect     : () => void
 * onDisconnect  : () => void
 * onSync        : () => void
 * loadingKey    : string — used to check loading state
 */
import React from 'react';
import { CheckCircle, AlertCircle, Clock, Link, Unlink, RefreshCw, ChevronRight } from 'lucide-react';

const STATUS_CONFIG = {
  connected:    { color: '#00C896', label: 'Connected',    Icon: CheckCircle },
  error:        { color: '#E53935', label: 'Error',         Icon: AlertCircle },
  connecting:   { color: '#F5A623', label: 'Connecting…',  Icon: Clock },
  suspended:    { color: '#F5A623', label: 'Suspended',    Icon: AlertCircle },
  disconnected: { color: '#6B7897', label: 'Not connected', Icon: null },
  revoked:      { color: '#E53935', label: 'Revoked',      Icon: AlertCircle },
};

const CONNECTION_TYPE_LABEL = {
  oauth:            'OAuth 2.0',
  api_key:          'API Key',
  api_key_secret:   'API Key + Secret',
  manual_upload:    'Manual Upload',
  username_password: 'Username / Password',
  partner_api:      'Partner API',
};

export default function MarketplaceCard({
  marketplace,
  connection,
  onConnect,
  onDisconnect,
  onSync,
  isLoading,
  error,
}) {
  const status       = connection?.status || 'disconnected';
  const cfg          = STATUS_CONFIG[status] || STATUS_CONFIG.disconnected;
  const isConnected  = status === 'connected';
  const isLive       = marketplace.is_live;
  const typeLabel    = CONNECTION_TYPE_LABEL[marketplace.connection_type] || marketplace.connection_type;

  return (
    <div style={{
      background:    '#fff',
      borderRadius:  14,
      border:        `1px solid ${isConnected ? cfg.color + '66' : '#E2E8F0'}`,
      padding:       20,
      display:       'flex',
      flexDirection: 'column',
      gap:           12,
      position:      'relative',
      opacity:       isLive ? 1 : 0.6,
    }}>
      {/* Coming soon badge */}
      {!isLive && (
        <div style={{
          position:     'absolute',
          top:           12,
          right:         12,
          background:   '#F5A62322',
          color:        '#F5A623',
          borderRadius:  6,
          padding:      '2px 8px',
          fontSize:      11,
          fontWeight:    600,
        }}>
          Coming Soon
        </div>
      )}

      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        {/* Logo placeholder */}
        <div style={{
          width:         44,
          height:        44,
          borderRadius:  10,
          background:    '#F0F4F8',
          display:       'flex',
          alignItems:    'center',
          justifyContent:'center',
          fontWeight:    700,
          fontSize:      18,
          color:         '#1A3A5C',
          flexShrink:    0,
        }}>
          {marketplace.name[0]}
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 600, fontSize: 16, color: '#1A2B4A' }}>
            {marketplace.name}
          </div>
          <div style={{ fontSize: 12, color: '#6B7897', marginTop: 2 }}>
            {typeLabel}
          </div>
        </div>
        {/* Status indicator */}
        {cfg.Icon && (
          <cfg.Icon size={18} color={cfg.color} />
        )}
      </div>

      {/* Status label + last sync */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{
          fontSize:     12,
          fontWeight:   600,
          color:        cfg.color,
          background:   cfg.color + '18',
          padding:      '3px 10px',
          borderRadius:  20,
        }}>
          {cfg.label}
        </div>
        {isConnected && connection.last_sync_at && (
          <div style={{ fontSize: 11, color: '#6B7897' }}>
            Synced {new Date(connection.last_sync_at).toLocaleDateString()}
          </div>
        )}
      </div>

      {/* Seller info */}
      {isConnected && connection.seller_name && (
        <div style={{ fontSize: 12, color: '#6B7897' }}>
          <span style={{ color: '#1A2B4A', fontWeight: 500 }}>{connection.seller_name}</span>
          {connection.seller_id && (
            <span style={{ marginLeft: 8 }}>· ID: {connection.seller_id}</span>
          )}
        </div>
      )}

      {/* Error message */}
      {error && (
        <div style={{
          fontSize:     12,
          color:        '#E53935',
          background:   '#E5393512',
          borderRadius:  8,
          padding:      '6px 10px',
        }}>
          {error}
        </div>
      )}

      {/* Connection error */}
      {status === 'error' && connection.last_sync_error && (
        <div style={{
          fontSize:     12,
          color:        '#E53935',
          background:   '#E5393512',
          borderRadius:  8,
          padding:      '6px 10px',
        }}>
          {connection.last_sync_error}
        </div>
      )}

      {/* Action buttons */}
      {isLive && (
        <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
          {isConnected ? (
            <>
              {/* Sync button */}
              <button
                onClick={onSync}
                disabled={isLoading}
                style={actionBtnStyle('#1A3A5C', false)}
              >
                <RefreshCw size={14} />
                {isLoading ? 'Syncing…' : 'Sync Now'}
              </button>
              {/* Disconnect button */}
              <button
                onClick={onDisconnect}
                disabled={isLoading}
                style={actionBtnStyle('#E53935', true)}
              >
                <Unlink size={14} />
                Disconnect
              </button>
            </>
          ) : (
            <button
              onClick={onConnect}
              disabled={isLoading || !isLive}
              style={{ ...actionBtnStyle('#1A3A5C', false), flex: 1 }}
            >
              <Link size={14} />
              {isLoading ? 'Connecting…' : 'Connect'}
            </button>
          )}
        </div>
      )}

      {/* Description */}
      {marketplace.description && (
        <p style={{ fontSize: 12, color: '#6B7897', margin: 0, lineHeight: 1.5 }}>
          {marketplace.description}
        </p>
      )}
    </div>
  );
}

function actionBtnStyle(color, outlined) {
  return {
    display:         'flex',
    alignItems:      'center',
    gap:             6,
    padding:         '7px 14px',
    borderRadius:    8,
    border:          outlined ? `1px solid ${color}` : 'none',
    background:      outlined ? 'transparent' : color,
    color:           outlined ? color : '#fff',
    fontSize:        13,
    fontWeight:      600,
    cursor:          'pointer',
    transition:      'opacity 0.15s',
  };
}
