// console.log('-> accueil.js')
import * as Sys from '/static/webview/js/modules/systeme.js'
import { getCurrentCurrency } from '/static/webview/js/modules/currencysList.js'
import { translate, getTranslate, getLanguages } from '/static/webview/js/modules/i8n.js'
import * as Fn from "/static/webview/js/modules/fonctions.js"

// --- logs ---
// sauvegarder l'ancienne fonction console.log
window.oldLogFunc = console.log

/**
 * Etend la fonction de log
 */
window.settingsStartLogs = function () {
  // init contenu settingsLogsContent
  window.settingsLogsContent = []

  // modifier fonction log - utilise le store
  window.console.log = function (message, plus) {
    if (plus === undefined) {
      plus = ''
    }
    // enregistre le message de log
    window.settingsLogsContent.push(message + ' ' +plus)
    // lance la fonction de log original
    window.oldLogFunc.apply(console, arguments)
  }
}

// active les logs si activés
if (localStorage.getItem("activatedLogs") === "true" && oldLogFunc === console.log) {
  settingsStartLogs()
}
// --- fin logs ---

// scope global
window.sys = Sys
window.translate = translate
window.getTranslate = getTranslate
window.getLanguages = getLanguages

// icon de chargement
sys.affCharge({ etat: 1, largeur: 80, couleur: '#0F0', nbc: 8, rpt: 4, epaisseur: 8 })

window.fn = Fn

window.glob = {}
window.rfid = new Nfc()
window.ledPossibilite = true
window.intervalActualisationVuePreparations = 5000 // 3600000
window.attenteLancerVerifierEtatCommandes = { rep: 0, etat: 0, interval: intervalActualisationVuePreparations }

// récupère les données de l'appli
try {
  window.glob['appConfig'] = JSON.parse(localStorage.getItem('laboutik'))
  // console.log('-> accueil.js, glob.appConfig =', glob.appConfig, '  --  DEMO =', DEMO)
} catch (err) {
  sys.log(`storage -> ${err}  !`)
}

// --- lance le programme ---
window.initProgramme = function () {
  // console.log('-> acceuil, initProgramme ')
  let contexte = {
    indexPv: 0,
    csrfToken: glob.csrf_token
  }
  fn.init_rendu('vue_pv', '/static/webview/js/points_ventes.js', contexte)
}

// étape 2 - après avoir reçu le tag_id, POST des infos de tous les points de vente
const demande_pvs = function (data) {
  // console.log('-> fonction demande_pvs')
  let tagIdCm = data.tagId
  glob.csrf_token = document.querySelector('input[name="csrfmiddlewaretoken"]').value
  let requete = {
    type: "post",
    url: "/wv/",
    dataTypeReturn: "json",
    dataType: 'form',
    csrfToken: glob.csrf_token,
    attente: { largeur: 80, couleur: '#0F0', nbc: 8, rpt: 4, epaisseur: 8, garderTemointDeCharge: true },
    data: { "type-action": "valider_carte_maitresse", "type-post": "ajax", "tag-id-cm": tagIdCm }
  }
  sys.ajax(requete, function (retour, status) {
    // sys.logJson('accueil.js - retour = ',retour)
    // sys.logJson('status = ',status)

    // icon de chargement
    sys.affCharge({ etat: 1, largeur: 80, couleur: '#0F0', nbc: 8, rpt: 4, epaisseur: 8 })

    if (status.code === 200) {
      if (retour.erreur === 1) { // ce n'est pas une carte maîtresse
        // avertissement
        rfid.muteEtat('message', `
          <div style="color:#ffff00;text-align: center;" data-i8n="isNot, capitalize">Ce n'est pas</div>
          <div style="color:#ffff00;text-align: center;" data-i8n="primaryCard">une carte primaire.</div>
          <div style="color:#ffff00;text-align: center;" data-i8n="awaitingCardReading">Attente lecture carte ..</div>`)
        rfid.lireTagId()
      } else {
        // pour payer le(s) commande(s) en plusieurs sommes
        glob.uuidArticlePaiementFractionne = retour.article_paiement_fractionne
        // si carte maitresse ok
        glob.tagIdCm = tagIdCm
        glob.data = retour.data

        // converti les décimal python
        for (const key in glob.data) {
          const pv = glob.data[key]
          for (const keyArticle in pv.articles) {
            const article = pv.articles[keyArticle]
            article.prix = sys.bigToFloat(article.prix)
          }
        }

        glob.responsable = retour.responsable
        glob.monnaie_principale_name = retour.monnaie_principale_name
        glob.tables = retour.tables
        glob.passageModeGerant = retour.responsable.edit_mode
        glob.modeGerant = false
        // data current curency
        glob['currencyData'] = getCurrentCurrency(retour.currency_code)
        retour = null
        initProgramme()
      }
    } else {
      let texte = ''
      if (status.texte) {
        texte = status.texte
        if (typeof status.texte === 'object') {
          texte = JSON.stringify(status.texte, null, '\t')
        }
      }
      let message = `
        <div id="popup-lecteur-nfc" class="BF-col">
          <div><span data-i8n="error, capitalize">Erreur</span>, status code = ${status.code} :</div>
          <div>${texte}</div>
          <div data-i8n="contactAdmin">Contactez l'administrateur !</div>
        </div>
      `
      // Afficher le message
      fn.popup({
        message: message,
        type: 'normal',
        boutons: ''
      })
    }
  })
}

// Initialise et détermine le type de lecteur NFC(RFID) (interne/serveur/DEMO)
rfid.initModeLectureNfc()

// lance la lecture pour la carte maîtresse
rfid.muteEtat('message', `<div style="white-space: pre-line; text-align: center;" role="status" aria-label="waiting primary card" data-i8n="waitPrimaryCard,capitalize">attente carte primaire</div>`)
rfid.muteEtat('callbackOk', demande_pvs)
rfid.muteEtat('tagIdIdentite', 'cm')
rfid.lireTagId()
