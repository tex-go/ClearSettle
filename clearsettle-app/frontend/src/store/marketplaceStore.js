/**
 * Marketplace Integration Zustand store.
 *
 * State
 * -----
 * marketplaces   — static catalog from /marketplace/
 * connections    — this company's connections from /marketplace/connections/
 * loading        — loading flags per operation key
 * error          — last error message per operation key
 * oauthPending   — { slug, state, expiresAt } while an OAuth flow is in progress
 */
import { create } from 'zustand';
import * as api from '../api/marketplace';

const useMarketplaceStore = create((set, get) => ({
  // ── State ─────────────────────────────────────────────────────────────────
  marketplaces:   [],
  connections:    [],
  loading:        {},
  error:          {},
  oauthPending:   null,

  // ── Helpers ───────────────────────────────────────────────────────────────
  _setLoading: (key, val) =>
    set(s => ({ loading: { ...s.loading, [key]: val } })),

  _setError: (key, msg) =>
    set(s => ({ error: { ...s.error, [key]: msg } })),

  _clearError: (key) =>
    set(s => ({ error: { ...s.error, [key]: null } })),

  // ── Marketplace catalog ───────────────────────────────────────────────────
  fetchMarketplaces: async () => {
    const { _setLoading, _setError } = get();
    _setLoading('marketplaces', true);
    try {
      const data = await api.listMarketplaces();
      set({ marketplaces: data });
      _setError('marketplaces', null);
    } catch (err) {
      _setError('marketplaces', err.response?.data?.detail || err.message);
    } finally {
      _setLoading('marketplaces', false);
    }
  },

  // ── Connections ───────────────────────────────────────────────────────────
  fetchConnections: async () => {
    const { _setLoading, _setError } = get();
    _setLoading('connections', true);
    try {
      const data = await api.listConnections();
      set({ connections: data.items || [] });
      _setError('connections', null);
    } catch (err) {
      _setError('connections', err.response?.data?.detail || err.message);
    } finally {
      _setLoading('connections', false);
    }
  },

  // ── Connect manual upload ─────────────────────────────────────────────────
  connectManual: async (marketplaceSlug, displayName) => {
    const { _setLoading, _setError, fetchConnections } = get();
    const key = `connect_${marketplaceSlug}`;
    _setLoading(key, true);
    _setError(key, null);
    try {
      await api.connectManual({ marketplace_slug: marketplaceSlug, display_name: displayName });
      await fetchConnections();
      return true;
    } catch (err) {
      _setError(key, err.response?.data?.detail || err.message);
      return false;
    } finally {
      _setLoading(key, false);
    }
  },

  // ── Connect via credentials (API key / WooCommerce) ───────────────────────
  connectCredentials: async (marketplaceSlug, credentials, displayName) => {
    const { _setLoading, _setError, fetchConnections } = get();
    const key = `connect_${marketplaceSlug}`;
    _setLoading(key, true);
    _setError(key, null);
    try {
      await api.connectCredentials({
        marketplace_slug: marketplaceSlug,
        credentials,
        display_name: displayName,
      });
      await fetchConnections();
      return true;
    } catch (err) {
      _setError(key, err.response?.data?.detail || err.message);
      return false;
    } finally {
      _setLoading(key, false);
    }
  },

  // ── Initiate OAuth ────────────────────────────────────────────────────────
  initiateOAuth: async (marketplaceSlug, options = {}) => {
    const { _setLoading, _setError } = get();
    const key = `oauth_${marketplaceSlug}`;
    _setLoading(key, true);
    _setError(key, null);
    try {
      const result = await api.initiateOAuth({
        marketplace_slug: marketplaceSlug,
        redirect_uri: options.redirectUri,
        shop_domain:  options.shopDomain,
      });
      set({
        oauthPending: {
          slug:       marketplaceSlug,
          state:      result.state,
          expiresAt:  result.expires_at,
          authUrl:    result.authorization_url,
        },
      });
      // Open the authorization URL in the same window (OAuth standard flow)
      window.location.href = result.authorization_url;
      return result;
    } catch (err) {
      _setError(key, err.response?.data?.detail || err.message);
      return null;
    } finally {
      _setLoading(key, false);
    }
  },

  // ── Disconnect ────────────────────────────────────────────────────────────
  disconnect: async (marketplaceSlug) => {
    const { _setLoading, _setError, fetchConnections } = get();
    const key = `disconnect_${marketplaceSlug}`;
    _setLoading(key, true);
    _setError(key, null);
    try {
      await api.disconnectMarketplace(marketplaceSlug);
      await fetchConnections();
      return true;
    } catch (err) {
      _setError(key, err.response?.data?.detail || err.message);
      return false;
    } finally {
      _setLoading(key, false);
    }
  },

  // ── Sync ──────────────────────────────────────────────────────────────────
  triggerSync: async (connectionId, syncType = 'full') => {
    const { _setLoading, _setError, fetchConnections } = get();
    const key = `sync_${connectionId}`;
    _setLoading(key, true);
    _setError(key, null);
    try {
      const job = await api.triggerSync(connectionId, { sync_type: syncType });
      await fetchConnections(); // refresh last_sync_at
      return job;
    } catch (err) {
      _setError(key, err.response?.data?.detail || err.message);
      return null;
    } finally {
      _setLoading(key, false);
    }
  },

  // ── Selectors ─────────────────────────────────────────────────────────────
  getConnection: (slug) =>
    get().connections.find(c => c.marketplace?.slug === slug),

  isConnected: (slug) => {
    const conn = get().connections.find(c => c.marketplace?.slug === slug);
    return conn?.status === 'connected';
  },

  isLoading: (key) => !!get().loading[key],

  getError: (key) => get().error[key] || null,

  clearOAuthPending: () => set({ oauthPending: null }),
}));

export default useMarketplaceStore;
