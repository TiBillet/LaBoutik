window.orthoPaiement = {
  espece: 'cash',
  carte_bancaire: 'cb',
  nfc: 'cashless',
  CH: 'cheque'
}

async function showButtonPrintTicket(retour, options) {
  // ne pas afficher ce bouton dans ce context
  const action = options.actionAValider !== undefined ? options.actionAValider : 'unknown'
  const noShowInThisAction = ["envoyer_preparation"]
  if (await websocketOnAndhasSunmiPrinter && !noShowInThisAction.includes(action)) {
    const btUuid = sys.uuidV4()
    window['xhValsAchats' + btUuid] = JSON.stringify(retour)
    // bt print
    return `<bouton-basique traiter-texte="1" texte="TICKET|2rem" couleur-fond="#2d20e2" icon="fa-print||2.5rem" width="200px" height="86px" 
      hx-post="/htmx/sales/print_ticket_purchases/" hx-trigger="click"
      hx-target="#print-ticket-status-${btUuid}" hx-swap="innerHTML"
      hx-vals='${window['xhValsAchats' + btUuid]}' style="margin-top:8px;min-width:200px;">
    </bouton-basique>
    <div id="print-ticket-status-${btUuid}"></div>`
  } else {
    return ''
  }
}

function gestionTransactionFondsInsuffisants(retour, options) {
  // console.log('--- fonction gestionTransactionFondsInsuffisants :')
  // sys.logValeurs({ retour, options })

  let boutons = ''
  let msg = `<div class="BF-col-uniforme message-fonds-insuffisants">`
  let rep_infos = document.querySelector('#pv' + pv_uuid_courant)
  let accepte_especes = rep_infos.getAttribute('data-accepte-especes')
  let accepte_carte_bancaire = rep_infos.getAttribute('data-accepte-carte-bancaire')
  let totalManque = retour.message.manque
  const paymentBtWidth = 280
  const paymentBtHeight = 90

  options['totalCarte2'] = totalManque

  glob.dataCarte1 = {
    retour: retour,
    options: options
  }

  if (retour.route === 'transcation_nfc_fonds_insuffisants') {
    // la première carte n'a pas les fonds
    if (accepte_especes === 'true') {
      // boutons += `<bouton-basique class="test-fonds-insuffisants-espece" traiter-texte="1" texte="ESPECE|2rem||cash-uppercase,[TOTAL] ${totalManque} [€]|1.5rem||total-uppercase;currencySymbol" width="400px" height="120px" couleur-fond="#3b567f" icon="fa-coins||2.5rem" onclick="fn.popupConfirme('espece', 'ESPECE', 'vue_pv.validerEtapeMoyenComplementaire')" style="margin-top:16px;"></bouton-basique>`
      boutons += paymentBt({
        width: paymentBtWidth,
        height: paymentBtHeight,
        backgroundColor: "#3b567f",
        textColor: "#FFFFFF",
        icon: "fa-coins",
        methods: ["fn.popupConfirme('espece', 'ESPECE', 'vue_pv.validerEtapeMoyenComplementaire')"],
        currency: { name: "ESPECE", tradIndex: 'cash', tradOption: 'uppercase' },
        total: totalManque,
        cssClass: ["test-fonds-insuffisants-espece"]
      })
    }
    if (accepte_carte_bancaire === 'true') {
      // boutons += `<bouton-basique class="test-fonds-insuffisants-cb" traiter-texte="1"  texte="CB|2rem||cb-uppercase,[TOTAL] ${totalManque} [€]|1.5rem||total-uppercase;currencySymbol" width="400px" height="120px" couleur-fond="#3b567f" icon="fa-coins||2.5rem" onclick="fn.popupConfirme('carte_bancaire', 'CB', 'vue_pv.validerEtapeMoyenComplementaire')" style="margin-top:16px;"></bouton-basique>`
      boutons += paymentBt({
        width: paymentBtWidth,
        height: paymentBtHeight,
        backgroundColor: "#3b567f",
        textColor: "#FFFFFF",
        icon: "fa-credit-card",
        methods: ["fn.popupConfirme('carte_bancaire', 'CB', 'vue_pv.validerEtapeMoyenComplementaire')"],
        currency: { name: "CB", tradIndex: 'cb', tradOption: 'uppercase' },
        total: totalManque,
        cssClass: ["test-fonds-insuffisants-cb"]
      })
    }

    // 2ème carte cashless
    // boutons += `<bouton-basique class="test-fonds-insuffisants-nfc" traiter-texte="1" texte="[autre] [CARTE]|2rem||other-uppercase;card-uppercase,(CASHLESS)|1.2rem,[TOTAL] ${totalManque} [€]|1.5rem||total-uppercase;currencySymbol" width="400px" height="120px" couleur-fond="#3b567f" icon="fa-coins||2.5rem" onclick="fn.popupAnnuler();vue_pv.validerEtapeMoyenComplementaire('nfc')" style="margin-top:16px;margin-bottom:40px;"></bouton-basique>`
    boutons += paymentBt({
      width: paymentBtWidth,
      height: paymentBtHeight,
      backgroundColor: "#3b567f",
      textColor: "#FFFFFF",
      icon: "fa-address-card",
      methods: ["fn.popupAnnuler();vue_pv.validerEtapeMoyenComplementaire('nfc')"],
      currency: [{ name: "AUTRE", tradIndex: 'other', tradOption: 'uppercase' }, { name: "CARTE", tradIndex: 'card', tradOption: 'uppercase' }],
      addHtmlContent: '<div style="font-size:1.2rem">(CASHLESS)</div>',
      total: totalManque,
      cssClass: ["test-fonds-insuffisants-nfc"],
      paymentBtForceHeight: 100
    })

    msg += `
      <div class="popup-titre1 test-return-title" data-i8n="insufficientFunds,capitalize">Fonds insuffisants.</div>
      <div class="popup-msg1 test-return-missing-cash">
        <span data-i8n="isMissing,capitalize">Il manque</span> <span id="test-manque-monnaie">${retour.message.manque}</span> <span>${getTranslate('currencySymbol', null, 'methodCurrency')}</span>
      </div>
      <div class="popup-msg1 test-return-fisrt-card-content">
        ${retour.carte.membre_name} <span data-i8n="has">a</span> <span id="test-carte-total-monnaie">${retour.carte.total_monnaie}</span>
      </div>
      <div class="popup-msg1 test-returm-possible-purchase" data-i8n="possiblePurchaseBy,capitalize">Achat possible par :</div>
    `
  } else {
    // console.log("-> Fonds insuffisants sur deuxieme carte")
    // la deuxième carte n'a pas les fonds
    msg += `<div class="popup-titre1" data-i8n="insufficientFunds,capitalize">Fonds insuffisants.</div>
    <div class="popup-titre1" data-i8n="onSecondCard">sur deuxieme carte</div>
    <div class="popup-msg1">
      <span data-i8n="isMissing,capitalize">Il manque</span> <span id="test-manque-monnaie">${retour.message.manque}</span> <span>${getTranslate('currencySymbol', null, 'methodCurrency')}</span>
    </div>`
  }

  boutons += `
    <div class="popup-conteneur-bt-retour BF-col">
      <bouton-basique id="popup-retour" traiter-texte="1" texte="RETOUR|2rem||return-uppercase" couleur-fond="#3b567f" icon="fa-undo-alt||2.5rem" width="400px" height="120px"  onclick="fn.popupAnnuler();" style="margin-top:16px;"></bouton-basique>
    </div>
  `
  msg += `</div>`

  // affichage du popup
  fn.popup({ message: msg, boutons: boutons, type: 'danger' })
}

function sortAssets(a, b) {
  /*
  if (a.monnaie_name.includes("cadeau"))
  */
}

function messageRetourAssets(retour) {
  // console.log('-> fonction messageRetourAssets')
  let assets, fragmentHtml = '', enumAssets = ''
  if (retour.carte !== undefined) {
    assets = retour.carte.assets
  } else {
    assets = retour.assets
  }
  // sys.logJson('assets = ', assets)
  let valAssetsTest = 0
  for (let i = 0; i < assets.length; i++) {
    let valeurAsset = parseFloat(assets[i].qty)
    let nomAsset = assets[i].monnaie_name
    let categorie = assets[i].categorie.toLowerCase()
    if (valeurAsset > 0) {
      valAssetsTest = 1
      enumAssets += `<div class="popup-msg1 test-return-monnaie-${categorie}">- <span class="test-return-nom-monnaie nom-monnaie-item${i}">${nomAsset}</span> : <span class="test-return-valeur-monnaie valeur-monnaie-item${i}">${valeurAsset} </span><span>${getTranslate('currencySymbol', null, 'methodCurrency')}</span></div>`
    }
  }
  if (valAssetsTest === 1) {
    // fragmentHtml = `<div class="popup-msg1"><span data-i8n="including">dont</span> :</div>`
    fragmentHtml = `<div class="popup-msg1" style="margin-top: 1rem;"><span data-i8n="totalCardWallet">total portefeuille carte</span> :</div>`
  }
  fragmentHtml += enumAssets + '<div style="margin-BOTTOM: 1rem;"></div>'
  return fragmentHtml
}

function messageRetourCarte(retour, options) {
  // console.log('-> fonction messageRetourCarte !')
  // sys.logValeurs({retour: retour, options: options})
  let nbArticles = options.achats.articles.length
  const translateAchat = getTranslate('purchase') === '' ? "achat" : getTranslate('purchase')
  let motsPourAchat = nbArticles > 1 ? `${translateAchat}s` : translateAchat

  let fragmentHtml = ''
  if (retour.carte) {
    // total sur carte avant achats
    if (retour.total_sur_carte_avant_achats) {
      fragmentHtml += `<div class="popup-msg1 test-carte-avant-achats">
        <span data-i8n="on,capitalize">Sur</span> <span data-i8n="card">carte</span> <span data-i8n="before">avant</span>
         ${motsPourAchat} : <span id="test-total-carte-avant-achats">${retour.total_sur_carte_avant_achats}</span> 
         ${getTranslate('currencySymbol', null, 'methodCurrency')}
      </div>`
    }
    // total acaht(s)
    if (retour.somme_totale) {
      let moyenDePaiement = window.orthoPaiement[options.achats.moyen_paiement]
      if (options.achats.complementaire !== undefined) {
        moyenDePaiement = window.orthoPaiement[options.achats.complementaire.moyen_paiement]
      }
      fragmentHtml += `<div class="popup-msg1 test-total-achats">
        <span data-i8n="total,capitalize">Total</span> (${moyenDePaiement}) : <span id="test-somme-payee">${retour.somme_totale}</span> ${getTranslate('currencySymbol', null, 'methodCurrency')}
      </div>`
    }
    // reste sur carte
    if (retour.carte.total_monnaie) {
      fragmentHtml += `<div class="popup-msg1 test-carte-apres-achats">
      <span data-i8n="rest,capitalize">Reste</span> <span data-i8n="on">sur</span> <span data-i8n="card">carte</span> : <span id="test-total-carte">${retour.carte.total_monnaie}</span> 
      ${getTranslate('currencySymbol', null, 'methodCurrency')}
      </div>`
    }
  }
  fragmentHtml += messageRetourAssets(retour)
  return fragmentHtml
}


/**
 * Afficher des infos de retour après une prise de commande
 * @param {Object} retour = données reçues de la requète
 * @param {Object} status = etat de la requète
 * @param {Object} options = données avant le lancement de la requète
 */
async function afficherRetourEnvoyerPreparation(retour, status, options) {
  // console.log('-> fonc afficherRetourEnvoyerPreparation !')
  // sys.logValeurs({ retour: retour, status: status, options: options })
  let msg = '', msgPaye = '', msgDifErreur = '', typeMsg = 'succes', fonction = '', msgAssets = '', msgTotalCarteApresAchats = '',
    msgTotalCartesAvantAchats = '', msgEspece = ''

  if (status.code === 200) {
    // fonds inssufisants
    if (typeof retour.message === 'object') {
      gestionTransactionFondsInsuffisants(retour, options)
    } else {
      // console.log('totalCarte2 = ', options.totalCarte2)
      vue_pv.rezet_commandes()
      if (options.actionAValider === 'envoyer_preparation_payer') {
        let infoTotal = options.achats.total
        if (options.totalCarte2 !== undefined) {
          infoTotal = options.totalCarte2
        }
        let moyenDePaiement = `(<span data-i8n="${orthoPaiement[options.achats.moyen_paiement]}"></span>)`
        if (options.achats.complementaire !== undefined) {
          moyenDePaiement = `(<span data-i8n="${orthoPaiement[options.achats.complementaire.moyen_paiement]}"></span>)`
        }
        msgPaye = `<div class="popup-msg1 test-return-total-achats">
          <span data-i8n="total,capitalize">Total</span>${moyenDePaiement} <span id="test-somme-payee">${infoTotal}</span> <span>${getTranslate('currencySymbol', null, 'methodCurrency')}</span>
        </div>`

        if (retour.carte) {
          // assets
          msgAssets = messageRetourAssets(retour)
          // total monnaie sur carte
          msgTotalCarteApresAchats = `<div class="popup-msg1 test-return-post-purchase-card">${retour.carte.membre_name} - <span data-i8n="postPurchaseCard">carte après achats</span> ${retour.carte.total_monnaie} </span>
          <span>${getTranslate('currencySymbol', null, 'methodCurrency')}</span></div>`

          // total sur carte avant achats
          console.log('options.achats.complementaire =', options.achats.complementaire)
          if (options.achats.complementaire === undefined) {
            if (retour.total_sur_carte_avant_achats !== undefined && retour.total_sur_carte_avant_achats !== null) {
              // pas de complémentaire
              msgTotalCartesAvantAchats = `<div class="popup-msg1 test-return-pre-purchase-card">${retour.carte.membre_name} - <span data-i8n="prePurchaseCard">carte avant achats</span> ${retour.total_sur_carte_avant_achats} 
              <span>${getTranslate('currencySymbol', null, 'methodCurrency')}</span></div>`
            }
          } else {
            // complémentaire nfc
            if (options.achats.complementaire.moyen_paiement === "nfc") {
              msgTotalCartesAvantAchats = `<div class="popup-msg1 test-return-purchase-cards"><span data-i8n="cardsTotal,capitalize">Total des cartes</span> ${retour.total_sur_carte_avant_achats} 
              <span>${getTranslate('currencySymbol', null, 'methodCurrency')}</span></div>`
            }
          }
        }
        // gestion moyen de paiement unique  "espèce", somme à rendre
        if (options.sommeDonnee !== undefined) {
          const totalAchat = parseFloat(options.achats.total)
          const sommeDonnee = parseFloat(options.sommeDonnee)
          const resultat = new Big(sommeDonnee).minus(totalAchat)
          console.log('-> sommeDonnee =', sommeDonnee, '  --  type =', typeof (sommeDonnee));

          if (sommeDonnee > 0) {
            msgEspece = `<div class="popup-msg1 test-return-given-sum" style="margin-top:2rem">
            <span data-i8n="givenSum">Somme donnée</span>
            <span>${sommeDonnee}</span>
            <span>${getTranslate('currencySymbol', null, 'methodCurrency')}</span>
          </div>
          <div class="test-return-change" style="font-size: 2rem;font-weight: bold;">
            <span data-i8n="change,capitalize">monnaie à rendre</span>
            <span role="status" aria-label="change">${resultat}</span>
            <span>${getTranslate('currencySymbol', null, 'methodCurrency')}</span>
          </div>`
          }
        }
      }

      msg = `
        <div class="BF-col-uniforme l100p h100p">
          <div class="BF-col">
            <div class="popup-titre1 retour-transaction-ok test-return-title-content">
              <span data-i8n="transaction,capitalize">Transaction</span> <span data-i8n="ok">Ok</span>
            </div>
            <div class="popup-msg1 test-return-msg-prepa" data-i8n="sentInPreparation,capitalize">Envoyée en préparation.</div>
            ${msgPaye}
            ${msgTotalCartesAvantAchats}
            ${msgTotalCarteApresAchats}
            ${msgAssets}
            ${msgEspece}
            ${ await showButtonPrintTicket(retour, options) }
          </div>
          <bouton-basique id="popup-retour" traiter-texte="1" texte="RETOUR|2rem||return-uppercase" couleur-fond="#3b567f" icon="fa-undo-alt||2.5rem" width="400px" height="120px" onclick="fn.popupAnnuler();vue_pv.initMode();"></bouton-basique>
        </div>`
      // affichage du popup
      fn.popup({ message: msg, type: typeMsg })
    }
  } else {
    if (options.actionAValider === 'envoyer_preparation_payer') {
      msgDifErreur = `<div class="popup-msg1 test-msg-paye-erreur">
        (<span data-i8n="errorMessageCommand3,capitalize" style="white-space: pre-line; text-align: center;">Après envoi en préparation plus paiementen une seule fois</span>)
      </div>`
    } else {
      msgDifErreur = `<div class="popup-msg1">
      (<span data-i8n="errorMessageCommand2,capitalize" style="white-space: pre-line; text-align: center;">Après envoi en préparation sans payer</span>)
      </div>`
    }

    typeMsg = 'attent'
    msg = `
      <div class="BF-col-uniforme l100p h100p">
        <div class="BF-col">
          <div class="popup-titre1">
            <span data-i8n="error,capitalize">Erreur</span> <span data-i8n="order">Commande !</span>
          </div>
          ${msgDifErreur}
        </div>
        <bouton-basique id="popup-retour" traiter-texte="1" texte="RETOUR|2rem||return-uppercase" couleur-fond="#3b567f" icon="fa-undo-alt||2.5rem" width="400px" height="120px" onclick="fn.popupAnnuler();vue_pv.afficherPointDeVentes('${pv_uuid_courant}');"></bouton-basique>
      </div>
    `
    // affichage du popup
    fn.popup({ message: msg, type: typeMsg })
  }
}

/**
 * Redirection vers la page paiement d'une commande
 * @param {Object} retour = données reçues de la requète
 * @param {Object} status = etat de la requète
 * @param {Object} options = données avant le lancement de la requète
 */
// TODO: mettre cette fonction dans restaurant.js
function aiguillagePagePaiementCommande(retour, status, options) {
  console.log(`-> fonction aiguillagePagePaiementCommande !`)
  sys.logValeurs({ retour: retour, status: status, options: options })

  if (status.code === 200) {
    // reset articles sélectionnés
    vue_pv.rezet_commandes()

    // sélectionner l'identifiant de la table
    let idTable = null
    if (retour.nouvelle_table === undefined) {
      idTable = options.achats.pk_table
    } else {
      idTable = retour.nouvelle_table
    }
    restau.afficherCommandesTable(idTable)

  } else {
    let fonction = `onclick="fn.popupAnnuler();vue_pv.afficherPointDeVentes('${pv_uuid_courant}');"`
    let msg = `
      <div class="BF-col-uniforme l100p h100p">
        <div class="BF-col">
          <div class="popup-titre1">
            <span data-i8n="error,capitalize">Erreur</span> <span data-i8n="order">Commande !</span>
          </div>
          <div class="popup-msg1" data-i8n="errorMessageCommand1,capitalize" style="white-space: pre-line; text-align: center;">
            Après envoi en préparation\net allez page de paiement.
          </div>
        </div>
        <bouton-basique id="popup-retour" traiter-texte="1" texte="RETOUR|2rem||return-uppercase" couleur-fond="#3b567f" icon="fa-undo-alt||2.5rem" width="400px" height="120px" ${fonction}></bouton-basique>
      </div>
    `
    // affichage du popup
    fn.popup({ message: msg, type: 'attent' })
  }
}

/**
 * R
 * @param {Object} retour = données reçues de la requète
 * @param {Object} status = etat de la requète
 * @param {Object} options = données avant le lancement de la requète
 */
async function infosPaiementRetourTable(retour, status, options) {
  console.log(`-> fonction infosPaiementRetourTable !`)
  sys.logValeurs({ retour: retour, status: status, options: options })
  let typeMsg = 'succes', msg = '', fonction = ''
  if (status.code === 200) {
    if (retour.message === undefined) {
      // reset articles sélectionnés
      vue_pv.rezet_commandes()

      // sélectionner l'identifiant de la table
      let idTable = null
      if (retour.nouvelle_table === undefined) {
        idTable = options.achats.pk_table
      } else {
        idTable = retour.nouvelle_table
        // mise à jour idTable venat du retour serveur
        glob.tableEnCours = { typeValeur: 'idTable', valeur: idTable }
      }
      fonction = `onclick="fn.popupAnnuler();restau.afficherCommandesTable(${idTable});"`
      let msgRetourCarte = '', msgDefaut = ''
      if (retour.carte !== undefined) {
        msgRetourCarte = messageRetourCarte(retour, options)
      } else {
        let moyensDePaiement = `(<span data-i8n="${orthoPaiement[options.achats.moyen_paiement]}"></span>)`
        msgDefaut += `<div class="popup-msg1 test-total-achats">
          <span data-i8n="total,capitalize">Total</span> ${moyensDePaiement}<span> ${retour.somme_totale}</span> <span>${getTranslate('currencySymbol', null, 'methodCurrency')}</span>
        </div>`
      }

      if (options.sommeDonnee !== undefined) {
        const totalAchat = parseFloat(options.achats.total)
        const sommeDonnee = parseFloat(options.sommeDonnee)
        const resultat = new Big(sommeDonnee).minus(totalAchat)
        if (sommeDonnee > 0) {
          msgDefaut += `<div class="popup-msg1 test-return-given-sum" style="margin-top:2rem">
          <span data-i8n="givenSum,capitalize">Somme donnée</span>
          <span>${sommeDonnee}</span>
          <span>${getTranslate('currencySymbol', null, 'methodCurrency')}</span>
        </div>
        <div class="test-return-change" style="font-size: 2rem;font-weight: bold;">
          <span data-i8n="change,capitalize">monnaie à rendre</span>
          <span role="status" aria-label="change">${resultat}</span>
          <span>${getTranslate('currencySymbol', null, 'methodCurrency')}</span>
        </div>`
        }
      }

      msg = `
      <div class="BF-col-uniforme l100p h100p">
        <div class="BF-col">
          <div class="popup-titre1 test-return-title-content">
            <span data-i8n="transaction,capitalize">Transaction</span> <span data-i8n="ok">Ok</span>
          </div>
          <div class="BF-col">
            ${msgDefaut} ${msgRetourCarte}
            ${await showButtonPrintTicket(retour, options)}
          </div>
        </div>
        <bouton-basique id="popup-retour" traiter-texte="1" texte="RETOUR|2rem||return-uppercase" couleur-fond="#3b567f" icon="fa-undo-alt||2.5rem" width="400px" height="120px" ${fonction}></bouton-basique>
      </div>`

      // affichage du popup
      fn.popup({ message: msg, type: typeMsg })
      glob.dataCarte1 = null
    } else { // fonds insuffisants
      gestionTransactionFondsInsuffisants(retour, options)
    }
  } else {
    fonction = `onclick="fn.popupAnnuler();"`
    typeMsg = 'attent'
    msg = `
      <div class="BF-col-uniforme l100p h100p">
        <div class="BF-col">
          <div class="popup-titre1">
            <span data-i8n="error,capitalize">Erreur</span>
            <span> ${status.code}</span>
          </div>
          <div class="popup-msg1" data-i8n="payment">Paiement !</div>
          <div class="popup-msg1">actionAValider = ${options.actionAValider}</div>
        </div>
        <bouton-basique id="popup-retour" traiter-texte="1" texte="RETOUR|2rem||return-uppercase" couleur-fond="#3b567f" icon="fa-undo-alt||2.5rem" width="400px" height="120px" ${fonction}></bouton-basique>
      </div>
    `
    // affichage du popup
    fn.popup({ message: msg, type: typeMsg })
  }
}

async function afficherRetourVenteDirecte(retour, status, options) {
  // console.log(`-> fonction afficherRetourVenteDirecte !`)
  // sys.logValeurs({ retour: retour, status: status, options: options })
  let typeMsg = 'succes', msgDefaut = '', msg = '', fonction = ''


  if (status.code === 200) {
    if (retour.message === undefined) {
      // reset articles sélectionnés
      vue_pv.rezet_commandes()
      fonction = `onclick="fn.popupAnnuler();"`

      const translateAchat = getTranslate('purchase') === '' ? "achat" : getTranslate('purchase')
      const translateTotal = getTranslate('total') === '' ? "total" : getTranslate('total', 'capitalize')
      let nbArticles = options.achats.articles.length
      // let msgTotalAchat = nbArticles > 1 ? `${translateTotal} ${translateAchat}s` : `${translateTotal} ${translateAchat}`
      // let motsPourAchat = nbArticles > 1 ? `${translateAchat}s` : translateAchat

      // méthode "VenteArticle"
      msgDefaut = `<div class="popup-titre1 retour-transaction-ok test-return-title-content">
        <span data-i8n="transaction,capitalize">Transaction</span> <span data-i8n="ok">Ok</span>
      </div>`

      // envoie les indexs de traduction des monnaies utilisées
      let moyensDePaiement = `(<span data-i8n="${orthoPaiement[options.achats.moyen_paiement]}"></span>`
      if (options.achats.complementaire !== undefined) {
        moyensDePaiement += `/<span data-i8n="${orthoPaiement[options.achats.complementaire.moyen_paiement]}"></span>`
      }
      moyensDePaiement += ')'

      if (options.methodes[0] === "VenteArticle" || options.methodes[0] === "AjoutMonnaieVirtuelle") {
        // affiche le total et la ou les monnaies utilisées
        msgDefaut += `<div class="test-return-total-achats" style="font-size: 2rem;font-weight: bold;">
          <span data-i8n="total,capitalize">Total</span>${moyensDePaiement}<span> ${retour.somme_totale}</span> <span>${getTranslate('currencySymbol', null, 'methodCurrency')}</span>
        </div>`

        if (options.achats.complementaire === undefined) {
          const totalAchat = parseFloat(options.achats.total)

          // total sur carte lors d'un achat de monnaies virtuelles
          if (options.methodes[0] === "AjoutMonnaieVirtuelle") {
            const surCarte = new Big(retour.carte.total_monnaie)
            msgDefaut += `<div class="popup-msg1 test-return-total-carte">${retour.carte.membre_name} - <span data-i8n="card">carte</span> ${surCarte} <span>${getTranslate('currencySymbol', null, 'methodCurrency')}</span></div>`
          }

          if (retour.carte) {
            msgDefaut += messageRetourAssets(retour)
          }

          // gestion moyen de paiement unique  "espèce", somme à rendre
          if (options.achats.moyen_paiement === 'espece') {
            const sommeDonnee = parseFloat(options.sommeDonnee)
            const resultat = new Big(sommeDonnee).minus(totalAchat)
            // const sumValue = (new Big(sum)).valueOf()
            if (sommeDonnee > 0) {
              msgDefaut += `<div class="popup-msg1 test-return-given-sum" style="margin-top:2rem">
              <span data-i8n="givenSum">Somme donnée</span>
              <span>${sommeDonnee}</span>
              <span>${getTranslate('currencySymbol', null, 'methodCurrency')}</span>
            </div>
            <div class="test-return-change" style="font-size: 2rem;font-weight: bold;">
              <span data-i8n="change,capitalize">monnaie à rendre</span>
              <span role="status" aria-label="change">${resultat}</span>
              <span>${getTranslate('currencySymbol', null, 'methodCurrency')}</span>
            </div>`
            }
          }

          // gestion moyen de paiement unique  "nfc"
          if (options.achats.moyen_paiement === 'nfc') {
            const surCarteAvantAchat = new Big(retour.total_sur_carte_avant_achats)
            const surCarteApresAchat = new Big(retour.carte.total_monnaie)
            msgDefaut += `<div class="popup-msg1 test-return-pre-purchase-card">${retour.carte.membre_name} - <span data-i8n="prePurchaseCard">carte avant achats</span> 
            ${surCarteAvantAchat} <span>${getTranslate('currencySymbol', null, 'methodCurrency')}</span></div>
            <div class="popup-msg1 test-return-post-purchase-card">${retour.carte.membre_name} - <span data-i8n="postPurchaseCard">carte après achats</span> ${surCarteApresAchat} 
            <span>${getTranslate('currencySymbol', null, 'methodCurrency')}</span></div>`
          }

        } else {
          // --- complémentaires ---
          // achat initial nfc, complémentaire avant achats
          if (retour.carte !== undefined) {
            const surCarteAvantAchat = new Big(retour.somme_totale).minus(options.achats.complementaire.manque)
            msgDefaut += `<div class="popup-msg1 test-return-pre-purchase-card">${retour.carte.membre_name} - <span data-i8n="prePurchaseCard">carte avant achats</span> ${surCarteAvantAchat} 
            <span>${getTranslate('currencySymbol', null, 'methodCurrency')}</span></div>`
          }
          // complémentaire espèce
          if (options.achats.complementaire.moyen_paiement === 'espece') {
            // paiement complémentaire espèce
            const sommeDonnee = parseFloat(options.sommeDonnee)

            msgDefaut += `<div class="popup-msg1 test-return-additional"><span data-i8n="additional,capitalize">Complémentaire</span> ${options.achats.complementaire.manque} 
            <span>${getTranslate('currencySymbol', null, 'methodCurrency')}</span> <span data-i8n="in">en</span> <span data-i8n="cash"></span></div>
            <div class="popup-msg1 test-total-achats">`
            if (sommeDonnee > 0) {
              msgDefaut += `<span data-i8n="givenSum">Somme donnée</span>
                <span>${sommeDonnee}</span>
                <span>${getTranslate('currencySymbol', null, 'methodCurrency')}</span>`
            }
            msgDefaut += '</div><br>'

            // --- complémentaire après achats ---
            // achat initial nfc
            if (retour.carte !== undefined) {
              msgDefaut += `<div class="popup-msg1 test-return-post-purchase-card">${retour.carte.membre_name} - <span data-i8n="postPurchaseCard">carte après achats</span> 0 <span>${getTranslate('currencySymbol', null, 'methodCurrency')}</span></div>`
            }

            if (sommeDonnee > 0) {
              const sommeManquante = parseFloat(options.achats.complementaire.manque)
              const resultat = new Big(sommeDonnee).minus(sommeManquante)
              msgDefaut += `<div class="test-return-change" style="margin-top:2rem; font-size: 2rem;font-weight: bold;">
                <span data-i8n="change,capitalize">monnaie à rendre</span>
                <span role="status" aria-label="change">${resultat}</span>
                <span>${getTranslate('currencySymbol', null, 'methodCurrency')}</span>
              </div>`
            }
          }

          // complémentaire nfc
          if (options.achats.complementaire.moyen_paiement === 'nfc') {
            msgDefaut += `<div class="popup-msg1 test-return-additional">
              <span data-i8n="additional,capitalize">Complémentaire</span> ${options.achats.complementaire.manque} 
              <span>${getTranslate('currencySymbol', null, 'methodCurrency')}</span> <span data-i8n="in">en</span> <span data-i8n="cashless"></span>
            </div>
            <div class="popup-msg1 test-return-post-purchase-card">
              <span>${retour.carte.membre_name} - <span data-i8n="postPurchaseCard">carte après achats</span> 0 </span>
              <span>${getTranslate('currencySymbol', null, 'methodCurrency')}</span>
            </div>`
          }

          // complémentaire carte bancaire
          if (options.achats.complementaire.moyen_paiement === 'carte_bancaire') {
            msgDefaut += `<div class="popup-msg1 test-return-additional">
            <span data-i8n="additional,capitalize">Complémentaire</span> ${options.achats.complementaire.manque} 
            <span>${getTranslate('currencySymbol', null, 'methodCurrency')}</span> <span data-i8n="in">en</span> <span data-i8n="cb"></span>
            </div>
            <div class="popup-msg1 test-return-post-purchase-card">
              <span>${retour.carte.membre_name} - <span data-i8n="postPurchaseCard">carte après achats</span> 0 </span>
              <span>${getTranslate('currencySymbol', null, 'methodCurrency')}</span>
            </div>`
          }
        }
      }

      if (options.methodes[0] === "AjoutMonnaieVirtuelleCadeau" && retour.carte) {
        msgDefaut += messageRetourAssets(retour)
      }

      // vider une carte
      if (options.methodes[0] === "ViderCarte") {
        msgDefaut = `
          <div class="popup-titre1 test-return-reset" data-i8n="clearingCardOk,capitalize">Vidage carte OK !</div>
          <div class="popup-msg1 test-msg-vider-carte">
            <span data-i8n="toRepay,capitalize">A rembourser</span> : ${retour.somme_totale} 
            <span>${getTranslate('currencySymbol', null, 'methodCurrency')}</span>
          </div>
        `
      }

      // adhésion
      if (options.methodes[0] === "Adhesion") {
        let msgCotisation = ''
        if (retour.carte !== undefined && retour.carte !== null) {
          msgCotisation = `
            <div class="popup-msg1">
              <span data-i8n="member">membre</span> : <span class="test-return-membre-name">${retour.carte.membre_name}</span>
            </div>
            <div class="popup-msg1 test-msg-adhesion-date">${retour.carte.cotisation_membre_a_jour}</div>
          `
        }

        msgDefaut = `<div class="popup-titre1 test-return-title-content" data-i8n="membership,capitalize">Adhésion</div>
        ${msgCotisation}
        <div class="test-return-total-achats" style="font-size: 2rem;font-weight: bold;">
          <span data-i8n="total,capitalize">Total</span>${moyensDePaiement}<span> ${retour.somme_totale}</span> 
          <span>${getTranslate('currencySymbol', null, 'methodCurrency')}</span>
        </div>`

        // paiement espèce, somme donnée; pas de complémentaire
        if (options.achats.complementaire === undefined && options.achats.moyen_paiement === 'espece') {
          const totalAchat = parseFloat(options.achats.total)
          const sommeDonnee = parseFloat(options.sommeDonnee)
          const resultat = new Big(sommeDonnee).minus(totalAchat)
          // const sumValue = (new Big(sum)).valueOf()
          msgDefaut += `<div class="popup-msg1 test-return-given-sum" style="margin-top:2rem">
              <span data-i8n="givenSum,capitalize">Somme donnée</span>
              <span>${sommeDonnee}</span>
              <span>${getTranslate('currencySymbol', null, 'methodCurrency')}</span>
            </div>
            <div class="test-return-change" style="font-size: 2rem;font-weight: bold;">
              <span data-i8n="change,capitalize">monnaie à rendre</span>
              <span role="status" aria-label="change">${resultat}</span>
              <span>${getTranslate('currencySymbol', null, 'methodCurrency')}</span>
            </div>`
        }
      }

      // retour consigne
      if (options.methodes[0] === "RetourConsigne") {
        msgDefaut = `
          <div class="popup-paragraphe">
            <div class="popup-titre1" data-i8n="returnDepositOk,capitalize">Retour de consigne OK !</div>
        `
        if (options.achats.moyen_paiement === 'espece') {
          msgDefaut += `<div class="popup-msg1 test-msg-retour-consigne-espece">
            <span data-i8n="toRepay,capitalize">A rembourser</span> : ${Math.abs(retour.somme_totale)} 
            <span>${getTranslate('currencySymbol', null, 'methodCurrency')}</span>
          </div>`
        }
        if (options.achats.moyen_paiement === 'nfc') {
          // msgDefaut += `<div class="popup-paragraphe test-msg-retour-consigne-nfc">Votre carte est crédité de ${Math.abs(retour.somme_totale)} ${glob.monnaie_principale_name}</div>`
          msgDefaut += `<div class="popup-msg1 test-msg-retour-consigne-nfc">
            <span data-i8n="cardCreditedWith,capitalize">Votre carte est crédité de</span> ${Math.abs(retour.somme_totale)} ${glob.monnaie_principale_name}
          </div>`
        }
        msgDefaut += `</div>`
      }

      msg = `<div class="BF-col-uniforme l100p h100p">
          <div class="BF-col">
            ${msgDefaut}
            ${await showButtonPrintTicket(retour, options)}
          </div>
          <bouton-basique id="popup-retour" traiter-texte="1" texte="RETOUR|2rem||return-uppercase" couleur-fond="#3b567f" icon="fa-undo-alt||2.5rem" width="400px" height="120px" ${fonction}></bouton-basique>
        </div>`
      // affichage du popup
      fn.popup({ message: msg, type: typeMsg })
    } else {
      gestionTransactionFondsInsuffisants(retour, options)
    }

  } else {
    // console.log('----> 406,  retour =', retour)
    let msgs = ''
    fonction = `onclick="fn.popupAnnuler();"`
    typeMsg = 'attent'
    for (const key in retour) {
      const item = retour[key]
      if (typeof (item) === 'object') {
        for (const id in item) {
          const subItem = item[id]
          if (typeof (subItem) === 'string') {
            msgs += `<div class="BF-col popup-msg1 test-msg-${key}-${id}" style="width:98%;white-space: pre-line; text-align: center;">${subItem}</div>`
          }
        }
      } else {
        if (typeof (item) === 'string') {
          msgs += `<div class="popup-msg1 test-msg-${key}" style="width:98%;white-space: pre-line; text-align: center;">${item}</div>`
        }
      }
    }

    msg = `
      <div class="BF-col-uniforme l100p h100p">
        ${msgs}
        <bouton-basique id="popup-retour" traiter-texte="1" texte="RETOUR|2rem||return-uppercase" couleur-fond="#3b567f" icon="fa-undo-alt||2.5rem" width="400px" height="120px" ${fonction}></bouton-basique>
      </div>
    `
    fn.popup({ message: msg, type: typeMsg })
  }

}


/**
 * Aiguille le retour des requètes POST pour le paiement
 * @param {Object} retour = données reçues de la requète
 * @param {Object} status = etat de la requète
 * @param {Object} options = données avant le lancement de la requète
 */
export function gererRetourPostPaiement(retour, status, options) {
  console.log('-> fonction gererRetourPostPaiement, options.actionAValider=', options.actionAValider)
  // sys.logValeurs({ retour: retour, status: status, options: options })
  try {
    // sys.logValeurs({retour: retour, status: status, options: options})

    // envoyer la commande en préparation
    if (options.actionAValider === "envoyer_preparation") {
      afficherRetourEnvoyerPreparation(retour, status, options)
    }

    // envoyer la commande en préparation et payer
    if (options.actionAValider === "envoyer_preparation_payer") {
      afficherRetourEnvoyerPreparation(retour, status, options)
    }

    if (options.actionAValider === "envoyer_preparation_payer_fractionner") {
      aiguillagePagePaiementCommande(retour, status, options)
    }

    if (options.actionAValider === "addition_liste" || options.actionAValider === "addition_fractionnee") {
      infosPaiementRetourTable(retour, status, options)
    }

    if (options.actionAValider === "vente_directe") {
      afficherRetourVenteDirecte(retour, status, options)
    }

  } catch (err) {
    // console.log('--> erreur de gererRetourPostPaiement !')
    let message = `
      <div class="BF-col">
        <div class="ft-1r mb16px">${err}</div>
      </div>
    `
    let bouton = `
     <div class="popup-conteneur-bt-retour BF-col">
      <bouton-basique id="popup-retour" traiter-texte="1" texte="RETOUR|2rem||return-uppercase" couleur-fond="#3b567f" icon="fa-undo-alt||2.5rem" width="400px" height="120px"  onclick="fn.popupAnnuler();"></bouton-basique>
     </div>
    `
    let options = {
      message: message,
      boutons: bouton,
      type: 'danger'
    }
    fn.popup(options)
  }
}

/**
 * Gère le retour de la requètes POST "check_carte"
 * @param {Object} retour = données reçues de la requète
 * @param {Object} status = etat de la requète
 * @param {Object} donnees = {typeCheckCarte, tagId}
 * @param {Function} callback = fonction de retour pour typeCheckCarte = 'manuel'
 */
export function gererRetourPostCheckCarte(retour, status, donnees, callback) {
  // console.log('-> fonction gererRetourPostCheckCarte !')
  // sys.logValeurs({retour: retour, status: status, donnees: donnees})
  // console.log('status =', status);
  // console.log('retour =', typeof(retour));
  if (donnees.typeCheckCarte === 'parLecteurNfc') {
    if (status.code === 200) {
      document.querySelector('#contenu').insertAdjacentHTML('beforeend', retour)
    } else {
      let message = `
      <div class="BF-col">
        <div class="ft-1r mb16px">${JSON.parse(retour).detail}</div>
      </div>
    `
      let bouton = `
     <div class="popup-conteneur-bt-retour BF-col">
      <bouton-basique id="popup-retour" traiter-texte="1" texte="RETOUR|2rem||return-uppercase" couleur-fond="#3b567f" icon="fa-undo-alt||2.5rem" width="400px" height="120px"  onclick="fn.popupAnnuler();"></bouton-basique>
     </div>
    `
      let options = {
        message: message,
        boutons: bouton,
        type: 'attent'
      }
      fn.popup(options)
    }
  }

  if (donnees.typeCheckCarte === 'manuel') {
    callback(retour, status, donnees.retourPremiereCarte)
  }
}