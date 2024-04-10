export default async function () {
  let pv = glob.data.filter(obj => obj.service_direct === true)[0]
  let name = pv.name
  let serviceDirect = pv.service_direct
  // sys.logJson('pv = ',pv)
  Test.titre(`Test service direct, un article, paiement "CB" point de vente "${name}" !`)
  Test.enregistrerErreur(null, `Attention: pour un point de ventes dont "accepte_carte_bancaire" est à "true"`)

  // cliquer sur menu "burger"
  Test.elementClique({selecteur: '.menu-burger-icon'})

  // cliquer sur menu "POINTS DE VENTES"
  Test.elementClique({ selecteur: '#menu-burger-conteneur .menu-burger-item[onclick="vue_pv.afficherMenuPV()"]'})

  // clique sur le point de ventes
  Test.elementClique({ selecteur: `#menu-burger-conteneur div[class~="test-${name.toLowerCase()}"` })

  // attendre l'affichage de la vue
  let attente = await Test.elementAttendreAffichage({
    dureeMaxiAttente: 10000,
    selecteur: `#page-commandes`,
    msg: `Attendre(10 secondes maxi) l'affichage des articles !`,
  })

  // Clique sur le premier article du point de vente
  let article = document.querySelectorAll(`#products  #pv${ pv.id } bouton-article`)[0]
  let articlePrixBrut  = article.getAttribute('prix')
  let articlePrix  = `${ articlePrixBrut }€`
  let articleNom  = article.getAttribute('nom')
  article.click()

  // attende rendu du DOM après click
  attente = await Test.attendre(500)
  let articleNb = parseInt(document.querySelectorAll(`#products  #pv${ pv.id } bouton-article`)[0].getAttribute('nb-commande'))

  // addition ok
  let articleAddition = document.querySelectorAll('#achats-liste .achats-ligne')[0]
  let articleAdditionNb = parseInt(articleAddition.querySelector('.achats-col-qte').innerHTML)
  let articleAdditionNom = articleAddition.querySelector('.achats-ligne-produit-contenu').innerHTML
  // 5€
  let articleAdditionPrix = articleAddition.querySelector('.achats-col-prix-contenu').innerHTML.trim()
  if (articlePrix === articleAdditionPrix && articleNom === articleAdditionNom && articleNb === articleAdditionNb) {
    Test.enregistrerErreur(false, `- L'article dans l'addition est correcte !`)
  } else {
    Test.enregistrerErreur(true, `. L'article dans l'addition est incorrecte !`)
  }

  // Total à valider
  Test.textElementEgal({
    selecteur: '#bt-valider-total',
    valeur: `TOTAL ${ articlePrixBrut } €`,
    msgOk: `- Le total à valider est correcte !`,
    msgEr: `. Le total à valider est incorrecte !`
  })

  Test.elementFonctionCliqueInclut({
    selecteur: '#bt-valider',
    valeur: `vue_pv.testPaiementPossible('vente_directe')`,
    msgOk: `- Bouton "VALIDER TOTAL" configurer pour le "service direct" correcte !`,
    msgEr: `. Bouton "VALIDER TOTAL" configurer pour le "service direct" incorrecte !`
  })

  // clique sur le bouton VALIDER
  Test.elementClique({ selecteur: '#bt-valider' })

    // test cashless
  Test.elementExiste({
    selecteur: `#popup-cashless bouton-basique[onclick="fn.popupAnnuler();vue_pv.obtenirIdentiteClientSiBesoin('nfc')"]`,
    msgOk: `- Le bouton "CASHLESS" est présent !`,
    msgEr: `. Le bouton "CASHLESS" n'est pas présent !`
  })

  // Dans le bt 'cashless' la somme est présente ?
  let boutonCashless = document.querySelector(`#popup-cashless bouton-basique[onclick="fn.popupAnnuler();vue_pv.obtenirIdentiteClientSiBesoin('nfc')"]`).shadowRoot
  let sommeFront = boutonCashless.querySelectorAll('.sous-element .sous-element-texte div')[1].innerHTML.trim()
  if (sommeFront === `TOTAL ${ articlePrixBrut } €`) {
    Test.enregistrerErreur(false, `- Le total sur le bouton "CASHLESS" est correcte !`)
  } else {
    Test.enregistrerErreur(true, `. Le total sur le bouton "CASHLESS" est incorrecte !`)
  }

  // exemple insertion erreur (accepte espece = false, insertion bouton-basique espèce
  // let t = `<bouton-basique traiter-texte="1" texte="ESPECE|2rem|,TOTAL 5 €|1.5rem|" width="400px" height="120px" couleur-fond="#339448" icon="fa-coins||2.5rem" onclick="fn.popupAnnuler();vue_pv.obtenirIdentiteClientSiBesoin('espece')" style="margin-top:16px;"></bouton-basique>`
  // document.querySelector('#popup-cashless').insertAdjacentHTML('beforeend', t)

  // test espèces
  let especes = document.querySelector(`#popup-cashless bouton-basique[onclick="fn.popupAnnuler();vue_pv.obtenirIdentiteClientSiBesoin('espece')"]`)
  if (pv.accepte_especes === true && especes === null) {
    Test.enregistrerErreur(true, `. Le Bouton "ESPECE" n'est pas présent !`)
  }
  if (pv.accepte_especes === true && especes !== null) {
    Test.enregistrerErreur(false, `- Le Bouton "ESPECE" est présent !`)
  }
  if (pv.accepte_especes === false && especes !== null) {
    Test.enregistrerErreur(true, `. Le Bouton "ESPECE" est présent !`)
  }

  // test cb
  let ele = document.querySelector(`#popup-cashless bouton-basique[onclick="fn.popupAnnuler();vue_pv.obtenirIdentiteClientSiBesoin('carte_bancaire')"]`)
  if (pv.accepte_carte_bancaire === true && ele === null) {
    Test.enregistrerErreur(true, `. Le Bouton "CB" n'est pas présent !`)
  }
  if (pv.accepte_carte_bancaire === true && ele !== null) {
    Test.enregistrerErreur(false, `- Le Bouton "CB" est présent !`)
  }
  if (pv.accepte_carte_bancaire === false && ele !== null) {
    Test.enregistrerErreur(true, `. Le Bouton "CB" est présent !`)
  }

  // bouton "RETOUR" présent
  Test.elementExiste({
    selecteur: '#popup-retour',
    msgOk: `- Le bouton "RETOUR" est présent !`,
    msgEr: `. Le bouton "RETOUR" n'est pas présent !`
  })

  // fonction de callback à lancer "gererRetourPostPaiement"
  Test.apresFonction('gererRetourPostPaiement', async function (retour, status, options) {

    Test.textElementEgal({
      selecteur: `#popup-cashless div[class~="popup-titre1"]`,
      valeur: `Transaction OK !`,
      msgOk: `- Titre "Transaction OK !" affiché !`,
      msgEr: `. Titre "Transaction OK !" pas affiché !`
    })

    Test.textElementEgal({
      selecteur: `#popup-cashless .test-total-achats`,
      valeur: `Total (${window.orthoPaiement[options.achats.moyen_paiement]}) : ${retour.somme_totale}`,
      msgOk: `- Le total et le type de paiement sont correctes !`,
      msgEr: `. Le total et le type de paiement sont incorrectes !`
    })

    // bouton "RETOUR" présent
    Test.elementExiste({
      selecteur: '#popup-retour',
      msgOk: `- Le bouton "RETOUR" est présent !`,
      msgEr: `. Le bouton "RETOUR" n'est pas présent !`
    })

    // clique sur "RETOUR"
    Test.elementClique({
      selecteur: '#popup-retour',
      msg: `Clique sur le bouton "RETOUR" !`
    })

    // attende de l'affichage du point de vents
    let attente = await Test.elementAttendreAffichage({
      dureeMaxiAttente: 10000,
      selecteur: `#page-commandes`,
      msg: `Attente de (10 secondes maxi) l'affichage du point de vents !`
    })

    //affiche point de ventes courant est affiché
    if (document.querySelector(`#products #pv${ pv.id }`).style.display === 'block') {
      Test.enregistrerErreur(false, `- Retour sur le point de vente courant "${ pv.name }" correcte !`)
    } else {
      Test.enregistrerErreur(true, `. Retour sur le point de vente courant "${ pv.name }" incorrecte !`)
    }

    // document.querySelector(`#achats-liste`).innerHTML = 'hahaha'
    // la liste de l'addition est bien vide
    Test.textElementEgal({
      selecteur: `#achats-liste`,
      valeur: '',
      msgOk: `- L'addition est bien vide !`,
      msgEr: `. L'addition n'est pas vide !`
    })

    // le bouton "VALIDER TOTAL" est égal à 0
    Test.textElementEgal({
      selecteur: `#bt-valider-total`,
      valeur: 'TOTAL 0 €',
      msgOk: `- Le bouton "VALIDER TOTAL" est égal à 0 !`,
      msgEr: `. Le bouton "VALIDER TOTAL" n'est pas égal à 0`
    })

    Test.afficherBlockslogs()
  })

  // Clique sur le bouton "CB"
  Test.elementClique({
    selecteur: `#popup-cashless bouton-basique[onclick="fn.popupAnnuler();vue_pv.obtenirIdentiteClientSiBesoin('carte_bancaire')"]`,
    msg: `Clique sur le bouton "CB"`
  })
}