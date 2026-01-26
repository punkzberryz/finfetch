import { formatPercent, formatPrice } from "../lib/digest-format";
import type { DailyDigest } from "../lib/digest-types";

type DailyDigestViewProps = {
	digest: DailyDigest;
};

export default function DailyDigestView({ digest }: DailyDigestViewProps) {
	const snapshot = digest.market_snapshot;

	return (
		<div className="space-y-10">
			<section className="rounded-2xl border border-white/10 bg-white/5 p-6 shadow-[0_0_40px_-20px_rgba(15,23,42,0.8)]">
				<h2 className="text-xl font-semibold text-white">Market Snapshot</h2>
				{snapshot?.note ? (
					<p className="mt-3 text-sm text-slate-300">{snapshot.note}</p>
				) : (
					<div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
						<div className="rounded-xl border border-white/10 bg-slate-900/60 p-4">
							<p className="text-xs uppercase tracking-[0.2em] text-slate-400">
								Breadth
							</p>
							<p className="mt-2 text-2xl font-semibold text-white">
								{snapshot.breadth?.up ?? 0} up / {snapshot.breadth?.down ?? 0}{" "}
								down
							</p>
						</div>
						<div className="rounded-xl border border-white/10 bg-slate-900/60 p-4">
							<p className="text-xs uppercase tracking-[0.2em] text-slate-400">
								Average Change
							</p>
							<p className="mt-2 text-2xl font-semibold text-white">
								{formatPercent(snapshot.average_change)}
							</p>
						</div>
						<div className="rounded-xl border border-white/10 bg-slate-900/60 p-4">
							<p className="text-xs uppercase tracking-[0.2em] text-slate-400">
								Best Performer
							</p>
							<p className="mt-2 text-2xl font-semibold text-white">
								{snapshot.best?.ticker ?? "N/A"}{" "}
								<span className="text-sm text-emerald-300">
									{formatPercent(snapshot.best?.change)}
								</span>
							</p>
						</div>
						<div className="rounded-xl border border-white/10 bg-slate-900/60 p-4">
							<p className="text-xs uppercase tracking-[0.2em] text-slate-400">
								Worst Performer
							</p>
							<p className="mt-2 text-2xl font-semibold text-white">
								{snapshot.worst?.ticker ?? "N/A"}{" "}
								<span className="text-sm text-rose-300">
									{formatPercent(snapshot.worst?.change)}
								</span>
							</p>
						</div>
					</div>
				)}
			</section>

			<section className="grid gap-6 lg:grid-cols-[1.2fr_1fr]">
				<div className="rounded-2xl border border-white/10 bg-white/5 p-6">
					<h2 className="text-xl font-semibold text-white">Sector Rotation</h2>
					{digest.sector_rotation.length > 0 ? (
						<div className="mt-4 space-y-3">
							{digest.sector_rotation.map((sector) => (
								<div
									key={sector.sector}
									className="flex items-center justify-between text-sm text-slate-300"
								>
									<span>{sector.sector}</span>
									<span className="font-semibold text-white">
										{formatPercent(sector.average_change)}
									</span>
								</div>
							))}
						</div>
					) : (
						<p className="mt-4 text-sm text-slate-400">
							Sector data not available yet.
						</p>
					)}
				</div>

				<div className="rounded-2xl border border-white/10 bg-white/5 p-6">
					<h2 className="text-xl font-semibold text-white">Top Themes</h2>
					{digest.top_themes.length > 0 ? (
						<div className="mt-4 flex flex-wrap gap-2">
							{digest.top_themes.map((theme) => (
								<span
									key={theme.theme}
									className="rounded-full border border-white/10 bg-slate-900/60 px-3 py-1 text-xs font-semibold text-slate-200"
								>
									{theme.theme}{" "}
									<span className="text-slate-400">({theme.count})</span>
								</span>
							))}
						</div>
					) : (
						<p className="mt-4 text-sm text-slate-400">
							No headline themes available.
						</p>
					)}
				</div>
			</section>

			{digest.include_market_news && (
				<section className="rounded-2xl border border-white/10 bg-white/5 p-6">
					<h2 className="text-xl font-semibold text-white">Market News</h2>
					{digest.market_news.length > 0 ? (
						<div className="mt-4 space-y-3 text-sm text-slate-300">
							{digest.market_news.map((item) => (
								<a
									key={`${item.title}-${item.url}`}
									href={item.url}
									target="_blank"
									rel="noreferrer"
									className="block rounded-lg border border-white/10 bg-slate-900/60 p-3 transition hover:border-cyan-400/60 hover:text-white"
								>
									<div className="flex items-center justify-between gap-4">
										<span className="font-semibold text-white">
											{item.title}
										</span>
										<span className="text-xs uppercase tracking-[0.2em] text-slate-400">
											{item.source}
										</span>
									</div>
									<p className="mt-1 text-xs text-slate-400">
										{item.published_at}
									</p>
								</a>
							))}
						</div>
					) : (
						<p className="mt-4 text-sm text-slate-400">
							No cached market news for this digest.
						</p>
					)}
				</section>
			)}

			<section className="space-y-6">
				<div className="flex flex-col gap-2">
					<h2 className="text-xl font-semibold text-white">
						Ticker Highlights
					</h2>
					<p className="text-sm text-slate-400">
						Key moves and headlines for {digest.tickers.length} tracked names.
					</p>
				</div>
				<div className="grid gap-6 lg:grid-cols-2">
					{digest.ticker_highlights.map((ticker) => (
						<article
							key={ticker.ticker}
							className="rounded-2xl border border-white/10 bg-white/5 p-6"
						>
							<div className="flex items-start justify-between gap-4">
								<div>
									<h3 className="text-lg font-semibold text-white">
										{ticker.ticker}
									</h3>
									<p className="text-sm text-slate-400">{ticker.name}</p>
									<p className="text-xs text-slate-500">
										{ticker.sector} • {ticker.industry}
									</p>
								</div>
								<div className="text-right text-sm text-slate-300">
									<p className="font-semibold text-white">
										{formatPercent(ticker.change)}
									</p>
									<p className="text-xs text-slate-500">
										{formatPrice(ticker.start_price)} →{" "}
										{formatPrice(ticker.end_price)}
									</p>
								</div>
							</div>

							<div className="mt-4 rounded-xl border border-white/10 bg-slate-900/60 p-3 text-sm text-slate-300">
								<span className="text-xs uppercase tracking-[0.2em] text-slate-400">
									Sentiment
								</span>
								<p className="mt-1 font-semibold text-white">
									{ticker.sentiment.label}{" "}
									<span className="text-xs text-slate-400">
										({ticker.sentiment.source})
									</span>
								</p>
							</div>

							<div className="mt-4 space-y-2">
								<p className="text-xs uppercase tracking-[0.2em] text-slate-400">
									Headlines
								</p>
								{ticker.headlines.length > 0 ? (
									ticker.headlines.map((headline) => (
										<a
											key={`${ticker.ticker}-${headline.title}`}
											href={headline.url}
											target="_blank"
											rel="noreferrer"
											className="block rounded-lg border border-white/10 bg-slate-900/60 p-3 text-sm text-slate-200 transition hover:border-cyan-400/60"
										>
											<div className="flex items-center justify-between gap-3">
												<span className="font-semibold text-white">
													{headline.title}
												</span>
												<span className="text-xs uppercase tracking-[0.2em] text-slate-400">
													{headline.source}
												</span>
											</div>
											<p className="mt-1 text-xs text-slate-500">
												{headline.published_at}
											</p>
										</a>
									))
								) : (
									<p className="text-sm text-slate-500">
										No ticker headlines available.
									</p>
								)}
							</div>

							<div className="mt-4 space-y-2">
								<p className="text-xs uppercase tracking-[0.2em] text-slate-400">
									Risks / Catalysts
								</p>
								{ticker.risks_catalysts.length > 0 ? (
									<div className="flex flex-wrap gap-2">
										{ticker.risks_catalysts.map((item, index) => (
											<span
												key={`${ticker.ticker}-${item.label}-${index}`}
												className="rounded-full border border-white/10 bg-slate-900/60 px-3 py-1 text-xs text-slate-200"
											>
												{item.label}: {item.title}
											</span>
										))}
									</div>
								) : (
									<p className="text-sm text-slate-500">No signals yet.</p>
								)}
							</div>
						</article>
					))}
				</div>
			</section>
		</div>
	);
}
