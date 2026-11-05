document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-rc]').forEach((root) => {
    const track = root.querySelector('.rc-track');
    const prev = root.querySelector('.rc-prev');
    const next = root.querySelector('.rc-next');
    if (!track || !prev || !next) return;

    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    const cardStep = () => {
      const card = track.querySelector('.rc-card');
      if (!card) return track.clientWidth;
      const gap = parseFloat(getComputedStyle(track).columnGap) || 0;
      return card.getBoundingClientRect().width + gap;
    };

    const updateButtons = () => {
      const max = track.scrollWidth - track.clientWidth - 2;
      prev.disabled = track.scrollLeft <= 2;
      next.disabled = track.scrollLeft >= max;
    };

    const go = (direction) => {
      const step = cardStep();
      const visible = Math.max(1, Math.floor(track.clientWidth / step));
      track.scrollBy({ left: direction * step * visible, behavior: reduced ? 'auto' : 'smooth' });
    };

    prev.addEventListener('click', () => go(-1));
    next.addEventListener('click', () => go(1));
    track.addEventListener('scroll', () => window.requestAnimationFrame(updateButtons), { passive: true });
    window.addEventListener('resize', updateButtons);
    updateButtons();
  });
});