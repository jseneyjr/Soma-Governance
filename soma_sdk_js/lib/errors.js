'use strict';

class SomaError extends Error {
  constructor(message, code = 'ERR_SOMA') {
    super(message);
    this.name = this.constructor.name;
    this.code = code;
  }
}

class SomaValidationError extends SomaError {
  constructor(message, code = 'VALIDATION_ERROR') {
    super(message, code);
  }
}

class CellNotFoundError extends SomaError {
  constructor(filePath, message = '') {
    super(message || `Cell file not found: ${filePath}`, 'CELL_NOT_FOUND');
    this.filePath = filePath;
  }
}

class CellParseError extends SomaError {
  constructor(filePath, message = '') {
    super(message || `Failed to parse cell file: ${filePath}`, 'CELL_PARSE_ERROR');
    this.filePath = filePath;
  }
}

module.exports = {
  SomaError,
  SomaValidationError,
  CellNotFoundError,
  CellParseError,
};
