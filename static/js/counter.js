let leftCounter = 0;
let rightCounter = 0;

const leftLabel = document.getElementById('leftCounter');
const rightLabel = document.getElementById('rightCounter');

function incrementLeft() {
  leftCounter += 1;
  leftLabel.textContent = leftCounter.toString();
  leftLabel.classList.add('highlight'); // Change from leftCounter to leftLabel
}

// Also, you'll want to remove the highlight after some time, like so:
leftLabel.addEventListener('transitionend', () => {
  leftLabel.classList.remove('highlight');
});

function incrementRight() {
  rightCounter += 1;
  rightLabel.textContent = rightCounter.toString();
  rightLabel.classList.add('highlight'); // Add this line for the right label
}

// And don't forget to remove the highlight for the right counter too:
rightLabel.addEventListener('transitionend', () => {
  rightLabel.classList.remove('highlight');
});
document.body.onkeydown = function(event) {
  // Use 'event.code' if you want to be more specific, like 'Space' for the spacebar
  if (event.key === 'Backspace') {
    incrementLeft();
  } else if (event.key === ' ') {
    incrementRight();
  }
};

// Focus the body element immediately to capture key events
document.body.focus();

// There's no direct equivalent of `focus_force` in web browsers, but
// you can try to keep the focus by calling `focus` periodically.
// Uncomment the following to attempt it, but note that it may not
// work consistently across all browsers due to different focus policies.

setInterval(() => {
  document.body.focus();
  window.focus();
}, 5000);