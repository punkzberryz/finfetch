import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { Loader2, RefreshCw, Sparkles } from "lucide-react";
import { toast } from "react-toastify";
import DailyDigestView from "../components/DailyDigestView";
import {
	getLatestDailyDigest,
	runDailyDigest,
} from "../lib/daily-digest.server";
import { formatDateLabel } from "../lib/digest-format";

export const Route = createFileRoute("/")({ component: App });

function App() {
	const queryClient = useQueryClient();
	const digestQuery = useQuery({
		queryKey: ["daily-digest-latest"],
		queryFn: () => getLatestDailyDigest(),
		refetchOnWindowFocus: false,
	});

	const generateMutation = useMutation({
		mutationFn: () => runDailyDigest({ data: {} }),
		onSuccess: (data) => {
			if (data.ok) {
				toast.success("Daily digest generated successfully!");
				queryClient.invalidateQueries({ queryKey: ["daily-digest-latest"] });
			} else {
				toast.error(
					`Failed to generate digest: ${data.payload?.error?.message || "Unknown error"}`,
				);
			}
		},
		onError: (error) => {
			toast.error(`Error: ${error.message}`);
		},
	});

	const latestDigest = digestQuery.data?.found ? digestQuery.data.digest : null;
	const latestDate = digestQuery.data?.found ? digestQuery.data.date : null;

	return (
		<div className="min-h-screen bg-[#0b0f14] text-white">
			<div className="relative overflow-hidden border-b border-white/5">
				<div className="absolute inset-0">
					<div className="absolute -left-32 top-0 h-72 w-72 rounded-full bg-cyan-500/20 blur-[140px]" />
					<div className="absolute right-0 top-10 h-96 w-96 rounded-full bg-emerald-500/10 blur-[160px]" />
					<div className="absolute bottom-0 left-1/2 h-80 w-80 -translate-x-1/2 rounded-full bg-indigo-500/10 blur-[150px]" />
				</div>
				<section className="relative mx-auto flex w-full max-w-6xl flex-col gap-10 px-6 py-16 lg:flex-row lg:items-center">
					<div className="flex-1 space-y-6">
						<div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-xs uppercase tracking-[0.3em] text-slate-300">
							<Sparkles className="h-4 w-4 text-cyan-300" />
							Finfetch Daily
						</div>
						<div className="space-y-4">
							<h1 className="text-4xl font-semibold leading-tight md:text-6xl">
								Daily Market Digest
							</h1>
							<p className="max-w-xl text-base text-slate-300 md:text-lg">
								Browse the latest daily digest directly from your local exports.
								Generate a fresh run when you want the newest headlines.
							</p>
						</div>
						<div className="flex flex-wrap gap-4">
							<button
								type="button"
								onClick={() => generateMutation.mutate()}
								disabled={generateMutation.isPending}
								className="inline-flex items-center gap-2 rounded-full bg-cyan-400 px-6 py-3 text-sm font-semibold text-slate-900 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-60"
							>
								{generateMutation.isPending ? (
									<>
										<Loader2 className="h-4 w-4 animate-spin" />
										Generating...
									</>
								) : (
									"Generate Daily Digest"
								)}
							</button>
							<button
								type="button"
								onClick={() => digestQuery.refetch()}
								className="inline-flex items-center gap-2 rounded-full border border-white/15 px-6 py-3 text-sm font-semibold text-white transition hover:border-cyan-300/60 hover:text-cyan-200"
							>
								<RefreshCw className="h-4 w-4" />
								Refresh Latest
							</button>
						</div>
						<div className="text-xs text-slate-500">
							Output folder:{" "}
							<span className="text-slate-300">exports/digests</span>
						</div>
					</div>

					<div className="w-full max-w-md rounded-3xl border border-white/10 bg-white/5 p-6 shadow-[0_30px_120px_-60px_rgba(56,189,248,0.6)]">
						<h2 className="text-xs uppercase tracking-[0.3em] text-slate-400">
							Latest Digest
						</h2>
						<div className="mt-3 space-y-2">
							<p className="text-2xl font-semibold text-white">
								{latestDate ? formatDateLabel(latestDate) : "No digest yet"}
							</p>
							<p className="text-sm text-slate-400">
								{latestDigest
									? `${latestDigest.tickers.length} tickers • ${latestDigest.market_news.length} market headlines`
									: "Generate a digest to populate this view."}
							</p>
							{digestQuery.isFetching && (
								<p className="text-xs text-cyan-200">Refreshing digest data…</p>
							)}
						</div>
					</div>
				</section>
			</div>

			<main className="mx-auto w-full max-w-6xl px-6 py-12">
				{digestQuery.isLoading ? (
					<div className="rounded-2xl border border-white/10 bg-white/5 p-8 text-sm text-slate-400">
						Loading the latest digest...
					</div>
				) : latestDigest ? (
					<DailyDigestView digest={latestDigest} />
				) : (
					<div className="rounded-2xl border border-white/10 bg-white/5 p-8 text-sm text-slate-400">
						No daily digest JSON found in <strong>exports/digests</strong>.
						Generate a new digest to get started.
					</div>
				)}
			</main>
		</div>
	);
}
