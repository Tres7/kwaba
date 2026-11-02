// Prints the manifest to deploy and its images (key=value, for $GITHUB_OUTPUT): --manifest <file>, latest if empty;
// --environment production (default) or preprod, which picks the client image.
import { parseArgs } from 'node:util';

import { deployTarget } from './lib.mjs';

const { values } = parseArgs({
  options: {
    dir: { type: 'string', default: 'deploy/manifests' },
    manifest: { type: 'string', default: '' },
    environment: { type: 'string', default: 'production' },
  },
});

try {
  const target = deployTarget(values.dir, values.manifest.trim(), values.environment);
  console.log(`file=${target.file}`);
  console.log(`server_image=${target.serverImage}`);
  console.log(`client_image=${target.clientImage}`);
} catch (error) {
  console.error(error.message);
  process.exit(1);
}
