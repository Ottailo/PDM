// Rehearse the exact deployment source allowlist, without touching private data.
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const { spawnSync } = require('node:child_process');
const root = path.resolve(__dirname, '../..');
const source = path.join(root, 'frontend');
const stage = fs.mkdtempSync(path.join(root, '.pilot', 'public-source-'));
const web = path.join(stage, 'frontend');
fs.mkdirSync(web);
const allowed = ['package.json','package-lock.json','tsconfig.json','tsconfig.pilot.json','vite.pilot.config.ts','src/pilot-main.tsx','src/PilotPage.tsx','src/Brand.tsx','src/styles.css','src/pilot.css','pilot/index.html','public/mark.svg','public/pilot-unavailable.json'];
for (const file of allowed) {
  const target = path.join(web, file);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.copyFileSync(path.join(source, file), target);
}
// Use installed dependencies only; no install/network/private env inheritance.
fs.symlinkSync(path.join(source, 'node_modules'), path.join(web, 'node_modules'), os.platform() === 'win32' ? 'junction' : 'dir');
const env = Object.fromEntries(Object.entries(process.env).filter(([key]) => /^(PATH|SYSTEMROOT|WINDIR|TEMP|TMP|HOME|USERPROFILE|COMSPEC|PATHEXT|LOCALAPPDATA|APPDATA)$/i.test(key)));
for (const args of [[path.join(source,'node_modules/typescript/bin/tsc'),'--project',path.join(web,'tsconfig.pilot.json')], [path.join(source,'node_modules/vite/bin/vite.js'),'build','--config',path.join(web,'vite.pilot.config.ts')]]) {
  const result = spawnSync(process.execPath, args, { cwd: web, env, encoding: 'utf8' });
  fs.appendFileSync(path.join(stage,'build.log'), (result.stdout || '') + (result.stderr || ''));
  if (result.status !== 0) { console.error('FAIL: public source-only build; raw build output retained privately at', path.relative(root, stage)); process.exit(result.status || 1); }
}
console.log('PASS: public deployment source-only typecheck/build; no private modules or environment available');
