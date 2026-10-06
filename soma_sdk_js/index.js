'use strict';

const { Governance } = require('./lib/governance');
const { Cell, CellFitness } = require('./lib/cells');
const { shannonDiversity, letterGrade, specificityPenalty, antifragileBonus } = require('./lib/analysis');
const { SomaError, SomaValidationError, CellNotFoundError, CellParseError } = require('./lib/errors');

function parseCellFile(filePath) {
  const gov = new Governance('.');
  return gov.parseCellFile(filePath);
}

module.exports = {
  Governance,
  Cell,
  CellFitness,
  shannonDiversity,
  letterGrade,
  specificityPenalty,
  antifragileBonus,
  parseCellFile,
  SomaError,
  SomaValidationError,
  CellNotFoundError,
  CellParseError,
};
