# soma-governance

JavaScript SDK for Soma governance cells and analysis helpers.

## Installation

```bash
npm install soma-governance
```

Requires Node.js 16 or newer.

## Quick Start

```javascript
const { Governance } = require('soma-governance');

const gov = new Governance('.');

const cells = await gov.listCells();
const landscape = await gov.fitnessLandscape({ bayesian: true });
const coverage = await gov.coverageReport();
const grade = await gov.grade();

await gov.createCell({
  hypothesis: 'PPO clip ratio must be in [0.1, 0.3]',
  type: 'wall',
  targetPaths: ['agent/ppo/optimizer.py'],
  minimumMode: 'trident',
});

await gov.createCellFromDescription(
  'Make sure the PPO clip ratio stays between 0.1 and 0.3',
  { domain: 'rl' }
);

await gov.signal('wall-gae-truncation', 'tp', { survival_day: 12 });

const replay = await gov.replay({ commits: 20 });
const trends = await gov.trends({ days: 30 });
const entropy = await gov.entropy();
const adversarial = await gov.adversarial('wall-gae-truncation');
```

The script-backed `Governance` methods require access to the Soma repository's `enzymes/` directory. For host-agent integration and state-bound write/execute authorization, use the Python MCP server in `soma_mcp/`.

## Exports

`index.js` exports `Governance`, `Cell`, `CellFitness`, `shannonDiversity`, `letterGrade`, `specificityPenalty`, and `antifragileBonus`.

See [TypeScript declarations](./index.d.ts) for the full API.

## License

Apache-2.0
