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
          console.error('SSE readyState:', eventSource.readyState);
          console.error('SSE url:', eventSource.url);
          
          // Log to page for debugging in kiosk mode
          const debugDiv = document.getElementById('sse-debug') || createDebugDiv();
          const timestamp = new Date().toLocaleTimeString();
          debugDiv.innerHTML += `<div>${timestamp} - SSE Error: readyState=${eventSource.readyState}</div>`;
          
          eventSource.close();

          if (isActive) {
            setConnected(false);
            setError('Connection lost - readyState: ' + eventSource.readyState);
            
            if (onError) {
              onError(err);
            }

            // Exponential backoff: 1s, 2s, 4s, 8s, max 30s
            const backoffDelay = Math.min(
              1000 * Math.pow(2, reconnectAttemptsRef.current),
              30000
            );
            reconnectAttemptsRef.current++;
            
            const debugDiv2 = document.getElementById('sse-debug') || createDebugDiv();
            debugDiv2.innerHTML += `<div>${timestamp} - Reconnecting in ${backoffDelay}ms (attempt ${reconnectAttemptsRef.current})</div>`;

            reconnectTimeoutRef.current = setTimeout(connect, backoffDelay);
          }
        };
        
        function createDebugDiv() {
          const div = document.createElement('div');
          div.id = 'sse-debug';
          div.style.cssText = 'position:fixed;bottom:0;left:0;right:0;background:rgba(0,0,0,0.8);color:#0f0;padding:10px;font-family:monospace;font-size:12px;max-height:200px;overflow-y:auto;z-index:9999';
          document.body.appendChild(div);
          return div;
        }

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
