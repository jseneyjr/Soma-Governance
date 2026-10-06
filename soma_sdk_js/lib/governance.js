'use strict';

const { execFile } = require('child_process');
const path = require('path');
const fs = require('fs');
const { promisify } = require('util');

const execFileAsync = promisify(execFile);

class Governance {
  constructor(projectRoot = '.') {
    this.root = path.resolve(projectRoot);
    this.cellsDir = path.join(this.root, '.soma', 'cells');
    this.metricsDir = path.join(this.root, '.soma', 'metrics');
    this.scriptsDir = this._findScriptsDir();
  }

  _findScriptsDir() {
    const candidates = [
      path.join(this.root, 'vendor', 'soma', 'enzymes'),
      path.join(this.root, 'enzymes'),
      path.join(__dirname, '..', '..', 'enzymes'),
    ];
    for (const c of candidates) {
      if (fs.existsSync(path.join(c, 'cell_fitness.py'))) {
        return c;
      }
    }
    return null;
  }

  async _runScript(scriptName, args = [], { json: jsonOutput = true } = {}) {
    if (!this.scriptsDir) {
      throw new Error('Soma scripts directory not found');
    }

    const script = path.join(this.scriptsDir, scriptName);
    if (!fs.existsSync(script)) {
      throw new Error(`Script not found: ${scriptName}`);
    }

    const cmdArgs = [...args];
    if (jsonOutput) cmdArgs.push('--json');

    const isBash = scriptName.endsWith('.sh');
    const cmd = isBash ? 'bash' : process.execPath.includes('python') ? 'python3' : 'python3';
    const fullArgs = isBash ? [script, ...cmdArgs] : [script, ...cmdArgs];

    try {
      const { stdout } = await execFileAsync(
        isBash ? 'bash' : 'python3',
        [script, ...cmdArgs],
        { cwd: this.root, timeout: 30000 }
      );

      if (jsonOutput && stdout.trim()) {
        try {
          return JSON.parse(stdout);
        } catch {
          return { raw: stdout, error: 'JSON parse failed' };
        }
      }
      return stdout;
    } catch (err) {
      throw new Error(`Script ${scriptName} failed: ${err.message}`);
    }
  }

  // === Cell Management ===

  async listCells() {
    const yaml = await this._tryRequireYaml();
    const cells = [];
    if (!fs.existsSync(this.cellsDir)) return cells;

    const walk = (dir) => {
      for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
        if (entry.isDirectory()) {
          walk(path.join(dir, entry.name));
        } else if (entry.name.endsWith('.md') && entry.name !== 'README.md') {
          try {
            const content = fs.readFileSync(path.join(dir, entry.name), 'utf8');
            if (!content.startsWith('---')) return;
            const endIdx = content.indexOf('---', 3);
            const fm = yaml.load(content.slice(3, endIdx));
            fm._name = path.parse(entry.name).name;
            fm._path = path.relative(this.root, path.join(dir, entry.name));
            cells.push(fm);
          } catch { /* skip */ }
        }
      }
    };
    walk(this.cellsDir);
    return cells;
  }

  async _tryRequireYaml() {
    try {
      return require('js-yaml');
    } catch {
      // Inline minimal YAML parser for simple frontmatter
      return {
        load(str) {
          const result = {};
          for (const line of str.split('\n')) {
            const match = line.match(/^(\w[\w_]*)\s*:\s*(.+)$/);
            if (match) {
              let val = match[2].trim();
              if (val.startsWith('[') && val.endsWith(']')) {
                val = val.slice(1, -1).split(',').map(s => s.trim().replace(/["']/g, ''));
              } else if (val === 'true') val = true;
              else if (val === 'false') val = false;
              else if (val === 'null') val = null;
              else if (!isNaN(val) && val !== '') val = Number(val);
              else val = val.replace(/["']/g, '');
              result[match[1]] = val;
            }
          }
          return result;
        }
      };
    }
  }

  async createCell({ hypothesis, type = 'vacuole', targetPaths, minimumMode, tags, id }) {
    const args = ['--name', id || hypothesis.slice(0, 40), '--type', type, '--hypothesis', hypothesis];
    if (targetPaths) args.push('--target-paths', targetPaths.join(','));
    if (minimumMode) args.push('--minimum-mode', minimumMode);
    if (id) args.push('--id', id);
    return this._runScript('cell_create.sh', args, { json: false });
  }

  async createRule(options) {
    const opts = typeof options === 'object' ? Object.assign({}, options) : { hypothesis: options };
    if (opts.ruleId && !opts.id) opts.id = opts.ruleId;
    return this.createCell(opts);
  }

  async recordOutcome(ruleId, success, options = {}) {
    let signalType;
    if (typeof success === 'string') {
      const norm = success.trim().toLowerCase();
      if (['tp', 'pass', 'true', '1', 'success'].includes(norm)) {
        signalType = 'tp';
      } else if (['fp', 'fail', 'false', '0', 'failure'].includes(norm)) {
        signalType = 'fp';
      } else {
        throw new Error(`Invalid outcome string: ${success}`);
      }
    } else if (typeof success === 'boolean' || typeof success === 'number') {
      signalType = Boolean(success) ? 'tp' : 'fp';
    } else {
      throw new TypeError(`success must be a bool, number, or string, got ${typeof success}`);
    }

    const { metric, sessionId, source = 'manual', ...rest } = options;
    const mergedMetric = Object.assign({}, metric, rest);
    if (sessionId) mergedMetric.session_id = sessionId;

    return this.signal(ruleId, signalType, mergedMetric);
  }

  async parseCellFile(filePath) {
    const fullPath = path.isAbsolute(filePath) ? filePath : path.join(this.root, filePath);
    if (!fs.existsSync(fullPath)) {
      throw new Error(`Cell file not found: ${filePath}`);
    }
    const content = fs.readFileSync(fullPath, 'utf8');
    const cleanContent = content.startsWith('\ufeff') ? content.slice(1) : content;
    if (!cleanContent.startsWith('---')) {
      throw new Error(`No frontmatter delimiter in ${filePath}`);
    }
    const endIdx = cleanContent.indexOf('---', 3);
    if (endIdx === -1) {
      throw new Error(`Unclosed frontmatter in ${filePath}`);
    }
    const yaml = await this._tryRequireYaml();
    const yamlText = cleanContent.slice(3, endIdx).trim();
    const frontmatter = yaml.load(yamlText) || {};
    const body = cleanContent.slice(endIdx + 3).replace(/^\n+/, '');
    return [frontmatter, body];
  }

  async createCellFromDescription(description, { domain, type } = {}) {
    const args = [description];
    if (domain) args.push('--domain', domain);
    if (type) args.push('--type', type);
    return this._runScript('cell_create_nl.py', args, { json: false });
  }

  async signal(cellName, signalType, metric) {
    const args = [cellName, signalType];
    if (metric) {
      for (const [k, v] of Object.entries(metric)) {
        args.push('--metric', `${k}=${v}`);
      }
    }
    return this._runScript('cell_signal.sh', args, { json: false });
  }

  // === Analysis ===

  async fitnessLandscape({ bayesian = false } = {}) {
    const args = bayesian ? ['--bayesian'] : [];
    return this._runScript('cell_fitness.py', args);
  }

  async ruleFitness({ bayesian = false } = {}) {
    return this.fitnessLandscape({ bayesian });
  }

  async coverageReport() {
    return this._runScript('cell_coverage.py');
  }

  async replay({ commits = 20 } = {}) {
    return this._runScript('immune_replay.py', ['--commits', String(commits)]);
  }

  async trends({ days = 30 } = {}) {
    return this._runScript('immune_trends.py', ['--days', String(days)]);
  }

  async grade() {
    return this._runScript('immune_grade.py');
  }

  async quorum({ threshold = 3 } = {}) {
    return this._runScript('cell_quorum.py', ['--threshold', String(threshold)]);
  }

  async dependencies({ format = 'text' } = {}) {
    return this._runScript('cell_deps.py', ['--format', format], { json: format !== 'mermaid' });
  }

  async scan() {
    return this._runScript('cell_scan.py');
  }

  async entropy() {
    return this._runScript('immune_entropy.py');
  }

  async adversarial(cellName) {
    const args = cellName ? [cellName] : [];
    return this._runScript('cell_adversarial.py', args);
  }
}

module.exports = { Governance };
