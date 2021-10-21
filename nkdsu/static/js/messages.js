document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.messages').forEach(messageElement => {
    messageElement.addEventListener('click', () => {
      messageElement.classList.add('dismissed')
    })
  })
})
