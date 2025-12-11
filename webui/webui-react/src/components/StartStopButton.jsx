import { useState, useEffect, useRef } from 'react';
import { Button } from './Button';
import { api } from '../services/api';

export function StartStopButton({ threadName, thread, onMessage, onUpdate }) {
  const [starting, setStarting] = useState(false);
  const [stopping, setStopping] = useState(false);
  const [error, setError] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [isHovering, setIsHovering] = useState(false);
  const expectedStateRef = useRef(null);
  const stateChangeTimeRef = useRef(null);
  const consecutiveFailuresRef = useRef(0);

  const isRunning = thread?.running ?? false;
  const threadExists = thread?.exists ?? false;
  const isBusy = starting || stopping;

  // Monitor thread state changes
  useEffect(() => {
    // If we're expecting a state change, check if it happened
    if (expectedStateRef.current !== null) {
      const expectedRunning = expectedStateRef.current;
      const timeSinceRequest = stateChangeTimeRef.current ? Date.now() - stateChangeTimeRef.current : 0;
      
      if (isRunning === expectedRunning) {
        // State changed as expected - clear busy state
        setStarting(false);
        setStopping(false);
        setError(false);
        setErrorMessage('');
        consecutiveFailuresRef.current = 0;
        expectedStateRef.current = null;
        stateChangeTimeRef.current = null;
        onUpdate();
      } else if (threadExists && !isRunning && expectedRunning === true && timeSinceRequest > 5000) {
        // We expected it to start but it's not running and exists
        // Only check after 5 seconds grace period
        consecutiveFailuresRef.current += 1;
        
        if (consecutiveFailuresRef.current >= 5) {
          // Thread has failed to start after multiple checks - show error
          setStarting(false);
          setStopping(false);
          setError(true);
          setErrorMessage(`Thread '${threadName}' failed to start. Check logs for details.`);
          expectedStateRef.current = null;
          stateChangeTimeRef.current = null;
          onMessage(`✗ ${threadName} failed to start`, 'error');
        }
      } else if (!isRunning && expectedRunning === false && timeSinceRequest > 5000) {
        // We expected it to stop but it's still running
        // Only check after 5 seconds grace period
        consecutiveFailuresRef.current += 1;
        
        if (consecutiveFailuresRef.current >= 5) {
          // Thread has failed to stop - show error
          setStarting(false);
          setStopping(false);
          setError(true);
          setErrorMessage(`Thread '${threadName}' failed to stop. Check logs for details.`);
          expectedStateRef.current = null;
          stateChangeTimeRef.current = null;
          onMessage(`✗ ${threadName} failed to stop`, 'error');
        }
      }
    } else if (threadExists && !isRunning && !isBusy && consecutiveFailuresRef.current > 0) {
      // Thread exists but isn't running and we're not trying to do anything
      // This indicates a crash
      setError(true);
      setErrorMessage(`Thread '${threadName}' has crashed or exited unexpectedly.`);
    } else if (isRunning) {
      // Thread is running, clear error state
      setError(false);
      setErrorMessage('');
      consecutiveFailuresRef.current = 0;
    }
  }, [isRunning, threadExists, isBusy, threadName, onMessage, onUpdate]);

  const handleClick = async () => {
    if (isBusy || error) return;

    try {
      if (isRunning) {
        setStopping(true);
        setError(false);
        setErrorMessage('');
        expectedStateRef.current = false;
        stateChangeTimeRef.current = Date.now();
        consecutiveFailuresRef.current = 0;
        await api.stopThread(threadName);
        onMessage(`✓ Stopping ${threadName}...`, 'success');
        onUpdate();
      } else {
        setStarting(true);
        setError(false);
        setErrorMessage('');
        expectedStateRef.current = true;
        stateChangeTimeRef.current = Date.now();
        consecutiveFailuresRef.current = 0;
        await api.startThread(threadName);
        onMessage(`✓ Starting ${threadName}...`, 'success');
        onUpdate();
      }
    } catch (err) {
      const errMsg = err.message || 'Unknown error occurred';
      onMessage(errMsg, 'error');
      setStarting(false);
      setStopping(false);
      setError(true);
      setErrorMessage(errMsg);
      expectedStateRef.current = null;
      stateChangeTimeRef.current = null;
    }
  };

  let variant = 'secondary';
  let label = 'Stopped';

  if (error) {
    variant = 'danger';
    label = 'Error!';
  } else if (isBusy) {
    variant = 'secondary';
    label = starting ? 'Starting...' : 'Stopping...';
  } else if (isRunning) {
    variant = isHovering ? 'danger' : 'success';
    label = isHovering ? 'Stop' : 'Started';
  } else {
    variant = isHovering ? 'success' : 'danger';
    label = isHovering ? 'Start' : 'Stopped';
  }

  return (
    <Button
      variant={variant}
      size="sm"
      onClick={handleClick}
      onMouseEnter={() => setIsHovering(true)}
      onMouseLeave={() => setIsHovering(false)}
      disabled={isBusy}
      title={error ? errorMessage : ''}
    >
      {label}
    </Button>
  );
}
