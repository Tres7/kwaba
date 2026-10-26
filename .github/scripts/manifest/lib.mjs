// Deployment manifests: one file per deployable state of main (deploy/manifests).
import { execFileSync } from 'node:child_process';
import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

import Ajv from 'ajv/dist/2020.js';
import addFormats from 'ajv-formats';
import YAML from 'yaml';

const FILE_PATTERN = /^manifest-(\d{4,})-([a-f0-9]{7})\.yaml$/;

export function fileName(version, sourceRevision) {
  return `manifest-${String(version).padStart(4, '0')}-${sourceRevision.slice(0, 7)}.yaml`;
}

export function loadValidator(schemaPath) {
  const ajv = new Ajv({ allErrors: true, strict: true });
  addFormats(ajv);
  return ajv.compile(JSON.parse(readFileSync(schemaPath, 'utf8')));
}

/** Manifests of the folder, sorted by version number (the one in the file name). */
export function readManifests(dir) {
  return readdirSync(dir)
    .filter((file) => file.startsWith('manifest-'))
    .map((file) => {
      const match = FILE_PATTERN.exec(file);
      return {
        file,
        path: join(dir, file),
        nameVersion: match ? Number(match[1]) : null,
        nameRevision: match ? match[2] : null,
        data: YAML.parse(readFileSync(join(dir, file), 'utf8')),
      };
    })
    .sort((a, b) => (a.nameVersion ?? -1) - (b.nameVersion ?? -1));
}

export function latestManifest(dir) {
  return readManifests(dir).at(-1) ?? null;
}

/** Last commit that changes `path`: the revision of a service actually deployed. */
export function lastCommitTouching(path, cwd = '.') {
  return execFileSync('git', ['log', '-1', '--format=%H', '--', path], { cwd, encoding: 'utf8' }).trim();
}

export const SCHEMA_VERSION = 2;

/** Image repository of a service (GHCR requires lowercase). _main-push-image.yml pushes to the same name. */
export function imageRepository(owner, service) {
  return `ghcr.io/${owner.toLowerCase()}/kwaba-${service}`;
}

/**
 * Must a service be rebuilt? Yes if it changed, if the previous manifest had no image for it (v1), or if its image
 * is not in the expected repository (afristay-* → kwaba-* rename: both images switch at once).
 */
function needsImage(previousService, revision, repository) {
  return !previousService || previousService.kind !== 'image' || previousService.sourceRevision !== revision
    || (repository !== undefined && previousService.image.split('@')[0] !== repository);
}

/**
 * Compares the state of main with the latest manifest: an image is rebuilt only for a service that changed;
 * without any change, no manifest is created.
 */
export function plan({ previous, serverRevision, clientRevision, repositories = {} }) {
  const services = previous?.data.services;
  const buildServer = needsImage(services?.server, serverRevision, repositories.server);
  const buildClient = needsImage(services?.client, clientRevision, repositories.client);
  return { buildServer, buildClient, changed: buildServer || buildClient };
}

/** Service of the new manifest: the new image if it was built, otherwise the previous manifest's one. */
function service(name, { image, revision, previous }) {
  if (image) return { kind: 'image', sourceRevision: revision, image };
  const reused = previous?.data.services[name];
  if (!reused || reused.kind !== 'image') {
    throw new Error(`Aucune image ${name} : ni nouvelle image, ni image à reprendre du manifest précédent`);
  }
  if (reused.sourceRevision !== revision) {
    throw new Error(`Le ${name} a changé (${revision.slice(0, 7)}) : une nouvelle image est requise`);
  }
  return reused;
}

export function buildManifest({ previous, version, sourceRevision, createdAt, serverImage, serverRevision,
  clientImage, clientRevision }) {
  return {
    schemaVersion: SCHEMA_VERSION,
    manifestVersion: version,
    sourceRevision,
    createdAt,
    services: {
      server: service('server', { image: serverImage, revision: serverRevision, previous }),
      client: service('client', { image: clientImage, revision: clientRevision, previous }),
    },
  };
}

export function toYaml(manifest) {
  return YAML.stringify(manifest, { lineWidth: 0 });
}

/** Errors of the whole folder: schema, name/content consistency, strictly increasing versions. */
export function validateAll(dir, validate) {
  const errors = [];
  let previousVersion = 0;
  for (const manifest of readManifests(dir)) {
    const where = manifest.file;
    if (manifest.nameVersion === null) {
      errors.push(`${where} : nom attendu manifest-<version sur 4 chiffres>-<sha7>.yaml`);
      continue;
    }
    if (!validate(manifest.data)) {
      for (const e of validate.errors) errors.push(`${where} : ${e.instancePath || '/'} ${e.message}`);
      continue;
    }
    const { manifestVersion, sourceRevision } = manifest.data;
    if (manifestVersion !== manifest.nameVersion) {
      errors.push(`${where} : manifestVersion ${manifestVersion} ne correspond pas au nom du fichier`);
    }
    if (sourceRevision.slice(0, 7) !== manifest.nameRevision) {
      errors.push(`${where} : sourceRevision ${sourceRevision.slice(0, 7)} ne correspond pas au nom du fichier`);
    }
    if (manifestVersion <= previousVersion) {
      errors.push(`${where} : manifestVersion ${manifestVersion} doit être strictement supérieure à ${previousVersion}`);
    }
    previousVersion = Math.max(previousVersion, manifestVersion);
  }
  return errors;
}

/**
 * Manifest to deploy: the given file name, or the latest one when empty. Only a strict file name is accepted
 * (no path), and both services must be images: the result is passed to a remote shell on the VPS.
 */
export function deployTarget(dir, name = '') {
  const manifests = readManifests(dir);
  if (name && !FILE_PATTERN.test(name)) {
    throw new Error(`Nom de manifest invalide : « ${name} » (attendu : manifest-0008-2cf8427.yaml)`);
  }
  const manifest = name ? manifests.find((m) => m.file === name) : manifests.at(-1);
  if (!manifest) throw new Error(name ? `Manifest introuvable : ${name}` : `Aucun manifest dans ${dir}`);
  const images = {};
  for (const service of ['server', 'client']) {
    const entry = manifest.data.services?.[service];
    if (entry?.kind !== 'image' || !IMAGE_PATTERN.test(entry.image ?? '')) {
      throw new Error(`${manifest.file} : pas d'image ${service} par digest (manifest v1, non déployable sur le VPS)`);
    }
    images[service] = entry.image;
  }
  return { file: manifest.file, serverImage: images.server, clientImage: images.client };
}

const IMAGE_PATTERN = /^ghcr\.io\/[a-z0-9._/-]+@sha256:[a-f0-9]{64}$/;

/** Reads a dotted field ("services.server.image") of a manifest. */
export function field(manifest, path) {
  return path.split('.').reduce((value, key) => value?.[key], manifest.data);
}
