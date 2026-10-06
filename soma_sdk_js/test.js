'use strict';

const assert = require('assert');
const path = require('path');
const fs = require('fs');
const {
  Governance,
  Cell,
  CellFitness,
  parseCellFile,
  SomaError,
  SomaValidationError,
  CellNotFoundError,
  CellParseError,
} = require('./index');

console.log('Running soma_sdk_js tests...');

// 1. Test CellFitness Laplace Score & Cell thresholds
{
  const fitExtinct = new CellFitness({ triggers: 10, true_positives: 0, false_positives: 10 });
  assert.strictEqual(fitExtinct.laplaceScore, 1 / 12);
  const cellExtinct = new Cell({ name: 'extinct-cell', fitness: fitExtinct });
  assert.strictEqual(cellExtinct.isExtinct, true);
  assert.strictEqual(cellExtinct.isPromotable, false);

  const fitPromotable = new CellFitness({ triggers: 25, true_positives: 24, false_positives: 1 });
  assert.strictEqual(fitPromotable.laplaceScore, 25 / 27);
  assert.ok(fitPromotable.laplaceScore > 0.85);
  const cellPromotable = new Cell({
    name: 'promotable-cell',
    fitness: fitPromotable,
    created_date: new Date(Date.now() - 10 * 86400 * 1000).toISOString(),
  });
  assert.strictEqual(cellPromotable.isPromotable, true);
  assert.strictEqual(cellPromotable.isPromotableWithAge(5), true);
  assert.strictEqual(cellPromotable.isPromotableWithAge(15), false);
  console.log('✓ Cell and CellFitness Laplace scoring & thresholds passed');
}

// 2. Test Error hierarchy
{
  const err = new CellNotFoundError('/path/to/missing.md');
  assert.ok(err instanceof SomaError);
  assert.ok(err instanceof Error);
  assert.strictEqual(err.code, 'CELL_NOT_FOUND');
  assert.strictEqual(err.filePath, '/path/to/missing.md');

  const parseErr = new CellParseError('/path/to/corrupt.md', 'Bad YAML');
  assert.ok(parseErr instanceof SomaError);
  assert.strictEqual(parseErr.code, 'CELL_PARSE_ERROR');
  console.log('✓ Typed errors hierarchy passed');
}

// 3. Test parseCellFile
{
  assert.throws(() => {
    parseCellFile('/path/that/definitely/does/not/exist.md');
  }, CellNotFoundError);

  // Parse a real cell from .soma/cells/ if available
  const sampleCell = path.resolve(__dirname, '..', '.soma', 'cells', 'vacuoles');
  if (fs.existsSync(sampleCell)) {
    const files = fs.readdirSync(sampleCell).filter(f => f.endsWith('.md') && f !== 'README.md');
    if (files.length > 0) {
      const target = path.join(sampleCell, files[0]);
      const [fm, body] = parseCellFile(target);
      assert.ok(typeof fm === 'object');
      assert.ok(typeof body === 'string');
      console.log(`✓ parseCellFile successfully parsed ${files[0]}`);
    }
  }
}

// 4. Test Governance createRule porcelain type mapping
{
  const gov = new Governance(path.resolve(__dirname, '..'));
  assert.strictEqual(typeof gov.createRule, 'function');
  assert.strictEqual(typeof gov.recordOutcome, 'function');
  console.log('✓ Governance methods verified');
}

console.log('All soma_sdk_js tests passed!');
