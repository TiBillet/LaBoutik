export default async function () {
  Test.titre(`Test adhésion sur point de vente cashless !`)
  // cliquer sur menu "burger"
  Test.elementClique({selecteur: '.menu-burger-icon'})

  // cliquer sur menu "POINTS DE VENTES"
  Test.elementClique({selecteur: '#menu-burger-conteneur .menu-burger-item[onclick="vue_pv.afficherMenuPV()"]'})

  // clique sur le point de ventes
  Test.elementClique({selecteur: `#menu-burger-conteneur div[class~="test-cashless"`})

  // 1 - vérifier la date d'adhésion avec un check_carte
  Test.elementClique({
    selecteur: '.test-check-carte',
    msg: 'Clique sur bouton "CHECK CARTE" !'
  })

  // attendre l'affichage de la vue
  let attente =  await Test.elementAttendreAffichage({
    dureeMaxiAttente: 10000,
    selecteur: '#popup-cashless',
    msg: `Attendre(10 secondes maxi) l'affichage du popup "attente lecture carte" !`,
    msgEr: `. Le popup d'attente de lecture carte nfc n'est pas affiché !`
  })

  // émuler lecture carte nfc, tagId= '4D64463B'
  window.rfid.emulerLecture('4D64463B')

  attente =  await Test.elementAttendreAffichage({
    dureeMaxiAttente: 10000,
    selecteur: '#popup-cashless',
    msg: `Attendre(10 secondes maxi) l'affichage du popup "retour check_carte" !`,
    msgEr: `. Le popup de "retour check_carte" n'est pas affiché !`
  })

  // pas de cotisation
  let etatInit = document.querySelector(`#popup-cashless .check-carte-ok-cotisation`).innerHTML

  if (etatInit === 'Aucune cotisation') {
    // test couleur du fond
    Test.elementStyleEgale({
      selecteur: '#popup-cashless',
      typeStyle: 'background-color',
      valeur: 'rgb(184, 85, 33)',
      msgOk: `- Couleur de fond et message ok, lors d'absence de cotisation !`,
      msgEr: `. Couleur de fond ou/et message incorrecte, lors d'absence de cotisation !`
    })
  }

  // clique sur le bouton retour
  Test.elementClique({ selecteur: '#popup-retour' })

  // clique sur le bouton 'Adhésion'
  Test.boutonArticleClique({
    nom: 'Adhésion',
    msg: `Clique sur l'article "Adhésion" !`
  })

  // obtenir le prix d'une adhésion
  let prixAdhesion = parseFloat(document.querySelector(`#pv${ pv_uuid_courant } bouton-article[nom='Adhésion']`).getAttribute('prix'))

  // clique sur le bouton VALIDER
  Test.elementClique({ selecteur: '#bt-valider' })

  attente =  await Test.elementAttendreAffichage({
    dureeMaxiAttente: 10000,
    selecteur: '#popup-cashless',
    msg: `Attendre(10 secondes maxi) l'affichage du popup "moyens de paiement" !`,
    msgEr: `. Le popup de "moyens de paiement" n'est pas affiché !`
  })

  // date de l'adésion en cours
  const maintenant = new Date()
  const jour = `${ maintenant.getDate() }-${ maintenant.getMonth()+1 }-${ maintenant.getFullYear() }`

  // clique sur le bouton "ESPECE"
  Test.elementClique({ selecteur: `#popup-cashless bouton-basique[onclick="fn.popupAnnuler();vue_pv.obtenirIdentiteClientSiBesoin('espece')"]` })


  attente =  await Test.elementAttendreAffichage({
    dureeMaxiAttente: 10000,
    selecteur: '#popup-cashless',
    msg: `Attendre(10 secondes maxi) l'affichage du popup "Attente lecture carte" !`,
    msgEr: `. Le popup de "Attente lecture carte" n'est pas affiché !`
  })

  // émuler lecture carte nfc, tagId= '4D64463B'
  window.rfid.emulerLecture('4D64463B')
  Test.enregistrerErreur(null, 'tagId carte maîtresse entré !')

  attente =  await Test.elementAttendreAffichage({
    dureeMaxiAttente: 10000,
    selecteur: '#popup-cashless',
    msg: `Attendre(10 secondes maxi) l'affichage du popup "retour adhésion" !`,
    msgEr: `. Le popup de "retour adhésion" n'est pas affiché !`
  })

  // message de retour égal à 'Adhésion OK !'
  Test.textElementEgal({
    selecteur: '#popup-cashless .popup-titre1',
    valeur: 'Adhésion',
    msgOk: `- Le titre est correcte !`,
    msgEr: `. Le titre est incorrecte !`
  })

  // info membre
  Test.elementTextInclut({
    selecteur: '#popup-cashless .test-msg-membre',
    valeur: 'membre : ',
    msgOk: `- L'information membre est affichée !`,
    msgEr: `. L'information membre n'est pas affichée !`
  })

  // le jour de l'adhésion est ok !
  Test.textElementEgal({
    selecteur: '#popup-cashless .test-msg-adhesion-date',
    valeur: `A Jour ${ jour }`,
    msgOk: `- La date d'adhésion est correcte !`,
    msgEr: `. La date d'adhésion est incorrecte !`
  })

  // info total
  Test.elementInclutLesMots({
    selecteur: '#popup-cashless .test-msg-adhesion',
    mots: ['Total','(',')',prixAdhesion],
    msgOk: `- L'information total est affichée !`,
    msgEr: `. L'information total est incorrecte !`
  })

  // clique sur le bouton retour
  Test.elementClique({ selecteur: '#popup-retour' })

  if (document.querySelector(`#products #pv${ pv_uuid_courant}[data-name-pdv='Cashless']`).style.display === 'block') {
    Test.enregistrerErreur(false, '- Retour sur point de vente cashless ok !')
  } else {
    Test.enregistrerErreur(true, '- Retour sur point de vente cashless incorrect !')
  }

  Test.afficherBlockslogs()
}
