export function formatDate(iso: string, withTime = false) {
  return new Intl.DateTimeFormat("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    ...(withTime && { hour: "2-digit", minute: "2-digit" }),
    timeZone: "Asia/Seoul",
  }).format(new Date(iso));
}
