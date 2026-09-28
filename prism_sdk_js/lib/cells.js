'use strict';

class CellFitness {
  constructor({
    triggers = 0,
    true_positives = 0,
    false_positives = 0,
    score = null,
    stress_survived = 0,
  } = {}) {
    this.triggers = triggers;
    this.truePositives = true_positives;
    this.falsePositives = false_positives;
    this.score = score;
    this.stressSurvived = stress_survived;
  }

  get rawScore() {
    if (this.triggers === 0) return null;
    const total = this.truePositives + this.falsePositives;
    if (total === 0) return null;
    return this.truePositives / total;
  }

  get snrDb() {
    const { truePositives: tp, falsePositives: fp } = this;
    if (tp > 0 && fp > 0) return Math.round(10 * Math.log10(tp / fp) * 10) / 10;
    if (tp > 0) return Infinity;
    return 0;
  }

  bayesian(confidence = 0.90) {
    const a = this.truePositives + 0.5;
    const b = this.falsePositives + 0.5;
    const mean = a / (a + b);
    const std = Math.sqrt((a * b) / (Math.pow(a + b, 2) * (a + b + 1)));
    const z = 1.645; // 90% CI
    const total = this.truePositives + this.falsePositives;
    return {
      mean: Math.round(mean * 10000) / 10000,
      lower: Math.round(Math.max(0, mean - z * std) * 10000) / 10000,
      upper: Math.round(Math.min(1, mean + z * std) * 10000) / 10000,
      certainty: total < 5 ? 'low' : total < 20 ? 'medium' : 'high',
    };
  }
}

class Cell {
  constructor({
    name = '',
    type = 'vacuole',
    hypothesis = '',
    prediction = '',
    falsification = '',
    target_paths = [],
    minimum_mode = 'breeze',
    tags = [],
    fitness = {},
  } = {}) {
    this.name = name;
    this.type = type;
    this.hypothesis = hypothesis;
    this.prediction = prediction;
    this.falsification = falsification;
    this.targetPaths = target_paths;
    this.minimumMode = minimum_mode;
    this.tags = tags;
    this.fitness = new CellFitness(fitness);
  }

  get isWall() { return this.type === 'wall'; }
  get isExtinct() { const s = this.fitness.rawScore; return s !== null && s <= 0.3; }
  get isPromotable() { const s = this.fitness.rawScore; return s !== null && s > 0.7 && this.fitness.triggers >= 5; }
}

module.exports = { Cell, CellFitness };
