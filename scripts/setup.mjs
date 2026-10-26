import { existsSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const windows = process.platform === 'win32';
const python = join(root, '.venv', windows ? 'Scripts/python.exe' : 'bin/python');

function run(command, args, cwd = root) {
  const result = spawnSync(command, args, { cwd, stdio: 'inherit', shell: false, windowsHide: true });
  if (result.error || result.status !== 0) {
    throw new Error(`${command} failed${result.error ? `: ${result.error.message}` : ` (exit ${result.status})`}.`);
  }
}

function npmCommand() {
  const candidates = [process.env.npm_execpath,
    join(dirname(process.execPath), 'node_modules/npm/bin/npm-cli.js'),
    resolve(dirname(process.execPath), '../lib/node_modules/npm/bin/npm-cli.js')];
  const cli = candidates.find((candidate) => candidate && existsSync(candidate));
  if (cli) return [process.execPath, [cli]];
  if (!windows) return ['npm', []];
  throw new Error('Could not locate npm. Run this script with npm run setup from a Node.js installation that includes npm.');
}

try {
  const [major, minor] = process.versions.node.split('.').map(Number);
  if (major < 22 || (major === 22 && minor < 12)) throw new Error('Install Node.js 22.12 or newer.');
  for (const binary of ['ffmpeg', 'ffprobe']) {
    const result = spawnSync(binary, ['-version'], { stdio: 'ignore', shell: false, windowsHide: true });
    if (result.error || result.status !== 0) {
      throw new Error(`${binary} is missing from PATH. Install FFmpeg (including ffprobe), reopen your terminal, then run npm run setup again.`);
    }
  }
  const systemPython = windows ? 'python' : 'python3';
  run(existsSync(python) ? python : systemPython, ['-c', 'import sys; assert sys.version_info >= (3, 11), "Python 3.11+ is required"']);
  if (!existsSync(python)) run(systemPython, ['-m', 'venv', join(root, '.venv')]);
  const lock = join(root, 'apps/api/requirements.lock');
  const requirements = existsSync(lock) ? lock : join(root, 'apps/api/requirements.txt');
  run(python, ['-m', 'pip', 'install', '-r', requirements]);
  const [npm, prefix] = npmCommand();
  run(npm, [...prefix, 'ci'], join(root, 'apps/web'));
  console.log('ReplayLab dependencies are ready. Run npm run dev.');
} catch (error) {
  console.error(`Setup failed: ${error.message}`);
  process.exitCode = 1;
}
