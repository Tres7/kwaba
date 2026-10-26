import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { copyFileSync, mkdirSync, mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { describe, test } from 'node:test';
import { fileURLToPath } from 'node:url';

import { buildManifest, deployTarget, fileName, imageRepository, loadValidator, plan, toYaml, validateAll } from '../lib.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const SCRIPTS = dirname(HERE);
const SCHEMA = join(SCRIPTS, '..', '..', '..', 'deploy', 'manifests', 'schema.json');
const SHA = (c) => c.repeat(40);
const IMAGE = `ghcr.io/tres7/kwaba-server@sha256:${'0'.repeat(64)}`;
const CLIENT_IMAGE = `ghcr.io/tres7/kwaba-client@sha256:${'1'.repeat(64)}`;
// Image names before the AfriStay → Kwa-Ba rename, still found in older manifests
const OLD_IMAGE = IMAGE.replace('kwaba-', 'afristay-');
const OLD_CLIENT_IMAGE = CLIENT_IMAGE.replace('kwaba-', 'afristay-');
const REPOSITORIES = { server: imageRepository('Tres7', 'server'), client: imageRepository('Tres7', 'client') };

function manifest(version, overrides = {}) {
  return {
    schemaVersion: 2,
    manifestVersion: version,
    sourceRevision: SHA('a'),
    createdAt: '2026-10-11T08:00:00Z',
    services: {
      server: { kind: 'image', sourceRevision: SHA('b'), image: IMAGE },
      client: { kind: 'image', sourceRevision: SHA('c'), image: CLIENT_IMAGE },
    },
    ...overrides,
  };
}

/** v1 format: client deployed from Git (manifests committed before the move to the VPS). */
function legacyManifest(version) {
  const m = manifest(version, { schemaVersion: 1 });
  m.services.client = { kind: 'git', sourceRevision: SHA('c') };
  return m;
}

function manifestsDir(...manifests) {
  const dir = mkdtempSync(join(tmpdir(), 'manifests-'));
  copyFileSync(SCHEMA, join(dir, 'schema.json'));
  for (const [name, content] of manifests) writeFileSync(join(dir, name), toYaml(content));
  return dir;
}

const validate = loadValidator(SCHEMA);

describe('fileName', () => {
  test('pads the version and keeps 7 characters of the revision', () => {
    assert.equal(fileName(42, SHA('a')), 'manifest-0042-aaaaaaa.yaml');
  });
});

describe('plan', () => {
  const previous = { data: manifest(1) };

  test('first manifest builds both images', () => {
    assert.deepEqual(plan({ previous: null, serverRevision: SHA('b'), clientRevision: SHA('c') }),
      { buildServer: true, buildClient: true, changed: true });
  });

  test('nothing changed: no manifest', () => {
    assert.deepEqual(plan({ previous, serverRevision: SHA('b'), clientRevision: SHA('c') }),
      { buildServer: false, buildClient: false, changed: false });
  });

  test('client only: rebuild the client image only', () => {
    assert.deepEqual(plan({ previous, serverRevision: SHA('b'), clientRevision: SHA('d') }),
      { buildServer: false, buildClient: true, changed: true });
  });

  test('server only: rebuild the server image only', () => {
    assert.deepEqual(plan({ previous, serverRevision: SHA('e'), clientRevision: SHA('c') }),
      { buildServer: true, buildClient: false, changed: true });
  });

  test('previous manifest in v1 (client from Git): the client image must be built', () => {
    assert.deepEqual(plan({ previous: { data: legacyManifest(1) }, serverRevision: SHA('b'), clientRevision: SHA('c') }),
      { buildServer: false, buildClient: true, changed: true });
  });

  test('images already in the expected repositories: nothing to rebuild', () => {
    assert.deepEqual(plan({ previous, serverRevision: SHA('b'), clientRevision: SHA('c'), repositories: REPOSITORIES }),
      { buildServer: false, buildClient: false, changed: false });
  });

  test('images still under the old name: both are rebuilt, even if unchanged', () => {
    const renamed = manifest(1);
    renamed.services.server.image = OLD_IMAGE;
    renamed.services.client.image = OLD_CLIENT_IMAGE;
    assert.deepEqual(plan({ previous: { data: renamed }, serverRevision: SHA('b'), clientRevision: SHA('c'), repositories: REPOSITORIES }),
      { buildServer: true, buildClient: true, changed: true });
  });
});

describe('buildManifest', () => {
  const base = { version: 2, sourceRevision: SHA('f'), createdAt: '2026-10-11T09:00:00Z', clientRevision: SHA('d') };

  const newClient = { clientImage: CLIENT_IMAGE.replace(/1/g, '2'), clientRevision: SHA('d') };

  test('reuses the previous server image when the server did not change', () => {
    const built = buildManifest({ ...base, ...newClient, previous: { data: manifest(1) }, serverImage: '',
      serverRevision: SHA('b') });
    assert.equal(built.schemaVersion, 2);
    assert.deepEqual(built.services.server, manifest(1).services.server);
    assert.deepEqual(built.services.client, { kind: 'image', sourceRevision: SHA('d'), image: newClient.clientImage });
    assert.ok(validate(built));
  });

  test('refuses to reuse an image when its service changed', () => {
    assert.throws(() => buildManifest({ ...base, ...newClient, previous: { data: manifest(1) }, serverImage: '',
      serverRevision: SHA('e') }), /server a changé/);
  });

  test('refuses to reuse a Git client from a v1 manifest', () => {
    assert.throws(() => buildManifest({ ...base, previous: { data: legacyManifest(1) }, serverImage: '',
      serverRevision: SHA('b'), clientImage: '', clientRevision: SHA('c') }), /Aucune image client/);
  });

  test('refuses a first manifest without images', () => {
    assert.throws(() => buildManifest({ ...base, ...newClient, previous: null, serverImage: '', serverRevision: SHA('b') }),
      /Aucune image server/);
  });
});

describe('validateAll', () => {
  test('accepts a consistent sequence, v1 manifests included', () => {
    const dir = manifestsDir(['manifest-0001-aaaaaaa.yaml', legacyManifest(1)], ['manifest-0002-aaaaaaa.yaml', manifest(2)]);
    assert.deepEqual(validateAll(dir, validate), []);
  });

  test('rejects a v2 manifest whose client is not an image, and a server image used as client', () => {
    const gitClient = manifest(1);
    gitClient.services.client = { kind: 'git', sourceRevision: SHA('c') };
    const swapped = manifest(2);
    swapped.services.client.image = IMAGE;
    const dir = manifestsDir(['manifest-0001-aaaaaaa.yaml', gitClient], ['manifest-0002-aaaaaaa.yaml', swapped]);
    const errors = validateAll(dir, validate).join('\n');
    assert.match(errors, /manifest-0001.*must have required property 'image'|manifest-0001.*must be equal to constant/);
    assert.match(errors, /manifest-0002.*must match pattern/);
  });

  test('rejects a version that does not match the file name', () => {
    const dir = manifestsDir(['manifest-0003-aaaaaaa.yaml', manifest(2)]);
    assert.match(validateAll(dir, validate).join(), /ne correspond pas au nom du fichier/);
  });

  test('rejects a revision that does not match the file name', () => {
    const dir = manifestsDir(['manifest-0001-bbbbbbb.yaml', manifest(1)]);
    assert.match(validateAll(dir, validate).join(), /sourceRevision aaaaaaa/);
  });

  test('rejects versions that do not strictly increase', () => {
    const dir = manifestsDir(['manifest-0002-aaaaaaa.yaml', manifest(2)], ['manifest-0002-bbbbbbb.yaml',
      manifest(2, { sourceRevision: SHA('b') })]);
    assert.match(validateAll(dir, validate).join(), /strictement supérieure/);
  });

  test('accepts older manifests with the images named before the rename (rollback)', () => {
    const before = manifest(1);
    before.services.server.image = OLD_IMAGE;
    before.services.client.image = OLD_CLIENT_IMAGE;
    const dir = manifestsDir(['manifest-0001-aaaaaaa.yaml', before], ['manifest-0002-bbbbbbb.yaml', manifest(2, { sourceRevision: SHA('b') })]);
    assert.deepEqual(validateAll(dir, validate), []);
  });

  test('rejects an image outside the project registry or not pinned by digest', () => {
    for (const image of ['docker.io/library/nginx@sha256:' + '0'.repeat(64), 'ghcr.io/tres7/kwaba-server:main']) {
      const bad = manifest(1);
      bad.services.server.image = image;
      const dir = manifestsDir(['manifest-0001-aaaaaaa.yaml', bad]);
      assert.match(validateAll(dir, validate).join(), /must match pattern/);
    }
  });

  test('rejects an invalid date and a bad file name', () => {
    const dir = manifestsDir(['manifest-0001-aaaaaaa.yaml', manifest(1, { createdAt: 'hier' })], ['manifest-1.yaml', manifest(1)]);
    const errors = validateAll(dir, validate).join('\n');
    assert.match(errors, /must match format "date-time"/);
    assert.match(errors, /nom attendu/);
  });
});

describe('deployTarget', () => {
  const dir = manifestsDir(['manifest-0001-aaaaaaa.yaml', legacyManifest(1)], ['manifest-0002-aaaaaaa.yaml', manifest(2)],
    ['manifest-0003-aaaaaaa.yaml', manifest(3)]);

  test('defaults to the latest manifest', () => {
    assert.deepEqual(deployTarget(dir), { file: 'manifest-0003-aaaaaaa.yaml', serverImage: IMAGE, clientImage: CLIENT_IMAGE });
  });

  test('returns an older manifest by file name (rollback)', () => {
    assert.equal(deployTarget(dir, 'manifest-0002-aaaaaaa.yaml').file, 'manifest-0002-aaaaaaa.yaml');
  });

  test('rejects anything but a plain manifest file name', () => {
    for (const name of ['../schema.json', 'manifest-0002-aaaaaaa.yaml; rm -rf /', 'deploy/manifests/manifest-0002-aaaaaaa.yaml']) {
      assert.throws(() => deployTarget(dir, name), /Nom de manifest invalide/);
    }
  });

  test('rejects an unknown manifest', () => {
    assert.throws(() => deployTarget(dir, 'manifest-0009-aaaaaaa.yaml'), /introuvable/);
  });

  test('rejects a v1 manifest whose client is deployed from Git', () => {
    assert.throws(() => deployTarget(dir, 'manifest-0001-aaaaaaa.yaml'), /pas d'image client/);
  });
});

describe('command line, on a real git history', () => {
  function git(cwd, ...args) {
    return execFileSync('git', args, { cwd, encoding: 'utf8' }).trim();
  }

  function commit(repo, path, message) {
    mkdirSync(join(repo, dirname(path)), { recursive: true });
    writeFileSync(join(repo, path), message);
    git(repo, 'add', '-A');
    git(repo, '-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qm', message);
    return git(repo, 'rev-parse', 'HEAD');
  }

  function run(repo, script, ...args) {
    const out = execFileSync('node', [join(SCRIPTS, script), '--dir', 'deploy/manifests', ...args], { cwd: repo, encoding: 'utf8' });
    return Object.fromEntries(out.trim().split('\n').filter((l) => l.includes('=')).map((l) => l.split(/=(.*)/s).slice(0, 2)));
  }

  test('first manifest, then a client-only change rebuilds only the client', () => {
    const repo = mkdtempSync(join(tmpdir(), 'repo-'));
    git(repo, 'init', '-q');
    mkdirSync(join(repo, 'deploy', 'manifests'), { recursive: true });
    copyFileSync(SCHEMA, join(repo, 'deploy', 'manifests', 'schema.json'));
    const serverRev = commit(repo, 'server/app.py', 'serveur');
    let head = commit(repo, 'client/page.tsx', 'client v1');

    let planned = run(repo, 'plan.mjs');
    assert.deepEqual([planned.build_server, planned.build_client], ['true', 'true']);
    let created = run(repo, 'create.mjs', '--source-revision', head, '--server-revision', planned.server_revision,
      '--client-revision', planned.client_revision, '--server-image', IMAGE, '--client-image', CLIENT_IMAGE);
    assert.equal(created.version, '1');
    assert.equal(planned.server_revision, serverRev);
    git(repo, 'add', '-A');
    git(repo, '-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qm', 'manifest 1');

    head = commit(repo, 'client/page.tsx', 'client v2');
    planned = run(repo, 'plan.mjs');
    assert.deepEqual([planned.changed, planned.build_server, planned.build_client, planned.previous_version],
      ['true', 'false', 'true', '1']);
    created = run(repo, 'create.mjs', '--source-revision', head, '--server-revision', planned.server_revision,
      '--client-revision', planned.client_revision, '--client-image', CLIENT_IMAGE.replace(/1/g, '3'));
    assert.equal(created.file, `deploy/manifests/manifest-0002-${head.slice(0, 7)}.yaml`);

    const latestImage = execFileSync('node', [join(SCRIPTS, 'latest.mjs'), '--field', 'services.server.image'],
      { cwd: repo, encoding: 'utf8' }).trim();
    assert.equal(latestImage, IMAGE);
    assert.match(execFileSync('node', [join(SCRIPTS, 'validate.mjs')], { cwd: repo, encoding: 'utf8' }), /2 manifest/);
  });
});
