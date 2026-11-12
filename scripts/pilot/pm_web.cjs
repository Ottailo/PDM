// Explicit isolated Vite launch; only preview_start runs this server.
const fs = require('node:fs');
const path = require('node:path');
const { spawn } = require('node:child_process');
const root = path.resolve(__dirname, '../..');
const manifest = JSON.parse(fs.readFileSync(path.join(root, '.pilot', 'pm-run.json'), 'utf8'));
if (!/^machivital_pm_[a-f0-9]{12}$/.test(manifest.namespace) || !Number.isInteger(manifest.api_port) || !Number.isInteger(manifest.web_port)) throw new Error('Invalid isolated run manifest');
const allowed = new Set(['SYSTEMROOT','WINDIR','PATH','HOME','USERPROFILE','LANG','TEMP','TMP','COMSPEC','PATHEXT','LOCALAPPDATA','APPDATA','PROGRAMFILES','PROGRAMFILES(X86)','PROGRAMW6432']);
const env = Object.fromEntries(Object.entries(process.env).filter(([key]) => allowed.has(key.toUpperCase())));
env.PDM_API_ORIGIN = `http://127.0.0.1:${manifest.api_port}`;
const child = spawn(process.execPath, [path.join(root, 'frontend/node_modules/vite/bin/vite.js'), '--host','127.0.0.1','--port',String(manifest.web_port),'--strictPort'], {cwd:path.join(root,'frontend'), env, stdio:'inherit'});
child.on('exit', (code) => process.exit(code ?? 1));
for (const signal of ['SIGINT','SIGTERM']) process.on(signal, () => child.kill(signal));
