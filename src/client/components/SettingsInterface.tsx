import React, { useState, useEffect } from 'react';
import { Box, Text, useInput } from 'ink';
import { Header } from './Header';
import { LoadingSpinner } from './LoadingSpinner';
import { ApiService } from '../api';

interface SettingSectionProps {
  title: string;
  settings: any;
  path: string[];
  onNavigate: (path: string[]) => void;
  onEdit: (path: string[], value: any) => void;
}

interface SettingsInterfaceProps {
  onBack: () => void;
  selectedProject?: Project;
}

import type { Project } from '../types';

type ViewMode = 'categories' | 'section' | 'edit';

interface SettingItem {
  key: string;
  value: any;
  type: string;
  masked?: boolean;
  optional?: boolean;
  min?: number;
  max?: number;
  step?: number;
  options?: string[];
}

export const SettingsInterface: React.FC<SettingsInterfaceProps> = ({ onBack, selectedProject }) => {
  const [globalSettings, setGlobalSettings] = useState<any>({});
  const [projectSettings, setProjectSettings] = useState<any>({});
  const [loading, setLoading] = useState(true);
  const [settingsType, setSettingsType] = useState<'global' | 'project'>('global');
  const [currentPath, setCurrentPath] = useState<string[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [viewMode, setViewMode] = useState<ViewMode>('categories');
  const [editingValue, setEditingValue] = useState('');
  const [currentEditItem, setCurrentEditItem] = useState<SettingItem | null>(null);

  useEffect(() => {
    loadSettings();
  }, [selectedProject]);

  const loadSettings = async () => {
    try {
      setLoading(true);
      
      // Load global settings
      const globalData = await ApiService.getGlobalSettings();
      setGlobalSettings(globalData);
      
      // Load project settings if a project is selected
      if (selectedProject) {
        const projectData = await ApiService.getProjectSettings(selectedProject.id);
        setProjectSettings(projectData);
      }
      
    } catch (error) {
      console.error('Failed to load settings:', error);
    } finally {
      setLoading(false);
    }
  };

  const saveGlobalSettings = async () => {
    try {
      await ApiService.updateGlobalSettings({ config_name: 'global', config_data: globalSettings });
    } catch (error) {
      console.error('Failed to save global settings:', error);
    }
  };
  
  const saveProjectSettings = async () => {
    try {
      if (selectedProject) {
        await ApiService.updateProjectSettings(selectedProject.id, { 
          project_id: selectedProject.id, 
          config_data: projectSettings 
        });
      }
    } catch (error) {
      console.error('Failed to save project settings:', error);
    }
  };

  useInput((input, key) => {
    if (viewMode === 'edit') {
      handleEditInput(input, key);
    } else {
      handleNavigationInput(input, key);
    }
  });

  const handleNavigationInput = (input: string, key: any) => {
    if (key.escape) {
      if (currentPath.length === 0) {
        onBack();
      } else {
        // Go back one level
        setCurrentPath(currentPath.slice(0, -1));
        setViewMode(currentPath.length === 1 ? 'categories' : 'section');
        setSelectedIndex(0);
      }
    } else if (key.upArrow) {
      const items = getCurrentItems();
      setSelectedIndex(Math.max(0, selectedIndex - 1));
    } else if (key.downArrow) {
      const items = getCurrentItems();
      setSelectedIndex(Math.min(items.length - 1, selectedIndex + 1));
    } else if (key.return) {
      handleEnterKey();
    } else if (input === 'r' || input === 'R') {
      resetToDefaults();
    } else if (input === 'g' || input === 'G') {
      // Switch to global settings
      setSettingsType('global');
      setCurrentPath([]);
      setSelectedIndex(0);
      setViewMode('categories');
    } else if (input === 'p' || input === 'P') {
      // Switch to project settings (only if project is selected)
      if (selectedProject) {
        setSettingsType('project');
        setCurrentPath([]);
        setSelectedIndex(0);
        setViewMode('categories');
      }
    }
  };

  const handleEditInput = (input: string, key: any) => {
    if (key.escape) {
      // Cancel edit
      setViewMode('section');
      setEditingValue('');
      setCurrentEditItem(null);
    } else if (key.return) {
      // Save edit
      saveCurrentEdit();
    } else if (key.backspace || key.delete) {
      setEditingValue(editingValue.slice(0, -1));
    } else if (input && !key.ctrl && !key.meta) {
      if (currentEditItem?.type === 'number') {
        // Only allow numbers, dots, and minus for number inputs
        if (/^[0-9.\-]$/.test(input)) {
          setEditingValue(editingValue + input);
        }
      } else {
        setEditingValue(editingValue + input);
      }
    } else if (input === ' ' && currentEditItem?.type === 'boolean') {
      // Toggle boolean with space
      toggleBoolean();
    }
  };

  const getCurrentItems = () => {
    const currentSettings = settingsType === 'global' ? globalSettings : projectSettings;
    
    if (currentPath.length === 0) {
      // Top level categories
      return Object.keys(currentSettings);
    } else {
      // Navigate to current section
      let current = currentSettings;
      for (const path of currentPath) {
        current = current[path];
      }
      return Object.keys(current || {});
    }
  };

  const getCurrentSection = () => {
    const currentSettings = settingsType === 'global' ? globalSettings : projectSettings;
    let current = currentSettings;
    for (const path of currentPath) {
      current = current[path];
    }
    return current;
  };

  const handleEnterKey = () => {
    const items = getCurrentItems();
    const selectedKey = items[selectedIndex];
    const currentSection = getCurrentSection();
    const selectedItem = currentSection[selectedKey];

    if (typeof selectedItem === 'object' && selectedItem.type) {
      // This is a setting item
      if (selectedItem.type === 'boolean') {
        toggleBooleanSetting(selectedKey);
      } else if (selectedItem.type === 'selector' && selectedItem.options) {
        cycleSelectorOption(selectedKey);
      } else {
        // Text or number input
        startEditing(selectedKey, selectedItem);
      }
    } else {
      // This is a category/section, navigate into it
      setCurrentPath([...currentPath, selectedKey]);
      setViewMode('section');
      setSelectedIndex(0);
    }
  };

  const toggleBooleanSetting = (key: string) => {
    if (settingsType === 'global') {
      const newSettings = { ...globalSettings };
      let current = newSettings;
      for (const path of currentPath) {
        current = current[path];
      }
      current[key].value = !current[key].value;
      setGlobalSettings(newSettings);
      saveGlobalSettings();
    } else {
      const newSettings = { ...projectSettings };
      let current = newSettings;
      for (const path of currentPath) {
        current = current[path];
      }
      current[key].value = !current[key].value;
      setProjectSettings(newSettings);
      saveProjectSettings();
    }
  };

  const cycleSelectorOption = (key: string) => {
    if (settingsType === 'global') {
      const newSettings = { ...globalSettings };
      let current = newSettings;
      for (const path of currentPath) {
        current = current[path];
      }
      const item = current[key];
      const currentIndex = item.options.indexOf(item.value);
      const nextIndex = (currentIndex + 1) % item.options.length;
      current[key].value = item.options[nextIndex];
      setGlobalSettings(newSettings);
      saveGlobalSettings();
    } else {
      const newSettings = { ...projectSettings };
      let current = newSettings;
      for (const path of currentPath) {
        current = current[path];
      }
      const item = current[key];
      const currentIndex = item.options.indexOf(item.value);
      const nextIndex = (currentIndex + 1) % item.options.length;
      current[key].value = item.options[nextIndex];
      setProjectSettings(newSettings);
      saveProjectSettings();
    }
  };

  const startEditing = (key: string, item: any) => {
    setCurrentEditItem({ key, ...item });
    setEditingValue(item.masked ? '' : String(item.value));
    setViewMode('edit');
  };

  const saveCurrentEdit = () => {
    if (!currentEditItem) return;

    let newValue = editingValue;
    if (currentEditItem.type === 'number') {
      const numValue = parseFloat(editingValue);
      if (!isNaN(numValue)) {
        // Apply min/max constraints
        if (currentEditItem.min !== undefined) {
          newValue = Math.max(currentEditItem.min, numValue);
        }
        if (currentEditItem.max !== undefined) {
          newValue = Math.min(currentEditItem.max, newValue);
        }
      }
    }

    if (settingsType === 'global') {
      const newSettings = { ...globalSettings };
      let current = newSettings;
      for (const path of currentPath) {
        current = current[path];
      }
      current[currentEditItem.key].value = newValue;
      setGlobalSettings(newSettings);
      saveGlobalSettings();
    } else {
      const newSettings = { ...projectSettings };
      let current = newSettings;
      for (const path of currentPath) {
        current = current[path];
      }
      current[currentEditItem.key].value = newValue;
      setProjectSettings(newSettings);
      saveProjectSettings();
    }

    setViewMode('section');
    setEditingValue('');
    setCurrentEditItem(null);
  };

  const toggleBoolean = () => {
    if (currentEditItem?.type === 'boolean') {
      setEditingValue(editingValue === 'true' ? 'false' : 'true');
    }
  };

  const resetToDefaults = async () => {
    try {
      if (settingsType === 'global') {
        await ApiService.resetGlobalSettings();
      } else if (selectedProject) {
        await ApiService.resetProjectSettings(selectedProject.id);
      }
      await loadSettings();
    } catch (error) {
      console.error('Failed to reset settings:', error);
    }
  };

  const formatValue = (item: any) => {
    if (item.type === 'boolean') {
      return item.value ? '✓ Enabled' : '✗ Disabled';
    } else if (item.masked && item.value) {
      return '●●●●●●●●';
    } else if (item.type === 'number') {
      return String(item.value);
    } else {
      return item.value || '(empty)';
    }
  };

  const renderBreadcrumb = () => {
    const typeLabel = settingsType === 'global' ? 'Global Settings' : `Project Settings (${selectedProject?.name})`;
    if (currentPath.length === 0) return typeLabel;
    return `${typeLabel} > ${currentPath.map(p => p.replace('_', ' ')).join(' > ')}`;
  };

  if (loading) {
    return (
      <Box flexDirection="column" width="100%" height="100%">
        <Header title="Settings" subtitle="Loading configuration..." />
        <Box flexGrow={1} justifyContent="center" alignItems="center">
          <LoadingSpinner text="Loading settings..." />
        </Box>
      </Box>
    );
  }

  if (viewMode === 'edit' && currentEditItem) {
    return (
      <Box flexDirection="column" width="100%" height="100%">
        <Header title="Edit Setting" subtitle={renderBreadcrumb()} />
        
        <Box flexGrow={1} flexDirection="column" padding={1}>
          <Box paddingBottom={1}>
            <Text bold>Editing: </Text>
            <Text>{currentEditItem.key.replace('_', ' ')}</Text>
          </Box>
          
          <Box paddingBottom={1}>
            <Text dimColor>Type: {currentEditItem.type}</Text>
            {currentEditItem.min !== undefined && (
              <Text dimColor> (min: {currentEditItem.min})</Text>
            )}
            {currentEditItem.max !== undefined && (
              <Text dimColor> (max: {currentEditItem.max})</Text>
            )}
          </Box>
          
          <Box borderStyle="round" paddingX={1} paddingY={0} minHeight={3}>
            <Text>
              {editingValue}
              <Text backgroundColor="white" color="black">█</Text>
            </Text>
          </Box>
          
          <Box justifyContent="center" paddingTop={1}>
            <Text dimColor>
              {currentEditItem.type === 'boolean' 
                ? 'Space to toggle • Enter to save • Esc to cancel'
                : 'Type value • Enter to save • Esc to cancel'
              }
            </Text>
          </Box>
        </Box>
      </Box>
    );
  }

  const items = getCurrentItems();

  return (
    <Box flexDirection="column" width="100%" height="100%">
      <Header 
        title="Settings" 
        subtitle={renderBreadcrumb()}
      />

      <Box flexGrow={1} flexDirection="column" padding={1}>
        {/* Settings type switcher */}
        <Box paddingBottom={1} justifyContent="center">
          <Text>
            <Text color={settingsType === 'global' ? 'cyan' : 'gray'} bold={settingsType === 'global'}>
              [G] Global
            </Text>
            <Text> | </Text>
            <Text color={settingsType === 'project' ? 'cyan' : selectedProject ? 'gray' : 'red'} 
                  bold={settingsType === 'project'}>
              [P] Project {selectedProject ? `(${selectedProject.name})` : '(none selected)'}
            </Text>
          </Text>
        </Box>
        
        {items.map((key, index) => {
          const isSelected = index === selectedIndex;
          const currentSection = getCurrentSection();
          const item = currentSection[key];
          
          return (
            <Box key={key} flexDirection="row">
              <Text color={isSelected ? "cyan" : undefined}>
                {isSelected ? "► " : "  "}
              </Text>
              <Text bold={isSelected}>
                {key.replace('_', ' ')}
              </Text>
              {typeof item === 'object' && item.type && (
                <>
                  <Text>: </Text>
                  <Text color="green">{formatValue(item)}</Text>
                </>
              )}
            </Box>
          );
        })}
      </Box>

      <Box justifyContent="center" paddingX={1} paddingBottom={1}>
        <Text dimColor>
          ↑↓ Navigate • Enter Select/Edit • G Global • {selectedProject ? 'P Project • ' : ''}R Reset • Esc {currentPath.length === 0 ? 'Back' : 'Up level'}
        </Text>
      </Box>
    </Box>
  );
};