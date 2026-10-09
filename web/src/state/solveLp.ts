// LP solving for the build optimiser (state/optimiser.ts).
//
// The optimiser writes its integer programme as CPLEX LP text and hands it to an
// `LpSolver`. In the app that is HiGHS compiled to WebAssembly (the `highs` npm
// package — the same solver `scipy.optimize.milp` uses in the Python analysis, so
// the app and analysis/cost_effective_builds.py agree), run in a Web Worker
// (state/optimiser.worker.ts) because a solve blocks its thread. Tests call
// `highs` directly under Node through `solverFromHighs`.

/** Wall-clock cap per solve, in seconds. Typical solves take well under a second. */
export const OPTIMISER_TIME_LIMIT_S = 10;

export interface LpSolution {
  /** HiGHS model status, e.g. "Optimal", "Infeasible", "Time limit reached". */
  status: string;
  /** Primal value per column name; empty when the solver found no solution. */
  columns: Record<string, number>;
}

export type LpSolver = (lp: string) => Promise<LpSolution>;

/** The part of a loaded `highs` module the optimiser uses. */
export interface HighsLike {
  solve(problem: string, options?: Record<string, unknown>): {
    Status: string;
    /** Per column; infeasible results carry no `Primal`, so it is read defensively. */
    Columns?: Record<string, unknown>;
  };
}

/** Options for every solve: quiet, time-limited. */
export const HIGHS_OPTIONS = { output_flag: false, time_limit: OPTIMISER_TIME_LIMIT_S } as const;

/** One solve with a loaded HiGHS instance (worker and tests share this). */
export function solveWithHighs(highs: HighsLike, lp: string): LpSolution {
  const result = highs.solve(lp, HIGHS_OPTIONS);
  const columns: Record<string, number> = {};
  for (const [name, col] of Object.entries(result.Columns ?? {})) {
    const primal = (col as { Primal?: unknown } | null)?.Primal;
    if (typeof primal === "number" && Number.isFinite(primal)) columns[name] = primal;
  }
  return { status: result.Status, columns };
}

/** An `LpSolver` over an already loaded HiGHS instance (synchronous underneath). */
export function solverFromHighs(highs: HighsLike): LpSolver {
  return (lp) => Promise.resolve(solveWithHighs(highs, lp));
}

// --- the app's solver: one lazily started worker, requests matched by id ----------

type WorkerReply = { id: number; solution: LpSolution } | { id: number; error: string };

let worker: Worker | null = null;
let nextId = 0;
const pending = new Map<number, { resolve: (s: LpSolution) => void; reject: (e: Error) => void }>();

function failAll(message: string): void {
  for (const { reject } of pending.values()) reject(new Error(message));
  pending.clear();
  worker = null;
}

function startWorker(): Worker {
  const w = new Worker(new URL("./optimiser.worker.ts", import.meta.url), { type: "module" });
  w.onmessage = (event: MessageEvent<WorkerReply>) => {
    const reply = event.data;
    const request = pending.get(reply.id);
    if (!request) return;
    pending.delete(reply.id);
    if ("error" in reply) request.reject(new Error(reply.error));
    else request.resolve(reply.solution);
  };
  w.onerror = (event) => {
    failAll(`The optimiser could not start (${event.message || "worker error"}).`);
    w.terminate();
  };
  return w;
}

/** The app's `LpSolver`: HiGHS in a Web Worker, started on first use and kept for later solves. */
export const workerSolver: LpSolver = (lp) =>
  new Promise<LpSolution>((resolve, reject) => {
    worker ??= startWorker();
    const id = ++nextId;
    pending.set(id, { resolve, reject });
    worker.postMessage({ id, lp });
  });
