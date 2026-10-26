// Writes the next manifest in the folder and validates it. Output in GITHUB_OUTPUT format (file=, version=).
import { writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { parseArgs } from 'node:util';

import { buildManifest, fileName, latestManifest, loadValidator, toYaml, validateAll } from './lib.mjs';

const { values } = parseArgs({
  options: {
    dir: { type: 'string', default: 'deploy/manifests' },
    'source-revision': { type: 'string' },
    'server-revision': { type: 'string' },
    'client-revision': { type: 'string' },
    // Empty: the previous manifest's image is reused (unchanged service)
    'server-image': { type: 'string', default: '' },
    'client-image': { type: 'string', default: '' },
  },
});
for (const required of ['source-revision', 'server-revision', 'client-revision']) {
  if (!values[required]) throw new Error(`--${required} est obligatoire`);
}

const previous = latestManifest(values.dir);
const version = (previous?.data.manifestVersion ?? 0) + 1;
const manifest = buildManifest({
  previous,
  version,
  sourceRevision: values['source-revision'],
  createdAt: new Date().toISOString().replace(/\.\d{3}Z$/, 'Z'),
  serverImage: values['server-image'],
  serverRevision: values['server-revision'],
  clientImage: values['client-image'],
  clientRevision: values['client-revision'],
});

const file = fileName(version, manifest.sourceRevision);
writeFileSync(join(values.dir, file), toYaml(manifest));

const errors = validateAll(values.dir, loadValidator(join(values.dir, 'schema.json')));
if (errors.length) {
  console.error(errors.join('\n'));
  process.exit(1);
}
console.log(`file=${join(values.dir, file)}`);
console.log(`version=${version}`);
