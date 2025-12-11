import { useState, useEffect } from 'react';
import { Button } from './Button';
import { api } from '../services/api';
import './TagEditor.css';

export function TagEditor({ dbType, onClose, onMessage, onSave }) {
  const [tags, setTags] = useState([]);
  const [loading, setLoading] = useState(true);
  const [hasChanges, setHasChanges] = useState(false);
  const [originalTags, setOriginalTags] = useState({});
  
  const configKey = `database.${dbType}.tags`;

  useEffect(() => {
    loadTags();
  }, []);

  const loadTags = async () => {
    try {
      const config = await api.getConfig(configKey);
      const tagsValue = config.value || {};
      
      // Convert object to array of {key, value} for editing
      const tagsArray = Object.entries(tagsValue).map(([key, value]) => ({
        key,
        value,
        id: Math.random().toString(36).substring(7)
      }));
      
      setTags(tagsArray);
      setOriginalTags(tagsValue);
      setLoading(false);
    } catch (error) {
      onMessage(`Failed to load tags: ${error.message}`, 'error');
      setLoading(false);
    }
  };

  const handleAddTag = () => {
    setTags([...tags, {
      key: '',
      value: '',
      id: Math.random().toString(36).substring(7)
    }]);
    setHasChanges(true);
  };

  const handleRemoveTag = (id) => {
    setTags(tags.filter(tag => tag.id !== id));
    setHasChanges(true);
  };

  const handleKeyChange = (id, newKey) => {
    setTags(tags.map(tag => 
      tag.id === id ? { ...tag, key: newKey } : tag
    ));
    setHasChanges(true);
  };

  const handleValueChange = (id, newValue) => {
    setTags(tags.map(tag => 
      tag.id === id ? { ...tag, value: newValue } : tag
    ));
    setHasChanges(true);
  };

  const handleSave = async () => {
    try {
      // Filter out tags with blank keys or values, convert to object
      const tagsObject = {};
      tags.forEach(tag => {
        const trimmedKey = tag.key.trim();
        const trimmedValue = tag.value.trim();
        if (trimmedKey && trimmedValue) {
          tagsObject[trimmedKey] = trimmedValue;
        }
      });

      // Save to backend
      await api.setConfig(configKey, tagsObject);
      
      onMessage('✓ Tags saved successfully', 'success');
      setHasChanges(false);
      setOriginalTags(tagsObject);
      
      // Show restart notification
      setTimeout(() => {
        onMessage('ℹ️ Database thread restart may be required for tag changes to take effect. Use the Restart button if needed.', 'success');
      }, 1500);
      
      if (onSave) onSave();
    } catch (error) {
      onMessage(`Failed to save tags: ${error.message}`, 'error');
    }
  };

  const handleCancel = () => {
    loadTags();
    setHasChanges(false);
  };

  if (loading) {
    return (
      <div className="tag-editor-overlay">
        <div className="tag-editor-modal">
          <p>Loading tags...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="tag-editor-overlay" onClick={onClose}>
      <div className="tag-editor-modal" onClick={(e) => e.stopPropagation()}>
        <div className="tag-editor-header">
          <h3>📝 Edit {dbType.charAt(0).toUpperCase() + dbType.slice(1)} Tags</h3>
          <button className="close-button" onClick={onClose}>✕</button>
        </div>
        
        <div className="tag-editor-content">
          <p className="tag-editor-help">
            Tags are key-value pairs added to all data points. Blank entries will be discarded.
          </p>
          
          {tags.length === 0 ? (
            <p className="no-tags-message">No tags configured. Click "Add Tag" to create one.</p>
          ) : (
            <div className="tags-list">
              {tags.map((tag) => (
                <div key={tag.id} className="tag-row">
                  <input
                    type="text"
                    placeholder="Key"
                    value={tag.key}
                    onChange={(e) => handleKeyChange(tag.id, e.target.value)}
                    className="tag-input tag-key"
                  />
                  <input
                    type="text"
                    placeholder="Value"
                    value={tag.value}
                    onChange={(e) => handleValueChange(tag.id, e.target.value)}
                    className="tag-input tag-value"
                  />
                  <button
                    className="remove-tag-btn"
                    onClick={() => handleRemoveTag(tag.id)}
                    title="Remove tag"
                  >
                    🗑️
                  </button>
                </div>
              ))}
            </div>
          )}
          
          <Button variant="primary" onClick={handleAddTag} style={{ marginTop: '12px' }}>
            ➕ Add Tag
          </Button>
        </div>
        
        <div className="tag-editor-footer">
          {hasChanges && (
            <>
              <Button variant="success" onClick={handleSave}>
                💾 Save Tags
              </Button>
              <Button variant="secondary" onClick={handleCancel}>
                Cancel
              </Button>
            </>
          )}
          {!hasChanges && (
            <Button variant="secondary" onClick={onClose}>
              Close
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
