import { execSync } from 'node:child_process';

interface GitDates {
  datePublished: string;
  dateModified: string;
}

const cache = new Map<string, GitDates>();

function gitLog(args: string): string {
  try {
    return execSync(`git log ${args}`, { encoding: 'utf8' }).trim();
  } catch {
    return '';
  }
}

export function getGitDates(filePath: string): GitDates {
  const cached = cache.get(filePath);
  if (cached) return cached;

  const escaped = filePath.replace(/"/g, '\\"');
  const firstLine = gitLog(
    `--diff-filter=A --follow --format=%aI -- "${escaped}"`
  )
    .split('\n')
    .filter(Boolean)
    .pop();
  const lastLine = gitLog(`-1 --format=%aI -- "${escaped}"`);

  const fallback = new Date().toISOString();
  const result: GitDates = {
    datePublished: firstLine || lastLine || fallback,
    dateModified: lastLine || firstLine || fallback,
  };
  cache.set(filePath, result);
  return result;
}
