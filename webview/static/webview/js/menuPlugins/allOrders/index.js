window.allOrderInterface = function () {
  // quelle vue est active et l'enreguistrer dans le dom(header dans le body)
  const idVues = ['#page-commandes', '#tables', '#commandes-table']
  let idCurrentVue = ''
  for (let i = 0; i < idVues.length; i++) {
    const target = idVues[i];
    const show = document.querySelector(target).style.display
    if (show !== 'none') {
      idCurrentVue = target
      break
    }
  }

  // enregistrer l'info "idCurrentVue" dans le header
  document.querySelector('header').setAttribute('current-vue', idCurrentVue)

  // enregistrer l'info "modeGerant" dans le header
  document.querySelector('header').setAttribute('modeGerant', glob.modeGerant)

  // indexer le header et le faire disparaitre
  document.querySelector('header').id = "header-laboutik"
  document.querySelector('#header-laboutik').style.display = 'none'
  
  // hide menu
  document.querySelector('#menu-burger-conteneur').classList.toggle('burger-show')

  // bascule l'affichage et l'éffacement de pages
  sys.effacerElements(['#page-commandes', '#tables', '#commandes-table'])
  sys.afficherElements(['#service-commandes,block'])

  // <button hx-get="allOrders/null" hx-target="#service-commandes">clique</button>
  // htmx.ajax('GET', '/htmx/sales', '#service-commandes')
  htmx.ajax('GET', `/htmx/sales?oldest_first=false&manager_mode_enabled=${glob.modeGerant}`, '#service-commandes')
}

window.allOrderReturnOriginalInterface = function () {
  document.querySelector('#header-laboutik').style.display = 'block'
  sys.effacerElements(['#service-commandes,block'])
  const idCurrentVue = document.querySelector('header').getAttribute('current-vue')
  sys.afficherElements([`${idCurrentVue},block`])
}

export const menu = {
  func: "allOrderInterface",
  icon: "fas fa-concierge-bell", // font awesome 5
  i8nIndex: "allOrders,uppercase"
}
