// 날짜 포맷, id 생성 등 공용 유틸
const Utils = (() => {
  const DAYS = ['일', '월', '화', '수', '목', '금', '토'];

  const pad = (n) => String(n).padStart(2, '0');

  // 로컬 시간대 기준 'YYYY-MM-DD' (UTC를 쓰면 자정 근처에서 날짜가 어긋남)
  function toDateKey(date = new Date()) {
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
  }

  function formatKoreanDate(date = new Date()) {
    return `${date.getFullYear()}년 ${date.getMonth() + 1}월 ${date.getDate()}일 (${DAYS[date.getDay()]})`;
  }

  function createId() {
    if (window.crypto && typeof crypto.randomUUID === 'function') return crypto.randomUUID();
    return Date.now().toString(36) + Math.random().toString(36).slice(2);
  }

  return { toDateKey, formatKoreanDate, createId };
})();
