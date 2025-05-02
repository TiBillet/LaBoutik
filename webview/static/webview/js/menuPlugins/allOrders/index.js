window.allOrderInterface = function () {
  // hide menu
  document.querySelector('#menu-burger-conteneur').classList.toggle('burger-show')

  // éfface les autres élément(pages)
  sys.effacerElements(['#page-commandes', '#tables', '#commandes-table'])
  // rend visible l'élément(page) '#service-commandes'
  sys.afficherElements(['#service-commandes,block'])

  // changer titre
  vue_pv.asignerTitreVue('<span data-i8n="sales,capitalize">Ventes</span>')

  // ci-dessous <=> <button hx-get="allOrders/null" hx-target="#service-commandes">clique</button>
  htmx.ajax('GET', `/htmx/sales?oldest_first=false`, '#service-commandes')
}

export const menu = {
  func: "allOrderInterface",
  icon: "fas fa-concierge-bell", // font awesome 5
  i8nIndex: "sales,uppercase"
}
