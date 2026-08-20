// @ts-nocheck — pi loads this file directly; the dotfiles repo has no Node TS workspace.
import { createHash, randomUUID } from "node:crypto";
import { homedir } from "node:os";
import { basename, join } from "node:path";
import { mkdir, open, readFile, rename, rm } from "node:fs/promises";

const root =
	process.env.AGENT_OBSERVABILITY_DIR ??
	join(homedir(), ".local/share/agent-observability");
const eventsDir = join(root, "events");
const liveDir = join(root, "live");
let writeQueue = Promise.resolve();

function skillFromPath(path: unknown): string | undefined {
	if (typeof path !== "string") return undefined;
	const match = path.match(/(?:^|[\\/])([^\\/]+)[\\/]SKILL\.md$/i);
	return match?.[1];
}

async function persist(rawEvent: Record<string, unknown>): Promise<void> {
	const event = { ...rawEvent, schema_version: 2, ts: new Date().toISOString() };
	if (typeof event.cwd === "string") event.cwd = basename(event.cwd) || "?";
	const skillPath = event.skill_path;
	delete event.skill_path;
	if (typeof skillPath === "string") {
		try {
			event.skill_version = `sha256:${createHash("sha256")
				.update(await readFile(skillPath))
				.digest("hex")}`;
		} catch {
			// A missing skill file must not affect the agent.
		}
	}

	await Promise.all([
		mkdir(eventsDir, { recursive: true }),
		mkdir(liveDir, { recursive: true }),
	]);
	const journal = await open(
		join(eventsDir, `${event.ts.slice(0, 10)}.jsonl`),
		"a",
	);
	try {
		await journal.appendFile(`${JSON.stringify(event)}\n`);
		await journal.sync();
	} finally {
		await journal.close();
	}

	const liveKey = createHash("sha256")
		.update(`${event.agent}\0${event.session_id}`)
		.digest("hex")
		.slice(0, 24);
	const livePath = join(liveDir, `${liveKey}.json`);
	if (event.event === "session_ended") {
		await rm(livePath, { force: true });
		return;
	}

	let live: Record<string, unknown> = {};
	try {
		live = JSON.parse(await readFile(livePath, "utf8"));
	} catch {
		// New or interrupted sessions have no prior live state.
	}
	if (["session_started", "agent_started"].includes(String(event.event)))
		live.skills = [];
	if (event.event === "skill_activated" && typeof event.skill === "string") {
		const skills = Array.isArray(live.skills)
			? live.skills.filter((skill): skill is string => typeof skill === "string")
			: [];
		if (!skills.includes(event.skill)) skills.push(event.skill);
		live.skills = skills;
	}
	for (const key of ["agent", "session_id", "cwd", "model", "state", "ts"])
		if (event[key] !== undefined) live[key] = event[key];
	live.last_event = event.event;

	const tempPath = join(liveDir, `.state-${process.pid}-${randomUUID()}`);
	const temp = await open(tempPath, "w");
	try {
		await temp.writeFile(JSON.stringify(live));
		await temp.sync();
	} finally {
		await temp.close();
	}
	try {
		await rename(tempPath, livePath);
	} finally {
		await rm(tempPath, { force: true });
	}
}

function record(event: Record<string, unknown>, ctx: any): Promise<void> {
	const sessionId = ctx?.sessionManager?.getSessionId?.();
	const model = ctx?.model ? `${ctx.model.provider}/${ctx.model.id}` : undefined;
	const payload = {
		agent: "pi",
		session_id: sessionId ?? `pid-${process.pid}`,
		cwd: ctx?.cwd ?? process.cwd(),
		...(model ? { model } : {}),
		...event,
	};
	writeQueue = writeQueue.then(() => persist(payload)).catch(() => {});
	return writeQueue;
}

function verificationKind(toolName: string, args: any): string | undefined {
	if (["lsp_diagnostics", "lens_diagnostics"].includes(toolName))
		return "diagnostics";
	const command = typeof args?.command === "string" ? args.command : "";
	if (
		/(?:^|\s)(?:pytest|go test|cargo test|npm test|pnpm test|yarn test)(?:\s|$)/i.test(
			command,
		)
	)
		return "test";
	if (/(?:^|\s)(?:nix build|nix flake check)(?:\s|$)/i.test(command))
		return "build";
	return undefined;
}

export default function (pi: any) {
	const verificationCalls = new Map<string, string>();
	const pendingSkills = new Set<string>();
	pi.on("session_start", async (_event, ctx) => {
		await record({ event: "session_started", state: "idle" }, ctx);
	});

	pi.on("agent_start", async (_event, ctx) => {
		await record({ event: "agent_started", state: "working" }, ctx);
		for (const skill of pendingSkills) {
			await record(
				{ event: "skill_activated", skill, invocation: "explicit" },
				ctx,
			);
		}
		pendingSkills.clear();
	});

	pi.on("tool_execution_start", async (event, ctx) => {
		const args = (event as any).args;
		const path = args?.path;
		const skill = skillFromPath(path);
		const verification = verificationKind(event.toolName, args);
		if (verification) verificationCalls.set(event.toolCallId, verification);
		await record(
			skill
				? {
						event: "skill_activated",
						skill,
						skill_path: path,
						invocation: "read",
					}
				: verification
					? {
							event: "verification_started",
							tool: event.toolName,
							verification,
						}
					: { event: "tool_started", tool: event.toolName },
			ctx,
		);
	});

	pi.on("tool_execution_end", async (event, ctx) => {
		const verification = verificationCalls.get(event.toolCallId);
		verificationCalls.delete(event.toolCallId);
		const result = (event as any).result;
		const details = result?.details ?? {};
		const listedErrors = Array.isArray(details.diagnostics)
			? details.diagnostics.filter((item: any) =>
					[1, "error", "Error"].includes(item?.severity),
				).length
			: 0;
		const diagnosticCount = Math.max(
			Number(details.totalBlocking) || 0,
			Number(details.totalErrors) || 0,
			listedErrors,
			details.severity === "error" ? Number(details.totalDiagnostics) || 0 : 0,
		);
		const warningCount = Number(details.totalWarnings) || 0;
		const diagnosticFailure =
			verification === "diagnostics" &&
			(diagnosticCount > 0 || details.unconfirmed || details.timedOut);
		await record(
			verification
				? {
						event: "verification_finished",
						tool: event.toolName,
						verification,
						status: event.isError || diagnosticFailure ? "failed" : "passed",
						...(verification === "diagnostics"
							? {
									diagnostics: diagnosticCount,
									warnings: warningCount,
									unconfirmed: Boolean(details.unconfirmed),
								}
							: {}),
					}
				: {
						event: "tool_finished",
						tool: event.toolName,
						status: event.isError ? "failed" : "passed",
					},
			ctx,
		);
	});

	pi.on("input", (event) => {
		const match = event.text.match(/(?:^|\s)\/skill:([a-z0-9][a-z0-9-]*)/i);
		if (match) pendingSkills.add(match[1].toLowerCase());
	});

	pi.on("agent_settled", async (_event, ctx) => {
		await record({ event: "agent_end", state: "idle" }, ctx);
	});

	pi.on("session_shutdown", async (_event, ctx) => {
		await record({ event: "session_ended", state: "idle" }, ctx);
	});
}
