export interface CellFitnessData {
  triggers: number;
  true_positives: number;
  false_positives: number;
  score: number | null;
  stress_survived: number;
}

export interface BayesianResult {
  mean: number;
  lower: number;
  upper: number;
  certainty: 'low' | 'medium' | 'high';
}

export interface CellData {
  name: string;
  type: 'wall' | 'vacuole' | 'membrane' | 'chloroplast' | 'plasmodesmata';
  hypothesis: string;
  prediction: string;
  falsification: string;
  target_paths: string[];
  minimum_mode: string;
  tags: string[];
  fitness: CellFitnessData;
}

export interface CoverageReport {
  total_files: number;
  covered: number;
  uncovered: number;
  coverage_pct: number;
  by_directory: Record<string, { covered: number; total: number }>;
}

export interface GradeReport {
  coverage: { pct: number; grade: string };
  avg_fitness: { pct: number; grade: string };
  diversity: { pct: number; grade: string };
  staleness: { pct: number; grade: string };
  wall_integrity: { pct: number; grade: string };
  overall: { pct: number; grade: string };
  top_improvement: string;
}

export class CellFitness {
  constructor(data?: Partial<CellFitnessData>);
  get rawScore(): number | null;
  get snrDb(): number;
  bayesian(confidence?: number): BayesianResult;
}

export class Cell {
  constructor(data: Partial<CellData>);
  get isWall(): boolean;
  get isExtinct(): boolean;
  get isPromotable(): boolean;
}

export class Governance {
  constructor(projectRoot?: string);
  listCells(): Promise<CellData[]>;
  createCell(options: {
    hypothesis: string;
    type?: string;
    targetPaths?: string[];
    minimumMode?: string;
    tags?: string[];
    id?: string;
  }): Promise<string>;
  createRule(options: {
    hypothesis: string;
    type?: string;
    targetPaths?: string[];
    minimumMode?: string;
    tags?: string[];
    id?: string;
    ruleId?: string;
  }): Promise<string>;
  recordOutcome(
    ruleId: string,
    success: boolean | string | number,
    options?: {
      metric?: Record<string, any>;
      sessionId?: string;
      source?: string;
      idempotencyKey?: string;
      idempotencyScope?: string;
      expectedGeneration?: number;
      [key: string]: any;
    }
  ): Promise<Record<string, any>>;
  parseCellFile(filePath: string): [Record<string, any>, string];
  createCellFromDescription(description: string, options?: {
    domain?: string;
    type?: string;
  }): Promise<string>;
  signal(cellName: string, signalType: 'tp' | 'fp', metric?: Record<string, any>): Promise<string>;
  fitnessLandscape(options?: { bayesian?: boolean }): Promise<any>;
  ruleFitness(options?: { bayesian?: boolean }): Promise<any>;
  coverageReport(): Promise<CoverageReport>;
  replay(options?: { commits?: number }): Promise<any>;
  trends(options?: { days?: number }): Promise<any>;
  grade(): Promise<GradeReport>;
  quorum(options?: { threshold?: number }): Promise<any>;
  dependencies(options?: { format?: 'text' | 'mermaid' }): Promise<any>;
  scan(): Promise<any>;
  entropy(): Promise<any>;
  adversarial(cellName?: string): Promise<any>;
}

export function parseCellFile(filePath: string): [Record<string, any>, string];

export class SomaError extends Error {
  code: string;
  constructor(message?: string, code?: string);
}

export class SomaValidationError extends SomaError {}

export class CellNotFoundError extends SomaError {
  filePath: string;
  constructor(filePath: string, message?: string);
}

export class CellParseError extends SomaError {
  filePath: string;
  constructor(filePath: string, message?: string);
}

export function shannonDiversity(typeCounts: Record<string, number>): {
  entropy: number;
  evenness: number;
  assessment: string;
};

export function letterGrade(pct: number): string;
export function specificityPenalty(triggerRate: number): number;
export function antifragileBonus(stressSurvived: number, cap?: number): number;
