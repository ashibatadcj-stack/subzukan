/* =====================================================
   サブスク図鑑 共通スクリプト
   - モバイルTOC折り畳み
   - ランキングタブ切替
   - スティッキーCTA表示制御
   ===================================================== */

/* ===== モバイルTOC 折り畳み（既存） ===== */
(function () {
  var title = document.querySelector('.toc-box-title');
  var list = document.querySelector('.toc-list');
  if (!title || !list) return;

  function isMobile() { return window.innerWidth <= 768; }

  function initToc() {
    if (isMobile()) {
      list.classList.remove('open');
    } else {
      list.classList.add('open');
    }
  }

  title.addEventListener('click', function () {
    list.classList.toggle('open');
    title.classList.toggle('open');
  });

  initToc();
  window.addEventListener('resize', initToc);
})();

/* ===== ランキングタブ切替 ===== */
(function () {
  var btns = document.querySelectorAll('[data-rank-tab]');
  var panels = document.querySelectorAll('[data-rank-panel]');
  if (!btns.length) return;

  btns.forEach(function (btn) {
    btn.addEventListener('click', function () {
      var target = btn.getAttribute('data-rank-tab');
      btns.forEach(function (b) { b.classList.toggle('active', b === btn); });
      panels.forEach(function (p) {
        p.classList.toggle('active', p.getAttribute('data-rank-panel') === target);
      });
    });
  });
})();

/* ===== スティッキーCTA 表示制御 ===== */
(function () {
  var sticky = document.getElementById('stickyCta');
  if (!sticky) return;
  var hero = document.querySelector('.hero');
  var quiz = document.getElementById('quiz');

  function shouldShow() {
    // ヒーローを抜けたら表示、クイズに到達したら非表示
    if (!hero || !quiz) return false;
    var heroBottom = hero.getBoundingClientRect().bottom;
    var quizTop = quiz.getBoundingClientRect().top;
    var quizBottom = quiz.getBoundingClientRect().bottom;
    var winH = window.innerHeight;

    // ヒーローがまだ見えている（heroBottom > 0）→ 非表示
    if (heroBottom > 0) return false;
    // クイズが画面内に大きく見えている → 非表示
    if (quizTop < winH * 0.6 && quizBottom > winH * 0.2) return false;
    return true;
  }

  function update() {
    if (shouldShow()) sticky.removeAttribute('hidden');
    else sticky.setAttribute('hidden', '');
  }

  window.addEventListener('scroll', update, { passive: true });
  window.addEventListener('resize', update);
  update();
})();
