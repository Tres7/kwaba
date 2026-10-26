// Prints a field of the latest manifest (e.g. --field services.server.image), or nothing if there is none.
import { parseArgs } from 'node:util';

import { field, latestManifest } from './lib.mjs';

const { values } = parseArgs({
  options: {
    dir: { type: 'string', default: 'deploy/manifests' },
    field: { type: 'string' },
  },
});

const latest = latestManifest(values.dir);
if (latest) console.log(values.field ? field(latest, values.field) ?? '' : latest.path);
