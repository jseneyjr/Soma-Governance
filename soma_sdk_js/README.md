# soma-steering

Adaptive governance framework for AI coding assistants. Soma models your codebase as a living organism with an immune system that evolves based on observed agent behavior.

## Installation

```bash
npm install soma-steering
```

## Quick Start

```javascript
const { Governance } = require('soma-steering');

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

// Signal a cell (Outcome capture)
await gov.signal('wall-gae-truncation', 'tp', { survival_day: 12 });

// Run analysis
const replay = await gov.replay({ commits: 20 });
const trends = await gov.trends({ days: 30 });
const entropy = await gov.entropy();
const adversarial = await gov.adversarial('wall-gae-truncation');
```

> **Note on v0.25+**: This SDK provides programmatic access to the governance cells, analysis, and manual signaling. For full end-to-end biological execution (including Interoception, Test-Time Compute (TTC), Coherence checking, and Sleep cycles), use the Python Master Orchestrator (`soma_run.py`) provided in the core repository.

## API

See [TypeScript declarations](./index.d.ts) for the full API.

## License

Apache-2.0
