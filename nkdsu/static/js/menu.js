function bindUserMenu() {
  const menu = document.getElementById('user-menu')

  document.addEventListener('click', e => {
    if (menu.open && !menu.contains(e.target)) {
      menu.open = false
    }
  })
}

document.addEventListener('DOMContentLoaded', bindUserMenu)
