#!/usr/bin/env node

import React from 'react';
import { render } from 'ink';
import { App } from './components/App';

async function main() {
  try {
    render(React.createElement(App));
  } catch (error) {
    console.error('Error starting AI CLI:', error);
    process.exit(1);
  }
}

main();