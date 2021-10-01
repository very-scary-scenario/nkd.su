document.addEventListener('DOMContentLoaded', function() {
  document.querySelectorAll('.messages').forEach(function(messageElement) {
    messageElement.addEventListener('click', function() {
      messageElement.classList.add('dismissed');
    });
  });
});
