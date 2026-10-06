'use strict';

class CellFitness {
  constructor(data = {}) {
    if (data instanceof CellFitness) {
      this.triggers = data.triggers;
      this.truePositives = data.truePositives;
      this.falsePositives = data.falsePositives;
      this.score = data.score;
      this.stressSurvived = data.stressSurvived;
      return;
    }
    const {
      triggers = 0,
      true_positives = 0,
      truePositives = 0,
      false_positives = 0,
      falsePositives = 0,
      score = null,
      stress_survived = 0,
      stressSurvived = 0,
    } = data;
    this.triggers = triggers;
    this.truePositives = true_positives || truePositives;
    this.falsePositives = false_positives || falsePositives;
    this.score = score;
    this.stressSurvived = stress_survived || stressSurvived;
  }

  get laplaceScore() {
    return (this.truePositives + 1) / (this.triggers + 2);
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
    created_date = null,
  } = {}) {
    this.name = name;
    this.type = type;
    this.hypothesis = hypothesis;
    this.prediction = prediction;
    this.falsification = falsification;
    this.targetPaths = target_paths;
    this.minimumMode = minimum_mode;
    this.tags = tags;
    this.createdDate = created_date;
    this.fitness = fitness instanceof CellFitness ? fitness : new CellFitness(fitness);
  }

  get isWall() { return this.type === 'wall'; }
  get isExtinct() {
    if (this.fitness.triggers === 0) return false;
    return this.fitness.laplaceScore <= 0.15;
  }
  get isPromotable() {
    if (this.fitness.triggers === 0) return false;
    return this.fitness.laplaceScore > 0.85 && this.fitness.triggers >= 20;
  }
  isPromotableWithAge(minAgeDays = 0) {
    if (!this.isPromotable) return false;
    if (minAgeDays <= 0) return true;
    if (!this.createdDate) return false;
    const created = new Date(this.createdDate);
    if (isNaN(created.getTime())) return false;
    const ageDays = (Date.now() - created.getTime()) / (1000 * 60 * 60 * 24);
    return ageDays >= minAgeDays;
  }
}

module.exports = { Cell, CellFitness };
