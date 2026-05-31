/**
 * Marketplace Integration API client
 * All calls go through the shared axios instance (auth interceptors included).
 */
import api from '../utils/api';

const BASE = '/marketplace';

// ── Marketplace registry ────────────────────────────────────────────────────

export const listMarketplaces = (liveOnly = false) =>
  api.get(`${BASE}/`, { params: { live_only: liveOnly } }).then(r => r.data);

// ── Connections ─────────────────────────────────────────────────────────────

export const listConnections = () =>
  api.get(`${BASE}/connections/`).then(r => r.data);

export const getConnection = (connectionId) =>
  api.get(`${BASE}/connections/${connectionId}`).then(r => r.data);

export const connectManual = (payload) =>
  api.post(`${BASE}/connections/manual`, payload).then(r => r.data);

export const connectCredentials = (payload) =>
  api.post(`${BASE}/connections/credentials`, payload).then(r => r.data);

export const disconnectMarketplace = (marketplaceSlug) =>
  api.delete(`${BASE}/connections/${marketplaceSlug}`).then(r => r.data);

// ── OAuth ───────────────────────────────────────────────────────────────────

export const initiateOAuth = (payload) =>
  api.post(`${BASE}/oauth/initiate`, payload).then(r => r.data);

// ── Sync ────────────────────────────────────────────────────────────────────

export const triggerSync = (connectionId, payload = { sync_type: 'full' }) =>
  api.post(`${BASE}/connections/${connectionId}/sync`, payload).then(r => r.data);

export const listSyncJobs = (connectionId, limit = 20) =>
  api.get(`${BASE}/connections/${connectionId}/jobs`, { params: { limit } }).then(r => r.data);

// ── Validate ────────────────────────────────────────────────────────────────

export const validateConnection = (connectionId) =>
  api.post(`${BASE}/connections/${connectionId}/validate`).then(r => r.data);

// ── Audit ───────────────────────────────────────────────────────────────────

export const getAuditLog = (connectionId, limit = 50) =>
  api.get(`${BASE}/audit/${connectionId}`, { params: { limit } }).then(r => r.data);
