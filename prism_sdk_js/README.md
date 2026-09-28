# prism-steering

Adaptive governance framework for AI coding assistants.

## Installation

```bash
npm install prism-steering
```

## Quick Start

```javascript
const { Governance } = require('prism-steering');

const gov = new Governance('.');

// List all cells
const cells = await gov.listCells();

// Get fitness landscape
const landscape = await gov.fitnessLandscape({ bayesian: true });

// Get coverage report
const coverage = await gov.coverageReport();

// Get report card
const grade = await gov.grade();

// Create a cell programmatically
await gov.createCell({
  hypothesis: 'PPO clip ratio must be in [0.1, 0.3]',
  type: 'wall',
  targetPaths: ['agent/ppo/optimizer.py'],
  minimumMode: 'trident',
});

// Create a cell from natural language
await gov.createCellFromDescription(
  'Make sure the PPO clip ratio stays between 0.1 and 0.3',
  { domain: 'rl' }
);

// Signal a cell
await gov.signal('wall-gae-truncation', 'tp', { survival_day: 12 });

// Run analysis
const replay = await gov.replay({ commits: 20 });
const trends = await gov.trends({ days: 30 });
const entropy = await gov.entropy();
const adversarial = await gov.adversarial('wall-gae-truncation');
```

## API

See [TypeScript declarations](./index.d.ts) for the full API.

## License

Apache-2.0
