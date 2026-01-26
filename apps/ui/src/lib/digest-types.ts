export type DigestMarketSnapshot = {
	breadth?: {
		up: number;
		down: number;
	};
	average_change?: number;
	best?: {
		ticker: string;
		change: number | null;
	};
	worst?: {
		ticker: string;
		change: number | null;
	};
	note?: string;
};

export type DigestTheme = {
	theme: string;
	count: number;
};

export type DigestMarketNewsItem = {
	title: string;
	source: string;
	url: string;
	published_at: string;
	provider: string;
};

export type DigestSentiment = {
	source: string;
	label: string;
	score: number | null;
};

export type DigestHeadline = {
	title: string;
	source: string;
	url: string;
	published_at: string;
	provider: string;
};

export type DigestRiskCatalyst = {
	label: string;
	title: string;
};

export type DigestTickerHighlight = {
	ticker: string;
	name: string;
	sector: string;
	industry: string;
	change: number | null;
	start_price: number | null;
	end_price: number | null;
	sentiment: DigestSentiment;
	headlines: DigestHeadline[];
	risks_catalysts: DigestRiskCatalyst[];
};

export type DailyDigest = {
	type: "daily";
	date: string;
	title: string;
	tickers: string[];
	include_market_news: boolean;
	market_snapshot: DigestMarketSnapshot;
	sector_rotation: { sector: string; average_change: number }[];
	top_themes: DigestTheme[];
	market_news: DigestMarketNewsItem[];
	ticker_highlights: DigestTickerHighlight[];
	news_links: {
		scope: string;
		ticker: string;
		source: string;
		title: string;
		url: string;
		published_at: string;
		provider: string;
	}[];
};
