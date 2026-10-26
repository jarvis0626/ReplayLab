import { existsSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const windows = process.platform === 'win32';
const python = join(root, '.venv', windows ? 'Scripts/python.exe' : 'bin/python');

function run(command, args, cwd) {
  const result = spawnSync(command, args, { cwd, stdio: 'inherit', shell: false, windowsHide: true });
  if (result.error || result.status !== 0) throw new Error(`${command} failed${result.error ? `: ${result.error.message}` : ` (exit ${result.status})`}.`);
}

function npmCommand() {
  const candidates = [process.env.npm_execpath,
    join(dirname(process.execPath), 'node_modules/npm/bin/npm-cli.js'),
    resolve(dirname(process.execPath), '../lib/node_modules/npm/bin/npm-cli.js')];
  const cli = candidates.find((candidate) => candidate && existsSync(candidate));
  if (cli) return [process.execPath, [cli]];
  if (!windows) return ['npm', []];
  throw new Error('Could not locate npm. Run checks through npm run check.');
}

try {
  if (!existsSync(python)) throw new Error('The Python environment is missing. Run npm run setup first.');
  if (process.argv.includes('--contracts')) {
    run(python, [join(root, 'scripts/export-contracts.py')], root);
  } else {
    run(python, ['-m', 'pytest', '-q'], join(root, 'apps/api'));
    run(python, ['-m', 'ruff', 'check', 'app', 'tests'], join(root, 'apps/api'));
    const [npm, prefix] = npmCommand();
    run(npm, [...prefix, 'test'], join(root, 'apps/web'));
    run(npm, [...prefix, 'run', 'build'], join(root, 'apps/web'));
    console.log('Backend tests and lint, frontend tests, and production build passed.');
  }
} catch (error) {
  console.error(`Check failed: ${error.message}`);
  process.exitCode = 1;
}
