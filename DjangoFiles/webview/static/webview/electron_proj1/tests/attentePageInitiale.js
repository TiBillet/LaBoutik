/**
 * Attente la fin de l'initialisation de l'application(initMode) avant de commencer les tests
 * @returns {Promise<void>}
 */
export default async function () {
  let pv = glob.data.filter(obj => obj.id === window.pv_uuid_courant)[0]
  let serviceDirect = pv.service_direct
  let selecteur = ''
  if (serviceDirect === false) {
    selecteur = '#tables'
  } else {
    selecteur = '#page-commandes'
  }

  Test.titre(`Initialisation du lance des tests !`)

  // attendre l'affichage de la vue
  let attente = await Test.elementAttendreAffichage({
    dureeMaxiAttente: 10000,
    selecteur: selecteur,
    msg: null
  })

  Test.afficherBlockslogs()
}
