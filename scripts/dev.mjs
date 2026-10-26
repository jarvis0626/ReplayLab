import { existsSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { spawn, spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const windows = process.platform === 'win32';
const python = join(root, '.venv', windows ? 'Scripts/python.exe' : 'bin/python');
const children = [];
let stopping = false;

function terminate(child, force = false) {
  if (!child.pid || child.exitCode !== null || child.signalCode !== null) return;
  try {
    if (windows) {
      spawnSync('taskkill', ['/pid', String(child.pid), '/T', '/F'], { stdio: 'ignore', windowsHide: true, shell: false });
    } else {
      process.kill(-child.pid, force ? 'SIGKILL' : 'SIGTERM');
    }
  } catch { /* The process may have exited between checking and signaling. */ }
}

function stop(code = 0) {
  if (stopping) return;
  stopping = true;
  process.exitCode = code;
  for (const child of children) terminate(child);
  const timer = setTimeout(() => { for (const child of children) terminate(child, true); }, 2000);
  timer.unref();
}

function launch(command, args, cwd) {
  const child = spawn(command, args, { cwd, stdio: 'inherit', shell: false, windowsHide: true, detached: !windows });
  children.push(child);
  child.once('error', (error) => { console.error(`Could not start ${command}: ${error.message}`); stop(1); });
  child.once('exit', (code, signal) => {
    if (!stopping) {
      console.error(`Development service exited (${signal || code}). Stopping the other service.`);
      stop(code || (signal ? 1 : 0));
    }
  });
}

process.once('SIGINT', () => stop(0));
process.once('SIGTERM', () => stop(0));
process.once('exit', () => { for (const child of children) terminate(child, true); });

if (!existsSync(python) || !existsSync(join(root, 'apps/web/node_modules/vite/bin/vite.js'))) {
  console.error('Dependencies are missing. Run npm run setup first.');
  process.exitCode = 1;
} else {
  console.log('ReplayLab: http://127.0.0.1:5173 | API: http://127.0.0.1:8010 | Ctrl+C stops both.');
  launch(python, ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8010', '--reload'], join(root, 'apps/api'));
  launch(process.execPath, [join(root, 'apps/web/node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', '5173', '--strictPort'], join(root, 'apps/web'));
}
