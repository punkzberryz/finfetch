const dateFormatter = new Intl.DateTimeFormat("en-US", {
	month: "short",
	day: "2-digit",
	year: "numeric",
	timeZone: "UTC",
});

export function formatDateLabel(dateStr: string) {
	const date = new Date(`${dateStr}T00:00:00Z`);
	if (Number.isNaN(date.getTime())) {
		return dateStr;
	}
	return dateFormatter.format(date);
}

export function formatPercent(value: number | null | undefined) {
	if (value === null || value === undefined || Number.isNaN(value)) {
		return "N/A";
	}
	return `${value.toFixed(2)}%`;
}

export function formatPrice(value: number | null | undefined) {
	if (value === null || value === undefined || Number.isNaN(value)) {
		return "N/A";
	}
	return value.toFixed(2);
}
