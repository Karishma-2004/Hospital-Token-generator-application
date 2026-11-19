import { useEffect, useRef, useState } from 'react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

function socketUrl(hospitalId) {
  const u = new URL(API_BASE, window.location.href); // also works when VITE_API_URL is a relative path like /api
  const protocol = u.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${u.host}/ws/queue/${hospitalId}/`;
}

/**
 * Live queue connection for one hospital.
 *  - connects to the WebSocket and calls onUpdate(board) on every change
 *  - if the socket is not available (server started without WebSocket support, network drop)
 *    it falls back to calling onUpdate(null) every 5 seconds, so the screen still refreshes
 * Returns true while the WebSocket is connected.
 */
export default function useQueueSocket(hospitalId, onUpdate) {
  const [connected, setConnected] = useState(false);
  const callback = useRef(onUpdate);
  callback.current = onUpdate;

  useEffect(() => {
    if (!hospitalId) return undefined;
    let ws = null;
    let retryTimer = null;
    let pollTimer = null;
    let closed = false;

    const startPolling = () => {
      if (!pollTimer) pollTimer = setInterval(() => callback.current?.(null), 5000);
    };
    const stopPolling = () => {
      clearInterval(pollTimer);
      pollTimer = null;
    };

    const connect = () => {
      try {
        ws = new WebSocket(socketUrl(hospitalId));
      } catch {
        startPolling();
        return;
      }
      ws.onopen = () => {
        setConnected(true);
        stopPolling();
      };
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          callback.current?.(data.board || null);
        } catch {
          /* ignore malformed message */
        }
      };
      ws.onerror = () => ws.close();
      ws.onclose = () => {
        setConnected(false);
        if (closed) return;
        startPolling();
        retryTimer = setTimeout(connect, 5000);
      };
    };

    connect();
    return () => {
      closed = true;
      clearTimeout(retryTimer);
      stopPolling();
      if (ws) ws.close();
    };
  }, [hospitalId]);

  return connected;
}