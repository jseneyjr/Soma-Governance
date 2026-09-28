'use strict';

function shannonDiversity(typeCounts) {
  const values = Object.values(typeCounts);
  const total = values.reduce((a, b) => a + b, 0);
  if (total === 0 || values.length <= 1) {
    return { entropy: 0, evenness: 0, assessment: 'monoculture' };
  }

  const entropy = -values
    .filter(n => n > 0)
    .reduce((sum, n) => sum + (n / total) * Math.log(n / total), 0);
  const maxEntropy = Math.log(values.length);
  const evenness = maxEntropy > 0 ? entropy / maxEntropy : 0;

  let assessment;
  if (evenness > 0.8) assessment = 'healthy';
  else if (evenness > 0.6) assessment = 'acceptable';
  else if (evenness > 0.4) assessment = 'imbalanced';
  else assessment = 'monoculture';

  return {
    entropy: Math.round(entropy * 10000) / 10000,
    evenness: Math.round(evenness * 10000) / 10000,
    assessment,
  };
}

function letterGrade(pct) {
  if (pct >= 97) return 'A+';
  if (pct >= 93) return 'A';
  if (pct >= 90) return 'A-';
  if (pct >= 87) return 'B+';
  if (pct >= 83) return 'B';
  if (pct >= 80) return 'B-';
  if (pct >= 77) return 'C+';
  if (pct >= 73) return 'C';
  if (pct >= 70) return 'C-';
  if (pct >= 67) return 'D+';
  if (pct >= 60) return 'D';
  return 'F';
}

function specificityPenalty(triggerRate) {
  return triggerRate > 0.8 ? 1.0 - Math.min(triggerRate, 1.0) : 1.0;
}

function antifragileBonus(stressSurvived, cap = 10) {
  return 1.0 + 0.05 * Math.min(stressSurvived, cap);
}

module.exports = { shannonDiversity, letterGrade, specificityPenalty, antifragileBonus };
