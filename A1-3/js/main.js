// ============================================================================
// FitRoutine — main.js
// 네비게이션 토글, 칩 선택 UI, /api/generate 호출, 실패 처리(빈값/오류/타임아웃)
// ============================================================================

// --- 모바일 네비게이션 토글 -------------------------------------------------
const navToggle = document.getElementById('navToggle');
const navLinks = document.getElementById('navLinks');

navToggle.addEventListener('click', () => {
  const isOpen = navLinks.classList.toggle('is-open');
  navToggle.setAttribute('aria-expanded', String(isOpen));
});

navLinks.querySelectorAll('.nav__link').forEach((link) => {
  link.addEventListener('click', () => {
    navLinks.classList.remove('is-open');
    navToggle.setAttribute('aria-expanded', 'false');
  });
});

// --- 보너스: 마이크로 인터랙션 - 스크롤 리빌 (tip 카드) ----------------------
const revealEls = document.querySelectorAll('.reveal');

if ('IntersectionObserver' in window && revealEls.length) {
  const revealObserver = new IntersectionObserver(
    (entries, observer) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.2 }
  );
  revealEls.forEach((el) => revealObserver.observe(el));
} else {
  // IntersectionObserver 미지원 환경 대비: 즉시 표시
  revealEls.forEach((el) => el.classList.add('is-visible'));
}

// --- 칩(선택형 버튼) 그룹 처리 ----------------------------------------------
function setupChipGroup(groupId) {
  const group = document.getElementById(groupId);
  const chips = Array.from(group.querySelectorAll('.chip'));

  chips.forEach((chip) => {
    chip.addEventListener('click', () => {
      chips.forEach((c) => c.classList.remove('is-selected'));
      chip.classList.add('is-selected');
    });
  });

  return {
    getValue() {
      const selected = group.querySelector('.chip.is-selected');
      return selected ? selected.dataset.value : '';
    },
  };
}

const goalGroup = setupChipGroup('goalGroup');
const durationGroup = setupChipGroup('durationGroup');

// --- 폼 제출 & API 호출 -----------------------------------------------------
const form = document.getElementById('routineForm');
const submitBtn = document.getElementById('submitBtn');
const formMessage = document.getElementById('formMessage');
const resultBox = document.getElementById('result');
const resultTitle = document.getElementById('resultTitle');
const resultList = document.getElementById('resultList');

const REQUEST_TIMEOUT_MS = 15000;

form.addEventListener('submit', async (e) => {
  e.preventDefault();

  const goal = goalGroup.getValue();
  const duration = durationGroup.getValue();

  // 실패 처리 1: 빈 입력(필수값 누락) — API 호출 없이 즉시 안내
  if (!goal || !duration) {
    formMessage.textContent = '운동 목표와 시간을 모두 선택해주세요.';
    return;
  }

  formMessage.textContent = '';
  setLoading(true);
  resultBox.hidden = true;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const res = await fetch('/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ goal, duration }),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    const data = await res.json().catch(() => ({}));

    // 실패 처리 2: API 오류(4xx/5xx)
    if (!res.ok) {
      formMessage.textContent = data.error || '루틴 생성 중 문제가 발생했습니다. 잠시 후 다시 시도해주세요.';
      return;
    }

    renderRoutine(goal, duration, data.routine);
  } catch (err) {
    clearTimeout(timeoutId);

    // 실패 처리 3: 지연/타임아웃
    if (err.name === 'AbortError') {
      formMessage.textContent = '응답이 지연되고 있습니다. 잠시 후 다시 시도해주세요.';
    } else {
      formMessage.textContent = '네트워크 오류가 발생했습니다. 연결 상태를 확인해주세요.';
    }
  } finally {
    setLoading(false);
  }
});

function setLoading(isLoading) {
  submitBtn.disabled = isLoading;
  submitBtn.classList.toggle('is-loading', isLoading);
  submitBtn.querySelector('.btn__label').textContent = isLoading ? '생성 중...' : '루틴 생성하기';
}

function renderRoutine(goal, duration, routineText) {
  resultTitle.textContent = `${goal} · ${duration}분 루틴`;
  resultList.innerHTML = '';

  const lines = (routineText || '')
    .split('\n')
    .map((line) => line.replace(/^\d+[\.\)]\s*/, '').trim())
    .filter(Boolean);

  if (lines.length === 0) {
    const li = document.createElement('li');
    li.textContent = '루틴을 표시할 수 없습니다. 다시 시도해주세요.';
    resultList.appendChild(li);
  } else {
    lines.forEach((line, index) => {
      const li = document.createElement('li');
      li.textContent = line;
      li.style.setProperty('--i', index); // 마이크로 인터랙션: 순서대로 지연 등장
      resultList.appendChild(li);
    });
  }

  resultBox.hidden = false;
  resultBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}