const motionButton = document.querySelector('#motion');
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
let paused = reducedMotion.matches;
function updateMotion() {
  document.body.classList.toggle('motion-paused', paused);
  motionButton.setAttribute('aria-pressed', String(paused));
  motionButton.textContent = paused ? '✦ glitter paused' : '✦ pause glitter';
}
updateMotion();
motionButton.addEventListener('click', () => { paused = !paused; updateMotion(); });
document.querySelector('#copy-link').addEventListener('click', async () => {
  const status = document.querySelector('#copy-status');
  try {
    await navigator.clipboard.writeText('https://buttholechopper.com/gayboy/');
    status.textContent = '♥ Link copied. Spread the tiny noises.';
  } catch {
    status.textContent = 'Copy this: https://buttholechopper.com/gayboy/';
  }
});
document.querySelector('#back-top').addEventListener('click', event => {
  event.preventDefault();
  window.scrollTo({top: 0, behavior: paused ? 'instant' : 'smooth'});
});
