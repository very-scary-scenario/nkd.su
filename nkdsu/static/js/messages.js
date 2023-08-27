document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.messages.dismissable').forEach(messageElement => {
    messageElement.addEventListener('click', () => {
      messageElement.classList.add('dismissed')
    })
  })
})
