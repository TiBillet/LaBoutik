window.allOrderInterface = function () {
  // hide menu
  document.querySelector('#menu-burger-conteneur').classList.toggle('burger-show')

  // bascule l'affichage et l'éffacement de pages
  sys.effacerElements(['#page-commandes', '#tables', '#commandes-table'])
  sys.afficherElements(['#service-commandes,block'])

  // <button hx-get="allOrders/null" hx-target="#service-commandes">clique</button>
  // htmx.ajax('GET', '/htmx/sales', '#service-commandes')
  htmx.ajax('GET', `/htmx/sales?oldest_first=false&mode_manage=${glob.modeGerant}`, '#service-commandes')
}

export const menu = {
  func: "allOrderInterface",
  icon: "fas fa-concierge-bell", // font awesome 5
  i8nIndex: "allOrders,uppercase"
}
