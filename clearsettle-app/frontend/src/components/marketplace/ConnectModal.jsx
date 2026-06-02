/**
 * ConnectModal — handles all connection types:
 *   OAuth          → redirects to provider auth page
 *   API Key        → shows api_key form
 *   API Key+Secret → shows key + secret form
 *   Manual Upload  → one-click confirm
 *   WooCommerce    → shows store_url + consumer_key + consumer_secret
 *
 * Props
 * -----
 * marketplace  : MarketplaceOut
 * onClose      : () => void
 * onConnected  : () => void  (called after successful connection)
 */
import React, { useState } from 'react';
import { X, ExternalLink, Upload, Key, Globe } from 'lucide-react';
import useMarketplaceStore from '../../store/marketplaceStore';

const FIELD_LABELS = {
  store_url:       { label: 'Store URL',       placeholder: 'https://mystore.com',  type: 'url' },
  consumer_key:    { label: 'Consumer Key',    placeholder: 'ck_…',                 type: 'text' },
  consumer_secret: { label: 'Consumer Secret', placeholder: 'cs_…',                 type: 'password' },
  api_key:         { label: 'API Key',         placeholder: 'Your API key',          type: 'text' },
  api_secret:      { label: 'API Secret',      placeholder: 'Your API secret',       type: 'password' },
  client_id:       { label: 'Client ID',       placeholder: 'Client ID',             type: 'text' },
  client_secret:   { label: 'Client Secret',   placeholder: 'Client Secret',         type: 'password' },
  shop_domain:     { label: 'Shop Domain',     placeholder: 'mystore.myshopify.com', type: 'text' },
};

export default function ConnectModal({ marketplace, onClose, onConnected }) {
  const {
    connectManual,
    connectCredentials,
    initiateOAuth,
    isLoading,
    getError,
    _clearError,
  } = useMarketplaceStore();

  const [fields,       setFields]       = useState({});
  const [shopDomain,   setShopDomain]   = useState('');
  const [displayName,  setDisplayName]  = useState('');
  const [submitted,    setSubmitted]    = useState(false);

  const slug         = marketplace.slug;
  const connType     = marketplace.connection_type;
  const reqFields    = marketplace.required_credential_fields || [];
  const loading      = isLoading(`connect_${slug}`) || isLoading(`oauth_${slug}`);
  const error        = getError(`connect_${slug}`) || getError(`oauth_${slug}`);
  const isOAuth      = connType === 'oauth';
  const isManual     = connType === 'manual_upload';

  const handleField = (k, v) => setFields(f => ({ ...f, [k]: v }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitted(true);
    _clearError(`connect_${slug}`);
    _clearError(`oauth_${slug}`);

    let ok = false;

    if (isOAuth) {
      // OAuth: redirect to provider — modal closes when we come back
      await initiateOAuth(slug, { shopDomain: shopDomain || undefined });
      return; // page redirects
    } else if (isManual) {
      ok = await connectManual(slug, displayName);
    } else {
      // API key / credential-based
      const creds = { ...fields };
      ok = await connectCredentials(slug, creds, displayName);
    }

    if (ok) {
      onConnected?.();
      onClose();
    }
  };

  return (
    <div style={overlayStyle} onClick={onClose}>
      <div style={modalStyle} onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', marginBottom: 20 }}>
          <div style={{
            width: 40, height: 40, borderRadius: 10,
            background: '#F0F4F8',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontWeight: 700, fontSize: 18, color: '#1A3A5C', marginRight: 12,
          }}>
            {marketplace.name[0]}
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 700, fontSize: 18, color: '#1A2B4A' }}>
              Connect {marketplace.name}
            </div>
            <div style={{ fontSize: 12, color: '#6B7897', marginTop: 2 }}>
              {marketplace.connection_type.replace(/_/g, ' ')}
            </div>
          </div>
          <button onClick={onClose} style={closeBtnStyle}>
            <X size={18} />
          </button>
        </div>

        {/* Description */}
        {marketplace.description && (
          <p style={{ fontSize: 13, color: '#6B7897', marginBottom: 16, lineHeight: 1.5 }}>
            {marketplace.description}
          </p>
        )}

        <form onSubmit={handleSubmit}>
          {/* OAuth — Shopify needs shop domain */}
          {isOAuth && slug === 'shopify' && (
            <FormField
              label="Shopify Store Domain"
              value={shopDomain}
              onChange={setShopDomain}
              placeholder="mystore.myshopify.com"
              required
              helper="Enter your Shopify store subdomain (without https://)"
            />
          )}

          {/* Manual upload */}
          {isManual && (
            <InfoBox icon={<Upload size={16} />}>
              This marketplace supports <strong>manual report upload</strong>.
              Once connected, upload your settlement files from the Reports section.
            </InfoBox>
          )}

          {/* OAuth (not Shopify) */}
          {isOAuth && slug !== 'shopify' && (
            <InfoBox icon={<ExternalLink size={16} />}>
              You'll be redirected to {marketplace.name} to authorize ClearSettle.
              Make sure you are logged into your seller account before continuing.
            </InfoBox>
          )}

          {/* API key fields */}
          {!isOAuth && !isManual && reqFields.map(field => (
            <FormField
              key={field}
              label={FIELD_LABELS[field]?.label || field}
              value={fields[field] || ''}
              onChange={v => handleField(field, v)}
              placeholder={FIELD_LABELS[field]?.placeholder || ''}
              type={FIELD_LABELS[field]?.type || 'text'}
              required
            />
          ))}

          {/* Optional display name */}
          <FormField
            label="Display Name (optional)"
            value={displayName}
            onChange={setDisplayName}
            placeholder={`My ${marketplace.name} account`}
          />

          {/* Docs link */}
          {marketplace.docs_url && (
            <a
              href={marketplace.docs_url}
              target="_blank"
              rel="noopener noreferrer"
              style={{ fontSize: 12, color: '#1A3A5C', display: 'flex', alignItems: 'center', gap: 4, marginBottom: 16 }}
            >
              <ExternalLink size={12} />
              View {marketplace.name} API documentation
            </a>
          )}

          {/* Error */}
          {error && (
            <div style={{
              background: '#E5393512', color: '#E53935',
              borderRadius: 8, padding: '8px 12px',
              fontSize: 13, marginBottom: 12,
            }}>
              {error}
            </div>
          )}

          {/* Submit */}
          <button
            type="submit"
            disabled={loading}
            style={{
              width: '100%', padding: '12px',
              background: loading ? '#B0BAC9' : '#1A3A5C',
              color: '#fff', border: 'none',
              borderRadius: 10, fontSize: 15, fontWeight: 700,
              cursor: loading ? 'not-allowed' : 'pointer',
            }}
          >
            {loading
              ? 'Connecting…'
              : isOAuth
              ? `Authorize with ${marketplace.name} →`
              : isManual
              ? 'Enable Manual Upload'
              : 'Connect'}
          </button>
        </form>
      </div>
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

function FormField({ label, value, onChange, placeholder, type = 'text', required, helper }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <label style={{ display: 'block', fontSize: 13, fontWeight: 600, color: '#1A2B4A', marginBottom: 5 }}>
        {label} {required && <span style={{ color: '#E53935' }}>*</span>}
      </label>
      <input
        type={type}
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        required={required}
        style={{
          width: '100%', padding: '10px 12px',
          borderRadius: 8, border: '1px solid #E2E8F0',
          fontSize: 14, outline: 'none', boxSizing: 'border-box',
        }}
      />
      {helper && (
        <div style={{ fontSize: 11, color: '#6B7897', marginTop: 4 }}>{helper}</div>
      )}
    </div>
  );
}

function InfoBox({ icon, children }) {
  return (
    <div style={{
      display:      'flex',
      gap:           10,
      background:   '#F0F4F8',
      borderRadius:  10,
      padding:      '12px 14px',
      marginBottom:  16,
      fontSize:      13,
      color:        '#1A2B4A',
      lineHeight:    1.5,
    }}>
      <span style={{ flexShrink: 0, color: '#1A3A5C', marginTop: 2 }}>{icon}</span>
      <span>{children}</span>
    </div>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const overlayStyle = {
  position:  'fixed',
  inset:      0,
  background: 'rgba(0,0,0,0.45)',
  display:   'flex',
  alignItems: 'center',
  justifyContent: 'center',
  zIndex:    1000,
  padding:   16,
};

const modalStyle = {
  background:   '#fff',
  borderRadius:  16,
  padding:       28,
  width:         460,
  maxWidth:     '100%',
  maxHeight:    '90vh',
  overflowY:    'auto',
  boxShadow:    '0 20px 60px rgba(0,0,0,0.2)',
};

const closeBtnStyle = {
  background:  'none',
  border:      'none',
  cursor:      'pointer',
  padding:      6,
  borderRadius: 6,
  color:       '#6B7897',
  display:     'flex',
};
