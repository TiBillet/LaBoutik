var testIdTimeout
// Attention l'emplacement des fonctions dans la liste des "fonctionsTests" n'est pas annodin
// les actions dans de test dans lk'application peuvent être complémentaire
// créer les tables "table1", "table2", ...., "table11"
// avant de lancer les tests: supprimer les commandes et libérer les tables
let fonctionsTests = ['./tests/attentePageInitiale.js',/*
  './tests/menuPrincipal.js',
  './tests/PvServiceDirectFalse.js',
  './tests/PvServiceDirectTrue.js',
  './tests/checkCarte/checkCartePlusBoutonRetour.js',
  './tests/checkCarte/reelPostCheckCarte.js',
  './tests/checkCarte/simuPostCheckCarteInconnue.js',
  './tests/checkCarte/simuPostCheckCartePasDeCotisation.js',
  './tests/checkCarte/simuPostCheckCarteOkMonnaies10lieu5cadeau.js',
  './tests/checkCarte/simuPostCheckCarteOk0Monnaie.js',
  './tests/checkCarte/simuPostCheckCarteStatus400.js',
  './tests/commandes/selectionCategoriesTables.js',
  './tests/commandes/envoyerEnPreparation.js',
  './tests/commandes/envoyerEnPreparationPayerUneFois/cashless.js',
  './tests/commandes/envoyerEnPreparationPayerUneFois/cashlessFondsInsuffisants.js',
  './tests/commandes/envoyerEnPreparationPayerUneFois/cashlessFondsInsuffisantsDeuxFois.js',
  './tests/commandes/envoyerEnPreparationPayerUneFois/cashlessFondsInsuffisantsPlusEspece.js',
  './tests/commandes/envoyerPreparationAllerPagePaiement/pagePaiementBoutons_Tout_Reset_Retour.js',
  './tests/commandes/envoyerPreparationAllerPagePaiement/Tout.js',
  './tests/commandes/envoyerPreparationAllerPagePaiement/valeurPartiellePlusTout.js',
  './tests/commandes/envoyerPreparationAllerPagePaiement/valeurPartielle2articlesPlusTout.js',
  './tests/pagePreparation/table11ValiderCommande.js',
  './tests/pagePreparation/table11ToutPayer.js', // ces tests suivent obligatoirement "table11ValiderCommande.js"
   // './tests/pagePreparation/modeGerant/modeGerant.js',
  './tests/venteDirecte/retourUnArticleCB.js',
  './tests/venteDirecte/retourUnArticleCashless.js'*/
  './tests/cashless/adhesion.js'
]
// en général fonctions lancées après le retour d'un POST ou GET
let fonctionsDansRetourAjax = ['gererRetourPostPaiement', 'gererRetourPostCheckCarte']

let niveauInfos = 1, tailleFonte = 10
let debutAttenteAffichageElement2
let idFonctionsTests
// resultatsTests = [{titre: string, infos: array}]
let idResultatsTests = -1
export let  resultatsTests = [], debBoucleResultatsTests

export let listeTagId = { carteMaitresse: '4D64463B', carteClient1: '41726443', carteClient2: '52BE6543'}

export function entrerTagId(clef) {
  window.rfid.emulerLecture(listeTagId[clef])
}

export function modifierListeTagId(ctx, clef) {
  let valeur = ctx.value
  listeTagId[clef] = valeur
}

export function lancer() {
  entrerTagId('carteMaitresse')
}


export function afficherBlockslogs() {
  // console.log('-> fonction verifierTests !')
  let erreurAffichageBlock =  false
  for (let i = debBoucleResultatsTests; i < resultatsTests.length; i++) {
    console.log('')
    console.log(`%c ${ resultatsTests[i].titre }`,`background-color:#000000;color:#FFFFFF;font-size:${ (tailleFonte+2) }px;font-weight:bold;`)
    for (let idInfos = 0; idInfos < resultatsTests[i].infos.length; idInfos++) {
      let info =resultatsTests[i].infos[idInfos]
      if (info.err === false) {
        console.log(`%c ${ info.msg } %c OK `, `color:#000000;font-size:${ tailleFonte }px;font-weight:bold;`, `background-color:green;color:#FFFFFF;font-style:italic;font-size:${ tailleFonte }px;font-weight:bold;`)
      }
      if (info.err === 'msg') {
        console.log(`%c* ${ info.msg } %c`, `color:#0000FF;font-size:${ tailleFonte }px;font-weight:bold;`, `color:green;font-style:italic;font-size:${ tailleFonte }px;font-weight:bold;`)
      }
      if (info.err === true) {
        console.log(`%c ${ info.msg }`, `background-color:red;color:#FFFFFF;font-size:${ tailleFonte }px;font-weight:bold;`)
        erreurAffichageBlock = true
        break
      }
    }
  }

  // console.log('erreurAffichageBlock =', erreurAffichageBlock, '  --  taille = ', fonctionsTests.length, '  --  idFonctionsTests = ', idFonctionsTests)
  if (erreurAffichageBlock === false  && (idFonctionsTests + 1) < fonctionsTests.length) {
    idFonctionsTests = idFonctionsTests + 1
    debBoucleResultatsTests = resultatsTests.length
    // charge le prochain fichier de test de la liste
    chargeTests(idFonctionsTests)
  } else {
    console.log('--> Fin des tests')
  }

}

// nomTests = ['modeFonctionAchats1','reset', 'viderCarte']
async function chargeTests(id) {
  // console.log('-> fonction chargeTests, ',fonctionsTests[id])
  if (fonctionsTests.length > 0) {
    window[fonctionsTests[id]] = await import(fonctionsTests[id])
    window[fonctionsTests[id]].default()
  } else {
    console.log('Pas de fonctions à tester !')
  }
}

/**
 * Après que "fonctionPremiere" soie lancée, "fonctionSuivante" est lancée
 * @param {String} fonctionPremiere - nom de la fonction
 * @param {Function} fonctionSuivante - fonction lancée après la fonction "fonctionPremiere"
 */
export function apresFonction(fonctionPremiere, fonctionSuivante) {
  let fonctionOriginale = window[fonctionPremiere]
  window[fonctionPremiere] = function () {
    fonctionOriginale.apply(this, arguments)
    fonctionSuivante.apply(this, arguments)
    window[fonctionPremiere] = fonctionOriginale
  }
}

export function init() {
  resultatsTests = []
  idFonctionsTests = 0
  debBoucleResultatsTests = 0
  idResultatsTests = -1
  chargeTests(idFonctionsTests)
}

function logINFOS(msg) {
  if (niveauInfos > 0 ) {
    console.log(`%c ${msg}`, `color:#000077;font-size:${tailleFonte}px;font-weight:bold;`)
  }
}

export function titre2(data) {
  idResultatsTests++
  resultatsTests[idResultatsTests] = { titre: data.titre, infos: [] }
  enregistrerErreur(null,fonctionsTests[idFonctionsTests])
}

// --- à changer ---
export function titre(titre) {
  idResultatsTests++
  resultatsTests[idResultatsTests] = { titre: titre, infos: [] }
  enregistrerErreur(null,fonctionsTests[idFonctionsTests])
}
// --- fin: à changer ---

export function enregistrerErreur(erreur, msg) {
  let tab = resultatsTests[idResultatsTests].infos
  if (erreur !== null) {
    if (erreur) {
      tab.push({err: true, msg: msg})
    } else {
      tab.push({err: false, msg: msg})
    }
  } else {
    tab.push({err: 'msg', msg: msg})
  }
}

// function clique
function clique(data) {
  clearTimeout(window.testCliqueRep)
  try {
    if (data.msg !== undefined) {
      enregistrerErreur(null, data.msg )
    }
    document.querySelector(data.selecteur).click()
  } catch (err) {
    enregistrerErreur(true, err )
  }
}

// appel la fonction clique, en direct ou avec délai(secondes)
export function elementClique(data) {
  if (data.delai === undefined) {
    clique(data)
  } else {
    window.testCliqueRep = setTimeout(clique, (data.delai * 1000), data)
  }
}

export function boutonArticleClique(data) {
  try {
    if (data.msg !== undefined) {
      enregistrerErreur(null, data.msg )
    }
    document.querySelector(`#pv${ pv_uuid_courant } bouton-article[nom='${ data.nom}']`).click()
  } catch (err) {
    enregistrerErreur(true, err )
  }
}

export function elementListeCliqueAttribut(data) {
  try {
    let eles = document.querySelectorAll(data.selecteur)
    eles[data.index].click()
    if (data.msg !== undefined) {
      enregistrerErreur(null, data.msg )
    }
  } catch (err) {
    enregistrerErreur(true, err )
  }
}

export function variableEgale(data) {
  if (data.msgOk === undefined ) {
    data.msgOk  = `- La variable "${ data.variableNom }" est égale à ${ data.valeur } !`
  }
  if (data.msgEr === undefined ) {
    data.msgEr = `. La variable "${ data.variableNom }" n'est pas égale à ${ data.valeur } !`
  }

  if (data.variable === data.valeur) {
    enregistrerErreur(false, data.msgOk )
  } else {
    enregistrerErreur(true, data.msgEr )
  }
}

export function elementExiste(data) {
  if (data.msgOk === undefined ) {
    data.msgOk  = `- L'élément "${ data.selecteur }" existe !`
  }
  if (data.msgEr === undefined ) {
    data.msgEr = `. L'élément "${ data.selecteur }" n'existe pas !`
  }

  if (document.querySelector(data.selecteur)) {
    enregistrerErreur(false, data.msgOk )
  } else {
    enregistrerErreur(true, data.msgEr )
  }
}

export function elementExistePas(data) {
  if (data.msgOk === undefined ) {
    data.msgOk  = `- L'élément "${ data.selecteur }" n'existe pas!`
  }
  if (data.msgEr === undefined ) {
    data.msgEr = `. L'élément "${ data.selecteur }" existe !`
  }

  if (document.querySelector(data.selecteur)) {
    enregistrerErreur(true, data.msgEr )
  } else {
    enregistrerErreur(false, data.msgOk )
  }
}

export function textElementEgal(data) {
  if (data.msgOk === undefined ) {
    data.msgOk  = `- Le texte de "${ data.selecteur }" est bien égal à "${ data.valeur }" !`
  }
  if (data.msgEr === undefined ) {
    data.msgEr = `. Le texte de "${ data.selecteur }" est différent de "${ data.valeur }" !`
  }

  try {
    if (document.querySelector(data.selecteur).innerHTML === data.valeur) {
      enregistrerErreur(false, data.msgOk )
    } else {
      enregistrerErreur(true, data.msgEr )
    }
  } catch (e) {
    enregistrerErreur(true, `. L'élément "${ data.selecteur }" n' existe pas !`)
  }
}

export function numElementEgal(data) {
  try {
    let numValeur = parseFloat(document.querySelector(data.selecteur).innerHTML)
    if (data.msgOk === undefined ) {
      data.msgOk  = `- Le nombre ${ numValeur } de "${ data.selecteur }" est bien égal à "${ data.valeur }" !`
    }
    if (data.msgEr === undefined ) {
      data.msgEr = `. Le nombre ${ numValeur } de "${ data.selecteur }" est différent de "${ data.valeur }" !`
    }
    // console.log('numValeur = ', numValeur, ' - type = ', typeof numValeur,'  -- valeur = ', data.valeur,' - type = ', typeof data.valeur)
    if (numValeur === parseFloat(data.valeur)) {
      enregistrerErreur(false, data.msgOk )
    } else {
      enregistrerErreur(true, data.msgEr )
    }
  } catch (e) {
    enregistrerErreur(true, `. L'élément "${ data.selecteur }" n' existe pas !`)
  }
}

export function elementVide(data) {
  if (data.msgOk === undefined ) {
    data.msgOk  = `- L' élément "${ data.selecteur }" est vide !`
  }
  if (data.msgEr === undefined ) {
    data.msgEr = `. L' élément "${ data.selecteur }" n'est pas vide !`
  }

  try {
    if (document.querySelector(data.selecteur).innerHTML.length === 0) {
      enregistrerErreur(false, data.msgOk )
    } else {
      enregistrerErreur(true, data.msgEr )
    }
  } catch (err) {
    enregistrerErreur(true, `. elementVide, erreur: ${ err }`)
  }
}

export function elementPasVide(data) {
  if (data.msgOk === undefined ) {
    data.msgOk  = `- L' élément "${ data.selecteur }" n'est pas vide, correct !`
  }
  if (data.msgEr === undefined ) {
    data.msgEr = `. L' élément "${ data.selecteur }" est vide, incorrcet !`
  }

  try {
    if (document.querySelector(data.selecteur).innerHTML.length > 0) {
      enregistrerErreur(false, data.msgOk )
    } else {
      enregistrerErreur(true, data.msgEr )
    }
  } catch (err) {
    enregistrerErreur(true, `. elementVide, erreur: ${ err }`)
  }
}


export function elementTextInclut(data) {
  if (data.msgOk === undefined ) {
    data.msgOk  = `- Le texte "${ data.valeur }" est bien inclus dans l'élément "${ data.selecteur }" !`
  }
  if (data.msgEr === undefined ) {
    data.msgEr = `. Le texte "${ data.valeur }" n'est pas inclus dans l'élément "${ data.selecteur }" !`
  }

  try {
    if (document.querySelector(data.selecteur).innerHTML.indexOf(data.valeur) !== -1) {
      enregistrerErreur(false, data.msgOk )
    } else {
      enregistrerErreur(true, data.msgEr )
    }
  } catch (err) {
    enregistrerErreur(true, `. textElementInclut, erreur: ${ err }`)
  }
}

export function elementInclutLesMots(data) {
  try {
    let compteMotInclut = []
    let motsNonInclus = []
    data.mots.forEach(motBrut => {
      let mot = motBrut.toString()
      if (document.querySelector(data.selecteur).innerHTML.indexOf(mot) !== -1) {
        compteMotInclut.push(mot)
      } else {
        motsNonInclus.push(mot)
      }
    })

    let sujet = `L'élément "${ data.selecteur }"`
    if (data.msgOk === undefined ) {
      sujet = data.sujet
    }

    if (data.msgOk === undefined ) {
      data.msgOk  = `- ${ sujet } inclut bien tous les mots "${ data.mots }" !`
    }
    if (data.msgEr === undefined ) {
      data.msgEr = `. ${ sujet } n'inclut pas le(s) mot(s) "${ motsNonInclus }" !`
    }

    if (compteMotInclut.length === data.mots.length) {
      enregistrerErreur(false, data.msgOk )
    } else {
      enregistrerErreur(true, data.msgEr )
    }
  } catch (err) {
    enregistrerErreur(true, `. elementInclutLesMots, erreur: ${ err }`)
  }
}

export function elementFonctionCliqueInclut(data) {
  if (data.msgOk === undefined ) {
    data.msgOk  = `- L'élément "${ data.selecteur }" contient le code "${ data.valeur }" !`
  }
  if (data.msgEr === undefined ) {
    data.msgEr = `. L'élément "${ data.selecteur }" ne contient pas le code "${ data.valeur }" !`
  }
  try {
    let tmp = document.querySelector(data.selecteur).getAttribute('onclick').indexOf(data.valeur)
    if (tmp !== -1) {
      enregistrerErreur(false, data.msgOk)
    } else {
      enregistrerErreur(true, data.msgEr)
    }
  } catch (e) {
    enregistrerErreur(true, data.msgEr)
  }
}

export function elementFonctionCliqueEgale(data) {
  if (data.msgOk === undefined ) {
    data.msgOk  = `- La fonction de l'élément "${ data.selecteur }" est égale à "${ data.valeur }" !`
  }
  if (data.msgEr === undefined ) {
    data.msgEr = `. La fonction de l'élément "${ data.selecteur }" n'est pas égale à "${ data.valeur }" !`
  }
  try {
    if (document.querySelector(data.selecteur).getAttribute('onclick').toString() === data.valeur) {
      enregistrerErreur(false, data.msgOk)
    } else {
      enregistrerErreur(true, data.msgEr)
    }
  } catch (e) {
    enregistrerErreur(true, data.msgEr)
  }
}

export function elementStyleEgale(data) {
  if (data.msgOk === undefined ) {
    data.msgOk  = `- Le style "${ data.typeStyle }" est égale à "${ data.valeur }" !`
  }
  if (data.msgEr === undefined ) {
    data.msgEr = `. Le style "${ data.typeStyle }" n'est pas égale à "${ data.valeur }" !`
  }
  try {
    if (document.querySelector(data.selecteur).style[data.typeStyle] === data.valeur) {
      enregistrerErreur(false, data.msgOk)
    } else {
      enregistrerErreur(true, data.msgEr)
    }
  } catch (e) {
    enregistrerErreur(true, data.msgEr)
  }
}

export function listeElementsFonctionCliqueInclut(data) {
  if (data.msgOk === undefined ) {
    data.msgOk  = `- L'un des éléments "${ data.selecteur }" contient le code "${ data.valeur }" !`
  }
  if (data.msgEr === undefined ) {
    data.msgEr = `. Aucun des éléments "${ data.selecteur }" ne contient le code "${ data.valeur }" !`
  }
  try {
   let eles = document.querySelectorAll(data.selecteur)
    let contient = 0
    for (let i = 0; i < eles.length ; i++) {
      let tmp = eles[i].onclick.toString().indexOf(data.valeur)
      if (tmp !== -1) {
        contient = 1
        break
      }
    }
    if (contient === 1) {
      enregistrerErreur(false, data.msgOk)
    } else {
      enregistrerErreur(true, data.msgEr)
    }
  } catch (e) {
    enregistrerErreur(true, data.msgEr)
  }
}

export function listeElementsFonctionCliqueInclutPas(data) {
  if (data.msgOk === undefined ) {
    data.msgOk = `. Aucun des éléments "${ data.selecteur }" ne contient le code "${ data.valeur }" !`
  }
  if (data.msgEr === undefined ) {
    data.msgEr = `- L'un des éléments "${ data.selecteur }" contient le code "${ data.valeur }" !`
  }
  try {
   let eles = document.querySelectorAll(data.selecteur)
    let contient = 0
    for (let i = 0; i < eles.length ; i++) {
      let tmp = eles[i].onclick.toString().indexOf(data.valeur)
      if (tmp !== -1) {
        contient = 1
        break
      }
    }
    if (contient === 0) {
      enregistrerErreur(false, data.msgOk)
    } else {
      enregistrerErreur(true, data.msgEr)
    }
  } catch (e) {
    enregistrerErreur(false, data.msgOk)
  }

}

export function listeElementsInclutText(data) {
  if (data.msgOk === undefined ) {
    data.msgOk  = `- L'un des éléments "${ data.selecteur }" contient le texte "${ data.valeur }" !`
  }
  if (data.msgEr === undefined ) {
    data.msgEr = `. L'un des éléments "${ data.selecteur }" ne contient pas le texte "${ data.valeur }" !`
  }

  try {
    let eles = document.querySelectorAll(data.selecteur)
    let contient = 0
    for (let i = 0; i < eles.length ; i++) {
      let ele = eles[i]
      if ( ele.innerHTML === data.valeur) {
        contient = 1
        break
      }
    }
    if (contient === 1) {
       enregistrerErreur(false, data.msgOk)
    } else {
      enregistrerErreur(true, data.msgEr)
    }
  } catch (e) {
    enregistrerErreur(true, `. L'un des éléments "${ data.selecteur }" ne contient pas le texte "${ data.valeur }" \n ou le selecteur n'est pas valide !`)
  }
}

function attendreAffichage(){
  return new Promise((resolve, reject) => {
    setTimeout(() => {
      // console.log('-> fonc attendreAffichage, data = ',JSON.stringify(window.dataForSetTimeout,null,'\t'))
      // l'élément n'existe pas
      if (document.querySelector(window.dataForSetTimeout.selecteur) === null) {
        window.clearTimeout(testIdTimeout)
        resolve({ erreur: 1, msg: `. Elément "${ window.dataForSetTimeout.selecteur }" inconnu !` })
      } else {
        // l'élément existe
        // l'état "dispaly" de l'élément est différent de 'none', c'est ok
         if (document.querySelector(window.dataForSetTimeout.selecteur).style.display !== 'none') {
           window.clearTimeout(testIdTimeout)
           resolve({ erreur: 0, msg: `- Elément "${ window.dataForSetTimeout.selecteur }" affiché !` })
         } else {
           // l'élément existe
           // l'état "dispaly" de l'élément est égale à 'none'
           let tempsActuel = new Date().getTime()
           let duree = tempsActuel - window.dataForSetTimeout.debutAttenteAffichageElement
           // console.log('-> tempsActuel = ',tempsActuel, '  -- duree = ', duree, '  --  maxi = ',  window.dataForSetTimeout.dureeMaxiAttente)
           if (duree > window.dataForSetTimeout.dureeMaxiAttente){
             resolve({erreur: 1, msg: `. Temps d'attente de l'élément "${window.dataForSetTimeout.selecteur}" dépassé !`})
           }else {
             attendreAffichage()
           }
         }
      }
    },500)
  })
}
export async function elementAttendreAffichage(data) {
  window.dataForSetTimeout = data
  window.dataForSetTimeout.debutAttenteAffichageElement = new Date().getTime()
  // console.log('-> fonc elementAttendreAffichage, data = ', JSON.stringify(window.dataForSetTimeout,null,'\t'))
  if (data.msg === undefined) {
    data.msg = `Attente(${data.dureeMaxiAttente}ms maxi) de l'affichage de l'élément "${data.selecteur}".`
  }

  // affichage du message "data.msg"
  if (data.msg !== null) {
    Test.enregistrerErreur(null, data.msg)
  }
  let resultat = await attendreAffichage()
  // console.log('Etape attente finale = ', resultat)
  if (resultat.erreur === 1) {
    let msgFinalEr = ''
    if (data.msgEr === undefined) {
      msgFinalEr = resultat.msg
    } else {
      msgFinalEr = data.msgEr
    }
    enregistrerErreur(true, msgFinalEr)
  }
  return resultat.erreur
}

function attendreSetTimeout(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}
export async function attendre(ms) {
  let resultat = await attendreSetTimeout(ms)
  return resultat
}

// Sélectionne une liste d'articles définie et la compare avec le retour de la foncion "vue_pv.obtenirAchats('listeArticlesPV')"
export function achats(data) {
  // articles (objet): nom bouton article = uuid bouton article
  let articles = {}, erreursListeArticles = []
  let pvBar = glob.data.filter((obj) => obj.name === data.pv)[0]

  let testTabArticles = pvBar.articles.filter(obj => obj.name).map(obj => obj.name)

  // si aucun articles sélectionnés, faire un choix automatique
  let ArticleInterdit = ['Retour Consigne', 'CONSIGNE CUP'], nbEnCours = 0
  if (data.articlesATester.length === 0) {
    if (data.nbChoix > (pvBar.articles.length - 1)) {
      data.nbChoix = pvBar.articles.length - 1
    }
    for (let i = 0; i < testTabArticles.length; i++) {
      let nom = testTabArticles[i]
      if (ArticleInterdit.includes(nom) === false && nbEnCours < data.nbChoix) {
        data.articlesATester.push(nom)
        nbEnCours++
      }
      if ((nbEnCours - 1) === data.nbChoix) {
        break
      }
    }
  } else {
    // verifier que le point de vente contient les articles
    for (let i = 0; i < data.articlesATester.length; i++) {
      let at = data.articlesATester[i]
      if (testTabArticles.includes(at) === false) {
        erreursListeArticles.push(at)
      }
    }
  }

  if (erreursListeArticles.length === 0) {
    pvBar.articles.forEach((obj) => {
      articles[obj.name] = obj.id
    })

    // sélectionne quelques articles
    let articlesReferants = []
    // total des articles sélectionnés
    let totalPrixSelection = 0
    data.articlesATester.forEach(nom => {
      document.querySelector(`#pv${pvBar.id} bouton-article[uuid="${articles[nom]}"]`).shadowRoot.querySelector('.ele-conteneur').click()
      totalPrixSelection = totalPrixSelection + parseFloat(document.querySelector(`#pv${pvBar.id} bouton-article[uuid="${articles[nom]}"]`).getAttribute('prix'))
      let pkExiste = 0, pkExisteId = 0
      for (let i = 0; i < articlesReferants.length; i++) {
        if (articlesReferants[i].pk === articles[nom]) {
          pkExiste = 1
          pkExisteId = i
        }
      }
      if (pkExiste === 1) {
        articlesReferants[pkExisteId].qty++
      } else {
        let objReferant = {
          pk: articles[nom], qty: 1, pk_pdv: pvBar.id
        }
        articlesReferants.push(objReferant)
      }
    })
    let articlesSelectionnes = vue_pv.obtenirAchats(data.actionAValider).articles

    // console.log('articlesReferants = ', articlesReferants)
    // console.log('articlesSelectionnes = ', articlesSelectionnes)

    sys.trierTableauObjetCroissantFoncAttribut(articlesReferants, 'pk')
    sys.trierTableauObjetCroissantFoncAttribut(articlesSelectionnes, 'pk')

    // prix afficher sur bouton valider
    let brutPrixTotalBoutonValider = document.querySelector('#bt-valider-total').innerText
    let prixTotalBoutonValider = parseFloat(brutPrixTotalBoutonValider.substring(6, (brutPrixTotalBoutonValider.length - 2)))

    // test que la liste d'articles cliqués est égale à la liste obtenu par la fonction vue_pv.obtenirAchats
    // et que le total du bouton "Valider soit égal au total calculé lors des cliques de sélection
    if (JSON.stringify(articlesReferants, null, '\t') === JSON.stringify(articlesSelectionnes, null, '\t') && prixTotalBoutonValider === totalPrixSelection) {
      Test.enregistrerErreur(false, `- Liste d'articles sélectionnés identique à la liste de référence "${data.articlesATester}" et total correcte !`)
    } else {
      Test.enregistrerErreur(true, `. Erreur liste d'articles !`)
    }
  } else {
    Test.enregistrerErreur(true, `. Erreur liste, article(s) inconnu(s) "${ erreursListeArticles }" !`)
  }
}


export function selectionnerArticlesCommandes(liste) {
  let articles = document.querySelectorAll('#commandes-table-articles bouton-commande-article')
  let tabArticles = []
  for (let i = 0; i < articles.length; i++) {
    tabArticles.push(articles[i].getAttribute('data-nom'))
  }
  // console.log('tabArticles = ',tabArticles)
  for (let ls = 0; ls < liste.length; ls++) {
    let eleListe = liste[ls]
    if (tabArticles.includes(eleListe) === false) {
      Test.enregistrerErreur(true, `. L'article ${ eleListe } n'existe pas dans les commandes de cette table !`)
      break
    } else {
      let eleACliquer = document.querySelector(`#commandes-table-articles bouton-commande-article[data-nom="${ eleListe }"]`)
      // console.log(ls + ' -> ' + eleListe)
      eleACliquer.click()
    }

  }

}

function initCreditsCarteEtape2(tagId, typeMonnaie, quantite, fonction) {
  let monnaie = {
    principale: {uuid: 'a981ca30-19b6-4e29-9840-0b63aedc12aa', valeur: 20 }, // +20
    cadeau: {uuid: 'afe0b364-5c4b-474f-b0f2-1abe52985d9d', valeur: 5 } // +5 cadeau
  }
  let valeur = quantite * monnaie[typeMonnaie].valeur
  let nomMonnaie = glob.monnaie_principale_name + ' Cadeau'
  if (typeMonnaie === 'principale') {
    nomMonnaie = glob.monnaie_principale_name
  }
  let achats = {
    "articles": [{
      "pk": monnaie[typeMonnaie].uuid,
      "qty": quantite,
      "pk_pdv": "a3fd2b0b-aebe-4582-b269-880b828c62ff"
    }],
    "pk_responsable": "2f66bd25-d90c-4f83-9417-649a5a9ee5e8",
    "pk_pdv": "a3fd2b0b-aebe-4582-b269-880b828c62ff",
    "total": valeur,
    "hostname_client": "phenix",
    "moyen_paiement": "espece",
    "tag_id": tagId
  }
  let requete = {
    type: "post",
    url: "paiement",
    csrfToken: document.querySelector('input[name="csrfmiddlewaretoken"]').value,
    dataType: 'json',
    dataTypeReturn: 'json',
    attente: {
      largeur: 160,
      couleur: '#FFFFFF',
      nbc: 10,
      rpt: 10,
      epaisseur: 20
    },
    data: achats
  }
  sys.ajax(requete, function(retour,status) {
    if (status.code === 200) {
      enregistrerErreur(false, `- Carte "${ tagId }" initialisée a ${ valeur } ${ nomMonnaie } !`)
      fonction()
    } else {
      enregistrerErreur(true, `. Erreur, créditation carte "${ tagId }" !`)
      afficherBlockslogs()
    }
  })

}

// --- à remplacer ---
export function initCreditsCarte(tagId, typeMonnaie, quantite, fonction) {
  // vider carte
  let achats = {
    "articles": [{
      "pk": "82c32b8f-3927-4228-8327-9fb344b74089",
      "qty": 1,
      "pk_pdv": "a3fd2b0b-aebe-4582-b269-880b828c62ff"
    }],
    "pk_responsable": "2f66bd25-d90c-4f83-9417-649a5a9ee5e8",
    "pk_pdv": "a3fd2b0b-aebe-4582-b269-880b828c62ff",
    "total": 0,
    "hostname_client": "phenix",
    "moyen_paiement": "nfc",
    "tag_id": tagId
  }

  let requete = {
    type: "post",
    url: "paiement",
    csrfToken: document.querySelector('input[name="csrfmiddlewaretoken"]').value,
    dataType: 'json',
    dataTypeReturn: 'json',
    attente: {
      largeur: 160,
      couleur: '#FFFFFF',
      nbc: 10,
      rpt: 10,
      epaisseur: 20
    },
    data: achats
  }
  sys.ajax(requete, function(retour,status) {
    // sys.logValeurs({retour: retour, status: status})
    if (status.code === 200) {
      initCreditsCarteEtape2(tagId, typeMonnaie, quantite, fonction)
    }else {
      enregistrerErreur(true, `. Erreur, créditation carte "${ tagId }", etape "vidage carte" !`)
      afficherBlockslogs()
    }
  })
}
// --- fin à remplacer ---

/**
 * Vider une carte
 * @param {Object} data
 * @param {String} data.tagId tagId de la carte
 * @param {Boolean} data.msg Afficher ou pas un message
 * @returns {Promise<void>}
 */
function viderCarte(data) {
  return new Promise((resolve, reject) => {
    let pkResponsable = document.querySelector(`#products #pv${window.pv_uuid_courant}`).getAttribute('data-responsable-uuid')
    // vider carte
    let achats = {
      "articles": [{
        "pk": "82c32b8f-3927-4228-8327-9fb344b74089",
        "qty": 1,
        "pk_pdv": window.pv_uuid_courant
      }],
      "pk_responsable": pkResponsable,
      "pk_pdv": window.pv_uuid_courant,
      "total": 0,
      "hostname_client": glob.infosNavigateur.hostname,
      "moyen_paiement": "nfc",
      "tag_id": data.tagId
    }

    let requete = {
      type: "post",
      url: "paiement",
      csrfToken: document.querySelector('input[name="csrfmiddlewaretoken"]').value,
      dataType: 'json',
      dataTypeReturn: 'json',
      attente: {
        largeur: 160,
        couleur: '#FFFFFF',
        nbc: 10,
        rpt: 10,
        epaisseur: 20
      },
      data: achats
    }
    sys.ajax(requete, function (retour, status) {
      // sys.logValeurs({retour: retour, status: status})
      if (status.code === 200) {
        if (data.msg !== null) {
          enregistrerErreur(false, `- Vider carte "${data.tagId}" correcte !`)
          resolve(true)
        }
      } else {
        enregistrerErreur(true, `. Erreur, vider carte "${data.tagId}" !`)
        reject(false)
      }
    })
  })
}

/**
 * Créditer carte
 * @param {Object} data
 * @param {String} data.tagId tagId de la carte
 * @param {String} data.articleUuid uuid de l'article
 * @param {String} data.typeMonnaie 'principale' ou 'cadeau'
 * @param {Number} data.quantite nombre de fois créditer
 * @param {Boolean} data.msg Afficher ou pas un message
 * @returns {Promise<unknown>}
 */
export function crediterCarte(data) {
  return new Promise((resolve, reject) => {
    let pkResponsable = document.querySelector(`#products #pv${window.pv_uuid_courant}`).getAttribute('data-responsable-uuid')
    let pv = glob.data.filter(obj => obj.comportement === 'C').filter(obj => obj.name === 'Cashless')[0]
    let article = pv.articles.filter(obj => obj.id === data.articleUuid)[0]
    let total = article.prix * data.quantite
    // crediter carte
    let achats = {
      "articles": [{
        "pk": data.articleUuid,
        "qty": data.quantite,
        "pk_pdv": window.pv_uuid_courant
      }],
      "pk_responsable": pkResponsable,
      "pk_pdv": window.pv_uuid_courant,
      "total": total,
      "hostname_client": glob.infosNavigateur.hostname,
      "moyen_paiement": "nfc",
      "tag_id": data.tagId
    }

    let requete = {
      type: "post",
      url: "paiement",
      csrfToken: document.querySelector('input[name="csrfmiddlewaretoken"]').value,
      dataType: 'json',
      dataTypeReturn: 'json',
      attente: {
        largeur: 160,
        couleur: '#FFFFFF',
        nbc: 10,
        rpt: 10,
        epaisseur: 20
      },
      data: achats
    }
    sys.ajax(requete, function (retour, status) {
      console.log('------> crediter carte !')
      sys.logValeurs({retour: retour, status: status})
      console.log('------------------------------------------------')
      if (status.code === 200) {
        if (data.msg !== null) {
          enregistrerErreur(false, `- Créditer carte "${data.tagId}" de ${ total } correcte !`)
          resolve(true)
        }
      } else {
        enregistrerErreur(true, `. Erreur, créditer carte "${data.tagId}" de ${ total } !`)
        reject(false)
      }
    })
  })
}

/**
 * Initialiser une carte Nfc de tant de crédit
 * @param {Object} data
 * @param {String} data.tagId tagId de la carte
 * @param {String} data.articleUuid uuid de l'article
 * @param {String} data.typeMonnaie 'principale' ou 'cadeau'
 * @param {Number} data.quantite nombre de fois créditer
 * @param {Boolean} data.msg Afficher ou pas un message
 */
export async function carteInitCredits(data) {
  let resultat = await viderCarte(data)
  let resulta2 = await crediterCarte(data)
}

export function postEtapeMoyenComplementaire(data,foncRetour){
  // console.log('-> fonc postEtapeMoyenComplementaire :')

  let achats = glob.dataCarte1.options.achats
  achats.tag_id = glob.dataCarte1.retour.carte.tag_id
  achats.complementaire = {
    manque: glob.dataCarte1.retour.message.manque,
    moyen_paiement: data.moyenPaiement,
  }
  achats.moyen_paiement = 'nfc'

  if (data.moyenPaiement === 'nfc') {
    achats.complementaire.tag_id = data.tagId
    glob.dataCarte1.options.tagId2 = data.tagId
  }

  // console.log('----------------------------------------------');

  let csrfToken = document.querySelector('input[name="csrfmiddlewaretoken"]').value;
  let requete = {
    type: "post",
    url: "paiement",
    csrfToken: csrfToken,
    dataType: 'json',
    dataTypeReturn: 'json',
    attente: {
      largeur: 160,
      couleur: '#FFFFFF',
      nbc: 10,
      rpt: 10,
      epaisseur: 20
    },
    data: achats
  }
  sys.ajax(requete, (retour,status) => {
    gererRetourPostPaiement(retour, status,glob.dataCarte1.options)
    foncRetour(retour,status)
  })
}

export function selectionnerTable(data) {
  try {
    let id = -1
    let eles = document.querySelectorAll(`#tables-liste .table-bouton`)
    for (let i = 0; i < eles.length; i++) {
      let ele = eles[i]
      let nomTable = ele.querySelector(`div[class~="table-nom"]`).innerHTML.trim()
      if (data.nom === nomTable) {
        id = i
        break
      }
    }

    if (id !== -1) {
      eles[id].click()
      if (data.msg === undefined) {
        data.msg = `Sélectionner la table "${ data.nom }" !`
      }
      enregistrerErreur(null, data.msg )
    } else {
      enregistrerErreur(true, `. Impossible de sélectionner une table, nom inconnue !` )
    }
  } catch (err) {
    enregistrerErreur(true, err )
  }
}

/**
 * Sélectionner des articles dans un point de ventes
 * La sélection se fait par 'nom' ou 'uuid', data.typeSelection = 'nom' ou 'uuid'
 * @param {object} - data
 */
export function selectionnerArticlesPv(data) {
  for (let i = 0; i < data.liste.length; i++) {
    let infosArticle = data.liste[i].split(',')
    // avoir 3 données nombre, nom, uuid
    if (infosArticle.length !== 4) {
      enregistrerErreur(true, `. Manque de données pour la sélection d'un article !` )
      break
    }
    let nbArticles = parseInt(infosArticle[0])
    let nomArticle = infosArticle[1]
    let uuidArticle = infosArticle[2]

    // nom uuid
    if (nomArticle === '' && uuidArticle === ''){
      enregistrerErreur(true, `. Pas de "nom" ou "uuid", impossible de sélectionner cer article !`)
      break
    }
    let choixSelection = { attribut: 'uuid', valeur: uuidArticle }
    if ((nomArticle !== '' && uuidArticle !== '') || (nomArticle !== '' && uuidArticle === '')) {
      choixSelection = { attribut: 'nom', valeur: nomArticle }
    }
    let selecteur  = `#products #pv${ data.uuidPv } bouton-article[${ choixSelection.attribut }="${ choixSelection.valeur }"]`
    if(nomArticle === '' && uuidArticle !== '') {
      nomArticle = document.querySelector(`#products #pv${ data.uuidPv } bouton-article[uuid="${ uuidArticle }"]`).getAttribute('nom')
      data.liste[i] = `${ nbArticles },${ nomArticle },${ uuidArticle }`
    }
    for (let nbC = 0; nbC < nbArticles; nbC++) {
      document.querySelector(selecteur).click()
    }
  }
}