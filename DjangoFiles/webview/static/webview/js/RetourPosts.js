function gestionTransactionFondsInsuffisants(retour, options) {
  // console.log('-------------------------------------------------------------------------')
  // console.log('--- fonction gestionTransactionFondsInsuffisants :')
  // sys.logValeurs({retour, options})

  let boutons = ''
  let msg = `<div class="BF-col-uniforme message-fonds-insuffisants">`
  let rep_infos = document.querySelector('#pv' + pv_uuid_courant)
  let accepte_especes = rep_infos.getAttribute('data-accepte-especes')
  let accepte_carte_bancaire = rep_infos.getAttribute('data-accepte-carte-bancaire')
  let totalManque = retour.message.manque
  options['totalCarte2'] = totalManque

  glob.dataCarte1 = {
    retour: retour,
    options: options
  }

  if (retour.route === 'transcation_nfc_fonds_insuffisants') {
    // la première carte n'a pas les fonds
    if (accepte_especes === 'true') {
      // boutons += `<bouton-basique class="test-fonds-insuffisants-espece" traiter-texte="1" texte="ESPECE|2rem|,TOTAL ${totalManque} €|1.5rem|" width="400px" height="120px" couleur-fond="#3b567f" icon="fa-coins||2.5rem" onclick="fn.popupAnnuler();vue_pv.validerEtapeMoyenComplementaire('espece')" style="margin-top:16px;"></bouton-basique>`
      boutons += `<bouton-basique class="test-fonds-insuffisants-espece" traiter-texte="1" texte="ESPECE|2rem||cash-uppercase,[TOTAL] ${totalManque} [€]|1.5rem||total-uppercase;currencySymbol" width="400px" height="120px" couleur-fond="#3b567f" icon="fa-coins||2.5rem" onclick="fn.popupConfirme('espece', 'ESPECE', 'vue_pv.validerEtapeMoyenComplementaire')" style="margin-top:16px;"></bouton-basique>`
    }
    if (accepte_carte_bancaire === 'true') {
      boutons += `<bouton-basique class="test-fonds-insuffisants-cb" traiter-texte="1"  texte="CB|2rem|,[TOTAL] ${totalManque} [€]|1.5rem||cb-uppercase;currencySymbol" width="400px" height="120px" couleur-fond="#3b567f" icon="fa-coins||2.5rem" onclick="fn.popupConfirme('carte_bancaire', 'CB', 'vue_pv.validerEtapeMoyenComplementaire')" style="margin-top:16px;"></bouton-basique>`
    }

    boutons += `<bouton-basique class="test-fonds-insuffisants-nfc" traiter-texte="1" texte="[autre] [CARTE]|2rem||other-uppercase;card-uppercase,(CASHLESS)|1.2rem,[TOTAL] ${totalManque} [€]|1.5rem||total-uppercase;currencySymbol" width="400px" height="120px" couleur-fond="#3b567f" icon="fa-coins||2.5rem" onclick="fn.popupAnnuler();vue_pv.validerEtapeMoyenComplementaire('nfc')" style="margin-top:16px;margin-bottom:40px;"></bouton-basique>`
    msg += `
      <div class="popup-titre1" data-i8n="insufficientFunds,capitalize">Fonds insuffisants.</div>
      <div class="popup-msg1">
        <span data-i8n="isMissing,capitalize">Il manque</span> <span id="test-manque-monnaie">${retour.message.manque}</span> <span data-i8n="currencySymbol">€</span>
      </div>
      <div class="popup-msg1">
        ${retour.carte.membre_name} <span data-i8n="has">a</span> <span id="test-carte-total-monnaie">${retour.carte.total_monnaie}</span>
      </div>
      <div class="popup-msg1" data-i8n="possiblePurchaseBy,capitalize">Achat possible par :</div>
    `
  } else {
    console.log("-> Fonds insuffisants sur deuxieme carte")
    // la deuxième carte n'a pas les fonds
    msg += `<div class="popup-titre1" data-i8n="insufficientFunds,capitalize">Fonds insuffisants.</div>
    <div class="popup-titre1" data-i8n="onSecondCard">sur deuxieme carte</div>
    <div class="popup-msg1">
      <span data-i8n="isMissing,capitalize">Il manque</span> <span id="test-manque-monnaie">${retour.message.manque}</span>
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
    if (valeurAsset > 0) {
      valAssetsTest = 1
      enumAssets += `<div class="popup-msg1 test-item-monnaie">- <span class="test-nom-monnaie nom-monnaie-item${i}">${nomAsset}</span> : <span class="test-valeur-monnaie valeur-monnaie-item${i}">${valeurAsset}</span></div>`
    }
  }
  if (valAssetsTest === 1) {
    fragmentHtml = `<div class="popup-msg1"><span data-i8n="including">dont</span> :</div>`
  }
  fragmentHtml += enumAssets
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
        <span data-i8n="on,capitalize">Sur</span> <span data-i8n="card">carte</span> <span data-i8n="before">avant</span> ${motsPourAchat} : <span id="test-total-carte-avant-achats">${retour.total_sur_carte_avant_achats}</span>
      </div>`
    }
    // total acaht(s)
    if (retour.somme_totale) {
      let moyenDePaiement = window.orthoPaiement[options.achats.moyen_paiement]
      if (options.achats.complementaire !== undefined) {
        moyenDePaiement = window.orthoPaiement[options.achats.complementaire.moyen_paiement]
      }
      fragmentHtml += `<div class="popup-msg1 test-total-achats">
        <span data-i8n="total,capitalize">Total</span> (${moyenDePaiement}) : <span id="test-somme-payee">${retour.somme_totale}</span>
      </div>`
    }
    // reste sur carte
    if (retour.carte.total_monnaie) {
      fragmentHtml += `<div class="popup-msg1 test-carte-apres-achats">
      <span data-i8n="rest,capitalize">Reste</span> <span data-i8n="on">sur</span> <span data-i8n="card">carte</span> : <span id="test-total-carte">${retour.carte.total_monnaie}</span>
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
function afficherRetourEnvoyerPreparation(retour, status, options) {
  // console.log('-> fonc afficherRetourEnvoyerPreparation !')
  // sys.logValeurs({retour: retour, status: status, options: options})
  let msg = '', msgPaye = '', msgDifErreur = '', typeMsg = 'succes', fonction = '', msgAssets = '', msgTotalCarte = '',
    msgTotalCarteAvantAchats = ''

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
        let moyenDePaiement = window.orthoPaiement[options.achats.moyen_paiement]
        if (options.achats.complementaire !== undefined) {
          moyenDePaiement = window.orthoPaiement[options.achats.complementaire.moyen_paiement]
        }
        msgPaye = `<div class="popup-msg1">
          <span data-i8n="total,capitalize">Total</span> (${moyenDePaiement}) : <span id="test-somme-payee">${infoTotal}</span>
        </div>`
        // msgPaye = `<div class="popup-msg1 test-total-achats">Total (${window.orthoPaiement[options.achats.moyen_paiement]}) : <span id="test-somme-payee">${ retour.somme_totale }</span></div>`

        if (retour.carte) {
          // assets
          msgAssets = messageRetourAssets(retour)
          // total monnaie sur carte
          msgTotalCarte = `<div class="popup-msg1 test-carte-apres-achats">
            <span data-i8n="rest,capitalize">Reste</span> <span data-i8n="on">sur</span> <span data-i8n="card">carte</span> : <span id="test-total-carte">${retour.carte.total_monnaie}</span>
          </div>`
        }
        // total sur carte avant achats
        if (retour.total_sur_carte_avant_achats !== undefined && retour.total_sur_carte_avant_achats !== null) {
          let nbArticles = options.achats.articles.length
          const translateAchat = getTranslate('purchase') === '' ? "achat" : getTranslate('purchase')
          let motsPourAchat = nbArticles > 1 ? `${translateAchat}s` : translateAchat
          msgTotalCarteAvantAchats = `<div class="popup-msg1 test-carte-avant-achats">
            <span data-i8n="on,capitalize">Sur</span> <span data-i8n="card,capitalize">carte</span> <span data-i8n="before,capitalize">avant</span> ${motsPourAchat} : <span id="test-total-carte-avant-achats">${retour.total_sur_carte_avant_achats}</span>
          </div>`
        }
      }

      msg = `
        <div class="BF-col-uniforme l100p h100p">
          <div class="BF-col">
            <div class="popup-titre1 retour-transaction-ok">
              <span data-i8n="transaction,capitalize">Transaction</span> <span data-i8n="ok">Ok</span>
            </div>
            <div class="popup-msg1 test-msg-prepa" data-i8n="sentInPreparation,capitalize">Envoyée en préparation.</div>
            ${msgPaye}
            ${msgTotalCarteAvantAchats}
            ${msgTotalCarte}
            ${msgAssets}
          </div>
          <bouton-basique id="popup-retour" traiter-texte="1" texte="RETOUR|2rem||return-uppercase" couleur-fond="#3b567f" icon="fa-undo-alt||2.5rem" width="400px" height="120px" onclick="fn.popupAnnuler();vue_pv.initMode();"></bouton-basique>
        </div>
      `
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
function aiguillagePagePaiementCommande(retour, status, options) {
  // console.log(`-> fonction aiguillagePagePaiementCommande !`)
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
function infosPaiementRetourTable(retour, status, options) {
  // console.log(`-> fonction infosPaiementRetourTable !`)
  // sys.logValeurs({retour: retour, status: status, options: options})
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
        msgDefaut += `<div class="popup-msg1 test-total-achats">
        <span data-i8n="total,capitalize">Total</span> (${window.orthoPaiement[options.achats.moyen_paiement]}) : ${retour.somme_totale}
        </div>`
      }
      msg = `
        <div class="BF-col-uniforme l100p h100p">
          <div class="BF-col">
            <div class="popup-titre1">
              <span data-i8n="transaction,capitalize">Transaction</span> <span data-i8n="ok">Ok</span>
            </div>
            ${msgDefaut} ${msgRetourCarte}
          </div>
          <bouton-basique id="popup-retour" traiter-texte="1" texte="RETOUR|2rem||return-uppercase" couleur-fond="#3b567f" icon="fa-undo-alt||2.5rem" width="400px" height="120px" ${fonction}></bouton-basique>
        </div>
      `
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
            <span data-i8n="error,capitalize">Erreur <span data-i8n="payment">Paiement !</span>
          </div>
          <div class="popup-msg1">actionAValider = ${options.actionAValider}</div>
        </div>
        <bouton-basique id="popup-retour" traiter-texte="1" texte="RETOUR|2rem||return-uppercase" couleur-fond="#3b567f" icon="fa-undo-alt||2.5rem" width="400px" height="120px" ${fonction}></bouton-basique>
      </div>
    `
    // affichage du popup
    fn.popup({ message: msg, type: typeMsg })
  }
}

function afficherRetourVenteDirecte(retour, status, options) {
  // console.log(`-> fonction afficherRetourVenteDirecte !`)
  sys.logValeurs({ retour: retour, status: status, options: options })
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
      msgDefaut = `<div class="popup-titre1 retour-transaction-ok">
        <span data-i8n="transaction,capitalize">Transaction</span> <span data-i8n="ok">Ok</span>
      </div>`

      // paiement "CASHLESS"
      let msgRetourCarte = ''
      if (retour.carte !== undefined) {
        msgRetourCarte = messageRetourCarte(retour, options)
        msgDefaut += msgRetourCarte
      } else {
        let moyenDePaiement = window.orthoPaiement[options.achats.moyen_paiement]
        if (options.achats.complementaire !== undefined) {
          moyenDePaiement = window.orthoPaiement[options.achats.complementaire.moyen_paiement]
        }
        msgDefaut += `<div class="popup-msg1 test-total-achats">
          <span data-i8n="total,capitalize">Total</span> (${moyenDePaiement}) : ${retour.somme_totale}
        </div>`
      }

      // gestion moyen de paiement "espèce", somme à rendre
      if (options.achats.moyen_paiement === 'espece') {
        const totalAchat = parseFloat(options.achats.total)
        const sommeDonnee = parseFloat(options.sommeDonnee)
        const resultat = new Big(sommeDonnee)
        // const sumValue = (new Big(sum)).valueOf()
        msgDefaut += `<div class="popup-msg1 test-total-achats">
          <span data-i8n="givenSum">Somme donnée</span>
          <span>${sommeDonnee}</span>
          <span data-i8n="currencySymbol"></span>
        </div>
        <div style="margin-top:2rem; font-size: 2rem;font-weight: bold;">
          <span data-i8n="change,capitalize">monnaie à rendre</span>
          <span role="status" aria-label="change">${(resultat.minus(totalAchat))}</span>
          <span data-i8n="currencySymbol"></span>
        </div>`
      }

      // vider une carte
      if (options.methodes[0] === "ViderCarte") {
        msgDefaut = `
          <div class="popup-titre1" data-i8n="clearingCardOk,capitalize">Vidage carte OK !</div>
          <div class="popup-msg1 test-msg-vider-carte">
            <span data-i8n="toRepay,capitalize">A rembourser</span> : ${retour.somme_totale}
          </div>
        `
      }

      // adhésion
      if (options.methodes[0] === "Adhesion") {
        let msgCotisation = ''
        if (retour.carte !== undefined && retour.carte !== null) {
          msgCotisation = `
            <div class="popup-msg1 test-msg-membre">
              <span data-i8n="member">membre</span> : ${retour.carte.membre_name}
            </div>
            <div class="popup-msg1 test-msg-adhesion-date">${retour.carte.cotisation_membre_a_jour}</div>
          `
        }
        msgDefaut = `
          <div class="popup-titre1" data-i8n="membership,capitalize">Adhésion</div>
          ${msgCotisation}
          <div class="popup-msg1 test-msg-adhesion">
            <span data-i8n="total,capitalize">Total</span> (${window.orthoPaiement[options.achats.moyen_paiement]}) : ${retour.somme_totale}
          </div>
        `
      }

      // retour consigne
      if (options.methodes[0] === "RetourConsigne") {
        msgDefaut = `
          <div class="popup-paragraphe">
            <div class="popup-titre1" data-i8n="returnDepositOk,capitalize">Retour de consigne OK !</div>
        `

        console.log('retour =', retour)
        console.log('nb articles =', options.achats.articles.length)

        if (options.achats.moyen_paiement === 'espece') {
          msgDefaut += `<div class="popup-msg1 test-msg-retour-consigne-espece">
            <span data-i8n="toRepay,capitalize">A rembourser</span> : ${Math.abs(retour.somme_totale)}
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

      msg = `
        <div class="BF-col-uniforme l100p h100p">
          <div class="BF-col">
            ${msgDefaut}
          </div>
          <bouton-basique id="popup-retour" traiter-texte="1" texte="RETOUR|2rem||return-uppercase" couleur-fond="#3b567f" icon="fa-undo-alt||2.5rem" width="400px" height="120px" ${fonction}></bouton-basique>
        </div>
      `
      // affichage du popup
      fn.popup({ message: msg, type: typeMsg })
    } else {
      gestionTransactionFondsInsuffisants(retour, options)
    }

  } else {
    fonction = `onclick="fn.popupAnnuler();"`
    typeMsg = 'attent'
    let infos = retour.detail
    if (retour.detail.toLowerCase().includes('pas trouvé')) {
      infos = '<span data-i8n="unknownCard,capitalize">Carte inconnue !</span>'
    }
    let messageDefaut = `<div class="popup-titre1">
      <span data-i8n="error,capitalize">Erreur</span> <span data-i8n="payment">Paiement !</span>
    </div>
    <div class="popup-msg1">${infos}</div>
    <!-- pour dev
    <div class="popup-msg1">actionAValider = ${options.actionAValider}</div>
    -->`

    msg = `
      <div class="BF-col-uniforme l100p h100p">
        <div class="BF-col">
          ${messageDefaut}
        </div>
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
  // console.log(`-> fonction gererRetourPostPaiement !`)
  // sys.logValeurs({retour: retour, status: status, options: options})
  window.orthoPaiement = {
    espece: 'espèce',
    carte_bancaire: 'carte bancaire',
    nfc: 'carte nfc'
  }
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

function checkCarteOk(retour) {
  // console.log('-> fonction checkCarteOk !')
  // sys.logJson('retour = ',retour)

  const translateName = getTranslate('name') === '' ? "Nom" : getTranslate('name', 'capitalize')
  let totalMonnaie = parseFloat(retour.total_monnaie)
  let membreName = retour.membre_name
  let typeMessage = 'succes'
  if (retour.cotisation_membre_a_jour_booleen === false) {
    typeMessage = 'attent'
  }

  // émet un message sur la matrice led, uniquement pour un raspberry "FPI"
  if (window.ledPossibilite === true && SOCKET && glob.appConfig.front_type === "FPI") {
    let assets = retour.assets
    let ledMessage = `${translateName} : ${membreName}  --  `
    for (let i = 0; i < assets.length; i++) {
      let valeurAsset = parseFloat(assets[i].qty)
      if (valeurAsset > 0) {
        ledMessage += assets[i].monnaie_name + ' : ' + valeurAsset + '  --  '
      }
    }
    SOCKET.emit('ecran_matrice', { data: ledMessage, scroll: 2 })
  }

  let msg = `
    <div class="BF-col-uniforme check-carte-ok">
      <div class="check-carte-ok-nom">${translateName} : ${membreName}</div>
      <div class="check-carte-ok-cotisation">${retour.cotisation_membre_a_jour}</div>
      <div class="check-carte-ok-total-carte">
      <span data-i8n="on,capitalize">Sur</span> <span data-i8n="card">carte</span> : ${totalMonnaie}
      </div>
      ${messageRetourAssets(retour)}
    </div>
  `

  let bouton = `
    <div class="popup-conteneur-bt-retour BF-col">
        <bouton-basique id="popup-retour" traiter-texte="1" texte="RETOUR|2rem||return-uppercase" couleur-fond="#3b567f" icon="fa-undo-alt||2.5rem" width="400px" height="120px"  onclick="fn.popupAnnuler();"></bouton-basique>
    </div>
  `

  let options = {
    message: msg,
    boutons: bouton,
    type: typeMessage
  }
  fn.popup(options)
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
  if (donnees.typeCheckCarte === 'parLecteurNfc') {
    // ---- carte ok ----
    if (status.code === 200) {
      checkCarteOk(retour)
    }
    // ---- carte inconnue ----
    if (status.code === 404) {
      // carte inconnue
      let message = `<div class="BF-col check-carte-inconnue l100p h100p">${retour.msg}</div>`
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
    // ---- erreurs ----
    if (status.code !== 200 && status.code !== 404) {
      let msg = `
          <!--
          <div class="d-flex flex-column justify-content-center align-items-center" style="font-weight:bold;color:#FFFFFF;text-shadow: 0px 1px 0px rgba(255,255,255,0.5);">
            <div style="font-size:2rem;margin-bottom:24px" class="test-erreur-dif200400">
            <span data-i8n="stausCodeError,uppercase">ERREUR STATUS CODE</span> : ${status.code}
            </div>
            <div style="font-size:1.5rem;margin-bottom:8px" class="test-erreur-text">${status.texte}</div>
          <div>
          -->
          <div class="popup-titre1"><span data-i8n="error,capitalize">Erreur</span> :</div>
          <div class="popup-msg1 test-msg-paye-erreur" data-i8n="afterCheckCard">après un check-carte !</div>
        `
      let bouton = `
          <div class="popup-conteneur-bt-retour BF-col">
              <bouton-basique id="popup-retour" traiter-texte="1" texte="RETOUR|2rem||return-uppercase" couleur-fond="#3b567f" icon="fa-undo-alt||2.5rem" width="400px" height="120px"  onclick="fn.popupAnnuler();"></bouton-basique>
          </div>
        `
      let options = {
        message: msg,
        boutons: bouton,
        type: 'danger'
      }
      fn.popup(options)
    }
  }

  if (donnees.typeCheckCarte === 'manuel') {
    callback(retour, status, donnees.retourPremiereCarte)
  }
}