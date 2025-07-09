window.showSettingsInterface = function () {
  // hide menu
  document.querySelector('#menu-burger-conteneur').classList.toggle('burger-show')

  // éfface les autres élément(pages)
  sys.effacerElements(['#page-commandes', '#tables', '#commandes-table'])
  // rend visible l'élément(page) '#service-commandes'
  sys.afficherElements(['#service-commandes,block'])

  // changer titre
  vue_pv.asignerTitreVue(`<span data-i8n="settings,capitalize">Paramètres</span> - <span data-i8n="infos",capitalize">Infos</span>`)

  // ci-dessous <=> <button hx-get="/htmx/appsettings/" hx-target="#service-commandes">clique</button>
  htmx.ajax('GET', '/htmx/appsettings/', '#service-commandes')

  // --- listen htmx:afterSwap and launch methods --
  document.body.addEventListener('htmx:afterSwap', async function (evt) {
    if (evt.target.querySelector('#service-commandes .nav-settings')) {
      // mettre à jour le hx-include du post "/manger_mode" avec la valeur glob.passageModeGerant
      const vals =`{
         "activation_mode_gerant": "${glob.modeGerant}",
         "autorisation_mode_gerant": "${glob.passageModeGerant}"
      }`
      document.querySelector('div[action="manage-mode"]').setAttribute('hx-vals', vals)
    }
  })
}


/**
 * initialization of the settings menu
 */
export const menu = {
  func: "showSettingsInterface",
  icon: "fas fa-cog", // font awesome 5.11
  i8nIndex: "settings,uppercase",
  testClass: 'test-action-change-settings'
}
