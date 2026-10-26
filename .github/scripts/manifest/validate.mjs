// Validates all manifests of the folder (schema, file name, strictly increasing versions).
import { join } from 'node:path';
import { parseArgs } from 'node:util';

import { loadValidator, readManifests, validateAll } from './lib.mjs';

const { values } = parseArgs({ options: { dir: { type: 'string', default: 'deploy/manifests' } } });

const errors = validateAll(values.dir, loadValidator(join(values.dir, 'schema.json')));
if (errors.length) {
  console.error(errors.join('\n'));
  process.exit(1);
}
console.log(`${readManifests(values.dir).length} manifest(s) valide(s)`);
