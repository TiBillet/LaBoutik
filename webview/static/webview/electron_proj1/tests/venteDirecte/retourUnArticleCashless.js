export default async function () {
  let pv = glob.data.filter(obj => obj.service_direct === true)[0]
  let name = pv.name
  let serviceDirect = pv.service_direct
  // sys.logJson('pv = ',pv)
  Test.titre(`Test service direct, un article, paiement "CASHLESS" point de vente "${name}" !`)
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
  let articleUuid = article.getAttribute('uuid')
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

  // clique sur "RETOUR"
  Test.elementClique({
    selecteur: '#popup-retour',
    msg: `Clique sur le bouton "RETOUR" !`
  })

  // initialise une carte de tant de crédit sur le point de vente nommé "Cashless" de comportement "C"
  // soit 2x20 ("Bisik +20" = "a981ca30-19b6-4e29-9840-0b63aedc12aa")
  let carteTagId = '52BE6543'
  attente = await Test.carteInitCredits({
    articleUuid: 'a981ca30-19b6-4e29-9840-0b63aedc12aa',
    tagId: carteTagId,
    typeMonnaie: 'principale',
    quantite: 2
  })

  let pkResponsable  = document.querySelector(`#products #pv${ pv.id }`).getAttribute('data-responsable-uuid')
  let data = {
    "donnees": {
      "options": {
        "url": "paiement",
        "actionAValider": "vente_directe",
        "achats": {
          "articles": [
            {
              "pk": articleUuid,
              "qty": 1,
              "pk_pdv": pv.id
            }
          ],
          "pk_responsable": pkResponsable,
          "pk_pdv": pv.id,
          "total": 5,
          "hostname_client": glob.infosNavigateur.hostname,
          "moyen_paiement": "nfc"
        }
      },
      "methodes": [
        "VenteArticle"
      ],
      "besoin_tag_id": [
        "nfc"
      ]
    },
    "tagId": "52BE6543"
  }

  // fonction de callback lancée après "vue_pv.validerEtape2(data)"
  Test.apresFonction('gererRetourPostPaiement', async function (retour, status, options) {
    // console.log('Clique sur "CASHLESS" !')
    // sys.logValeurs({retour: retour, status: status, options: options})
    Test.textElementEgal({
      selecteur: `#popup-cashless div[class~="popup-titre1"]`,
      valeur: `Transaction OK !`,
      msgOk: `- Titre "Transaction OK !" affiché !`,
      msgEr: `. Titre "Transaction OK !" pas affiché !`
    })
/*
    let nbArticles = options.achats.articles.length
    let msgTotalAchat = nbArticles > 1 ? `Total des achats` : `Total de l'achat`
    let motsPourAchat = nbArticles > 1 ? `les achats` : `l'achat`

    //  Sur carte avant l'achat : 40
    Test.textElementEgal({
      selecteur: `#popup-cashless .test-carte-avant-achats`,
      valeur: `Sur carte avant ${ motsPourAchat} : ${ retour.total_sur_carte_avant_achats }`,
      msgOk: `- Information sur carte avant l'achat correcte !`,
      msgEr: `. Information sur carte avant l'achat incorrecte !`
    })

    //  Total de l'achat
    Test.textElementEgal({
      selecteur: `#popup-cashless .test-total-achats`,
      valeur: `Total de l'achat (carte nfc) : 5`,
      msgOk: `- Information sur le total de l'achat est correcte !`,
      msgEr: `. Information sur le total de l'achat est incorrecte !`
    })

    //    Total de l'achat (carte nfc) : 5
    // test-carte-apres-achats   Sur carte après l'achat : 35
*/

    Test.afficherBlockslogs()
  })
  // Emule le clique sur bouton "CASHLESS"
  vue_pv.validerEtape2(data)
}