import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../../', import.meta.url));
const output = path.join(root, 'frontend/dist-pilot');
const config = JSON.parse(fs.readFileSync(path.join(root, 'vercel.json'), 'utf8'));
const excluded = fs.readFileSync(path.join(root, '.vercelignore'), 'utf8');
function files(directory) {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap(entry => {
    const name = path.join(directory, entry.name);
    return entry.isDirectory() ? files(name) : [name];
  });
}
function assertPublicJavaScript(code) {
  assert.doesNotMatch(code, /\/api\/v1|csrf_token|mfa_enrollment_required|XMLHttpRequest|recovery_codes|auth\/login|auth\/signup/);
}

test('Vercel builds only the public frontend, never Python', () => {
  assert.deepEqual(config.builds, [{ src: 'frontend/package.json', use: '@vercel/static-build', config: { distDir: 'dist-pilot' } }]);
  assert.match(excluded, /^\/\*$/m);
  assert.match(excluded, /^!\/frontend\/$/m);
  assert.doesNotMatch(excluded, /!\/app|!\/api|!\/\.pilot/);
});
test('all API paths are unavailable before the static fallback', () => {
  const rule = config.routes[0];
  const expression = new RegExp(`^(?:${rule.src})$`);
  for (const pathname of ['/api', '/api/', '/api/v1/auth/login', '/api/index.py', '/api/v1/documents/1/download']) assert.ok(expression.test(pathname));
  for (const pathname of ['/', '/apiculture', '/app']) assert.ok(!expression.test(pathname));
  assert.equal(rule.status, 503);
  assert.equal(rule.dest, '/pilot-unavailable.json');
  assert.equal(rule.headers['Cache-Control'], 'no-store');
  assert.match(rule.headers['Content-Type'], /application\/json/);
  assert.equal(rule.methods, undefined, 'unavailability must cover all HTTP methods');
});
test('public artifact contains no private API client or server files', () => {
  const artifact = files(output);
  assert.ok(artifact.some(file => file.endsWith('index.html')));
  assert.ok(artifact.some(file => file.endsWith('mark.svg')));
  assert.ok(!artifact.some(file => /\.(py|env|db|pdf|map)$/.test(file)));
  const javascript = artifact.filter(file => file.endsWith('.js'));
  assert.ok(javascript.length > 0);
  for (const file of javascript) assertPublicJavaScript(fs.readFileSync(file, 'utf8'));
  const unavailable = JSON.parse(fs.readFileSync(path.join(output, 'pilot-unavailable.json'), 'utf8'));
  assert.equal(unavailable.error.code, 'private_pilot_unavailable');
});
test('private-bundle guard rejects a deliberate negative control', () => {
  assert.throws(() => assertPublicJavaScript('fetch("/api/v1/auth/login")'), assert.AssertionError);
});
