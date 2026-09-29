"""Cell data structures and utilities."""
import math
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CellFitness:
    """Fitness metrics for a governance cell."""
    triggers: int = 0
    true_positives: int = 0
    false_positives: int = 0
    score: Optional[float] = None
    stress_survived: int = 0
    
    @property
    def raw_score(self):
        if self.triggers == 0:
            return None
        return self.true_positives / self.triggers
    
    @property
    def snr_db(self):
        """Signal-to-noise ratio in decibels."""
        tp, fp = self.true_positives, self.false_positives
        if tp > 0 and fp > 0:
            return round(10 * math.log10(tp / fp), 1)
        elif tp > 0:
            return None  # JSON-safe encoding of infinite SNR (RFC 8259)
        return 0.0
    
    def bayesian(self, confidence=0.90):
        """Beta-Binomial posterior with Jeffrey's prior."""
        a = self.true_positives + 0.5
        b = max(0, self.triggers - self.true_positives) + 0.5
        mean = a / (a + b)
        std = math.sqrt((a * b) / ((a + b) ** 2 * (a + b + 1)))
        z = 1.645  # 90% CI
        return {
            'mean': round(mean, 4),
            'lower': round(max(0, mean - z * std), 4),
            'upper': round(min(1, mean + z * std), 4),
            'certainty': 'low' if (self.true_positives + self.false_positives) < 5
                        else 'medium' if (self.true_positives + self.false_positives) < 20
                        else 'high'
        }


@dataclass
class Cell:
    """A Soma immune cell."""
    name: str
    type: str  # wall | vacuole | membrane | chloroplast | plasmodesmata
    hypothesis: str = ''
    prediction: str = ''
    falsification: str = ''
    target_paths: list = field(default_factory=list)
    minimum_mode: str = 'breeze'
    tags: list = field(default_factory=list)
    fitness: CellFitness = field(default_factory=CellFitness)
    
    @property
    def is_wall(self):
        return self.type == 'wall'
    
    @property
    def is_extinct(self):
        s = self.fitness.raw_score
        return s is not None and s <= 0.3
    
    @property
    def is_promotable(self):
        s = self.fitness.raw_score
        return s is not None and s > 0.7 and self.fitness.triggers >= 5
