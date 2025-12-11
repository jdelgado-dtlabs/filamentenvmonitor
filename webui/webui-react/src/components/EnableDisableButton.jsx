import { useState, useEffect, useRef } from 'react';
import { Button } from './Button';
import { api } from '../services/api';

export function EnableDisableButton({ 
  configKey, 
  currentValue, 
  onMessage, 
  onUpdate 
}) {
  const [enabling, setEnabling] = useState(false);
  const [disabling, setDisabling] = useState(false);
  const [error, setError] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const expectedValueRef = useRef(null);
  const requestTimeRef = useRef(null);
  const consecutiveFailuresRef = useRef(0);

  // Monitor config changes to detect when the request completes
  useEffect(() => {
    if (expectedValueRef.current !== null) {
      const timeSinceRequest = requestTimeRef.current ? Date.now() - requestTimeRef.current : 0;
      
      if (currentValue === expectedValueRef.current) {
        // Success - config matches expected value
        setEnabling(false);
        setDisabling(false);
        setError(false);
        setErrorMessage('');
        expectedValueRef.current = null;
        requestTimeRef.current = null;
        consecutiveFailuresRef.current = 0;
      } else if (timeSinceRequest > 5000) {
        // Grace period passed, check for failure
        consecutiveFailuresRef.current += 1;
        
        if (consecutiveFailuresRef.current >= 5) {
          // Show error after 5 consecutive failures
          setEnabling(false);
          setDisabling(false);
          setError(true);
          setErrorMessage(`Failed to ${expectedValueRef.current ? 'enable' : 'disable'}. Check logs for details.`);
          expectedValueRef.current = null;
          requestTimeRef.current = null;
        }
      }
    }
  }, [currentValue, onMessage, onUpdate]);

  const handleToggle = async () => {
    if (enabling || disabling || error) return;

    const newValue = !currentValue;
    expectedValueRef.current = newValue;
    requestTimeRef.current = Date.now();
    consecutiveFailuresRef.current = 0;

    if (newValue) {
      setEnabling(true);
    } else {
      setDisabling(true);
    }

    try {
      await api.setConfig(configKey, newValue);
      onUpdate();
    } catch (err) {
      setEnabling(false);
      setDisabling(false);
      setError(true);
      setErrorMessage(err.message || 'Failed to update configuration');
      onMessage(err.message, 'error');
      expectedValueRef.current = null;
      requestTimeRef.current = null;
    }
  };

  // Determine button text
  let buttonText;
  if (error) {
    buttonText = "Error!";
  } else if (enabling) {
    buttonText = "Enabling...";
  } else if (disabling) {
    buttonText = "Disabling...";
  } else if (currentValue) {
    buttonText = "✓ Enabled";
  } else {
    buttonText = "Disabled";
  }

  // Determine button variant
  let variant;
  if (error) {
    variant = "danger";
  } else if (enabling || disabling) {
    variant = "warning";
  } else if (currentValue) {
    variant = "success";
  } else {
    variant = "secondary";
  }

  return (
    <Button
      title={error ? errorMessage : ''}
      variant={variant}
      size="sm"
      onClick={handleToggle}
      disabled={enabling || disabling}
    >
      {buttonText}
    </Button>
  );
}
