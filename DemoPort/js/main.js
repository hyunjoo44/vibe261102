// 모바일 메뉴 토글
const toggle = document.querySelector(".nav-toggle");
const menu = document.querySelector(".nav-menu");

toggle.addEventListener("click", () => {
  const open = menu.classList.toggle("open");
  toggle.setAttribute("aria-expanded", open);
  toggle.setAttribute("aria-label", open ? "메뉴 닫기" : "메뉴 열기");
});

menu.querySelectorAll("a").forEach((link) => {
  link.addEventListener("click", () => {
    menu.classList.remove("open");
    toggle.setAttribute("aria-expanded", "false");
    toggle.setAttribute("aria-label", "메뉴 열기");
  });
});

// 스크롤 시 헤더 테두리 표시
const header = document.querySelector(".site-header");
window.addEventListener("scroll", () => {
  header.classList.toggle("scrolled", window.scrollY > 10);
});

// 현재 섹션에 해당하는 메뉴 강조
const navLinks = document.querySelectorAll(".nav-menu a");
const sections = document.querySelectorAll("main section[id]");

const sectionObserver = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      navLinks.forEach((link) => {
        link.classList.toggle("active", link.getAttribute("href") === `#${entry.target.id}`);
      });
    });
  },
  { rootMargin: "-45% 0px -50% 0px" }
);
sections.forEach((section) => sectionObserver.observe(section));

// 스크롤 등장 애니메이션
const revealTargets = document.querySelectorAll(".section-title, .about-grid, .skill-card, .project-card, .contact-email");
const revealObserver = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("visible");
        revealObserver.unobserve(entry.target);
      }
    });
  },
  { threshold: 0.15 }
);
revealTargets.forEach((el) => {
  el.classList.add("reveal");
  revealObserver.observe(el);
});

// 프로젝트 필터
const filterButtons = document.querySelectorAll(".filter-btn");
const projects = document.querySelectorAll(".project-card");

filterButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    filterButtons.forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    const filter = btn.dataset.filter;
    projects.forEach((card) => {
      card.classList.toggle("hidden", filter !== "all" && card.dataset.category !== filter);
    });
  });
});

// 이메일 주소 복사
const copyBtn = document.querySelector(".copy-btn");
copyBtn.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(copyBtn.dataset.email);
    copyBtn.textContent = "복사되었습니다!";
  } catch {
    copyBtn.textContent = copyBtn.dataset.email;
  }
  setTimeout(() => (copyBtn.textContent = "이메일 주소 복사"), 2000);
});

// 푸터 연도
document.getElementById("year").textContent = new Date().getFullYear();
