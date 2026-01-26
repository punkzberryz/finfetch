import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { createServerFn } from "@tanstack/react-start";
import type { DailyDigest } from "./digest-types";

type LatestDigestResult =
	| {
			found: false;
	  }
	| {
			found: true;
			date: string;
			path: string;
			digest: DailyDigest;
	  };

const DAILY_DIGEST_RE = /^daily_(\d{4}-\d{2}-\d{2})\.json$/;

function findRepoRoot() {
	let dir = process.cwd();
	for (let i = 0; i < 6; i += 1) {
		const hasAgents = fs.existsSync(path.join(dir, "AGENTS.md"));
		const hasExports = fs.existsSync(path.join(dir, "exports"));
		if (hasAgents && hasExports) {
			return dir;
		}
		const parent = path.dirname(dir);
		if (parent === dir) {
			break;
		}
		dir = parent;
	}
	return process.cwd();
}

async function readLatestDailyDigest(): Promise<LatestDigestResult> {
	const repoRoot = findRepoRoot();
	const digestsDir = path.join(repoRoot, "exports", "digests");
	let entries: string[] = [];
	try {
		entries = await fs.promises.readdir(digestsDir);
	} catch {
		return { found: false };
	}

	const candidates = entries
		.map((entry) => {
			const match = entry.match(DAILY_DIGEST_RE);
			if (!match) return null;
			return { entry, date: match[1] };
		})
		.filter((entry): entry is { entry: string; date: string } =>
			Boolean(entry),
		);

	if (candidates.length === 0) {
		return { found: false };
	}

	candidates.sort((a, b) => a.date.localeCompare(b.date));
	const latest = candidates[candidates.length - 1];
	const filePath = path.join(digestsDir, latest.entry);
	const raw = await fs.promises.readFile(filePath, "utf-8");
	const digest = JSON.parse(raw) as DailyDigest;

	return {
		found: true,
		date: latest.date,
		path: path.join("exports", "digests", latest.entry),
		digest,
	};
}

function formatToday() {
	const now = new Date();
	const year = now.getUTCFullYear();
	const month = `${now.getUTCMonth() + 1}`.padStart(2, "0");
	const day = `${now.getUTCDate()}`.padStart(2, "0");
	return `${year}-${month}-${day}`;
}

async function runFinfetchDaily(date: string) {
	const repoRoot = findRepoRoot();
	const binPath = path.join(repoRoot, "bin", "finfetch");
	const args = [
		"digest",
		"--type",
		"daily",
		"--date",
		date,
		"--out",
		"./exports",
		"--workers",
		"4",
	];

	return new Promise<{
		stdout: string;
		stderr: string;
		exitCode: number;
	}>((resolve, reject) => {
		const proc = spawn(binPath, args, {
			cwd: repoRoot,
			env: process.env,
		});

		let stdout = "";
		let stderr = "";

		proc.stdout.on("data", (chunk) => {
			stdout += chunk.toString();
		});

		proc.stderr.on("data", (chunk) => {
			stderr += chunk.toString();
		});

		proc.on("error", (err) => reject(err));
		proc.on("close", (code) =>
			resolve({ stdout, stderr, exitCode: code ?? 0 }),
		);
	});
}

function safeParseJson(text: string) {
	try {
		return JSON.parse(text);
	} catch {
		return {
			ok: false,
			error: {
				type: "UnknownError",
				message: "Invalid JSON output from finfetch CLI.",
				details: {},
			},
			meta: { version: 1 },
		};
	}
}

export const getLatestDailyDigest = createServerFn({
	method: "GET",
}).handler(async () => {
	return await readLatestDailyDigest();
});

export const runDailyDigest = createServerFn({ method: "POST" })
	.inputValidator((data: { date?: string }) => data)
	.handler(async ({ data }) => {
		const date = data?.date ?? formatToday();
		const result = await runFinfetchDaily(date);
		const payload = safeParseJson(result.stdout);

		return {
			date,
			ok: Boolean(payload?.ok),
			payload,
		};
	});
