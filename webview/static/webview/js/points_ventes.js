// construction d'une partie du menu provenant des plugins
import "./menuPlugins/addAllMenuPlugin.js"
import { getCurrentCurrency } from '/static/webview/js/modules/currencysList.js'
import { isCordovaApp, bluetoothHasSunmiPrinter, bluetoothWrite, bluetoothOpenCashDrawer } from './modules/mobileDevice.js'


// ---- cordova ---
window.mobile = isCordovaApp()

// condition has sunmi printer
window.hasSunmiPrinter = async function () {
  return await bluetoothHasSunmiPrinter()
}

// conditions websocket on and has sunmi printer
window.websocketOnAndhasSunmiPrinter = async function () {
  return wsTerminal.on === true && await hasSunmiPrinter() === true
}

window.openCashDrawer = async function () {
  try {
    if (await hasSunmiPrinter()) {
      await bluetoothOpenCashDrawer()
    }
  } catch (error) {
    console.log('-> openCashDrawer error infos:', error);
  }
}

function initWebsocket() {
  const server = `wss://${window.location.host}/ws/tuto_js/print/`
  // ---- websocket handler ----
  async function wsHandlerMessag(dataString) {
    // console.log('-> ws, dataString =', dataString)
    try {
      const data = JSON.parse(dataString)
      const testHasSunmiPrinter = await hasSunmiPrinter()
      if (data.message === 'print' && testHasSunmiPrinter === true) {
        // create print sunmi queue
        if (window.sunmiPrintQueue === undefined) {
          window.sunmiPrintQueue = []
        }

        // console.log('data.data =', data.data)

        const options = { printUuid: sys.uuidV4(), content: data.data }
        sunmiPrintQueue.push(options)
        await bluetoothWrite(options.printUuid)
      }

    } catch (error) {
      console.log("-> wsHandlerMessag, erreur :", error)
    }
  }

  // TODO: changer la route si besoin
  window.wsTerminal = {
    socket: new WebSocket(server),
    on: false
  }

  // Connection ws ok
  wsTerminal.socket.addEventListener("open", (event) => {
    // get color from  palette.css
    const vert01 = '#00FF00'

    // console.log("-> connection ws -", new Date())
    wsTerminal.on = true
    if (document.querySelector('#temps-charge-visuel') !== undefined && document.querySelector('#temps-charge-visuel') !== null) {
      document.querySelector('#temps-charge-visuel').innerHTML = `<div style="color: ${vert01};">ws</div>`
    }
  })

  // écoute data ws
  wsTerminal.socket.addEventListener("message", function (event) {
    // aiguillage en fonction du message
    wsHandlerMessag(event.data)
  })

  // connection hs
  wsTerminal.socket.addEventListener("close", (event) => {
    // get color from  palette.css
    const rouge01 = '#FF0000'
    console.log("The connection has been closed successfully.");
    document.querySelector('#temps-charge-visuel').innerHTML = `<div style="color: ${rouge01};">ws</div>`
    // supprime le WebSocket
    wsTerminal = null
    // relance le websocket après 3 secondes
    setTimeout(initWebsocket(server), 3000)
    // test network
    if (window.navigator.onLine === false) {
      document.dispatchEvent(new CustomEvent('netWorkOffLine', {}))
    }
  })
}

if (isCordovaApp()) {
  navigator.connection.addEventListener('change', () => {
    console.log('-> network change' + new Date());
    if (navigator.onLine === false) {
      document.dispatchEvent(new CustomEvent('netWorkOffLine', {}))
    }
  })
}

window.nomModulePrive = null
window.pv_uuid_courant = ''
window.pv_uuid_ancien = ''
window.testPagePrepa = false
window.nombreMaxSelectionArticle = 1000
if (window.methods_after_render === undefined) {
  window.methods_after_render = []
}
window.etatInitialServiceDirectePVs = []
let csrf_token = null, serviceDirecte, memorise_data_dernier_achat = {}

// le groupe identifie les boutons ayant une logique de traitement non contradictoire"
// TODO: proposer de mettre en lien les groupes et les méthodes dans la BD
glob.bt_groupement = {
  'VenteArticle': {
    moyens_paiement: 'espece|carte_bancaire|nfc|CH',
    besoin_tag_id: 'nfc',
    groupe: 'groupe1',
    nb_commande_max: nombreMaxSelectionArticle
  },
  'RetourConsigne': {
    moyens_paiement: 'espece|nfc',
    besoin_tag_id: 'nfc',
    groupe: 'groupe2',
    nb_commande_max: nombreMaxSelectionArticle
  },
  'Adhesion': {
    moyens_paiement: 'espece|carte_bancaire|CH',
    besoin_tag_id: 'tout',
    groupe: 'groupe3',
    nb_commande_max: nombreMaxSelectionArticle
  },
  'AjoutMonnaieVirtuelle': {
    moyens_paiement: 'espece|carte_bancaire|CH',
    besoin_tag_id: 'tout',
    groupe: 'groupe4',
    nb_commande_max: nombreMaxSelectionArticle
  },
  'AjoutMonnaieVirtuelleCadeau': {
    moyens_paiement: '',
    besoin_tag_id: 'tout',
    groupe: 'groupe5',
    nb_commande_max: nombreMaxSelectionArticle
  },
  'BG': {
    moyens_paiement: '',
    besoin_tag_id: 'tout',
    groupe: 'groupe6',
    nb_commande_max: nombreMaxSelectionArticle
  },
  'ViderCarte': { moyens_paiement: '', besoin_tag_id: 'tout', groupe: 'groupe7', nb_commande_max: 1 },
  'Inconnue': { moyens_paiement: '', besoin_tag_id: '', groupe: 'groupe888', nb_commande_max: 0 },
}
// pour vérifier si les méthodes ont été renseignées
glob.tabMethodesATester = []
for (let clef in glob.bt_groupement) {
  glob.tabMethodesATester.push(clef)
}

// attention on est dans le scope/contexte de cet import
// d'ou l'utilisation des variables nom_module et nomModulePrive, ....
import BoutonArticle from '/static/webview/js/components/bouton_article.js'
import BoutonCommandeArticle from '/static/webview/js/components/bouton_commande_article.js'
import BoutonBasique from '/static/webview/js/components/boutonBasique.js'
import { paymentBt } from '/static/webview/js/components/paymentButton.js'
import BoutonServiceArticle from '/static/webview/js/components/bouton_service_article.js'
import * as restaurant from '/static/webview/js/restaurant.js'

window.restau = restaurant
window.paymentBt = paymentBt

import { Keyboard } from '/static/webview/js/modules/virtualKeyboard/vk.js'
window.keyboard = new Keyboard(45)

import * as retourFront from '/static/webview/js/RetourPosts.js'

window.gererRetourPostPaiement = retourFront.gererRetourPostPaiement
window.gererRetourPostCheckCarte = retourFront.gererRetourPostCheckCarte
customElements.define('bouton-article', BoutonArticle)
customElements.define('bouton-basique', BoutonBasique)
customElements.define('bouton-commande-article', BoutonCommandeArticle)
customElements.define('bouton-service-article', BoutonServiceArticle)

// etat de la connexion
function showNetworkOff() {
  if (document.querySelector('#network-offline') !== null) {
    document.querySelector('#network-offline').remove()
  }
  const content = `<div id="network-offline">
       <svg xmlns="http://www.w3.org/2000/svg" width="100px" height="100px" style="color:#FF0000;" viewBox="0 0 24 24">
           <g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2">
               <path d="M6.528 6.536a6 6 0 0 0 7.942 7.933m2.247-1.76A6 6 0 0 0 8.29 4.284"/>
               <path d="M12 3q2 .5 2 6q0 .506-.017.968m-.55 3.473Q12.934 14.766 12 15m0-12q-1.405.351-1.822 3.167m-.16 3.838Q10.192 14.549 12 15M6 9h3m4 0h5M3 20h7m4 0h7m-11 0a2 2 0 1 0 4 0a2 2 0 0 0-4 0m2-5v3M3 3l18 18"/>
           </g>
       </svg>
       <p data-i8n="noNetwork">Connexion au serveur perdue.\nVeuillez vérifier votre réseau.</p>
   </div>`
  document.body.insertAdjacentHTML('beforeend', content)
  translate('#network-offline')
  // 5 secondes
  setTimeout(() => {
    if (window.navigator.onLine === false) {
      document.dispatchEvent(new CustomEvent('netWorkOffLine', {}))
    } else {
      document.querySelector('#network-offline').remove()
      reloadData()
    }
  }, 5000)
}

// event 'netWorkOffLine' send by sys.ajax
document.addEventListener('netWorkOffLine', showNetworkOff, false)

// les boutons contenant le total des achats
export var liste_id_totaux = ['bt-valider']

export function reloadData() {
  let requete = {
    type: 'post',
    url: '/wv/',
    dataTypeReturn: 'json',
    dataType: 'form',
    csrfToken: glob.csrf_token,
    attente: { largeur: 80, couleur: '#0F0', nbc: 8, rpt: 4, epaisseur: 8 },
    data: { 'type-action': 'valider_carte_maitresse', 'type-post': 'ajax', 'tag-id-cm': glob.tagIdCm }
  }
  sys.ajax(requete, function (retour, status) {
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
    // main(nomModulePrive, { indexPv: 0, csrfToken: glob.csrf_token })
  })
}

function actualiserPossibiliteDeCommander() {
  // mise à jour de la possibilité de commander en fonction du point de vente
  serviceDirecte = glob.data.filter(obj => obj.id === pv_uuid_courant)[0].service_direct
}

export function initMode() {
  // mode commandes, affiches une liste de tables pour l'assignement à une commande
  let dataPV = glob.data.filter(obj => obj.id === pv_uuid_courant)[0]
  serviceDirecte = dataPV.service_direct
  glob.tableEnCours = null
  if (serviceDirecte === false) {
    restau.afficherTables('assignerTable', dataPV.name)
  } else {
    afficherPointDeVentes(pv_uuid_courant)
  }
  // prise en compte de htmx
  htmx.process(document.querySelector('body'))
}

/**
 * Fonction lancée automatiquement par  la fonction init_rendu du fichier fonction.js
 * Attention: ne pas changer le nom de la fonction
 * @param {String} nom_module
 * @param {Object} contexte
 */

export function main(nom_module, contexte) {
  // mémorise l'état initiale de serviceDirecte des points de vente
  for (let i = 0; i < glob.data.length; i++) {
    let dataPV = glob.data[i]
    etatInitialServiceDirectePVs.push(dataPV.service_direct)
  }
  // initialise le point de vente courant
  pv_uuid_courant = glob.data[contexte.indexPv].id
  // initialise la possibilité de commander ou d'acheter en direct
  serviceDirecte = glob.data[contexte.indexPv].service_direct
  csrf_token = contexte.csrfToken
  nomModulePrive = nom_module

  // évalue le template avec les données "params" = "ctx" dans le template)
  // donc préfixer vos variables avec 'ctx.' dans html
  let params = {
    action_cible: 'remplacer',
    id_cible: 'contenu',
    nom_module: nom_module
  }

  // window.methods_after_render[0] = { method: initMode }
  window.methods_after_render = [{ method: initMode }, { method: initWebsocket }]

  // lance le rendu de la page html
  fn.template_render_file('/static/webview/templates/points_ventes.html', params, window.methods_after_render)
}

// insère la valeur du csrf token dans l'input dédié par django
export function maj_csrf_token() {
  return csrf_token
}

export function affiche_class(ctx, nom_class) {
  let eles = document.querySelectorAll('.bouton-article')
  for (let i = 0; i < eles.length; i++) {
    let ele = eles[i]
    if (ele.className.indexOf(nom_class) !== -1) {
      ele.style.display = 'block'
    } else {
      ele.style.display = 'none'
    }
  }

  // maj icon actif du menu vertical gauche
  eles = document.querySelectorAll('.categories-item')
  for (let i = 0; i < eles.length; i++) {
    let ele = eles[i]
    ele.classList.remove('active')
  }
  ctx.classList.add('active')
  // console.log('id = ' + ctx.id)
}

/**
 *  Basculer de la vue boutons articles / à la vue liste articles
 */
export function basculerListeArticles(evt) {
  let etatAffichageListeArticles = document.querySelector('#achats').style.display
  // liste artlicles affichées
  if (etatAffichageListeArticles === 'none') {
    sys.effacerElements(['#products'])
    sys.afficherElements(['#achats,flex'])
    // record element active
    const repElementActif = document.querySelector('#categories div[class~="active"]').getAttribute('data-rep')
    document.querySelector('#page-commandes').setAttribute('data-active-item-categorie', repElementActif)
    // remove active
    let eles = document.querySelectorAll('.categories-item')
    for (let i = 0; i < eles.length; i++) {
      let ele = eles[i]
      ele.classList.remove('active')
    }
    // active
    evt.target.classList.add('active')
  } else {
    sys.effacerElements(['#achats'])
    sys.afficherElements(['#products,flex'])
    // désactive
    evt.target.classList.remove('active')
    // active ancien choix
    const repOldElementActif = document.querySelector('#page-commandes').getAttribute('data-active-item-categorie')
    document.querySelector(`#categories div[data-rep="${repOldElementActif}"]`).classList.add('active')
  }
}

export function afficher_categories() {
  // traite le point de vente (pv_donnees variable privée à la fonction)
  let pv_donnees = traitement_donnees_pv()
  let frag = `
    <div id="bt-bascule-btouliste" class="BF-col categories-item active" onclick="vue_pv.basculerListeArticles(event)">
      <i class="categories-table-icon fas fa-list"></i>
      <div class="categories-nom" data-i8n="select,capitalize">Selection</div>
    </div>
    
    <div id="categorie-tous" data-rep="all" class="BF-col categories-item active" onclick="${nomModulePrive + '.affiche_class(this,\'bouton-article\');'}">
      <i class="categories-icon fas fa-th"></i>
      <div class="categories-nom" data-i8n="all,capitalize">Tous</div>
    </div>
  `

  // trie poid en ordre croissant
  pv_donnees.categories.sort(function (a, b) {
    return a.poid - b.poid
  })

  for (let index_cat in pv_donnees.categories) {
    // sys.logJson('cat', pv_donnees.categories)
    // console.log('-----------------------------')
    let nom = pv_donnees.categories[index_cat].nom
    let blockIcon = ''
    if (pv_donnees.categories[index_cat].icon !== null) {
      blockIcon = `<i class="categories-icon fas ${pv_donnees.categories[index_cat].icon}"></i>`
    }
    frag += `
      <div class="BF-col categories-item" data-rep="${pv_donnees.categories[index_cat].nom_class}" onclick="${nomModulePrive + '.affiche_class(this,\'' + pv_donnees.categories[index_cat].nom_class + '\');'}">
        ${blockIcon}
        <div class="categories-nom" style="white-space: pre-line; text-align: center">${nom}</div>
      </div>
    `
  }
  return frag
}

/**
 * Cacher ou Afficher des éléments html en fonction de sa class (css)
 * @param {string} nomClasse - nom de la class (css)
 * @param {string} action - cacher ou afficher la class
 * @param {string} typeEle - flex ou block (uniquement pour l'affichage)
 */
function cacherAfficherClassElementHtml(nomClasse, action, typeEle) {
  // les éléments de la class
  let eles = document.querySelectorAll('.' + nomClasse)
  Object.keys(eles).forEach((id) => {
    let ele = eles[id]
    if (action === 'cacher') {
      ele.style.display = 'none'
    }
    if (action === 'afficher') {
      ele.style.display = typeEle
    }
  })
}

/**
 * Renseigne la div titre
 * @param {String} titre - titre de la vue (peut contenir un élément html + attribut 'data-i8n')
 */
export function asignerTitreVue(titre) {
  document.querySelector('#header-part-left-titre').innerHTML = `
  <div class="titre-vue">
    ${titre}
  </div>`
  translate('#header-part-left-titre')
}

/**
 * Afficher un point de vente en fonction de son uuid
 * @param {String} pv_uuid - uuid du point de vente courant
 */
export function afficherPointDeVentes(pv_uuid) {
  // console.log('-> fonction afficherPointDeVentes, pv_uuid = ', pv_uuid, '  --  type = ', typeof pv_uuid)
  let dataPV = glob.data.filter(obj => obj.id === pv_uuid)[0]

  if (dataPV.comportement === "K") {
    // --- pv kiosque ---
    // htmx.ajax('GET', '/htmx/payment_intent_tpe/request_card/', {target:'#tb-kiosque', swap:'outerHTML'})
    window.location = "/htmx/kiosk/"
  } else {
    // --- pv différent de kioske ---
    // initialisation vue table
    sys.effacerElements(['#commandes-table', '#tables', '#service-commandes'])
    sys.afficherElements(['#page-commandes,block'])

    // arrivé dans le pv la liste est affiché ou pas en fonction de la largeur  de l'écran
    const largeurSup1203px = window.matchMedia('(min-width: 1023px)').matches
    if (largeurSup1203px === true) {
      sys.afficherElements(['#achats,flex', '#products,flex'])
    } else {
      sys.effacerElements(['#achats'])
      sys.afficherElements(['#products,flex'])
    }

    // titre vue
    let nomTitre = dataPV.name
    let iconTitre = dataPV.icon

    let titre = ''
    if (dataPV.service_direct === false) {
      titre = `<span data-i8n="newTableOrder,capitalize">Nouvelle commande sur table</span> ${glob.tableEnCours.nom}, <span data-i8n="ps,uppercase">PV</span> ${nomTitre}`
    } else {
      titre = `<span data-i8n="directService,capitalize">Service Direct</span> - <i class="fas ${iconTitre}"></i> ${nomTitre}`
    }

    // console.log('test -> service_direct = ', dataPV.service_direct)
    vue_pv.asignerTitreVue(titre)

    let ele_tous = document.querySelector('#categorie-tous')
    // cacher tous les blocks point de ventes
    cacherAfficherClassElementHtml('block-pv', 'cacher')

    // définir le point de vente en cours
    pv_uuid_courant = pv_uuid

    // actualisation de la possibilité de commander ou d'acheter directement
    serviceDirecte = glob.data.filter(obj => obj.id === pv_uuid_courant)[0].service_direct
    // console.log('serviceDirecte = ',serviceDirecte)

    // mise à jour du bouton valider
    majBoutonValiderPointsDeVentes(1)

    // afficher le block point de vente voulu
    document.querySelector('#pv' + pv_uuid).style.display = 'block'

    // ---- catégories ----
    // compose la liste de catégories en fonction du point de ventes
    let contenu_categories = afficher_categories()

    // insertion de la liste dans la page
    document.querySelector('#categories').innerHTML = contenu_categories
    translate('#categories')

    // sélectionner la catégorie "tous" = class 'bouton-article'
    affiche_class(ele_tous, 'bouton-article')
    ele_tous.classList.add('active')

    // clique sur "Tous"
    document.querySelector('#categorie-tous').click()
  }
}

export function retourne_index_pv(uuid_courant) {
  for (let ipv = 0; ipv < glob.data.length; ipv++) {
    if (glob.data[ipv].id === uuid_courant) {
      return ipv
    }
  }
  console.log('-> Erreur: uuid_courant inconnu !!')
  return 999999 // émet un index de tableau erroné
}

// obtenir l'enregistrement de la variable "total" du DOM
export function getTotalPointDeVentes() {
  if (document.querySelector('#article-infos-divers')) {
    return parseFloat(document.querySelector('#article-infos-divers').getAttribute('data-total'))
  } else {
    return 0
  }
}

/**
 * Mise à jour du bouton valider des points de ventes
 * Change le bouton Valider("prendre_commande" ou vente_directe) des points de ventes en fonction du mode en cours "modeCommandes"
 * @param {Number} typeMaj = 0 retourne un fragment html / 1 insert un fragment html
 * @returns {String} fragment html
 */
export function majBoutonValiderPointsDeVentes(typeMaj) {
  // console.log('-> fonction majBoutonValiderPointsDeVentes !')

  // supprime le bouton valider
  if (typeMaj === 1) {
    sys.supElement('#bt-valider')
  }

  let dataPv = glob.data.filter(obj => obj.id === pv_uuid_courant)[0]
  serviceDirecte = dataPv.service_direct
  // console.log('serviceDirecte = ', serviceDirecte)

  // Pour les points de ventes qui acceptent les commandes
  let foncBouton = `onclick="vue_pv.testPaiementPossible('prendre_commande')"`

  // Pour les points de ventes qui n'acceptent pas les commandes ou le "Cashless" qui lui n'autorise pas les commandes donc "vente_directe"
  if (serviceDirecte === true || dataPv.comportement === 'C') {
    foncBouton = `onclick="vue_pv.testPaiementPossible('vente_directe')"`
  }

  let boutonValider = `<div id="bt-valider" class="BF-ligne footer-bt fond-ok" ${foncBouton}>
    <i class="footer-bt-icon fas fa-check-circle md4px"></i>
    <div class="BF-col-deb footer-bt-text mg4px">
      <div data-i8n="validate,uppercase">VALIDER</div>
      <div id="bt-valider-total"><span data-i8n="total,uppercase">TOTAL</span> ${vue_pv.getTotalPointDeVentes()} ${getTranslate('currencySymbol', null, 'methodCurrency')}</div>
    </div>
  </div>`

  if (typeMaj === 1) {
    let ele = document.querySelector('#page-commandes-footer')
    ele.insertAdjacentHTML('beforeend', boutonValider)
    translate('#page-commandes-footer')
  } else {
    return boutonValider
  }
}

// affiche les articles
export function compose_liste_articles(afficher_les_prix, monnaie_principale_name, pv_uuid) {
  // traite le point de vente (pv_donnees variable privée à la fonction)
  let pv_donnees = traitement_donnees_pv()

  let frag_html = ''
  for (let index_article in pv_donnees.articles) {
    let article = pv_donnees.articles[index_article]
    // sys.logJson('article = ', article)
    // ignorer l'article fractionné
    if (article.id !== glob.uuidArticlePaiementFractionne) {
      // si la méthode n'est pas renseignée la mettre dans méthode "Inconnue"
      if (glob.tabMethodesATester.includes(article.methode_name) === false) {
        article.bt_groupement = glob.bt_groupement['Inconnue']
      } else {
        article.bt_groupement = glob.bt_groupement[article.methode_name]
      }
      article.afficher_les_prix = afficher_les_prix
      article.nom_module = nomModulePrive
      article.monnaie_principale_name = monnaie_principale_name
      article.pv = pv_uuid
      if (article.categorie !== null) {
        for (let index_cat in pv_donnees.categories) {
          if (pv_donnees.categories[index_cat].nom === article.categorie.name) {
            article.class_categorie = pv_donnees.categories[index_cat].nom_class
            break
          }
        }
      }
      frag_html += `<bouton-article data="${sys.html_pass_obj_in(article)}" id="cypress${article.id}"></bouton-article>`
    }
  }
  return frag_html
}

export function prepareContenuPointsDeVentes() {
  let frag = '', pv_style = '', afficher_les_prix = null
  // memorise le point de vente courant
  let mem_pv_uuid_courant = pv_uuid_courant

  for (let pv = 0; pv < glob.data.length; pv++) {
    // cache les points de ventes sauf le premier
    pv_style = 'style="display:none;"'
    if (pv === 0) {
      pv_style = ''
    }

    // change temporairement le uuid_courant
    pv_uuid_courant = glob.data[pv].id

    afficher_les_prix = glob.data[pv].afficher_les_prix

    frag += `<div id="pv${glob.data[pv].id}" class="block-pv" ${pv_style} data-responsable-uuid="${glob.responsable.uuid}" data-responsable-nom="${glob.responsable.nom}" data-monnaie-principale-name="${glob.monnaie_principale_name}" data-name-pdv="${glob.data[pv].name}" data-pv-uuid="${glob.data[pv].id}" data-accepte-commandes="${glob.data[pv].accepte_commandes}" data-accepte-especes="${glob.data[pv].accepte_especes}" data-accepte-carte-bancaire="${glob.data[pv].accepte_carte_bancaire}">`
    frag += compose_liste_articles(afficher_les_prix, glob.monnaie_principale_name, pv_uuid_courant)
    frag += '</div>'
  }
  // reinitialise le point de vente courant
  pv_uuid_courant = mem_pv_uuid_courant
  return frag
}

// lance l'affichage d'un point de vente
export function initDataPVcourant(indexPV) {
  // supprime les articles sélectionnés
  rezet_commandes()

  // point de vente ancien
  pv_uuid_ancien = pv_uuid_courant
  // point de vente courant
  pv_uuid_courant = glob.data[indexPV].id

  // etat initial du service directe
  glob.data[indexPV].service_direct = etatInitialServiceDirectePVs[indexPV]
  document.querySelector('#menu-burger-conteneur').classList.toggle('burger-show')

  if (glob.data[indexPV].service_direct === true) {
    vue_pv.afficherPointDeVentes(glob.data[indexPV].id)
  } else {
    glob.tableEnCours = null
    restau.afficherTables('assignerTable', glob.data[indexPV].name)
  }
}

/**
 * Afficher les points de ventes dans le menu
 */
export function afficherMenuPV() {
  // console.log('-> fonction afficherMenuPV !')
  let fragPV = '', classPlus = ''

  // tri sur le poid des points de ventes
  sys.trierTableauObjetCroissantFoncAttribut(glob.data, 'poid_liste')

  for (let pv = 0; pv < glob.data.length; pv++) {
    let active = ''
    if (pv === 0) {
      active = 'active'
    }
    let icon = 'fa-smile-wink'
    if (glob.data[pv].icon !== null) {
      icon = glob.data[pv].icon
    }

    classPlus = ''
    if (glob.data[pv].comportement === 'C') {
      classPlus = 'fond-menu-cashless'
    }

    fragPV += `
    <div class="menu-burger-item BF-ligne-deb ${classPlus} test-${glob.data[pv].name.toLowerCase()}" onclick="vue_pv.initDataPVcourant('${pv}')">
      <i class="fas ${icon}"></i>
      <div>${glob.data[pv].name}</div>
    </div>
    `
  }

  fragPV += `
    <div class="menu-burger-item BF-ligne" onclick="vue_pv.composeMenuPrincipal(1)">
      <i class="fas fa-caret-up"></i>
    </div>
  `
  let burgerMenuContent = document.querySelector('#menu-burger-conteneur')
  // insertion des points de ventes
  burgerMenuContent.innerHTML = fragPV
  // process dynamic htmx content
  htmx.process(burgerMenuContent)
}

export function afficherMenuPreparations() {
  // réinitialisation de l'interval d'actualisation de la vue préparation
  glob.intervalRelanceServiceAfficherCommandesTable = 5000
  let csrfToken = document.querySelector('input[name="csrfmiddlewaretoken"]').value
  let requete = {
    type: 'get',
    url: 'preparation',
    dataTypeReturn: 'json',
    csrfToken: csrfToken,
    // attente = paramètres pour l'icon de chargement
    attente: { largeur: 80, couleur: '#0F0', nbc: 8, rpt: 4, epaisseur: 8 }
  }
  sys.ajax(requete, function (retour, status) {
    // sys.logJson('status = ',status)
    // sys.logJson('retour = ',retour)
    if (status.code === 200) {
      let servicesFrag = ''
      for (let i = 0; i < retour.length; i++) {
        let nomGroupement = retour[i].name
        let idGroupement = retour[i].pk
        let iconGroupement = retour[i].icon
        let fonction = `document.querySelector('#menu-burger-conteneur').classList.toggle('burger-show');vue_pv.composeMenuPrincipal(1);attenteLancerVerifierEtatCommandes.interval=intervalActualisationVuePreparations;attenteLancerVerifierEtatCommandes.etat=0;restau.serviceAfficherCommandesTable(${idGroupement}, ${null})`
        // console.log('-> ', nomGroupement, '  --  ', idGroupement)
        servicesFrag += `
          <div class="menu-burger-item BF-ligne-deb" onclick="${fonction}">
            <i class="fas ${iconGroupement}"></i>
            <div>${nomGroupement.toUpperCase()}</div>
          </div>
        `
      }
      servicesFrag += `
        <div class="menu-burger-item BF-ligne" onclick="vue_pv.composeMenuPrincipal(1)">
          <i class="fas fa-caret-up"></i>
        </div>
      `
      document.querySelector('#menu-burger-conteneur').innerHTML = servicesFrag

    } else {
      vue_pv.afficher_message_erreur_requete(retour, status)
    }
  })
}

/**
 * change la valeur du booléen
 */
export function changerModeGerant() {
  glob.modeGerant = !glob.modeGerant

  //actualisation de préparations si le mode gérant change
  let affichageEtatCommandes = document.querySelector('#service-commandes').style.display
  if (affichageEtatCommandes === 'block') {
    // récupérer les données "groupementCategories, idTable" sur le premier élément
    let elementCible = document.querySelector('#service-commandes')
    let idTable = parseInt(elementCible.getAttribute('data-table-id'))
    let groupementCategories = parseInt(elementCible.getAttribute('data-groupement-categories'))
    let provenance = elementCible.getAttribute('data-provenance')
    // actualise la vue
    restau.serviceAfficherCommandesTable(groupementCategories, idTable, provenance)
  }
}

/**
 * Compose le menu principal
 * @param {Number} typeMaj = 0 retourne un fragment html / 1 insert un fragment html
 */
export function composeMenuPrincipal(typeMaj) {
  // trie => sys.trierTableauObjetCroissantFoncAttribut(glob.tables, 'poids')
  // sys.logJson('glob.data = ', glob.data)

  let frag = ''

  // points de ventes
  frag += `<div class="menu-burger-item BF-ligne-deb" onclick="vue_pv.afficherMenuPV()">
      <i class="fas fa-store"></i>
      <div data-i8n="pointOfSales,uppercase">POINTS DE VENTES</div>
    </div>`

  // services
  frag += `<div class="menu-burger-item BF-ligne-deb" onclick="vue_pv.afficherMenuPreparations()">
      <i class="fas fa-concierge-bell"></i>
      <div data-i8n="preparations,uppercase">PREPARATIONS</div>
    </div>`

  // commandes
  frag += `<div class="menu-burger-item BF-ligne-deb fond-menu-tables" onclick="document.querySelector('#menu-burger-conteneur').classList.toggle('burger-show');restau.afficherTables('visualiserCommandes')">
      <i class="fas fa-utensils"></i>
      <div data-i8n="tables,uppercase">TABLES</div>
    </div>`

  // mode édition
  // console.log('--> glob.passageModeGerant  = ', glob.passageModeGerant)
  if (glob.passageModeGerant === true) {
    let iconModeGerant = `<i class="fas fa-lock" style="color:#FF0000;"></i>`
    if (glob.modeGerant === true) {
      iconModeGerant = `<i class="fas fa-lock-open" style="color:#00FF00;"></i>`
    }
    frag += `<div id="conteneur-menu-mode-gerant" class="menu-burger-item BF-ligne-deb" onclick="document.querySelector('#menu-burger-conteneur').classList.toggle('burger-show');vue_pv.changerModeGerant();">
      ${iconModeGerant}
      <div data-i8n="managingMode,uppercase">MODE GERANT.E</div>
    </div>`
  }

  // add all menus plugin "../webview/js/menuPlugins/addAllMenuPlugin.js"
  frag += addPluginFunctionsToMenu()

  if (typeMaj === 0) {
    return frag
  } else {
    document.querySelector('#menu-burger-conteneur').innerHTML = frag
    translate('#menu-burger-conteneur')
  }
}

// ---- fin: partie rendu html ----

export function decrementer_nombre_produit(uuid_bt_article) {
  //liste_ligne_article
  // console.log('uuid article = ' + uuid_bt_article)
  let bt = document.querySelector(`#pv${pv_uuid_courant} bouton-article[uuid="${uuid_bt_article}"]`)
  let nb_commande = parseInt(bt.getAttribute('nb-commande'))
  let prix_article = parseFloat(bt.getAttribute('prix'))

  // console.log('nb_commande =', nb_commande, '  --  prix_article =', prix_article)
  if (nb_commande > 0) {
    nb_commande--
    // maj sur bouton
    bt.setAttribute('nb-commande', nb_commande)
    bt.shadowRoot.querySelector('#rep-nb-article' + uuid_bt_article).innerHTML = nb_commande
    // maj liste prix
    document.querySelector('#achats-liste-ligne-nb' + uuid_bt_article).innerHTML = nb_commande
    // obtenir l'enregistrement de la variable "total" du DOM
    let total = parseFloat(document.querySelector('#article-infos-divers').getAttribute('data-total'))
    // soustraire le prix de l'article sélectionné
    total = new Big(total).minus(prix_article)
    // enregistre la nouvelle valeur dans le DOM
    document.querySelector('#article-infos-divers').setAttribute('data-total', total)
    // maj bouton valider
    document.querySelector('#bt-valider-total').innerHTML = `<span data-i8n="total,uppercase">TOTAL</span> ${total} ${getTranslate('currencySymbol', null, 'methodCurrency')}`
    // une fois plus de produit dans la liste d'achats, reset les boutons articles
    if (total === 0) {
      rezet_commandes()
    }
    if (nb_commande === 0) sys.supElement('#achats-liste-ligne' + uuid_bt_article)
  }
}

export function rezet_commandes() {
  // console.log('fonc rezet_commandes !!');
  // désactive l'achat
  document.querySelector('#article-infos-divers').setAttribute('achat-possible', 0)

  // renseigne le bouton "VALIDER" contenant l'information du total des achats
  document.querySelector('#bt-valider-total').innerHTML = `<span data-i8n="total,uppercase">TOTAL</span> 0 ${getTranslate('currencySymbol', null, 'methodCurrency')}`
  translate('#bt-valider-total')

  // met le nombre d'article commander de tous les articles à 0
  let eles = document.querySelectorAll('.bouton-article')
  for (let i = 0; i < eles.length; i++) {
    let ele = eles[i]
    ele.setAttribute('nb-commande', 0)
    // efface le groupe-actif
    ele.setAttribute('groupe-actif', '')
    // enlève la class 'grise'
    ele.shadowRoot.querySelector('#bt-rideau').style.display = 'none'

    let uuid = ele.getAttribute('uuid')
    ele.shadowRoot.querySelector('#rep-nb-article' + uuid).innerHTML = 0
  }

  // enregistre le total des commandes à 0 dans le DOM
  document.querySelector('#article-infos-divers').setAttribute('data-total', 0)

  // vider la liste d'achats
  document.querySelector('#achats-liste').innerHTML = ''
}

export function exit() {
  window.location = '/wv'
}

/** @function
 * Afficher les erreurs suite à une connexion ajax
 * @param {Object} retour - données
 * @param {Object.<number,string>} status - nombre et texte
 */
export function afficher_message_erreur_requete(retour, status) {
  // sys.logJson('retour = ',retour);
  let message = `<div class="BF-col l100p h100p pdep m0" style="font-size:1rem;font-weight:bold;color:#FFFFFF;text-shadow: 0 1px 0 rgba(255,255,255,0.5);">
    <div style="font-size:1.5rem;margin-bottom:8px" data-i8n="stausCodeError,uppercase">ERREUR STATUS CODE : ${status.code}</div>
    <div style="font-size:1.5rem;margin-bottom:16px">${status.texte}</div>`

  for (let clef in retour) {
    message += '<div class="BF-ligne">'
    message += '<div style="font-size:1rem;margin-right:8px">' + clef + ' : </div>'
    let textes = retour[clef]
    message += '<div class="BF-col">'
    if (textes.isArray) {
      for (let i = 0; i < textes.length; i++) {
        message += '<div>' + textes[i] + '</div>'
      }
    } else {
      message += '<div>' + textes + '</div>'
    }
    message += '</div>'
    message += '</div>'
  }
  message += '</div>'
  let bouton = `<div class="popup-conteneur-bt-retour BF-col">
    <bouton-basique id="popup-retour" traiter-texte="1" texte="RETOUR|2rem||return-uppercase" couleur-fond="#3b567f" icon="fa-undo-alt||2.5rem" width="400px" height="120px"  onclick="fn.popupAnnuler();"></bouton-basique>
   </div>`

  let options = {
    message: message,
    boutons: bouton,
    type: 'danger'
  }
  fn.popup(options)
}

export function obtenirAchats(actionAValider, options) {
  // console.log('-> fonction obtenirAchats !')
  // console.log('actionAValider : ', actionAValider)
  // sys.logJson('options = ', options)

  let eles, total
  let repInfos = document.querySelector('#pv' + pv_uuid_courant)
  let pkResponsable = repInfos.getAttribute('data-responsable-uuid')
  let pkPdv = repInfos.getAttribute('data-pv-uuid')

  let pkTable = parseInt(document.querySelector('#commandes-table-contenu').getAttribute('data-idtable'))
  let articlesTempo = []
  let achats = {}

  // points de ventes
  // envoyer en préparation et envoyer_preparation_payer
  if (actionAValider === 'vente_directe' || actionAValider === 'envoyer_preparation' || actionAValider === 'envoyer_preparation_payer' || actionAValider === 'envoyer_preparation_payer_fractionner') {
    eles = document.querySelectorAll('.bouton-article')
    total = parseFloat(document.querySelector('#article-infos-divers').getAttribute('data-total'))
    for (let i = 0; i < eles.length; i++) {
      let don = {}, qty
      qty = parseInt(eles[i].getAttribute('nb-commande'))
      if (qty > 0) {
        don = {
          pk: eles[i].getAttribute('uuid'),
          qty: qty,
          pk_pdv: eles[i].getAttribute('uuid-pv')
        }
        articlesTempo.push(don)
      }
    }

    achats = {
      articles: articlesTempo,
      pk_responsable: pkResponsable,
      pk_pdv: pkPdv,
      total: total
    }

    achats.commentaire = glob.commentairesEnCours
    achats.hostname_client = glob.appConfig.hostname

    if (glob.tableEnCours !== null && actionAValider !== 'vente_directe') {
      if (glob.tableEnCours.typeValeur === 'idTable') {
        achats.pk_table = glob.tableEnCours.valeur
      } else {
        achats.nouvelle_table = glob.tableEnCours.valeur
      }
    }

    if (actionAValider === 'envoyer_preparation' || actionAValider === 'envoyer_preparation_payer_fractionner') {
      achats.moyen_paiement = 'commande'
    }
  }

  if (actionAValider === 'addition_liste') {
    let commandes = []
    eles = document.querySelectorAll('#addition-vase-communicant .article-commande')
    total = parseFloat(document.querySelector('#commandes-table-contenu').getAttribute('data-total-addition-en-cours'))
    // création du tableau de données en fonction du DOM
    for (let i = 0; i < eles.length; i++) {
      // console.log(eles[i])
      let uuidCommande = eles[i].getAttribute('data-uuid-commande')
      let uuidArticle = eles[i].getAttribute('data-uuid-article')
      if (!commandes[uuidCommande]) {
        commandes[uuidCommande] = []
        commandes[uuidCommande].push({
          uuid_commande: uuidCommande,
          pk: uuidArticle,
          qty: 1
        })
      } else {
        let nouvelArticle = 1
        for (let j = 0; j < commandes[uuidCommande].length; j++) {
          if (uuidArticle === commandes[uuidCommande][j].pk) {
            commandes[uuidCommande][j].qty = commandes[uuidCommande][j].qty + 1
            nouvelArticle = 0
            break
          }
        }
        if (nouvelArticle === 1) {
          commandes[uuidCommande].push({
            uuid_commande: uuidCommande,
            pk: uuidArticle,
            qty: 1
          })
        }
      }
    }
    // console.log('commandes = ', commandes)
    for (const commande in commandes) {
      for (let i = 0; i < commandes[commande].length; i++) {
        articlesTempo.push(commandes[commande][i])
      }
    }
    achats = {
      articles: articlesTempo,
      pk_responsable: pkResponsable,
      pk_pdv: pkPdv,
      pk_table: pkTable,
      total: total,
    }
  }

  if (actionAValider === 'addition_fractionnee') {
    achats = {
      articles: [
        {
          'pk': glob.uuidArticlePaiementFractionne,
          'qty': options.valeurEntree
        }
      ],
      pk_responsable: pkResponsable,
      pk_pdv: pkPdv,
      pk_table: pkTable,
      total: options.valeurEntree
    }
  }

  return achats
}

//TODO: créditer carte après annulation donc définir ou créditer, donc dans valider = bt valider expèce et valider carte
//annule la dernière transaction données retournées type-annulation,achats(contenant le moyen de paiement)
export function annuler_derniere_action(uuid, pkPdv, pkResponsable) {
  let csrfToken = document.querySelector('input[name="csrfmiddlewaretoken"]').value
  let requete = {
    type: 'post',
    url: 'annulation_derniere_action',
    dataType: 'form',
    dataTypeReturn: 'json',
    csrfToken: csrfToken,
    // attente = paramètres pour l'icon de chargement
    attente: { largeur: 80, couleur: '#0F0', nbc: 8, rpt: 4, epaisseur: 8 },
    data: { 'type-annulation': 'valider_annulation', uuid: uuid, 'pk_pdv': pkPdv, 'pk_responsable': pkResponsable }
  }
  sys.ajax(requete, function (retour, status) {
    let message = '', bouton = '', options = {}
    if (status.code === 200) {
      sys.logJson('retour -> ', retour)
      if ('annulation' in retour) {
        if (retour.annulation === true) {
          message = `<div class="transaction-annulee" data-i8n="canceledTransaction,uppercase">TRANSACTION ANNULEE</div>`
          let bouton = `<div class="popup-conteneur-bt-retour BF-col">
            <bouton-basique id="popup-retour" traiter-texte="1" texte="RETOUR|2rem||return-uppercase" couleur-fond="#3b567f" icon="fa-undo-alt||2.5rem" width="400px" height="120px"  onclick="fn.popupAnnuler();"></bouton-basique>
          </div>`

          options = {
            titre: message,
            boutons: bouton,
            type: 'succes'
          }
          fn.popup(options)
        }
      }
    } else {
      afficher_message_erreur_requete(retour, status)
    }
  })
}

export function demander_annulation_derniere_action() {
  // TODO: penser à faire l'annulation sur le uuid responsable, problème si achats sur 2 points de ventes différents
  let csrfToken = document.querySelector('input[name="csrfmiddlewaretoken"]').value
  // var result = (animal === 'kitty') ? 'cute' : 'still nice';
  let pk_pdv = (memorise_data_dernier_achat.pk_pdv !== undefined) ? memorise_data_dernier_achat.pk_pdv : '1111'
  let pk_responsable = (memorise_data_dernier_achat.pk_responsable !== undefined) ? memorise_data_dernier_achat.pk_responsable : '1111'

  if (pk_pdv === '1111') {
    let message = `< class="BF-col-uniforme demander-annulation" style="white-space: pre-line" data-i8n="noCancellationContactAdmin,uppercase">
      AUCUNE\nANNULATION\nPOSSIBLE\nCONTACTER\nL'ADMINISTRATEUR
    </div>`

    let bouton = `<div class="popup-conteneur-bt-retour BF-col">
      <bouton-basique id="popup-retour" traiter-texte="1" texte="RETOUR|2rem||return-uppercase" couleur-fond="#3b567f" icon="fa-undo-alt||2.5rem" width="400px" height="120px"  onclick="fn.popupAnnuler();"></bouton-basique>
    </div>`

    let options = {
      message: message,
      boutons: bouton,
      type: 'normal'
    }
    fn.popup(options)
  } else {
    let requete = {
      type: 'post',
      url: 'annulation_derniere_action',
      dataType: 'form',
      dataTypeReturn: 'json',
      csrfToken: csrfToken,
      // attente = paramètres pour l'icon de chargement
      attente: { largeur: 80, couleur: '#0F0', nbc: 8, rpt: 4, epaisseur: 8 },
      data: { 'type-annulation': 'demande_info_pour_annulation', 'pk_pdv': pk_pdv, 'pk_responsable': pk_responsable }
    }
    sys.logJson('requete = ', requete)
    sys.ajax(requete, function (retour, status) {
      let message = '', options = {}
      sys.logJson('retour = ', retour)
      if (status.code === 200) {
        // si nombre d'articles est supérieur à 0
        let test_possibilite_annulation = 0
        for (const article in retour.articles_vdus) {
          if (retour.articles_vdus[article] > 0) {
            test_possibilite_annulation = 1
            break
          }
        }

        if (test_possibilite_annulation === 1) {
          let nom_monnaie_principale = document.querySelector('#pv' + pv_uuid_courant).getAttribute('data-monnaie-principale-name')
          message += `<div class="BF-col-uniforme demander-annulation">
            <div class="mb1" data-i8n="undoLast,uppercase">ANNULER LA DERNIERE</div>
            <div class="mb10" data-i8n="transaction,uppercase">TRANSACTION</div>
            <div class="demander-annulation-taille-liste">`

          for (const article in retour.articles_vdus) {
            message += '<div class="BF-ligne-deb demander-annulation-item">' + parseFloat(retour.articles_vdus[article]) + ' - ' + article + '</div>'
          }
          message += '</div>'
          if (retour.monnaie_bc_a_rembourser && parseFloat(retour.monnaie_bc_a_rembourser) > 0) message += '<div class="mb1"><span data-i8n="repay,capitalize">Rembourser</span> ' + nom_monnaie_principale + ' : ' + parseFloat(retour.monnaie_bc_a_rembourser) + '</div>'
          if (retour.cash_a_rembourser) message += '<div class="mb1"><span data-i8n="repay,capitalize">Rembourser</span> : ' + parseFloat(retour.cash_a_rembourser) + '</div>'
          message += '</div>'
          let boutons = `<bouton-basique traiter-texte="1" texte="CONFIRMER|||comfirm-uppercase" couleur-fond="#339448" icon="fa-check-circle||2.5rem" width="400px" height="120px"  onclick="fn.popupAnnuler();${nomModulePrive}.annuler_derniere_action('${retour.uuid}', '${pk_pdv}', '${pk_responsable}')" style="margin-top:16px;"></bouton-basique>
            <div class="popup-conteneur-bt-retour BF-col">
                <bouton-basique id="popup-retour" texte="RETOUR|2rem||return-uppercase" couleur-fond="#3b567f" icon="fa-undo-alt||2.5rem" width="400px" height="120px"  onclick="fn.popupAnnuler();"></bouton-basique>
            </div>`

          options = {
            annuler: nomModulePrive + '.rezet_commandes()',
            boutons: boutons,
            message: message,
            type: 'normal'
          }
          fn.popup(options)
        } else {
          message = `<div class="BF-col-uniforme derniere-vente-deja-annulee">
            <div data-i8n="lastSale,uppercase">DERNIERE VENTE</div>
            <div data-i8n="alreadyBeenCancelled,uppercase">DEJA ANNULEE !</div>
          </div>`

          options = {
            annuler: '',
            message: message,
            type: 'attent'
          }
          fn.popup(options)
        }
      } else {
        afficher_message_erreur_requete(retour, status)
      }
    })
  }
}

/**
 * Lance une requète pour avoir les informations sur une carte
 * @param {Object} donnees = {typeCheckCarte, tagId}
 * @param {Function} callback = fonction de retour pour typeCheckCarte = 'manuel'
 * typeCheckCarte = parLecteurNfc ou manuel, moyen d'obtention du tagId
 */
export function postCheckCarte(donnees, callback) {
  // console.log('-> fonction postCheckCarte !')
  // sys.logJson('donnee = ', donnees)
  let csrfToken = document.querySelector('input[name="csrfmiddlewaretoken"]').value
  let requete = {
    type: 'post',
    url: 'check_carte',
    dataType: 'form',
    // ancien type de donné retourné
    // dataTypeReturn: 'json',
    dataTypeReturn: 'text',
    csrfToken: csrfToken,
    // attente = paramètres pour l'icon de chargement
    attente: { largeur: 80, couleur: '#0F0', nbc: 8, rpt: 4, epaisseur: 8 },
    data: { tag_id_client: donnees.tagId }
  }
  // sys.logJson('requete = ',requete)
  sys.ajax(requete, function (retour, status) {
    // sys.logJson('status = ',status)
    // sys.logJson('-> postCheckCarte retour = ',retour)
    // sys.logJson('donnees = ',donnees)
    gererRetourPostCheckCarte(retour, status, donnees, callback)
  })
}

export function check_carte() {
  rfid.muteEtat('message', `<div style="white-space: pre-line; text-align: center;" role="status" aria-label="awaiting card reading"  data-i8n="awaitingCardReading,capitalize">Attente\nlecture carte</div>`)
  rfid.muteEtat('data', { typeCheckCarte: 'parLecteurNfc' })
  rfid.muteEtat('callbackOk', postCheckCarte)
  rfid.muteEtat('tagIdIdentite', 'client1')
  rfid.lireTagId()
}

export function obtenirIdentiteClientSiBesoin(moyenPaiement, sommeDonnee) {
  // console.log('-> fonction obtenirIdentiteClientSiBesoin !')
  // console.log('moyenPaiement = ', moyenPaiement)

  let donnees = glob.dataObtenirIdentiteClientSiBesoin
  donnees.options.achats.moyen_paiement = moyenPaiement
  // sys.logJson('donnees = ', donnees)

  // gestion de la somme donnée pour le moyen de paiement 'espèce'
  if (sommeDonnee !== undefined && moyenPaiement === 'espece') {
    donnees.options['sommeDonnee'] = sommeDonnee
  }

  if (donnees.besoin_tag_id.includes('tout') === true || moyenPaiement === 'nfc') {
    rfid.muteEtat('message', `<div data-i8n="awaitingCardReading,capitalize" style="white-space: pre-line; text-align: center;">Attente\nlecture carte</div>`)
    rfid.muteEtat('data', { donnees: donnees })
    rfid.muteEtat('callbackOk', vue_pv.validerEtape2)
    rfid.muteEtat('tagIdIdentite', 'client1')
    rfid.lireTagId()
  } else {
    vue_pv.validerEtape2({ tagId: 'inutile', donnees: donnees })
  }
}

function determinerInterfaceValidation(actionAValider, achats) {
  let dataPv = glob.data.filter(obj => obj.id === pv_uuid_courant)[0]
  let accepteEspeces = dataPv.accepte_especes
  let accepteCarteBancaire = dataPv.accepte_carte_bancaire
  let accepteCheque = dataPv.accepte_cheque

  // sys.logValeurs({ accepteEspeces: accepteEspeces, accepteCarteBancaire: accepteCarteBancaire })testPaiementPossible
  let moyens_paiement_tab = [], methodes_tab = [], besoin_tag_id = [], restriction_tab = []

  let eles
  // achat d'articles, vente directe
  if (actionAValider === 'vente_directe' || actionAValider === 'envoyer_preparation_payer') {
    eles = document.querySelectorAll('.bouton-article')
  }
  // addition, liste d'articles dans l'addition
  if (actionAValider === 'addition_liste') {
    eles = document.querySelectorAll('#addition-vase-communicant .article-commande')
  }
  // addition, liste d'articles à payer
  if (actionAValider === 'addition_fractionnee') {
    eles = document.querySelectorAll('#commandes-table-articles .bouton-commande-article')
  }

  for (var i = 0; i < eles.length; i++) {
    let qty
    if (actionAValider === 'vente_directe' || actionAValider === 'envoyer_preparation_payer') {
      qty = parseInt(eles[i].getAttribute('nb-commande'))
    }
    if (actionAValider === 'addition_liste') {
      qty = 1
    }
    if (actionAValider === 'addition_fractionnee') {
      qty = parseInt(eles[i].getAttribute('nb-commande'))
    }
    if (qty > 0) {
      let methode
      if (actionAValider === 'vente_directe' || actionAValider === 'envoyer_preparation_payer') {
        methode = eles[i].getAttribute('methode')
      }
      if (actionAValider === 'addition_liste') {
        methode = eles[i].getAttribute('data-methode')
      }
      if (actionAValider === 'addition_fractionnee') {
        methode = eles[i].getAttribute('methode')
      }
      if (methodes_tab.includes(methode) === false) methodes_tab.push(methode)
      let besoins_moyens_paiement = (glob.bt_groupement[methode].moyens_paiement).toString().split('|')
      besoin_tag_id = glob.bt_groupement[methode].besoin_tag_id.split('|')
      for (let mp = 0; mp < besoins_moyens_paiement.length; mp++) {
        let moyenPaiement = besoins_moyens_paiement[mp]
        if (moyens_paiement_tab.includes(moyenPaiement) === false) moyens_paiement_tab.push(moyenPaiement)
      }

    }
  }

  // depositIsPresent(achats)

  // restriction des moyens de paiement en fonction de ceux autorisés par points de ventes (accepteEspeces,accepteCarteBancaire, accepte_)
  for (let i = 0; i < moyens_paiement_tab.length; i++) {
    // le moyen de paiement espèce est ajouté si achats contient un "retour consigne" ou s'il est accepté par le point de ventes 
    if (moyens_paiement_tab[i].toLowerCase() === 'espece' && (accepteEspeces === true || depositIsPresent(achats) === true)) restriction_tab[1] = 'espece'
    if (moyens_paiement_tab[i].toLowerCase() === 'carte_bancaire' && accepteCarteBancaire === true) restriction_tab[2] = 'carte_bancaire'
    if (moyens_paiement_tab[i].toLowerCase() === 'ch' && accepteCheque === true) restriction_tab[3] = 'CH'
    if (moyens_paiement_tab[i].toLowerCase() === 'nfc') restriction_tab[0] = 'nfc'
  }
  return { moyens_paiement: restriction_tab, methodes: methodes_tab, besoin_tag_id: besoin_tag_id }
}

export function retour_entree() {
  let frag = `<div class="BF-ligne-uniforme footer-bt fond-normal" onclick="${ctx.nom_module}.check_carte()">
    <i class="footer-bt-icon fas fa-undo-alt"></i>
    <div class="BF-col footer-bt-text">
      <div data-i8n="return,uppercase">RETOUR</div>
    </div>
  </div>`
}

export function afficherCommentaire() {
  let infosCommentaire = document.querySelector('#commentaire-commande')
  let val = infosCommentaire.innerHTML
  let pkTable = parseInt(infosCommentaire.getAttribute('pkTable'))

  let bouton = `<div class="popup-conteneur-bt-retour BF-col">
    <bouton-basique id="popup-retour" traiter-texte="1" texte="RETOUR|2rem||return-uppercase" couleur-fond="#3b567f" icon="fa-undo-alt||2.5rem" width="400px" height="120px"  onclick="fn.popupAnnuler();"></bouton-basique>
  </div>`

  let commentaire = (val === '') ? 'aucun' : val

  let options = {
    titre: `<div data-i8n="comments,capitalize">Commentaires</div>`,
    message: commentaire,
    boutons: bouton,
    type: 'normal'
  }
  fn.popup(options)
}

function clickafficherPointDeVentes() {
  window[nomModulePrive].afficherPointDeVentes(pv_uuid_courant)
}

export function afficherMessageArticlesNonSelectionnes() {
  let bouton = `<div class="popup-conteneur-bt-retour BF-col">
    <bouton-basique id="popup-retour" traiter-texte="1" texte="RETOUR|2rem||return-uppercase" couleur-fond="#3b567f" icon="fa-undo-alt||2.5rem" width="400px" height="120px"  onclick="fn.popupAnnuler();"></bouton-basique>
  </div>`

  let message = `<div class="BF-col no-article-selected test-return-msg-about-article">
    <div data-i8n="noArticle,capitalize">Aucun article</div>
    <div data-i8n="hasBeenSelected">n'a été selectioné</div>
  </div>`

  let options = {
    message: message,
    boutons: bouton,
    type: 'normal'
  }
  fn.popup(options)
}

// test si il a au moins un article à payer
export function testPaiementPossible(actionAValider) {
  // console.log('-> fonction testPaiementPossible !')
  // console.log('actionAValider = ', actionAValider)
  glob['actionAValider'] = actionAValider

  // supprime les anciennes données pour des achats avec fond insuffisants
  glob['dataCarte1'] = undefined

  if (actionAValider === 'vente_directe' || actionAValider === 'prendre_commande') {
    let achatPossible = parseInt(document.querySelector('#article-infos-divers').getAttribute('achat-possible'))
    if (achatPossible === 1) {
      // vente directe
      if (actionAValider === 'vente_directe') {
        // les articles sélectionnés
        let achats = vue_pv.obtenirAchats(actionAValider)
        let options = {
          url: 'paiement',
          actionAValider: actionAValider,
          achats: achats
        }
        validerEtape1(options)
      }
      // prise de commande
      if (actionAValider === 'prendre_commande') {
        restau.choixTypePreparation()
      }
    } else {
      afficherMessageArticlesNonSelectionnes()
    }
  }

  if (actionAValider === 'addition_liste') {
    let articlesListeAddition = document.querySelectorAll('#addition-vase-communicant .article-commande')
    if (articlesListeAddition.length > 0) { // paiement possible
      restau.validerPaiementArticleCommande(actionAValider)
    } else {
      afficherMessageArticlesNonSelectionnes()
    }
  }
}

/**
 * lister les "retours de consignes" de tous les points de ventes
 * @returns 
 */
function findAllDepositsInAllPs() {
  let findDeposits = []
  for (let item in glob.data) {
    const search = glob.data[item].articles.find(art => art.methode_name === 'RetourConsigne')
    if (search !== undefined) {
      findDeposits.push(search.id)
    }
  }
  return findDeposits
}


/**
 * Test la présence de la méthode "RetourConsigne" dans les achats
 * @param {object} achats 
 * @returns 
 */
function depositIsPresent(achats) {
  let retour = false
  const findDeposits = findAllDepositsInAllPs()

  for (let j in achats.articles) {
    const article = achats.articles[j]
    retour = findDeposits.includes(article.pk)
    if (retour === true) {
      break
    }
  }
  return retour
}

export function wsSendTotalCb() {
  const achats = glob.dataObtenirIdentiteClientSiBesoin.options.achats
  console.log('-> wsSendTotalCb')

  if (wsTerminal.on === true) {
    const data = {
      amount: achats.total,
      pk_pdv: achats.pk_pdv,
      pk_responsable: achats.pk_responsable
    }
    console.log('data =', data)
    wsTerminal.socket.send(JSON.stringify(data))
  } else {
    console.log('ws terminal déconnecté !');
  }

}

export function validerEtape1(options) {
  // console.log('-> fonction validerEtape1 !')
  // sys.logJson('options = ', options)

  let comportementPointDeVentes = glob.data.filter(obj => obj.id === pv_uuid_courant)[0].comportement
  let total = 0, resteAPayerCommande

  // vente directe
  if (options.actionAValider === 'vente_directe') {
    total = document.querySelector('#article-infos-divers').getAttribute('data-total')
  }

  // prises de commandes
  if (options.actionAValider === 'envoyer_preparation_payer') {
    total = document.querySelector('#article-infos-divers').getAttribute('data-total')
  }

  // payer addition (addition_liste ou addition_fractionnee)
  if (options.actionAValider === 'addition_liste' || options.actionAValider === 'addition_fractionnee') {
    total = options.valeurEntree
  }

  // donnees = moyens_paiement/methodes/besoin_tag_id
  let donnees = determinerInterfaceValidation(options.actionAValider, options.achats)

  let moyens_paiement_tab = donnees.moyens_paiement
  let besoin_tag_id = donnees.besoin_tag_id

  // ajout des boutons moyens de paiement + form htmx
  let boutons = ''

  if (moyens_paiement_tab.length >= 1) {
    const paymentBtWidth = 280
    const paymentBtHeight = 90
    for (let i = 0; i < moyens_paiement_tab.length; i++) {
      glob.dataObtenirIdentiteClientSiBesoin = {
        options: options,
        methodes: donnees.methodes,
        besoin_tag_id: besoin_tag_id
      }

      if (moyens_paiement_tab[i] === 'nfc') {
        // attente de traitement,erreur adhésion cashless
        let dataTest = glob.data.filter(obj => obj.id === pv_uuid_courant)[0]
        let obtenirPvCashless = dataTest.comportement
        let testAchatsArticlesAdhesion = 0
        try {
          let obtenirUuidAdhesion = dataTest.articles.filter(obj => obj.name === 'Adhésion')[0].id
          testAchatsArticlesAdhesion = options.achats.articles.filter(obj => obj.pk === obtenirUuidAdhesion).length
          // console.log('obtenirUuidAdhesion = ', obtenirUuidAdhesion)
        } catch (e) {
          testAchatsArticlesAdhesion = 0
        }
        // console.log('obtenirPvCashless = ',obtenirPvCashless)
        // console.log('testAchatsArticlesAdhesion', testAchatsArticlesAdhesion)

        if (obtenirPvCashless === 'C' && testAchatsArticlesAdhesion > 0) {
          // ne pas afficher le cashless , adhésion sur point de vente cashless
        } else {
          // boutons += `<bouton-basique class="test-ref-cashless" traiter-texte="1" texte="CASHLESS|2rem|,[TOTAL] ${total} [€]|1.5rem||total-uppercase;currencySymbol" width="400px" height="120px" couleur-fond="#339448" icon="fa-address-card||2.5rem" onclick="fn.popupAnnuler();vue_pv.obtenirIdentiteClientSiBesoin('nfc')" style="margin-top:16px;"></bouton-basique>`
          boutons += paymentBt({
            width: paymentBtWidth,
            height: paymentBtHeight,
            backgroundColor: "#339448",
            textColor: "#FFFFFF",
            icon: "fa-address-card",
            methods: ["fn.popupAnnuler()", "vue_pv.obtenirIdentiteClientSiBesoin('nfc')"],
            currency: { name: "CASHLESS" },
            total,
            cssClass: ["test-ref-cashless"]
          })
        }
      }

      if (moyens_paiement_tab[i] === 'espece') {
        if (depositIsPresent(options.achats) === false) {
          // je paye en espèce, ce n'est pas une consigne
          // boutons += `<bouton-basique class="test-ref-cash" traiter-texte="1" texte="ESPECE|2rem||cash-uppercase,[TOTAL] ${total} [€]|1.5rem||total-uppercase;currencySymbol" width="400px" height="120px" couleur-fond="#339448" icon="fa-coins||2.5rem" onclick="fn.popupConfirme('espece', 'ESPECE', 'vue_pv.obtenirIdentiteClientSiBesoin')" style="margin-top:16px;"></bouton-basique>`
          boutons += paymentBt({
            width: paymentBtWidth,
            height: paymentBtHeight,
            backgroundColor: "#339448",
            textColor: "#FFFFFF",
            icon: "fa-coins",
            methods: ["fn.popupConfirme('espece', 'ESPECE', 'vue_pv.obtenirIdentiteClientSiBesoin')"],
            currency: { name: "ESPECE", tradIndex: 'cash', tradOption: 'uppercase' },
            total,
            cssClass: ["test-ref-cash"]
          })
        } else {
          // c'est une consigne, espèce; mais espèce à rendre 
          // boutons += `<bouton-basique class="test-ref-cash" traiter-texte="1" texte="ESPECE|2rem||cash-uppercase,[TOTAL] ${total} [€]|1.5rem||total-uppercase;currencySymbol" width="400px" height="120px" couleur-fond="#339448" icon="fa-coins||2.5rem" onclick="fn.popupAnnuler();vue_pv.obtenirIdentiteClientSiBesoin('espece')" style="margin-top:16px;"></bouton-basique>`
          boutons += paymentBt({
            width: paymentBtWidth,
            height: paymentBtHeight,
            backgroundColor: "#339448",
            textColor: "#FFFFFF",
            icon: "fa-coins",
            methods: ["fn.popupAnnuler()", "vue_pv.obtenirIdentiteClientSiBesoin('espece')"],
            currency: { name: "ESPECE", tradIndex: 'cash', tradOption: 'uppercase' },
            total,
            cssClass: ["test-ref-cash"]
          })
        }
      }

      if (moyens_paiement_tab[i] === 'carte_bancaire') {
        // boutons += `<bouton-basique class="test-ref-cb" traiter-texte="1" texte="CB|2rem||cb-uppercase,[TOTAL] ${total} [€]|1.5rem||total-uppercase;currencySymbol" width="400px" height="120px" couleur-fond="#339448" icon="fa-credit-card||2.5rem" onclick="fn.popupConfirme('carte_bancaire', 'CB', 'vue_pv.obtenirIdentiteClientSiBesoin')" style="margin-top:16px;"></bouton-basique>`
        boutons += paymentBt({
          width: paymentBtWidth,
          height: paymentBtHeight,
          backgroundColor: "#339448",
          textColor: "#FFFFFF",
          icon: "fa-credit-card",
          methods: ["fn.popupConfirme('carte_bancaire', 'CB', 'vue_pv.obtenirIdentiteClientSiBesoin')"],
          currency: { name: "CB", tradIndex: 'cb', tradOption: 'uppercase' },
          total,
          cssClass: ["test-ref-cb"]
        })
      }

      if (moyens_paiement_tab[i] === 'CH') {
        // boutons += `<bouton-basique class="test-ref-ch" traiter-texte="1" texte="CH|2rem||cheque-uppercase,[TOTAL] ${total} [€]|1.5rem||total-uppercase;currencySymbol" width="400px" height="120px" couleur-fond="#339448" icon="fa-money-check||2.5rem" onclick="fn.popupConfirme('CH', 'CH', 'vue_pv.obtenirIdentiteClientSiBesoin')" style="margin-top:16px;"></bouton-basique>`
        boutons += paymentBt({
          width: paymentBtWidth,
          height: paymentBtHeight,
          backgroundColor: "#339448",
          textColor: "#FFFFFF",
          icon: "fa-money-check",
          methods: ["fn.popupConfirme('CH', 'CH', 'vue_pv.obtenirIdentiteClientSiBesoin')"],
          currency: { name: "CH", tradIndex: 'cheque', tradOption: 'uppercase' },
          total,
          cssClass: ["test-ref-ch"]
        })
      }

    }

    // bouton "OFFRIR"  en mode gérant uniquement masi pas pour le point de ventes "CASHLESS"
    if (glob.modeGerant === true && comportementPointDeVentes !== 'C') {
      glob.dataObtenirIdentiteClientSiBesoin = { options: options, methodes: donnees.methodes, besoin_tag_id: '' }
      boutons += `<bouton-basique traiter-texte="1" texte="OFFRIR|2rem||offer-uppercase" width="400px" height="120px" couleur-fond="#339448" icon="fa-gift||2.5rem" onclick="fn.popupConfirme('gift', 'OFFRIR', 'vue_pv.obtenirIdentiteClientSiBesoin')" style="margin-top:16px;"></bouton-basique>`
    }

    boutons += `<bouton-basique id="popup-retour" traiter-texte="1" texte="RETOUR|2rem||return-uppercase" couleur-fond="#3b567f" icon="fa-undo-alt||2.5rem" width="400px" height="120px"  onclick="fn.popupAnnuler();" style="margin-top:16px;"></bouton-basique>`
    let optionsPopup = {
      boutons: boutons,
      titre: `<div class="selection-type-paiement" data-i8n="paymentTypes,capitalize">Types de paiement</div>`,
      type: 'normal'
    }
    fn.popup(optionsPopup)

  } else { // passer directement à la méthode
    glob.dataObtenirIdentiteClientSiBesoin = {
      options: options,
      methodes: donnees.methodes,
      besoin_tag_id: besoin_tag_id
    }
    obtenirIdentiteClientSiBesoin('')
  }
}

/**
 * Demander d'envoyer un ticket
 * @param {String} tagId = tagId de la carte débiter
 */
export function demanderEnvoyerTicket(tagId, data) {
  console.log('-> fonction demanderEnvoyerTicket !')
  let fonctionsRetour = JSON.parse(unescape(data)).fonc

  console.log('--> ', fonctionsRetour)
  let csrfToken = document.querySelector('input[name="csrfmiddlewaretoken"]').value
  let requete = {
    type: 'get',
    url: `ticket_client/${tagId}`,
    csrfToken: csrfToken,
    // dataType: 'json',
    dataTypeReturn: 'json',
    attente: {
      largeur: 160,
      couleur: '#FFFFFF',
      nbc: 10,
      rpt: 10,
      epaisseur: 20
    }
  }
  // sys.logJson('requete = ', requete)
  sys.ajax(requete, (retour, status) => {
    sys.logJson('status = ', status)
    sys.logJson('retour = ', retour)
    let msg = `<div class="BF-col-uniforme message-transaction-ok-titre">`
    let typeMessage = ''
    if (status === 200) {
      typeMessage = 'succes'
    } else {
      typeMessage = 'danger'
    }
    msg += `<div class="message-transaction-ok-divers">${retour}</div>`
    msg += '</div>'
    let boutons = `<div class="popup-conteneur-bt-retour BF-col">
      <bouton-basique id="popup-retour" traiter-texte="1" texte="RETOUR|2rem||return-uppercase" couleur-fond="#3b567f" icon="fa-undo-alt||2.5rem" width="400px" height="120px" onclick="${fonctionsRetour}"></bouton-basique>
    </div>`

    fn.popup({ message: msg, boutons: boutons, type: 'succes' })
  })
}

export function postEtapeMoyenComplementaire(data) {
  // console.log('-> fonc postEtapeMoyenComplementaire :')
  // sys.logJson('data = ', data)
  // sys.logJson('glob.dataCarte1 = ', glob.dataCarte1)

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

  if (data.moyenPaiement === 'espece') {
    glob.dataCarte1.options['sommeDonnee'] = data.sommeDonnee
  }

  // console.log('glob.dataCarte1.options', glob.dataCarte1.options)

  let csrfToken = document.querySelector('input[name="csrfmiddlewaretoken"]').value
  let requete = {
    type: 'post',
    url: 'paiement',
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
  sys.ajax(requete, async (retour, status) => {
    // console.log(`-> postEtapeMoyenComplementaire !`)
    // sys.logValeurs({ retour: retour, status: status, globSataCarte1: glob.dataCarte1.options })
    if (data.moyenPaiement === 'espece') {
      await openCashDrawer()
    }
    gererRetourPostPaiement(retour, status, glob.dataCarte1.options)
  })

}

export function validerEtapeMoyenComplementaire(moyenPaiement, sommeDonnee) {
  // console.log('-> fonction validerEtapeMoyenComplementaire !')
  //glob.dataCarte1.moyenPaiement = moyenPaiement

  let data
  if (sommeDonnee === undefined) {
    data = { moyenPaiement }
  } else {
    data = { moyenPaiement, sommeDonnee }
  }

  if (moyenPaiement === 'nfc') {
    rfid.muteEtat('message', `<div data-i8n="awaitingCardReading,capitalize" style="white-space: pre-line; text-align: center;">Attente\nlecture carte</div>`)
    rfid.muteEtat('data', data)
    rfid.muteEtat('callbackOk', postEtapeMoyenComplementaire)
    rfid.muteEtat('tagIdIdentite', 'client2')
    rfid.lireTagId()
  } else {
    postEtapeMoyenComplementaire(data)
  }
}

export function validerEtape2(data) {
  // console.log('-> fonction validerEtape2 !')
  // sys.logJson('data = ', data)
  let options = {}

  // L'utilisation du lecteur nfc, impose un format de données différent.
  // Formatage des données lors d'une commande, pour uniformisation de cette fonction
  if (data.tagId !== undefined) {
    options = data.donnees.options
    options.tagId = data.tagId
    options.methodes = data.donnees.methodes
    options.besoin_tag_id = data.donnees.besoin_tag_id
    // ne renseigne le tag id que si besoin
    if (data.tagId !== 'inutile') {
      options.achats.tag_id = data.tagId
    }
  } else {
    options = data
  }

  if (options.achats.moyen_paiement === '') {
    options.achats.moyen_paiement = 'nfc'
  }

  let csrfToken = document.querySelector('input[name="csrfmiddlewaretoken"]').value

  options.achats.total = Math.abs(options.achats.total)

  let requete = {
    type: 'post',
    url: options.url,
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
    data: options.achats
  }
  // console.log('options.achats =', options.achats)
  sys.ajax(requete, async function (retour, status) {
    gererRetourPostPaiement(retour, status, options)
    // sys.logValeurs({retour: retour, status: status, options: options})
    // ouvre la caisse
    if (options.achats.moyen_paiement === 'espece') {
      await openCashDrawer()
    }
  })
}

/**
 * éfface les conteneurs(<div>) de class 'visu-item' affichant le contenu de chaque catégorie
 * @return {void}
 */
function efface_conteneur_categorie() {
  let eles = document.querySelectorAll('.visu-item')
  for (let i = 0; i < eles.length; i++) {
    eles[i].style.display = 'none'
  }
}

//affiche le contenu d'une catégorie identifié par 'id_categorie'
export function afficher_conteneur_categorie(id_categorie) {
  // console.log('categorie = ' + id_categorie);
  // effacer 'visu-base'
  document.querySelector('#visu_base').style.display = 'none'
  // effacer les 'visu-item'
  efface_conteneur_categorie()
  // afficher la catégorie sélectyionnée
  document.querySelector('#visu_' + id_categorie).style.display = 'block'
}

// Retour à la vue initiale de la page article(articles.html, function vue_initiale)
export function retour_visuel_depart() {
  // effacer les 'visu-item'
  efface_conteneur_categorie()
  // afficher 'visu-bas'
  document.querySelector('#visu_base').style.display = 'block'
}

/**
 * Réorganise les données points de ventes : {categories: [objet], articles: [objet]}
 * @returns {Array}
 */
function traitement_donnees_pv() {
  let pv_en_cours = retourne_index_pv(pv_uuid_courant)
  let donnees = glob.data[pv_en_cours]

  let retour = {}
  // sys.logJson('--> donnees = ',donnees)

  // 1 - recherche des catégories
  let liste_categories = []
  let liste_categories_class = []
  let nom_categorie = '', poid = null
  const regexReplaceClass = / /g
  for (let index_article = 0; index_article < donnees.articles.length; index_article++) {
    let article = donnees.articles[index_article]
    // sys.logJson('-> article = ',article);
    // console.log('-------------------------------------------------------');

    if (article.categorie !== null) {
      nom_categorie = article.categorie.name
      poid = article.categorie.poid_liste
    }
    if (liste_categories.includes(nom_categorie) === false) {
      let nom_cat = sys.supAccents(nom_categorie.replace(regexReplaceClass, '-').toLowerCase())
      let icon = null
      if (article.categorie !== null) icon = article.categorie.icon

      let infos = { nom: nom_categorie, nom_class: nom_cat, icon: icon, poid: poid }
      liste_categories_class.push(infos)
      liste_categories.push(nom_categorie)
    }
  }
  retour.categories = liste_categories_class

  // 2 - regroupe les articles par tableau de catégories
  retour.articles = donnees.articles

  liste_categories = null
  liste_categories_class = null

  return retour
}