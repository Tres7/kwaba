// What must be produced for the current state of main? Output in GITHUB_OUTPUT format (key=value).
import { parseArgs } from 'node:util';

import { imageRepository, lastCommitTouching, latestManifest, plan } from './lib.mjs';

const { values } = parseArgs({ options: { dir: { type: 'string', default: 'deploy/manifests' } } });

const previous = latestManifest(values.dir);
const serverRevision = lastCommitTouching('server');
const clientRevision = lastCommitTouching('client');
// Set by GitHub Actions; the fallback is the repository owner, for local runs
const owner = process.env.GITHUB_REPOSITORY_OWNER || 'tres7';
const repositories = { server: imageRepository(owner, 'server'), client: imageRepository(owner, 'client') };
const { buildServer, buildClient, changed } = plan({ previous, serverRevision, clientRevision, repositories });

console.log(`changed=${changed}`);
console.log(`build_server=${buildServer}`);
console.log(`build_client=${buildClient}`);
console.log(`server_revision=${serverRevision}`);
console.log(`client_revision=${clientRevision}`);
console.log(`previous_version=${previous?.data.manifestVersion ?? 0}`);
