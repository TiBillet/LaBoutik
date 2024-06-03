// console.log('-> accueil.js')
import * as Sys from '/static/webview/js/modules/systeme.js'
import { translate, getTranslate, getLanguages } from '/static/webview/js/modules/i8n.js'

// scope global
window.sys = Sys
window.translate = translate
window.getTranslate = getTranslate
window.getLanguages = getLanguages

// icon de chargement
sys.affCharge({ etat: 1, largeur: 80, couleur: '#0F0', nbc: 8, rpt: 4, epaisseur: 8 })

import * as Fn from "/static/webview/js/modules/fonctions.js"

window.fn = Fn

window.glob = {}
window.rfid = new Nfc()
window.ledPossibilite = true
window.intervalActualisationVuePreparations = 5000 // 3600000
window.attenteLancerVerifierEtatCommandes = { rep: 0, etat: 0, interval: intervalActualisationVuePreparations }

try {
  Sentry.init({
    dns: "https://677e4405e6f765888fdec02d174000d6@o262913.ingest.us.sentry.io/4506881155596288",
    tracesSampleRate: 1.0,
    replaysSessionSampleRate: 0.1,
    replaysOnErrorSampleRate: 1.0,
  })  
} catch (error) {
  console.log('sentry :', error) 
}

// récupère les données de l'appli
try {
  window.glob['appConfig'] = JSON.parse(localStorage.getItem('laboutik'))
  // console.log('-> accueil.js, glob.appConfig =', glob.appConfig, '  --  DEMO =', DEMO)
} catch (err) {
  sys.log(`storage -> ${err}  !`)
}

// --- lance le programme ---
window.initProgramme = function () {
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
    // sys.logJson('retour = ',retour)
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
