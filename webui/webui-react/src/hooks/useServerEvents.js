import { useEffect, useState, useRef } from 'react';

/**
 * Custom hook for Server-Sent Events connection
 * Automatically reconnects on disconnect with exponential backoff
 * 
 * @param {string} url - SSE endpoint URL
 * @param {function} onMessage - Callback for incoming messages
 * @param {function} onError - Optional callback for errors
 * @returns {object} - Connection state and control methods
 */
export function useServerEvents(url, onMessage, onError) {
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState(null);
  const eventSourceRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);

  useEffect(() => {
    let isActive = true;

    const connect = () => {
      if (!isActive) return;

      try {
        // Close existing connection if any
        if (eventSourceRef.current) {
          eventSourceRef.current.close();
        }

        // Create new EventSource connection
        const eventSource = new EventSource(url);
        eventSourceRef.current = eventSource;

        eventSource.onopen = () => {
          if (isActive) {
            setConnected(true);
            setError(null);
            reconnectAttemptsRef.current = 0;
          }
        };

        eventSource.onmessage = (event) => {
          if (isActive) {
            try {
              const data = JSON.parse(event.data);
              onMessage(data);
            } catch (err) {
              console.error('Failed to parse SSE message:', err);
            }
          }
        };

        eventSource.onerror = (err) => {
          console.error('SSE error:', err);
          eventSource.close();

          if (isActive) {
            setConnected(false);
            setError('Connection lost');
            
            if (onError) {
              onError(err);
            }

            // Exponential backoff: 1s, 2s, 4s, 8s, max 30s
            const backoffDelay = Math.min(
              1000 * Math.pow(2, reconnectAttemptsRef.current),
              30000
            );
            reconnectAttemptsRef.current++;

            reconnectTimeoutRef.current = setTimeout(connect, backoffDelay);
          }
        };

      } catch (err) {
        console.error('Failed to create EventSource:', err);
        setError(err.message);
        
        if (onError) {
          onError(err);
        }
      }
    };

    // Initial connection
    connect();

    // Cleanup
    return () => {
      isActive = false;
      
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, [url, onMessage, onError]);

  const disconnect = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      setConnected(false);
    }
  };

  return {
    connected,
    error,
    disconnect,
  };
}
