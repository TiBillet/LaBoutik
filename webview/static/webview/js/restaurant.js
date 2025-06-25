/** @function
 * Affiche seulement une catégorie de tables en fonction de sa class (css)
 * @export
 * @param {Object} ctx - contexte element html cliqué
 * @param {String} tableClass - catégorie de table à afficher
 */
export function afficheTableFonctionClass(ctx, tableClass) {
  // cache toutes les tables
  sys.effacerElements(['.table-bouton'])

  //affiche les tables de catégories tableClass
  sys.afficherElements(['.' + tableClass + ',flex'])

  // modifier l'activation (active le bouton catégorie table sélectionné)
  // 1 - enlève la class "active" sur tous les enfants des boutons de class "categories-table-item"
  let eles = document.querySelectorAll('.categories-table-item')
  Object.keys(eles).forEach((id) => {
    let ele = eles[id]
    ele.querySelector('i').classList.remove('active')
    ele.querySelector('div').classList.remove('active')
  })
  // 2 - ajoute la class "active" sur les enfants du boutons de categories table cliqué
  ctx.querySelector('i').classList.add('active')
  ctx.querySelector('div').classList.add('active')
}

/** @function
 * Retourne un fragment html des categories de tables
 * @returns {String} - fragment html
 */
function elementsCategoriesTables() {
  // console.log('-> fonction elementsCategoriesTables !')
  let tabCategories = []
  let fragCategories = ''

  // Ajouter la catégorie éphémère au tables éphémères
  Object.keys(glob.tables).forEach((key) => {
    let table = glob.tables[key]
    if (table.ephemere === true) {
      table.categorie = {
        "name": "ephemere",
        "icon": "fa-hourglass"
      }
    }
  })

  let tableTries = sys.trierTableauObjetCroissantFoncAttribut(glob.tables, 'poids')

  // obtenir les catégories de tables
  Object.keys(glob.tables).forEach((key) => {
    const table = glob.tables[key]
    if (table.categorie !== '' && table.categorie !== null) {
      // sys.logJson('table = ', table)
      const test = tabCategories.some((cat) => cat.name === table.categorie.name)
      if (test === false) {
        tabCategories.push(table.categorie)
      }
    }
  })

  // composition de l'affichage des catégories / position des tables
  fragCategories = `<div id="choix-pos-tous" data-rep="all" class="BF-col categories-table-item curseur-action" onclick="restau.afficheTableFonctionClass(this,\'table-bouton\');">
    <i class="categories-table-icon fas fa-th active"></i>
    <div class="categories-table-nom active" data-i8n="all,capitalize">Tous</div>
  </div>`

  Object.keys(tabCategories).forEach((id) => {
    const categorie = tabCategories[id]
    // console.log("nom = " + categorie.name + "  --  icon = " + categorie.icon)
    let nomClass = sys.supAccents(categorie.name).toLowerCase()
    fragCategories += `
      <div class="BF-col categories-table-item curseur-action" onclick="restau.afficheTableFonctionClass(this,\'table-${nomClass}\');">
        <i class="categories-table-icon fas ${categorie.icon}"></i>
        <div class="categories-table-nom">${categorie.name}</div>
      </div>
    `
  })
  tableTries = null
  tabCategories = null
  return fragCategories
}

/**
 * Mémorise la table en cours pour les commandes à venir et reset commentaires
 * @param ${Number} - idTable
 */
export function memoriseTableEncours(typeValeur, idTable, nom) {
  // console.log('-> fonc memoriseTableEncours !')
  glob.tableEnCours = { typeValeur: typeValeur, valeur: idTable, nom: nom }
  glob.commentairesEnCours = ''
}

/** @function
 * Identifier une commande par un nom
 */
export function obtenirNomPourTable() {
  // console.log('-> fonc obtenirNomPourTable !')
  let element = document.querySelector('#entree-nom-table')
  let nomTable = element.value
  // console.log('--> data = ', data, '  --  nom table = ', nomTable)

  let messagesErreurs = ''
  // TODO: peut être s'assurer que ce n'est pas un nombre
  if (nomTable.length < 2) {
    messagesErreurs += '<span data-i8n="minimumLettersTableName,capitalize">Minimum deux lettres pour la table</span>'
  }

  if (messagesErreurs !== '') {
    element.classList.add('erreur-input')
    document.querySelector('#entree-nom-table-msg-erreur').innerHTML = messagesErreurs
  } else {
    fn.popupAnnuler()
    restau.memoriseTableEncours('nomTable', nomTable, nomTable)
    vue_pv.afficherPointDeVentes(pv_uuid_courant)
  }
}

/** @function
 * Identifier une commande par un tagId
 * @param {Object|tagId>} - data = contient la méthode de validation(validerEtape1/validerEtape2) et un tagId
 */
export function obtenirTagIdPourTable(data) {
  // console.log('-> fonc obtenirTagIdPourTable !')
  // sys.logJson('data = ', data)
  restau.memoriseTableEncours('tagId', data.tagId)
  // console.log('pv_uuid_courant = ', pv_uuid_courant, '  --  tagId = ', data.tagId)
  vue_pv.afficherPointDeVentes(pv_uuid_courant)
}

/** @function
 * Configure un popup pour la lecture du tagId:
 * message, option, callback gérant la commande
 */
export function popupLireTagIdNomTableEphemere() {
  rfid.muteEtat('message', `<div data-i8n="awaitingCardReading,capitalize">Attente lecture carte</div>`)
  rfid.muteEtat('data', {})
  rfid.muteEtat('callbackOk', restau.obtenirTagIdPourTable)
  rfid.lireTagId()
}

/**
 * Assigner un nom ou un tagId lors d'un clique sur le bouton "+" de la liste des tables
 */
export function assignerTableEphemere() {
  // Avec clavier virtuel pour raspberry pi
  let placeHolder = 'Entrez un nom de table.'
  const translatePlaceHolder = getTranslate('enterTableName', 'capitalize')
  if (translatePlaceHolder !== '') {
    placeHolder = translatePlaceHolder
  }
  let entreeClavier = `<input id="entree-nom-table" class="input-nom-table" placeholder="${placeHolder}" keyboard-type="alpha" onclick="keyboard.run(this, {keySize: 90})" autofocus style="margin-top:2.5rem;" autofocus>
    <small id="entree-nom-table-msg-erreur" style="margin-bottom:0.5rem;"></small>`

  // Sans clavier virtuel pour les autres fronts
  if (glob.appConfig.front_type !== 'FPI') {
    entreeClavier = `<input id="entree-nom-table" class="input-nom-table" placeholder="${placeHolder}" autofocus>
      <small id="entree-nom-table-msg-erreur" style="margin-bottom:0.5rem;"></small>`
  }

  let titre = `<div class="BF-col">
    <div class="BF-ligne ft-2r" data-i8n="creationEphemeralTable,capitalize" style="white-space: pre-line; text-align: center;">Création d'une table éphémère.</div>
  </div>`

  // compose le bouton retour à afficher
  let boutons = `
    ${entreeClavier}
    <bouton-basique id="test-valider-ephemere" traiter-texte="1" texte="VALIDER|2rem||validate-uppercase" width="400px" height="120px" couleur-fond="#339448" icon="fa-check-circle||2.5rem" onclick="keyboard.hide();restau.obtenirNomPourTable()" style="margin-bottom:2.5rem;"></bouton-basique>     
    <bouton-basique id="test-importer-ephemere" traiter-texte="1" texte="IMPORTER NOM|2rem||importName-uppercase,DEPUIS CARTE|2rem||fromCard-uppercase" width="400px" height="120px" couleur-fond="#339448" icon="fa-tag||2.5rem" onclick="keyboard.hide();fn.popupAnnuler();restau.popupLireTagIdNomTableEphemere()" style="margin-bottom:4.5rem;"></bouton-basique>
    <div class="popup-conteneur-bt-retour BF-col">
      <bouton-basique id="popup-retour" traiter-texte="1" texte="RETOUR|2rem||return-uppercase" couleur-fond="#3b567f" icon="fa-undo-alt||2.5rem" width="400px" height="120px"  onclick="keyboard.hide();fn.popupAnnuler();"></bouton-basique>
    </div>`

  fn.popup({
    titre: titre,
    type: 'normal',
    boutons: boutons
  })
}

/** @function
 * Retourne un fragment html listant les tables
 * @param {String|assignerTable|visualiserCommandes} mode
 * @returns {String} - fragment html
 */
function elementsListeTables(mode) {
  // console.log('-> fonction elementsListeTables !')
  let fragContenu = ''

  let tableNonEphemere = glob.tables.filter(obj => obj.ephemere === false)
  let tableNonEphemereTriee = sys.trierTableauObjetCroissantFoncAttribut(tableNonEphemere, 'poids').concat('separation')
  let tableEphemere = glob.tables.filter(obj => obj.ephemere === true)
  let tableEphemereTriee = sys.trierTableauObjetAlphaNumerique(tableEphemere, 'name')
  tableNonEphemere = []
  tableEphemere = []
  let tableTries = tableNonEphemereTriee.concat(tableEphemereTriee)
  tableNonEphemereTriee = []
  tableEphemereTriee = []
  // console.log('tableTries ', tableTries)

  // état des tables par couleurs
  const etatsCouleur = {
    S: '#ce4d1a', // service en attente (commande prise, mais par servie)
    O: '#FF0000', // en cours de service
    L: '#39e80a', // libre
  }

  // affichage des tables
  Object.keys(tableTries).forEach((id) => {
    const table = tableTries[id]
    if (typeof table !== 'string') {
      // sys.logJson('table = ', table)
      let fonc = '', curseurAction = ''
      if (mode === 'assignerTable') {
        fonc = `onclick="restau.memoriseTableEncours('idTable', ${table.id}, '${table.name}');vue_pv.afficherPointDeVentes('${pv_uuid_courant}')"`
        curseurAction = 'curseur-action'
      }

      if (mode === 'visualiserCommandes') {
        fonc = `onclick="restau.memoriseTableEncours('idTable', ${table.id}, '${table.name}');restau.afficherCommandesTable(${table.id})"`
        curseurAction = 'curseur-action'
      }

      let nomClass = '', iconCategorie = ''
      if (table.categorie) {
        nomClass = 'table-' + sys.supAccents(table.categorie.name).toLowerCase()
        iconCategorie = `<i class="fas ${table.categorie.icon}"></i>`
      }

      fragContenu += `<div class="BF-col-haut table-bouton ${nomClass} ${curseurAction}" data-id-table="${table.id}" ${fonc}>
        <div class="BF-col table-nom">${table.name.toString()}</div>
        <div class="BF-ligne table-etat" style="background-color: ${etatsCouleur[table.statut]}">
          ${iconCategorie}
        </div>
      </div>`
    } else {
      fragContenu += `<div style="width: 100%;"></div>`
    }
  })

  // Bouton 'table' permettant l'ajout d'une commande à la table "éphémère" associée à un nom entré par un input ou lecture  carte nfc
  if (mode === 'assignerTable') {
    fragContenu += `<div class="BF-col-haut table-bouton curseur-action test-table-ephemere" style="background-color: #008000;" onclick="restau.assignerTableEphemere()">
      <div class="BF-col table-nom" style="width:100%;height:100%;">
        <i class="fas fa-plus" style="font-size:2rem;"></i>
      </div>
    </div>`
  }

  tableTries = null
  return fragContenu
}

/** @function
 *  Afficher / Cacher l'addition
 */
export function basculerListeAchatsCommandes() {
  let etatAffichageListeArticles = document.querySelector('#commandes-table-articles').style.display
  // console.log('etat = ', etatAffichageListeArticles)

  // liste artlicles affichées
  if (etatAffichageListeArticles === 'flex') {
    sys.effacerElements(['#commandes-table-articles'])
    sys.afficherElements(['#commandes-table-addition,flex'])
  } else {
    sys.effacerElements(['#commandes-table-addition'])
    sys.afficherElements(['#commandes-table-articles,flex'])
  }

}

/**
 * Retourne le total des articles dèjà payés
 * @returns {number} - total des articles dèjà payés
 */
export function totalDejaPayer() {
  let total = 0
  let elements = document.querySelectorAll(`#addition-liste-deja-paye .BF-ligne-deb`)
  for (let i = 0; i < elements.length; i++) {
    let ele = elements[i]
    let prixHtml = ele.querySelector('.addition-col-prix div').innerHTML
    let prix = parseFloat(prixHtml.substring(0, (prixHtml.length - 1)))
    total += prix
  }
  return total
}

/** @function
 * Emule un clique sur tous les articles à payer
 */
export function ajouterTousArticlesAddition() {
  // console.log('-> fonction ajouterTousArticlesAddition !')
  let cible = document.querySelector('#commandes-table-contenu')
  let totalDejaPayer = restau.totalDejaPayer()
  let elesDom = document.querySelectorAll('.bouton-commande-article')
  if (totalDejaPayer === 0) {
    for (let i = 0; i < elesDom.length; i++) {
      let eleDom = elesDom[i]
      let nbCommande = parseInt(eleDom.getAttribute('nb-commande'))
      for (let j = 0; j < nbCommande; j++) {
        // console.log(i, ' ', j, ' -> nbCommande = ', nbCommande)
        eleDom.click()
      }
    }
  } else { // valeur fractionnée
    let resteAPayer = parseFloat(cible.getAttribute('data-reste-a-payer'))
    let idTable = cible.getAttribute('data-idTable')
    let nomTable = cible.getAttribute('data-nomTable')
    let actionAValider = 'addition_fractionnee'
    let options = {
      url: "paiement",
      actionAValider: actionAValider,
      messageResteAPayer: 0,
      valeurEntree: resteAPayer,
      idTable: idTable,
      nomTable: nomTable
    }
    // les articles sélectionnés
    let achats = vue_pv.obtenirAchats(actionAValider, options)
    options.achats = achats
    vue_pv.validerEtape1(options)
  }
}

/** @function
 * Obtenir la valeur entrée au clavier à soustraire pour l'addition
 */
export function obtenirValeurAdditionFractionnee() {
  // console.log('-> fonction obtenirValeurAdditionFractionnee !')

  let cible = document.querySelector('#commandes-table-contenu')
  let idTable = cible.getAttribute('data-idTable')
  let nomTable = cible.getAttribute('data-nomTable')
  // let mode = cible.getAttribute('data-mode')

  // somme entrée
  let element = document.querySelector('#addition-fractionnee')
  let valeurEntree = parseFloat(element.value)

  // calcul de la somme totale des articles restant à payer
  let sommeTotalRestantAPayer = parseFloat(document.querySelector('#commandes-table-contenu').getAttribute('data-reste-a-payer'))

  let messageResteAPayer = sommeTotalRestantAPayer - valeurEntree

  let messagesErreurs = ''
  // vide le conteneur de messages erreurs
  document.querySelector('#addition-fractionnee-msg-erreur').innerHTML = messagesErreurs
  if (isNaN(valeurEntree)) {
    const msg = getTranslate('mustEnterNumber') === '' ? "Vous devez entrer un nombre !" : getTranslate('mustEnterNumber', 'capitalize')
    messagesErreurs += msg
  }

  if (valeurEntree > sommeTotalRestantAPayer) {
    const msg = getTranslate('valueGreaterThanAddition') === '' ? "Valeur supérieure à l'addition !" : getTranslate('valueGreaterThanAddition', 'capitalize')
    messagesErreurs += msg
  }

  if (valeurEntree <= 0) {
    const msg = getTranslate('valueSmallerOrEqual0') === '' ? "Valeur plus petite ou égale à 0 !" : getTranslate('valueSmallerOrEqual0', 'capitalize')
    messagesErreurs += msg
  }

  if (messagesErreurs !== '') {
    element.classList.add('erreur-input')
    document.querySelector('#addition-fractionnee-msg-erreur').innerHTML = messagesErreurs
  } else {
    fn.popupAnnuler()
    let actionAValider = 'addition_fractionnee'
    let options = {
      url: "paiement",
      actionAValider: actionAValider,
      messageResteAPayer: messageResteAPayer,
      valeurEntree: valeurEntree,
      idTable: idTable,
      nomTable: nomTable
    }
    // les articles sélectionnés
    let achats = vue_pv.obtenirAchats(actionAValider, options)
    options.achats = achats
    vue_pv.validerEtape1(options)

  }
}

/** @function
 * Afficher un popup permettant de rentrer la valeur à soustraire(qui sera payée) pour l'addition
 */
export function demanderValeurAdditionFractionnee() {
  // console.log('-> fonction demanderValeurAdditionFractionnee !')

  let resteAPayer = parseFloat(document.querySelector('#commandes-table-contenu').getAttribute('data-reste-a-payer'))

  if (resteAPayer > 0) {
    // --- compose le message à afficher du poppup ---
    // Avec clavier virtuel pour raspberry pi
    let message = `<input id="addition-fractionnee" class="addition-fractionnee-input keyboard-use" keyboard-type="numpad" onclick="keyboard.run(this,{keySize: 90})">
    <small id="addition-fractionnee-msg-erreur"></small>`

    // Sans clavier virtuel pour les autres fronts
    // console.log('glob.storage = ', glob.storage)
    if (glob.appConfig.front_type !== 'FPI') {
      message = `<input id="addition-fractionnee" class="addition-fractionnee-input">
      <small id="addition-fractionnee-msg-erreur"></small>`
    }

    // compose le bouton retour à afficher
    let boutons = `<bouton-basique traiter-texte="1" texte="VALIDER|1.5rem||validate-uppercase" width="400px" height="120px" couleur-fond="#339448" icon="fa-check-circle||2.5rem" onclick="keyboard.hide();restau.obtenirValeurAdditionFractionnee();" style="margin-top:16px;"></bouton-basique>
    <bouton-basique id="popup-retour" traiter-texte="1" texte="RETOUR|2rem||return-uppercase" couleur-fond="#3b567f" icon="fa-undo-alt||2.5rem" width="400px" height="120px"  onclick="keyboard.hide();fn.popupAnnuler();" style="margin-top:16px;"></bouton-basique>`

    fn.popup({
      titre: '<h1 data-i8n="sum,capitalize">Somme</h1>',
      message: message,
      type: 'normal',
      boutons: boutons
    })
  }
}

/** @function
 * Décrémenter le nombre d'article dans la liste de l'addition
 * @param {String} uuidArticle - uuid article
 */
export function decrementerNbArticleListeAddition(uuidArticle) {
  // console.log('-> fonction decrementerNbArticleListeAddition')
  let eles = document.querySelectorAll(`#addition-vase-communicant .article-commande[data-uuid-article="${uuidArticle}"]`)

  // clone le premier élément
  let clone = eles[0].cloneNode(true)

  // supprimer l'original du clone
  eles[0].parentNode.removeChild(eles[0])

  // obtenir la cible
  let cible = document.querySelector(`#commandes-table-articles .bouton-commande-article[data-uuid-article="${uuidArticle}"]`)
  // console.log('-> uuid = ', cible.getAttribute('data-uuid-article'))

  // insérer le clone dans la cible
  cible.shadowRoot.querySelector(`.ele-conteneur #vase-communicant-article${uuidArticle}`).append(clone)

  // modifier le nombre de l'attribut "nb-commande" de + 1
  let val = parseInt(cible.getAttribute('nb-commande')) + 1
  cible.setAttribute('nb-commande', val)

  // lancer la mise à jour de la liste de l'addition
  majListeAddition()
}


/** @function
 * Mise à jour de la liste de l'addition
 */
export function majListeAddition() {
  // console.log('-> fonction  majListeAddition !')
  let liste = document.querySelector('#addition-liste')
  liste.innerHTML = ''
  // les éléments du vase communicant de l'addition composeront la liste de l'addition
  let eles = document.querySelectorAll('#addition-vase-communicant .article-commande')
  // let totalAddition = 0
  let totalAddition = new Big(0)
  // monnaie
  const monnaie = getTranslate('currencySymbol', null, 'methodCurrency')

  for (let i = 0; i < eles.length; i++) {
    let ele = eles[i]
    let eleUuidArticle = ele.getAttribute('data-uuid-article')
    let eleNomArticle = ele.getAttribute('data-nom')
    let elePrixArticle = ele.getAttribute('data-prix')
    // totalAddition = totalAddition + parseFloat(elePrixArticle)
    totalAddition = totalAddition.plus(parseFloat(elePrixArticle))
    if (document.querySelector(`#addition-article-ligne${eleUuidArticle}`)) {
      // --- article déjà dans la liste ---
      // maj nombre d'article
      let eleAdditionNbArticle = document.querySelector(`#addition-article-ligne-nb${eleUuidArticle}`)
      let val = parseInt(eleAdditionNbArticle.innerHTML)
      eleAdditionNbArticle.innerHTML = val + 1
    } else {
      // 1er article jouté
      let fonction = `restau.decrementerNbArticleListeAddition('${eleUuidArticle}')`
      let frag = `
        <div id="addition-article-ligne${eleUuidArticle}" class="BF-ligne-deb test-addition-article-ligne l100p">
          <div class="addition-col-bt">
            <i class="fas fa-minus-square curseur-action" onclick="${fonction}" title="Enlever un article !"></i>
          </div>
          <div id="addition-article-ligne-nb${eleUuidArticle}" class="addition-col-qte">1</div>
          <div class="addition-col-produit">
            <div>${eleNomArticle}</div>
          </div>
          <div class="addition-col-prix">
            <div>${elePrixArticle}${monnaie}</div>
          </div>
        </div>
      `
      liste.insertAdjacentHTML('beforeend', frag)
    }
  }
  // contenu bouton valider
  document.querySelector('#bt-valider-total-restau').innerHTML = `<span data-i8n="total,uppercase">TOTAL</span>  ${totalAddition} ${getTranslate('currencySymbol', null, 'methodCurrency')}`
  translate('#bt-valider-total-restau')
  document.querySelector('#commandes-table-contenu').setAttribute('data-total-addition-en-cours', totalAddition)
}

/** @function
 * Valider le paiement de l'addition
 */
export function validerPaiementArticleCommande(actionAValider) {
  let cible = document.querySelector('#commandes-table-contenu')
  let idTable = cible.getAttribute('data-idTable')
  let nomTable = cible.getAttribute('data-nomTable')
  // let mode = cible.getAttribute('data-mode')

  let sommeTotalRestantAPayer = parseFloat(document.querySelector('#commandes-table-contenu').getAttribute('data-reste-a-payer'))
  let additionArticleAPayer = parseFloat(document.querySelector('#commandes-table-contenu').getAttribute('data-total-addition-en-cours'))
  let messageResteAPayer = sommeTotalRestantAPayer - additionArticleAPayer


  // les articles sélectionnés
  let achats = vue_pv.obtenirAchats(actionAValider)

  let options = {
    url: "paiement",
    actionAValider: actionAValider,
    achats: achats,
    messageResteAPayer: messageResteAPayer,
    valeurEntree: additionArticleAPayer,
    idTable: idTable,
    nomTable: nomTable
  }

  vue_pv.validerEtape1(options)
}

function totalPrixCommandesTable(commandes, idTable) {
  // console.log('-> fonc totalPrixCommandesTable !')
  let total = new Big(0)
  for (let nbCom = 0; nbCom < commandes.length; nbCom++) {
    let articles = commandes[nbCom].articles
    for (let idArt = 0; idArt < articles.length; idArt++) {
      let dataArticle = articles[idArt]
      let uuidArticle = dataArticle.article.id
      let prix = new Big(dataArticle.article.prix)
      let nbArticle = new Big(dataArticle.qty)
      if (uuidArticle !== glob.uuidArticlePaiementFractionne) {
        total = total.plus(prix.times(nbArticle))
      }
    }
  }
  return sys.bigToFloat(total)
}

/** @function
 * Afficher ce qui est déjà payé dans la(les) commande(s) d'une table
 * @param {Array.<Object>} commandes - tableau d'objets, liste des commandes
 */
function dejaPayeeDansCommandes(commandes) {
  // console.log('-> fonction dejaPayeeDansCommandes !')

  let listFragHtml = '', total = 0
  for (const idcom in commandes) {
    // sys.logJson('commande = ', commandes[idcom])
    let articles = commandes[idcom].articles
    for (const idArt in articles) {
      let article = articles[idArt].article
      let qty, prix = article.prix

      if (article.id === glob.uuidArticlePaiementFractionne) {
        qty = 1
        prix = Math.abs(articles[idArt].qty)
        // console.log('-> ',  article.name, '  --  quantité = ', qty, '  --  prix = ', prix)
        listFragHtml += `
          <div class="BF-ligne-deb l100p pdep">
            <div class="addition-col-bt"></div>
            <div class="addition-col-qte">1</div>
            <div class="addition-col-produit">
              <div>${article.name}</div>
            </div>
            <div class="addition-col-prix">
              <div>${prix}${getTranslate('currencySymbol', null, 'methodCurrency')}</div>
            </div>
          </div>
        `
      }

      if (articles[idArt].reste_a_payer !== articles[idArt].qty && article.id !== glob.uuidArticlePaiementFractionne) {
        qty = articles[idArt].qty - articles[idArt].reste_a_payer
        if (articles[idArt].reste_a_payer === 0) {
          qty = articles[idArt].qty
        }
        // console.log('-> ',  article.name, '  --  quantité = ', qty, '  --  prix = ', prix)
        listFragHtml += `
          <div class="BF-ligne-deb l100p pdep">
            <div class="addition-col-bt"></div>
            <div class="addition-col-qte">${qty}</div>
            <div class="addition-col-produit">
              <div>${article.name}</div>
            </div>
            <div class="addition-col-prix">
              <div>${prix} ${getTranslate('currencySymbol', null, 'methodCurrency')}</div>
            </div>
          </div>
        `

      }
    }
  }
  if (listFragHtml !== '') {
    document.querySelector('#addition-liste-deja-paye').innerHTML = listFragHtml
    translate('#contenu')
    document.querySelector('#addition-liste-deja-paye').classList.add('addition-ldp-bordure-basse', 'fond-ok')
  } else {
    document.querySelector('#addition-liste-deja-paye').innerHTML = ''
  }
}

/** @function
 * @param {Object} data - données initiales
 */
export function resetEtatCommande(data) {
  let etatInit = JSON.parse(unescape(data))
  sys.logJson('etatInit = ', etatInit)
}

/** @function
 *  Incremente un nombre d'article pour offrir ou supprimer
 * @param {Integer} resteAServir - nombre d'article à serveir d'un type d'article
 * @param {String} uuidarticle - uuid de l'article
 * @param {String} uuidCommande - uuid de la commande
 */
export function incrementerArticlePreparation(resteAServir, uuidarticle, uuidCommande) {
  // console.log('-> fonction incrementerArticlePreparation , resteAServir = ', resteAServir, '  --  uuidarticle = ', uuidarticle, '  --  uuidCommande = ', uuidCommande)
  let resteAServirModifier = parseInt(document.querySelector(`#com-article-actions${uuidarticle}-${uuidCommande}`).getAttribute('data-reste-servir-modifier')) + 1
  if (resteAServirModifier > resteAServir) {
    resteAServirModifier = 0
  }
  // console.log('resteAServirModifier = ', resteAServirModifier)
  // actualiser la quantité modifiée (mémorisée)
  document.querySelector(`#com-article-actions${uuidarticle}-${uuidCommande}`).setAttribute('data-reste-servir-modifier', resteAServirModifier)
  // modifier la quantité affiché (soustraction)
  document.querySelector(`#com-article-infos-reste-servir-modifier${uuidarticle}-${uuidCommande}`).innerHTML = resteAServirModifier
}

/** @function
 *  Incremente le nombre d'article à supprimer
 * @param {Number} qty - nombre courant d'articles
 * @param {String} uuidarticle - uuid de l'article
 * @param {String} uuidCommande - uuid de la commande
 */
export function incrementerArticlePourSuppression(qty, uuidarticle, uuidCommande) {
  // console.log('-> fonction incrementerArticlePourSuppression , qty = ', qty, '  --  uuidarticle = ', uuidarticle, '  --  uuidCommande = ', uuidCommande)
  let qtyModifier = parseInt(document.querySelector(`#com-article-actions${uuidarticle}-${uuidCommande}`).getAttribute('data-qty-modifier')) + 1
  if (qtyModifier > qty) {
    qtyModifier = 0
  }
  // console.log('qtyModifier = ', qtyModifier)
  // actualiser la quantité modifiée (mémorisée)
  document.querySelector(`#com-article-actions${uuidarticle}-${uuidCommande}`).setAttribute('data-qty-modifier', qtyModifier)
  // modifier la quantité affiché (soustraction)
  document.querySelector(`#com-article-infos-reste-servir-modifier${uuidarticle}-${uuidCommande}`).innerHTML = qtyModifier
}


/** @function
 * Configurer le nombre d'articles qui sont à supprimer
 * @param {String} uuidCommande - uuid de la commande
 * @param {Number} pkGroupCategories - pk du groupement des catégories
 * @param {String} typeModification - 'reset'
 */
export function configurerNombreArticlesPourSuppression(uuidCommande, pkGroupCategories, typeModification) {
  // console.log('-> fonction modifierArticlesCommande !')
  let elements = document.querySelectorAll(`#com-conteneur${uuidCommande}-${pkGroupCategories} .com-article-actions`)
  for (let i = 0; i < elements.length; i++) {
    let element = elements[i]
    //data-reste-servir-init="${ obj.reste_a_servir }" data-reste-servir-modifier="0"
    let qtyInit = element.getAttribute('data-qty-init')
    // typeModification = total, par défaut
    let quantite = qtyInit
    if (typeModification === "reset") {
      quantite = 0
    }
    // remise à 0 de la quantité modifiée
    element.setAttribute('data-qty-modifier', quantite)

    // maj "visuell soustraction"
    let articleId = element.getAttribute('data-article-id')
    document.querySelector(`#com-article-infos-reste-servir-modifier${articleId}-${uuidCommande}`).innerHTML = quantite
  }
}


/** @function
 * Remise à l'état initiale les quantités des articles d'une commande
 * @param {String} uuidCommande - uuid de la commande
 * @param {Number} pkGroupCategories - pk du groupement des catégories
 * @param {String} typeModification - 'reset'
 */
export function modifierArticlesCommande(uuidCommande, pkGroupCategories, typeModification) {
  // console.log('-> fonction modifierArticlesCommande !')
  let elements = document.querySelectorAll(`#com-conteneur${uuidCommande}-${pkGroupCategories} .com-article-actions`)
  for (let i = 0; i < elements.length; i++) {
    let element = elements[i]
    //data-reste-servir-init="${ obj.reste_a_servir }" data-reste-servir-modifier="0"
    let resteAServirInit = element.getAttribute('data-reste-servir-init')
    // typeModification = total, par défaut
    let quantite = resteAServirInit
    if (typeModification === "reset") {
      quantite = 0
    }
    // remise à 0 de la quantité modifiée
    element.setAttribute('data-reste-servir-modifier', quantite)

    // maj "visuell soustraction"
    let articleId = element.getAttribute('data-article-id')
    document.querySelector(`#com-article-infos-reste-servir-modifier${articleId}-${uuidCommande}`).innerHTML = quantite
  }
}


/** @function
 * Valider la suppression d'un ou de tous les articles d'une commande
 * @param {String} uuidCommande - uuid de la commande
 * @param {Number} pkGroupCategories - pk du groupement des catégories
 */
export function validerSuppressionArtilcesCommande(uuidCommande, pkGroupCategories) {
  // console.log('-> fonction validerSuppressionArtilcesCommande !')
  let articles = []
  let elements = document.querySelectorAll(`#com-conteneur${uuidCommande}-${pkGroupCategories} .com-article-actions`)

  for (let i = 0; i < elements.length; i++) {
    let element = elements[i]
    let qtyInit = parseInt(element.getAttribute('data-qty-init'))
    let articleId = element.getAttribute('data-article-id')
    let qtyModifier = parseInt(element.getAttribute('data-qty-modifier'))

    // console.log(i, ' -> articleId = ', articleId, '  --  qtyInit = ', qtyInit, '  --  qtyModifier = ', qtyModifier)
    let obj = {
      pk: articleId,
      qty: qtyModifier,
      void: true
    }
    if (qtyModifier > 0) {
      articles.push(obj)
    }
  }

  let donnees = {
    pk_responsable: glob.responsable.uuid,
    uuid_commande: uuidCommande,
    articles: articles,
    tag_id_cm: glob.tagIdCm
  }

  if (donnees.articles.length === 0) {
    // pas darticles sélectionnés
    vue_pv.afficherMessageArticlesNonSelectionnes()
  } else {
    // sys.logJson('donnees = ', donnees)
    // validation
    let csrfToken = document.querySelector('input[name="csrfmiddlewaretoken"]').value
    let requete = {
      type: "post",
      url: "preparation",
      dataType: 'json',
      dataTypeReturn: 'json',
      csrfToken: csrfToken,
      // attente = paramètres pour l'icon de chargement
      attente: { largeur: 80, couleur: '#0F0', nbc: 8, rpt: 4, epaisseur: 8 },
      data: donnees
    }
    // sys.logJson('requete = ', requete)
    sys.ajax(requete, function (retour, status) {
      restau.ajouterOpacite(`com-conteneur${uuidCommande}-${pkGroupCategories}`)
      // sys.logJson('status = ', status)
      // sys.logJson('retour = ', retour)
      if (status.code === 200) {
        // filtre décimal to float
        for (const retourKey in retour) {
          const commandes = retour[retourKey].commandes
          for (const commandesKey in commandes) {
            const commande = commandes[commandesKey]
            commande.reste_a_payer = sys.bigToFloat(commande.reste_a_payer)
            const articles = commande.articles
            for (const articlesKey in articles) {
              const article = articles[articlesKey]
              article.qty = sys.bigToFloat(article.qty)
              article.reste_a_payer = sys.bigToFloat(article.reste_a_payer)
              article.reste_a_servir = sys.bigToFloat(article.reste_a_servir)
              article.article.prix = sys.bigToFloat(article.article.prix)
            }
          }
        }
        visualiserEtatCommandes(retour)
      } else {
        vue_pv.afficher_message_erreur_requete(retour, status)
      }
    })
  }
}

/** @function
 * Valide une(des) suppression(s) ou un(des) cadeau(x) ou une préparation, le tout total ou partiel
 * @param {String} typeAction - valider ou supprimer
 * @param {String} mode - edition ou normal
 * @param {String} uuidCommande - uuid de la commande
 * @param {Number} pkGroupCategories - pk du groupement des catégories
 */
export function actionSurCommande(typeAction, mode, uuidCommande, pkGroupCategories) {
  // console.log('-> fonction actionSurCommande, typeAction = ', typeAction, '  --  mode = ', mode, '  --  pkGroupCategories = ', pkGroupCategories)
  let articles = [], elements

  if (mode === "normal") {
    elements = document.querySelectorAll(`#com-conteneur${uuidCommande}-${pkGroupCategories} .com-article-infos`)
  } else {
    elements = document.querySelectorAll(`#com-conteneur${uuidCommande}-${pkGroupCategories} .com-article-actions`)
  }

  for (let i = 0; i < elements.length; i++) {
    let element = elements[i]
    let qtyResteAServirInit = parseInt(element.getAttribute('data-reste-servir-init'))
    let articleId = element.getAttribute('data-article-id')
    let qtyResteAServirModifier
    if (mode !== "normal") {
      qtyResteAServirModifier = parseInt(element.getAttribute('data-reste-servir-modifier'))
    }
    // console.log(i,' -> articleId = ', articleId, '  --  qtyResteAServirInit = ',qtyResteAServirInit, '  --  qtyResteAServirModifier = ', qtyResteAServirModifier)
    let obj = {}
    if (typeAction === 'valider' && mode === 'normal') {
      obj = {
        pk: articleId,
        qty: qtyResteAServirInit
      }
      articles.push(obj)
    } else {
      obj = {
        pk: articleId,
        qty: qtyResteAServirModifier
      }
      if (typeAction === "supprimer") {
        obj.void = true
      }

      if (qtyResteAServirModifier > 0) {
        articles.push(obj)
      }
    }
  }
  let donnees = {
    pk_responsable: glob.responsable.uuid,
    uuid_commande: uuidCommande,
    articles: articles,
    tag_id_cm: glob.tagIdCm
  }


  if (donnees.articles.length === 0) {
    // pas darticles sélectionnés
    vue_pv.afficherMessageArticlesNonSelectionnes()
  } else {
    // validation
    let csrfToken = document.querySelector('input[name="csrfmiddlewaretoken"]').value
    let requete = {
      type: "post",
      url: "preparation",
      dataType: 'json',
      dataTypeReturn: 'json',
      csrfToken: csrfToken,
      // attente = paramètres pour l'icon de chargement
      attente: { largeur: 80, couleur: '#0F0', nbc: 8, rpt: 4, epaisseur: 8 },
      data: donnees
    }
    // console.log(`-> actionSurCommande, ${  new Date().toLocaleTimeString() } -> requête "preparation" lancée !`)
    // sys.logJson('requete = ', requete)
    sys.ajax(requete, function (retour, status) {
      // sys.logJson('status = ', status)
      // sys.logJson('retour = ', retour)
      if (status.code === 200) {

        // filtre décimal to float
        for (const retourKey in retour) {
          const commandes = retour[retourKey].commandes
          for (const commandesKey in commandes) {
            const commande = commandes[commandesKey]
            commande.reste_a_payer = sys.bigToFloat(commande.reste_a_payer)
            const articles = commande.articles
            for (const articlesKey in articles) {
              const article = articles[articlesKey]
              article.qty = sys.bigToFloat(article.qty)
              article.reste_a_payer = sys.bigToFloat(article.reste_a_payer)
              article.reste_a_servir = sys.bigToFloat(article.reste_a_servir)
              article.article.prix = sys.bigToFloat(article.article.prix)
            }
          }
        }

        // réseau ok, réinit. attenteLancerVerifierEtatCommandes.interval avec valeur d'origine(intervalActualisationVuePreparations)
        attenteLancerVerifierEtatCommandes.interval = intervalActualisationVuePreparations
        attenteLancerVerifierEtatCommandes.etat = 1
        window.clearTimeout(attenteLancerVerifierEtatCommandes.rep)
        visualiserEtatCommandes(retour)
      } else {
        vue_pv.afficher_message_erreur_requete(retour, status)
      }
    })

  }
}

/** @function
 * Lancer l'impression d'une commande
 * @param ${String} uuidCommande - uuid de la commande
 * @param ${Number} pkGroupementCategories - numero de regroupement de catégories
 */
export function imprimerTicket(uuidCommande, pkGroupementCategories) {
  console.log('-> fonction imprimerTicket !')
  let csrfToken = document.querySelector('input[name="csrfmiddlewaretoken"]').value
  let requete = {
    type: "post",
    url: "reprint",
    dataType: 'json',
    dataTypeReturn: 'json',
    csrfToken: csrfToken,
    attente: {},
    data: {
      uuid_commande: uuidCommande,
      pk_groupement_categories: pkGroupementCategories
    }
  }
  // sys.logJson('requete = ', requete)
  // TODO: afficher le nom du groupement et le numero de commande
  sys.ajax(requete, function (retour, status) {
    sys.logJson('status = ', status)
    sys.logJson('retour = ', retour)
    if (status.code === 200) {
      let bouton = `<bouton-basique id="popup-retour" traiter-texte="1" texte="RETOUR|1.5rem||return-uppercase" couleur-fond="#3b567f" icon="fa-undo-alt||2.5rem" width="400px" height="120px"  onclick="fn.popupAnnuler();" style="margin-top:16px;"></bouton-basique>`
      let options = {
        message: `<h1 data-i8n="printOk,capitalize">Impression ok !</h1>`,
        boutons: bouton,
        type: 'normal'
      }
      fn.popup(options)
    } else {
      vue_pv.afficher_message_erreur_requete(retour, status)
    }
  })
}


export function enleverOpacite(idElementDom) {
  document.querySelector(`#${idElementDom}`).classList.remove('com-contenur-inactif')
}

export function ajouterOpacite(idElementDom) {
  document.querySelector(`#${idElementDom}`).classList.add('com-contenur-inactif')
}


/** @function
 * Visualise les commandes pour la préparation
 * @param {Object <ajax>} retour - données, commandes de la table
 */
export function visualiserEtatCommandes(retour) {
  console.log('-> fonction visualiserEtatCommandes !')
  // sys.logJson('retour =',retour)

  // TODO: à vérifier avant lancement prod
  // attention, dev = true; stop actu prépa !!! / prod = false
  window.testPagePrepa = true

  // local
  const local = getLanguages().find(item => item.language === localStorage.getItem("language")).locale

  // info (html title)
  const printTicket = getTranslate('printTicket') === '' ? "Imprimer ticket." : getTranslate('printTicket', 'capitalize')

  // console.log('window.lanceVerificationEtatCommandesAffiche = ', window.lanceVerificationEtatCommandesAffiche)
  // statut tables/commandes
  const transO = getTranslate('notServedUnpaidOrder') === '' ? "Non servie - Non payée" : getTranslate('notServedUnpaidOrder', 'capitalize')
  const transS = getTranslate('servedUnpaidOrder') === '' ? "Servie - Non payée" : getTranslate('servedUnpaidOrder', 'capitalize')
  const transP = getTranslate('notServedPaidOrder') === '' ? "Non Servie - Payée" : getTranslate('notServedPaidOrder', 'capitalize')
  const transSP = getTranslate('servedPaidOrder') === '' ? "Servie et Payée" : getTranslate('servedPaidOrder', 'capitalize')
  const transCA = getTranslate('cancelledOrder') === '' ? "Annulée" : getTranslate('cancelledOrder', 'capitalize')
  let statutLisible = { "O": transO, "S": transS, "P": transP, "SP": transSP, "CA": transCA }

  // obtenir données d'affichages des commandes dans le dom
  let elementCible = document.querySelector('#service-commandes') // où insérer les éléments html
  let idTable = parseInt(elementCible.getAttribute('data-table-id'))
  let groupementCategories = parseInt(elementCible.getAttribute('data-groupement-categories'))
  // console.log('  --  idTable = ', idTable, '  --  groupementCategories = ', groupementCategories)

  // largeur écran
  let largeurEcran = document.querySelector('body').clientWidth

  // initialisation vue table
  sys.effacerElements(['#page-commandes', '#tables', '#commandes-table'])
  sys.afficherElements(['#service-commandes,block'])

  let data = []
  // service du côté des serveurs, sur une table donnée et tous les groupements de catégories (pk)
  if (groupementCategories === 0) {
    // console.log('--> Affiche tous les groupement -- ', groupementCategories)
    for (let i = 0; i < retour.length; i++) {
      let groupement = retour[i]
      console.log('groupement =', groupement)
      let commandes = groupement.commandes
      let commandesFiltrees = commandes.filter(obj => obj.table === idTable)
      let nouvelObjet = {
        pk: groupement.pk,
        name: groupement.name,
        icon: groupement.icon,
        commandes: commandesFiltrees
      }
      data.push(nouvelObjet)
    }
  }

  if (groupementCategories !== 0) {
    data = retour.filter(obj => obj.pk === groupementCategories)
  }

  // recupe mémoire
  retour = []

  let fragmentHtml = ''

  // les groupements non servis
  for (let idGroupement = 0; idGroupement < data.length; idGroupement++) {
    let groupement = data[idGroupement]
    // sys.logJson('groupement =',groupement)
    // trie par date (les plus anciennes aux plus récentes)
    groupement.commandes.sort((a, b) => ((new Date(a.datetime)).getTime()) - ((new Date(b.datetime)).getTime()))

    // sys.logJson('groupement = ', groupement)
    // console.log('----------------------------------------------------------------------------')

    // les commandes
    for (let idCommande = 0; idCommande < groupement.commandes.length; idCommande++) {
      let commande = groupement.commandes[idCommande]
      let uuidCommande = commande.uuid

      // si aucun article à servir, n'affiche pas la commande
      let maxNbArticleAServir = 0
      for (let idArticle = 0; idArticle < commande.articles.length; idArticle++) {
        maxNbArticleAServir += commande.articles[idArticle].reste_a_servir
      }

      if (maxNbArticleAServir > 0) {
        // ------------ entête ------------
        let dateStringTmp = new Date(commande.datetime)
        const baseTmp = commande.datetime.split('T')[1].split(':')
        const heureCommande = baseTmp[0] + ':' + baseTmp[1]
        let dateJour = dateStringTmp.toLocaleDateString()
        let dateDuJour = (new Date()).toLocaleDateString()
        let styleCouleurAlerteDate = '', couleurIconTable = ''
        if (dateJour !== dateDuJour) {
          styleCouleurAlerteDate = `style="color:#FF0000;"`
          couleurIconTable = 'coul-rouge'
        }
        fragmentHtml += `
          <div id="com-conteneur${uuidCommande}-${groupement.pk}" class="com-conteneur BF-col" data-table-uuid-command="${uuidCommande}" data-table-id="${commande.table}" data-groupement-categories="${groupementCategories}">
            <!-- entête -->
            <div class="com-titre-conteneur BF-ligne-deb coulBlanc l100p" ${styleCouleurAlerteDate}>
              <div class="com-titre-icon BF-ligne">
                <i class="fas ${groupement.icon}"></i>
              </div>
              <div class="com-titre-heure BF-ligne">
                <div class="test-ref-time-value">${heureCommande}</div>
              </div> <!-- fin: .com-titre-heure -->
        `
        // signale jour différent
        if (dateJour !== dateDuJour) {
          fragmentHtml += `
              <div class="com-titre-date BF-ligne">
                ${dateJour}
              </div>
          `
        } else {
          fragmentHtml += `<div class="com-titre-date BF-ligne"></div>`
        }
        // largeur écran supérieure ou égale à 800 pixels
        if (largeurEcran >= 800) {
          fragmentHtml += `            
              <div class="com-titre-partie-centre BF-ligne">
          `
          // si reception info numéro de ticket imprimé
          // affichage numéro de commande avec nom du groupmement de catégorie, exemple: "Bar 9"
          if (Object.entries(commande.numero_du_ticket_imprime).length !== 0) {
            for (const [pos, nombre] of Object.entries(commande.numero_du_ticket_imprime)) {
              fragmentHtml += `
                  <i class="fas fa-receipt md4px"></i>
                  <div class="md16px test-ref-location">${pos} ${nombre}</div>
              `
            }
          }
          fragmentHtml += `
                <img class="icon-table-ronde-svg md4px" alt="table" src="../static/webview/images/table_ronde0.svg" />
                <div class="test-ref-table-name">${commande.table_name}</div>
              </div> <!-- fin: com-titre-partie-centre -->
              <div class="com-titre-partie-droite BF-ligne">
                <span class="md16px test-ref-preparation-place">${groupement.name}</span>
                <div class="mg4px test-ref-status-order">${statutLisible[commande.statut]}</div>
          `
          // impression si ticket et mode gérant activé
          if (Object.entries(commande.numero_du_ticket_imprime).length !== 0 && glob.modeGerant === true) {
            fragmentHtml += `
              <div class="com-bt-imprimer mg4px" onclick="restau.imprimerTicket('${uuidCommande}', ${groupement.pk})" title="${printTicket}">
                <i class="fas fa-print"></i>
              </div>
            `
          }
          fragmentHtml += `
              </div> <!-- fin: com-titre-partie-droite -->
          `
        } else {
          // largeur écran inférieure à 800 pixels
          fragmentHtml += `
              <div class="com-titre-partie-centre BF-ligne"></div>
              <div class="com-titre-partie-droite">
              <span class="md16px test-ref-preparation-place">${groupement.name}</span>
          `
          // affichage numéro de commande avec nom du groupmement de catégorie, exemple: "Bar 9"
          if (Object.entries(commande.numero_du_ticket_imprime).length !== 0) {
            for (const [pos, nombre] of Object.entries(commande.numero_du_ticket_imprime)) {
              fragmentHtml += `
                  <i class="fas fa-receipt md4px"></i>
                  <div class="md16px test-ref-location">${pos} ${nombre}</div>
              `
            }
          }
          // impression si ticket et mode gérant activé
          if (Object.entries(commande.numero_du_ticket_imprime).length !== 0 && glob.modeGerant === true) {
            fragmentHtml += `
              <div class="com-bt-imprimer mg4px" onclick="restau.imprimerTicket('${uuidCommande}', ${groupement.pk})" title="${printTicket}">
                <i class="fas fa-print"></i>
              </div>
            `
          }
          fragmentHtml += `
              </div> <!-- fin: com-titre-partie-droite -->
          `
        }
        fragmentHtml += `
            </div> <!-- fin: com-titre-conteneur -->
        `
        // largeur écran inférieure à 800 pixels
        if (largeurEcran < 800) {
          // console.log('largeurEcran < 800; commande =', commande)
          fragmentHtml += `
            <div class="com-titre-conteneur-plus coulBlanc l100p" ${styleCouleurAlerteDate}>
              <div class="BF-ligne">
                <img class="icon-table-ronde-svg md4px ${couleurIconTable}" alt="table" src="../static/webview/images/table_ronde0.svg" />
                <div class="test-moins800-nom test-ref-table-name">${commande.table_name}</div>
                <div class="mg4px test-moins800-etat test-ref-status-order">${statutLisible[commande.statut]}</div>
          `
          if (glob.modeGerant === true) {
            fragmentHtml += `
                <div class="mg8px">id:${uuidCommande.substr(0, 3)}</div>
            `
          }
          fragmentHtml += `
              </div>
            </div>
          `
        }

        // ------------ affichages des articles ------------
        // mode non gerant
        if (glob.modeGerant === false) {
          fragmentHtml += `
            <div class="com-articles-valider-conteneur BF-ligne l100p">
              <div class="com-articles-conteneur">
          `
        } else {
          // mode gérant
          fragmentHtml += `
            <div class="BF-col l100p mb4px"> <!-- div contenant les articles en mode gérant -->
          `
        }
        let maxNbArticle = 0
        for (let idArticle = 0; idArticle < commande.articles.length; idArticle++) {
          let objArticle = commande.articles[idArticle]
          // sys.logJson('objArticle = ', objArticle)
          // console.log('----------------------')
          maxNbArticle = objArticle.reste_a_servir
          // mode non gerant
          if (glob.modeGerant === false) {
            fragmentHtml += `
                <div class="com-article-infos BF-ligne-deb" data-reste-servir-init="${objArticle.reste_a_servir}" data-article-id="${objArticle.article.id}">
                  <div class="md16px test-return-rest-serve-qty">${objArticle.reste_a_servir}</div>
                  <div class="md16px test-return-rest-serve-name">${objArticle.article.name}</div>
                </div>
            `
          } else {
            // mode gerant
            fragmentHtml += `
              <div class="com-article-ligne BF-ligne-deb">
                <div id="com-article-actions${objArticle.article.id}-${uuidCommande}" class="com-article-actions" data-article-id="${objArticle.article.id}" data-reste-servir-init="${objArticle.reste_a_servir}" data-reste-servir-modifier="0" onclick="restau.incrementerArticlePreparation(${objArticle.reste_a_servir}, '${objArticle.article.id}', '${uuidCommande}')">
                  <div class="com-bt com-ident1">
                    <i class="fas fa-plus test-return-icon-plus"></i>
                  </div>
                </div>
                <div class="com-article-infos BF-ligne-deb">
                  <div id="com-article-infos-reste-servir-modifier${objArticle.article.id}-${uuidCommande}" class="md4px test-return-reste-servir-modifier">0</div>
                  <div class="md16px">sur <span class="test-return-rest-serve-qty">${objArticle.reste_a_servir}</span></div>
                  <div class="md16px test-return-rest-serve-name">${objArticle.article.name}</div>
                </div>
              </div> <!-- fin com-block1-article-conteneur -->
            `
          }
        }
        // mode non gerant
        if (glob.modeGerant === false) {
          // bouton valider préparation (tous les articles)
          const titleValidatePreparation = getTranslate('validatePreparation') === '' ? "Valider préparation." : getTranslate('validatePreparation', 'capitalize')
          fragmentHtml += `
              </div> <!-- fin: com-articles-conteneur -->
               <div class="com-articles-valider BF-col">
                <div class="com-bt-valider-normal BF-col fond-ok test-action-validate-prepa" title="${titleValidatePreparation}" onclick="restau.actionSurCommande('valider', 'normal', '${uuidCommande}', ${groupement.pk})">
                  <i class="fas fa-check"></i>
                </div>
               </div>
            </div> <!-- fin: com-articles-valider-conteneur -->
          `
        } else {
          // mode gérant
          fragmentHtml += `
               <div class="com-article-ligne BF-ligne-deb">
          `
          if (commande.articles.length > 1 || maxNbArticle > 1) {
            fragmentHtml += `
              <div class="com-bt com-ident1 md8px" onclick="restau.modifierArticlesCommande('${uuidCommande}',  ${groupement.pk}, 'total')">
                <i class="fas fa-th mg4px test-return-icon-grid"></i>
              </div>
            `
          }
          fragmentHtml += `
                <div class="com-bt com-ident3 test-return-action-reset" onclick="restau.modifierArticlesCommande('${uuidCommande}', ${groupement.pk}, 'reset')" data-i8n="reset,uppercase">RESET</div>
               </div>
            </div> <!-- fin: div contenant les articles en mode gérant -->
            <div class="com-article-footer BF-ligne-deb">
              <div class="BF-ligne com-ident-supp fond-retour test-action-delete-article" onclick="restau.actionSurCommande('supprimer', 'edition', '${uuidCommande}', ${groupement.pk})" data-i8n="deleteArticles,uppercase">SUPPRIMER ARTICLE(S)</div>
              <div class="BF-ligne com-ident-val fond-ok test-action-validate-article" onclick="restau.actionSurCommande('valider', 'edition', '${uuidCommande}', ${groupement.pk})" data-i8n="validatePreparation,uppercase">VALIDER PREPARATION</div>
            </div>  
          `
        }
        fragmentHtml += `</div> <!-- fin: .com-conteneurs -->`
      }
    }
  }


  // -----------------------------------------
  // --- les groupements servis ou annulés ---
  // -----------------------------------------
  for (let idGroupement = 0; idGroupement < data.length; idGroupement++) {
    let groupement = data[idGroupement]

    // les commandes
    for (let idCommande = 0; idCommande < groupement.commandes.length; idCommande++) {
      let commande = groupement.commandes[idCommande]
      let uuidCommande = commande.uuid
      let dateStringTmp = new Date(commande.datetime)
      let dateJour = dateStringTmp.toLocaleDateString()
      let dateDuJour = (new Date()).toLocaleDateString()
      let heureLocaleTab = dateStringTmp.toLocaleTimeString(local, { hour12: false }).split(':')
      const heureCommande = heureLocaleTab[0] + ':' + heureLocaleTab[1]

      // si aucun article à servir, n'affiche pas la commande
      let maxNbArticleAServir = 0
      for (let idArticle = 0; idArticle < commande.articles.length; idArticle++) {
        maxNbArticleAServir += commande.articles[idArticle].reste_a_servir
      }

      if (commande.statut === 'S' || commande.statut === 'SP' || commande.statut === 'CA' || (commande.statut === 'O' && maxNbArticleAServir === 0)) {
        // ------------ entête ------------
        let foncOpacite = ''
        if (glob.modeGerant === true) {
          foncOpacite = `onclick="restau.enleverOpacite('com-conteneur${uuidCommande}-${groupement.pk}')"`
        }
        let styleCouleurAlerteDate = ''
        if (dateJour !== dateDuJour) {
          styleCouleurAlerteDate = `style="color:#FF0000;"`
        }
        fragmentHtml += `
          <div id="com-conteneur${uuidCommande}-${groupement.pk}" class="com-conteneur com-contenur-inactif BF-col" data-table-uuid-command="${uuidCommande}" data-table-id="${commande.table}" data-groupement-categories="${groupementCategories}"  ${foncOpacite}>
            <!-- entête -->
            <div class="com-titre-conteneur BF-ligne-deb coulBlanc l100p" ${styleCouleurAlerteDate}>
              <div class="com-titre-icon BF-ligne">
                <i class="fas ${groupement.icon}"></i>
              </div>
              <div class="com-titre-heure test-ref-time-value">${heureCommande}</div>
        `
        // signale jour différent
        if (dateJour !== dateDuJour) {
          fragmentHtml += `
              <div class="com-titre-date BF-ligne">
                ${dateJour}
              </div>
          `
        } else {
          fragmentHtml += `
              <div class="com-titre-date BF-ligne"></div>
          `
        }

        // largeur écran supérieure ou égale à 800 pixels
        if (largeurEcran >= 800) {
          fragmentHtml += `
              <div class="com-titre-partie-centre BF-ligne">
          `
          // si reception info numéro de ticket imprimé
          // affichage numéro de commande avec nom du groupmement de catégorie, exemple: "Bar 9"
          if (Object.entries(commande.numero_du_ticket_imprime).length !== 0) {
            for (const [pos, nombre] of Object.entries(commande.numero_du_ticket_imprime)) {
              fragmentHtml += `
                <i class="fas fa-receipt md4px"></i>
                <div class="md16px test-ref-location">${pos} ${nombre}</div>
              `
            }
          }
          fragmentHtml += `
                <img class="icon-table-ronde-svg md4px" alt="table" src="../static/webview/images/table_ronde0.svg" />
                <div class="test-ref-table-name">${commande.table_name}</div>
              </div> <!-- fin: com-titre-partie-centre -->
              <div id="statu-commande${uuidCommande}-${groupement.pk}" class="com-titre-partie-droite  BF-ligne">
                <div class="mg4px test-ref-status-order">${statutLisible[commande.statut]}</div>
          `
          // impression si ticket et mode gérant activé
          if (Object.entries(commande.numero_du_ticket_imprime).length !== 0 && glob.modeGerant === true) {
            fragmentHtml += `
              <div class="com-bt-imprimer mg4px" onclick="restau.imprimerTicket('${uuidCommande}', ${groupement.pk})" title="${printTicket}">
                <i class="fas fa-print"></i>
              </div>
            `
          }

          fragmentHtml += `
                <span class="md16px test-ref-preparation-place">${groupement.name}</span>
              </div> <!-- fin: com-titre-partie-droite -->
          `
        } else {
          // largeur écran inférieure à 800 pixels
          fragmentHtml += `
              <div class="com-titre-partie-droite BF-ligne" style="width:calc(100% - 102px);justify-content: flex-end;">
                <span class="md16px test-ref-preparation-place">${groupement.name}</span>
          `
          // affichage numéro de commande avec nom du groupmement de catégorie, exemple: "Bar 9"
          if (Object.entries(commande.numero_du_ticket_imprime).length !== 0) {
            for (const [pos, nombre] of Object.entries(commande.numero_du_ticket_imprime)) {
              fragmentHtml += `
                  <i class="fas fa-receipt md4px"></i>
                  <div class="md16px test-ref-location">${pos} ${nombre}</div>
              `
            }
          }

          // impression si ticket et mode gérant activé
          if (Object.entries(commande.numero_du_ticket_imprime).length !== 0 && glob.modeGerant === true) {
            fragmentHtml += `
              <div class="com-bt-imprimer mg4px" onclick="restau.imprimerTicket('${uuidCommande}', ${groupement.pk})" title="${printTicket}">
                <i class="fas fa-print"></i>
              </div>
            `
          }

          fragmentHtml += `
              </div> <!-- fin: com-titre-partie-droite -->
          `
        }

        fragmentHtml += `
            </div> <!-- fin: com-titre-conteneur -->
        `

        // largeur écran inférieure à 800 pixels
        if (largeurEcran < 800) {
          fragmentHtml += `
            <div class="com-titre-conteneur-plus BF-ligne-deb coulBlanc l100p">
              <div class="BF-ligne">
                <img class="icon-table-ronde-svg md4px" alt="table" src="../static/webview/images/table_ronde0.svg" style="color:#FFF;"/>
                <div class="test-ref-table-name">${commande.table_name}</div>
                <div class="mg4px test-moins800-etat test-ref-status-order">${statutLisible[commande.statut]}</div>
          `
          if (glob.modeGerant === true) {
            fragmentHtml += `
                <div class="mg8px">id:${uuidCommande.substr(0, 3)}</div>
            `
          }

          fragmentHtml += `
              </div>
            </div>
            <!-- fin: entête -->
          `
        }

        // ------------ affichages des articles ------------
        // mode non gérant
        if (glob.modeGerant === false) {
          fragmentHtml += `
            <div class="com-articles-valider-conteneur BF-ligne l100p">
              <div class="com-articles-conteneur">
          `
          for (let idArticle = 0; idArticle < commande.articles.length; idArticle++) {
            let objArticle = commande.articles[idArticle]
            fragmentHtml += `
                <div class="com-article-infos BF-ligne-deb" data-reste-servir-init="${objArticle.reste_a_servir}" data-article-id="${objArticle.article.id}">
                  <div class="md16px test-return-rest-serve-qty">${objArticle.qty}</div>
                  <div class="md16px test-return-rest-serve-name">${objArticle.article.name}</div>
                </div>
            `
          }
          fragmentHtml += `
              </div> <!-- fin: .com-articles-conteneur -->
              <div class="com-articles-valider BF-col"></div>
            </div>
          `
        } else {
          // mode gérant
          fragmentHtml += `
            <div class="BF-col l100p mb4px"> <!-- div contenant les articles en mode gérant -->
          `
          // articles
          for (let idArticle = 0; idArticle < commande.articles.length; idArticle++) {
            let objArticle = commande.articles[idArticle]
            // sys.logJson('objArticle = ', objArticle)
            // console.log('----------------------')
            fragmentHtml += `
              <div class="com-article-ligne BF-ligne-deb">
                <div id="com-article-actions${objArticle.article.id}-${uuidCommande}" class="com-article-actions" data-article-id="${objArticle.article.id}" data-qty-init="${objArticle.qty}" data-qty-modifier="0" onclick="restau.incrementerArticlePourSuppression(${objArticle.qty}, '${objArticle.article.id}', '${uuidCommande}')">
                  <div class="com-bt com-ident1">
                    <i class="fas fa-plus test-return-icon-plus"></i>
                  </div>
                </div>
                <div class="com-article-infos BF-ligne-deb">
                  <div id="com-article-infos-reste-servir-modifier${objArticle.article.id}-${uuidCommande}" class="md4px test-return-reste-servir-modifier">0</div>
                  <div class="md16px">sur <span class="test-return-rest-serve-qty">${objArticle.qty}</span></div>
                  <div class="md16px test-return-rest-serve-name">${objArticle.article.name}</div>
                </div>
              </div> <!-- fin com-block1-article-conteneur -->
            `
          }
          fragmentHtml += `
              <div class="com-article-ligne BF-ligne-deb">
            `
          if (commande.articles.length > 1) {
            fragmentHtml += `
                <div class="com-bt com-ident1 md8px" onclick="restau.configurerNombreArticlesPourSuppression('${uuidCommande}',  ${groupement.pk}, 'total')">
                  <i class="fas fa-th mg4px test-return-icon-grid"></i>
                </div>
              `
          }
          fragmentHtml += `
                <div class="com-bt com-ident3 test-return-action-reset" onclick="restau.configurerNombreArticlesPourSuppression('${uuidCommande}', ${groupement.pk}, 'reset')" data-i8n="reset,uppercase">RESET</div>
              </div>
              <div class="com-article-footer BF-ligne fond-retour" onclick="restau.validerSuppressionArtilcesCommande('${uuidCommande}', ${groupement.pk})">
                <div class="BF-ligne com-ident-supp test-action-delete-article" data-i8n="deleteArticles,uppercase">SUPPRIMER ARTICLE(S)</div>
              </div>  
            </div>
          `
        }
        fragmentHtml += `      
          </div> <!-- fin: .com-conteneurs -->
        `
      }
    }
  }

  // insert le fragment html
  document.querySelector('#service-commandes').innerHTML = fragmentHtml
  translate('#service-commandes')

  // if (glob.modeGerant === false && glob.testPagePrepa === false) {
  if (glob.modeGerant === false && window.testPagePrepa === false) {
    // console.log('attenteLancerVerifierEtatCommandes = ', attenteLancerVerifierEtatCommandes)
    if (attenteLancerVerifierEtatCommandes.etat === 1) {
      // console.log('-> lancer attente !')
      attenteLancerVerifierEtatCommandes.etat = 2
      attenteLancerVerifierEtatCommandes.rep = window.setTimeout(() => {
        attenteLancerVerifierEtatCommandes.etat = 1
        window.clearTimeout(attenteLancerVerifierEtatCommandes.rep)
        let etatVuePreparations = document.querySelector('#service-commandes').style.display
        // si au bout du temps demmandé encore sur la vue préparation relancer la requête
        if (etatVuePreparations !== 'none') {
          let idTable = parseInt(elementCible.getAttribute('data-table-id'))
          let groupementCategories = parseInt(elementCible.getAttribute('data-groupement-categories'))
          let provenance = elementCible.getAttribute('data-provenance')
          serviceAfficherCommandesTable(groupementCategories, idTable, provenance)
        }
      }, attenteLancerVerifierEtatCommandes.interval)

    }
  }
}

function relancePreparationApresDefaut() {
  // relance requête
  if (attenteLancerVerifierEtatCommandes.etat === 1) {
    attenteLancerVerifierEtatCommandes.etat = 2
    attenteLancerVerifierEtatCommandes.interval = attenteLancerVerifierEtatCommandes.interval + 5000
    // console.log('-> relancer fonction serviceAfficherCommandesTable dans ', attenteLancerVerifierEtatCommandes.interval)
    attenteLancerVerifierEtatCommandes.rep = window.setTimeout(() => {
      attenteLancerVerifierEtatCommandes.etat = 0
      let etatVuePreparations = document.querySelector('#service-commandes').style.display
      // si au bout du temps demmandé encore, ou sur la vue préparation relancer la requête
      if (etatVuePreparations !== 'none') {
        let elementCible = document.querySelector('#service-commandes')
        let idTable = parseInt(elementCible.getAttribute('data-table-id'))
        let groupementCategories = parseInt(elementCible.getAttribute('data-groupement-categories'))
        let provenance = elementCible.getAttribute('data-provenance')
        serviceAfficherCommandesTable(groupementCategories, idTable, provenance)
      }
    }, attenteLancerVerifierEtatCommandes.interval)
  }
}

/** @function
 * Pour la préparation
 * @param {Number} groupementCategories - example: 0 = tous, 1 = bar, 2 = restaurant
 * @param {Number} idTable - id de la table
 * @param {String} provenance - indique d'où vient la demande undefined = préparation / articles_table = articles/commande d'une table
 */
export function serviceAfficherCommandesTable(groupementCategories, idTable, provenance) {
  // console.log('-> fonc serviceAfficherCommandesTable !')
  // console.log('groupementCategories =', groupementCategories, '  --  idTable =', idTable, '  --  provenance =', provenance)
  let typeLoading = 'temps'
  // supprimer le settimeout
  if (attenteLancerVerifierEtatCommandes.etat === 0) {
    // console.log('-> supprimer le settimeout')
    attenteLancerVerifierEtatCommandes.etat = 1
    window.clearTimeout(attenteLancerVerifierEtatCommandes.rep)
    typeLoading = 'defaut'
  }

  let csrfToken = document.querySelector('input[name="csrfmiddlewaretoken"]').value
  let urlRequete = 'preparation'
  if (provenance === 'articles_table') {
    urlRequete = `preparation/${idTable}`
  }

  // mémoriser données d'affichages des commandes dans le dom
  let elementCible = document.querySelector('#service-commandes')
  elementCible.setAttribute('data-table-id', idTable)
  elementCible.setAttribute('data-groupement-categories', groupementCategories)
  elementCible.setAttribute('data-provenance', provenance)

  // titre vue
  const titrePreparation = getTranslate('preparations') === '' ? "Préparations" : getTranslate('preparations', 'capitalize')
  vue_pv.asignerTitreVue(titrePreparation)

  let requete = {
    type: "get",
    url: urlRequete,
    dataTypeReturn: 'json',
    csrfToken: csrfToken,
    // attente = paramètres pour l'icon de chargement
    attente: { typeVisuChargement: typeLoading }
  }
  // sys.logJson('requete = ', requete)
  // console.log(`-> serviceAfficherCommandesTable, ${  new Date().toLocaleTimeString() } -> requête "${ urlRequete }" lancée !`)
  sys.ajax(requete, function (retour, status) {
    // sys.logJson('status = ',status)
    // sys.logJson('retour = ', retour)
    if (status.code === 200) {
      // visuel enlever "signal en rouge"
      // document.querySelector('#temps-charge-visuel').innerHTML = ``
      // retour interval initial
      attenteLancerVerifierEtatCommandes.interval = intervalActualisationVuePreparations

      // filtre décimal to float
      for (const retourKey in retour) {
        const commandes = retour[retourKey].commandes
        for (const commandesKey in commandes) {
          const commande = commandes[commandesKey]
          commande.reste_a_payer = sys.bigToFloat(commande.reste_a_payer)
          const articles = commande.articles
          for (const articlesKey in articles) {
            const article = articles[articlesKey]
            article.qty = sys.bigToFloat(article.qty)
            article.reste_a_payer = sys.bigToFloat(article.reste_a_payer)
            article.reste_a_servir = sys.bigToFloat(article.reste_a_servir)
            article.article.prix = sys.bigToFloat(article.article.prix)
          }
        }
      }

      visualiserEtatCommandes(retour)
    } else {
      // vue_pv.afficher_message_erreur_requete(retour, status)
      // TODO: loger le retour et le status
      relancePreparationApresDefaut()
    }
  }, function (erreur) {
    // gestion des erreurs réseau
    // offline
    if (erreur === 0) {
      // console.log('->  après une erreur réseau:')
      // console.log('->  attenteLancerVerifierEtatCommandes.etat = ', attenteLancerVerifierEtatCommandes.etat)
      // visuel etat de la connexion
      // document.querySelector('#temps-charge-visuel').innerHTML = `<i class="fas fa-wifi" style="color:#FF0000;"></i>`
      relancePreparationApresDefaut()
    }
  })

}

/** @function
 * Afficher les commandes d'une table
 * @param {Number} idTable - id de la table
 * Status L Libre, O En cours de service, S Servie / en attente de paiement
 */

export function afficherCommandesTable(idTable) {
  // console.log('-> fonc afficherCommandesTable, idTable = ', idTable)
  let requete = {
    type: "get",
    url: `/wv/table_solo_et_commande/${idTable}`,
    dataTypeReturn: "json",
    csrfToken: glob.csrf_token,
    attente: { largeur: 80, couleur: '#0F0', nbc: 8, rpt: 4, epaisseur: 8 },
  }
  sys.ajax(requete, (retour, status) => {

    // sys.logJson('status = ', status)
    if (status.code === 200) {

      // filtre décimal
      retour.table.reste_a_payer = sys.bigToFloat(retour.table.reste_a_payer)
      for (let i = 0; i < retour.table.commandes.length; i++) {
        retour.table.commandes[i].reste_a_payer = sys.bigToFloat(retour.table.commandes[i].reste_a_payer)
        let articles = retour.table.commandes[i].articles
        for (const articlesKey in articles) {
          let article = articles[articlesKey]
          article.article.prix = sys.bigToFloat(article.article.prix)
          article.qty = sys.bigToFloat(article.qty)
          article.reste_a_payer = sys.bigToFloat(article.reste_a_payer)
          article.reste_a_servir = sys.bigToFloat(article.reste_a_servir)
        }
      }

      // initialisation vue table
      sys.effacerElements(['#page-commandes', '#tables', '#commandes-table-addition', '#service-commandes'])
      sys.afficherElements(['#commandes-table,block', '#commandes-table-articles,flex'])

      let table = retour.table
      // sys.logJson('table = ', retour.table)

      // titre vue
      const titreVue = getTranslate('articles') === '' ? `Articles ${table.name}` : `${getTranslate('articles', 'capitalize')} ${table.name}`
      vue_pv.asignerTitreVue(titreVue)

      let cible = document.querySelector('#commandes-table-contenu')
      // remise à zéro du total de l'addition en cours
      cible.setAttribute('data-total-addition-en-cours', 0)
      // maj idTable sélectionné
      cible.setAttribute('data-idTable', table.id)
      // maj nomTable sélectionné
      cible.setAttribute('data-nomTable', table.name)
      // supprimer les éléments du vase communicant de l'addition
      document.querySelector('#addition-vase-communicant').innerHTML = ''
      // éfface la liste de'articles à payer
      document.querySelector('#addition-liste').innerHTML = ''

      // déjà payé dans le(s) commande(s)
      dejaPayeeDansCommandes(table.commandes)

      let totalCommandesTable = totalPrixCommandesTable(table.commandes, idTable)
      document.querySelector('#commandes-table-contenu').setAttribute('data-total-commandes', totalCommandesTable)
      document.querySelector('#addition-total-commandes').innerHTML = totalCommandesTable + getTranslate('currencySymbol', null, 'methodCurrency')

      let resteAPayer = table.reste_a_payer
      document.querySelector('#commandes-table-contenu').setAttribute('data-reste-a-payer', resteAPayer)
      document.querySelector('#addition-reste-a-payer').innerHTML = resteAPayer + getTranslate('currencySymbol', null, 'methodCurrency')

      let listeArticles = []
      let commandes = table.commandes
      // boucle sur les commandes
      for (let idCom = 0; idCom < commandes.length; idCom++) {
        let commande = commandes[idCom]

        let uuidCommade = commande.uuid
        let responsable = commande.responsable_name
        let dateCommande = commande.datetime

        // boucle sur les articles de la commande
        for (let idArt = 0; idArt < commande.articles.length; idArt++) {
          let article = commande.articles[idArt].article
          // qty = reste_a_payer
          let qty = commande.articles[idArt].reste_a_payer

          // test article.id unique
          let presence = { etat: false }
          for (let idA = 0; idA < listeArticles.length; idA++) {
            if (article.id === listeArticles[idA].uuid) {
              presence.etat = true
              presence.index = idA
              break
            }
          }

          let obj = {}
          if (presence.etat === false) {
            obj.nbMax = qty
            obj.resteAservir = commande.articles[idArt].reste_a_servir
            obj.statut = commande.articles[idArt].statut
            obj.uuid = article.id
            obj.name = article.name
            obj.prix = article.prix
            obj.poidListe = article.poid_liste
            obj.categorie = article.categorie
            obj.urlImage = article.url_image
            obj.couleurTexte = article.couleur_texte
            obj.methodeName = article.methode_name
            obj.commandes = [{
              qty: qty,
              uuidCommande: uuidCommade,
              responsable: responsable,
              dateCommande: dateCommande
            }]
            if (article.id !== glob.uuidArticlePaiementFractionne) {
              listeArticles.push(obj)
            }
          } else {
            // TODO: gestion du poid_liste articles (prendre le plus petit ou bin plus grand ) ???
            if (listeArticles[presence.index].poidListe > article.poid_liste) {
              listeArticles[presence.index].poidListe = article.poid_liste
            }
            listeArticles[presence.index].nbMax += qty
            listeArticles[presence.index].commandes.push({
              qty: qty,
              uuidCommande: uuidCommade,
              responsable: responsable,
              dateCommande: dateCommande
            })
          }
        }
      }

      sys.trierTableauObjetDecroissantFoncAttribut(listeArticles, 'poidListe')

      // affichages des articles de la/des commande(s)
      let fragCommandesContenu = ''
      let monnaiePrincipaleName = document.querySelector('#pv' + pv_uuid_courant).getAttribute('data-monnaie-principale-name')
      for (let idArt = 0; idArt < listeArticles.length; idArt++) {
        let article = listeArticles[idArt]
        article.nomModule = 'vue_pv'
        article.monnaiePrincipaleName = monnaiePrincipaleName
        fragCommandesContenu += `<bouton-commande-article uuid-commande="${article.commandes[0].uuidCommande}" data-nom="${article.name}" data="${sys.html_pass_obj_in(article)}" methode="${article.methodeName}" data-prix="${article.prix}" data-uuid-article="${article.uuid}"></bouton-commande-article>`
      }
      document.querySelector('#commandes-table-articles').innerHTML = fragCommandesContenu

      //Afficher le bouton permettant de basculer de la liste d'articles des commandes à payer aux articles des commandes
      let fragMenuCommandesTable = `<div id="commandes-table-menu-commute-addition" class="BF-col categories-table-item curseur-action" onclick="restau.basculerListeAchatsCommandes();">
        <i class="categories-table-icon fas fa-list"></i>
        <div class="categories-table-nom" data-i8n="addition,capitalize">Addition</div>
      </div>`

      if (resteAPayer > 0) {
        // afficher le bouton permettant l'achat de tous les articles de la table
        fragMenuCommandesTable += `<div class="BF-col categories-table-item curseur-action" onclick="restau.ajouterTousArticlesAddition()">
          <i class="categories-table-icon fas fa-th"></i>
          <div class="categories-table-nom" data-i8n="all,capitalize">Tout</div>
        </div>`

        // afficher le bouton permettant d'entrer la somme à partager de l'addition
        fragMenuCommandesTable += `<div class="BF-col categories-table-item curseur-action" onclick="restau.demanderValeurAdditionFractionnee()">
          <i class="categories-table-icon fas fa-keyboard"></i>
          <div class="categories-table-nom" data-i8n="value,capitalize">Valeur</div>
        </div>`
      }

      // afficher le bouton pour la gestion des commandes de la table
      fragMenuCommandesTable += `<div class="BF-col categories-table-item curseur-action" onclick="attenteLancerVerifierEtatCommandes.interval=intervalActualisationVuePreparations;attenteLancerVerifierEtatCommandes.etat=0;restau.serviceAfficherCommandesTable(0, ${idTable}, 'articles_table');">
        <i class="categories-table-icon fas fa-concierge-bell"></i>
        <div class="categories-table-nom" data-i8n="shortcutPreparation,capitalize">Prépara.</div>
      </div>`

      document.querySelector('#commandes-table-menu').innerHTML = fragMenuCommandesTable
      translate('#commandes-table-menu')

      // footer
      let fragHtml = `<div id="table-footer-contenu" class="l100p h100p BF-ligne">  
        <div class="BF-ligne footer-bt fond-retour" onclick="restau.afficherCommandesTable(${table.id})">
          <i class="footer-bt-icon fas fa-trash md4px"></i>
          <div class="BF-col-deb footer-bt-text mg4px">
            <div data-i8n="reset,uppercase">RESET</div>
          </div>
        </div>
        <div class="BF-ligne fond-normal footer-bt curseur-action" onclick="vue_pv.initMode()">
          <i class="footer-bt-icon fas fa-undo-alt md4px"></i>
          <div class="BF-col-deb footer-bt-text mg4px">
            <div data-i8n="return,uppercase">RETOUR</div>
          </div>
        </div>
        <div id="bt-valider-commande" class="BF-ligne fond-ok footer-bt  curseur-action" onclick="vue_pv.testPaiementPossible('addition_liste')">
          <i class="footer-bt-icon fas fa-check-circle md4px"></i>
          <div class="BF-col-deb footer-bt-text mg4px">
            <div data-i8n="validate,uppercase">VALIDER</div>
            <div id="bt-valider-total-restau">
              <span data-i8n="total,uppercase">TOTAL</span> 0 ${getTranslate('currencySymbol', null, 'methodCurrency')}
            </div>
          </div>
        </div>
      </div>`

      document.querySelector('#commandes-table-footer').innerHTML = fragHtml
      translate('#commandes-table-footer')
    } else {
      vue_pv.afficher_message_erreur_requete(retour, status)
    }
  })
}

export function envoyerPreparation(actionAValider) {
  // console.log('-> fonc envoyerPreparation !')
  // console.log('actionAValider = ', actionAValider)

  // les articles sélectionnés
  let achats = vue_pv.obtenirAchats(actionAValider)

  let options = {
    url: "paiement",
    actionAValider: actionAValider,
    achats: achats
  }

  // envoyer en préparation
  if (actionAValider === 'envoyer_preparation' || actionAValider === 'envoyer_preparation_payer_fractionner') {
    vue_pv.validerEtape2(options)
  }

  // envoyer en préparation et payer en une seule fois
  if (actionAValider === 'envoyer_preparation_payer') {
    vue_pv.validerEtape1(options)
  }
}


export function choixTypePreparation() {
  let boutons = ''
  let msg = `<div class="BF-col-uniforme l100p h100p">
    <div id="test-prepa1" class="bt-envoyer-prepa" onclick="fn.popupAnnuler();restau.envoyerPreparation('envoyer_preparation')" style="background-color:#339448;">
      <div data-i8n="send,uppercase">ENVOYER</div>
      <div><span data-i8n="in,uppercase">EN</span> <span data-i8n="preparations,uppercase">PREPARATION</span></div>
    </div>

    <div id="test-prepa2" class="bt-envoyer-prepa" onclick="fn.popupAnnuler();restau.envoyerPreparation('envoyer_preparation_payer')" style="background-color:#cddc39;">
      <div data-i8n="send,uppercase">ENVOYER</div>
      <div><span data-i8n="in,uppercase">EN</span> <span data-i8n="preparations,uppercase">PREPARATION</span></div>
      <div>
      <span data-i8n="and,uppercase">ET</span> <span data-i8n="pay,uppercase">PAYER</span>
      </div>
      <div data-i8n="allAtOnce,uppercase">EN UNE SEULE FOIS</div>
    </div>

    <div id="test-prepa3" class="bt-envoyer-prepa" onclick="fn.popupAnnuler();restau.envoyerPreparation('envoyer_preparation_payer_fractionner')" style="background-color:#ff9800;">
      <div data-i8n="send,uppercase">ENVOYER</div>
      <div><span data-i8n="in,uppercase">EN</span> <span data-i8n="preparations,uppercase">PREPARATION</span></div>
      <div>
      <span data-i8n="and,uppercase">ET</span> <span data-i8n="goToPage,uppercase">ALLER A LA PAGE</span></div>
      <div data-i8n="payment,uppercase">DE PAIEMENT</div>
    </div>

    <div id="popup-retour" class="bt-envoyer-prepa" onclick="fn.popupAnnuler()" style="background-color:#3b567f;">
      <div class="BF-ligne-uniforme">
        <i class="fas fa-undo-alt md16px"></i>
        <div data-i8n="return,uppercase">RETOUR</div>
      </div>
    </div>
  </div>`

  let optionsPopup = {
    message: msg,
    type: 'normal'
  }
  fn.popup(optionsPopup)
}

/**
 * Mettre du mode commande à vente directe sans recharger les données
 */
export function lancerVenteDirecte() {
  console.log('Fonction  lancerVenteDirecte !')
  let dataPV = glob.data.filter(obj => obj.id === pv_uuid_courant)[0]
  dataPV.service_direct = true
  glob.tableEnCours = null
  vue_pv.afficherPointDeVentes(pv_uuid_courant)
}

/** pv_uuid_courant
 * Afficher les tables et leur état
 * @param {String} mode - 'visualiserCommandes' / assignerTable
 * @param {String} nomTable
 */
export function afficherTables(mode, nomTable) {
  console.log('-> afficherTables, mode = ', mode)

  let requete = {
    type: "post",
    url: "/wv/tables",
    dataTypeReturn: "json",
    dataType: 'form',
    csrfToken: glob.csrf_token,
    attente: { largeur: 80, couleur: '#0F0', nbc: 8, rpt: 4, epaisseur: 8 },
    data: {}
  }
  sys.ajax(requete, (retour, status) => {
    // sys.logJson('retour = ',retour)
    // sys.logJson('status = ',status)
    if (status.code === 200) {
      glob.tables = retour.tables

      sys.effacerElements(['#page-commandes', '#commandes-table', '#service-commandes'])
      sys.afficherElements(['#tables,block'])

      // titre vue
      let titreVue = getTranslate('displayCommandsTable') === '' ? "Afficher les commandes d'une table" : getTranslate('displayCommandsTable', 'capitalize')
      if (mode === 'assignerTable') {
        const transSelectTable = getTranslate('selectTable') === '' ? "Sélectionner une table" : getTranslate('selectTable', 'capitalize')
        titreVue = `${transSelectTable} : ${nomTable}`
      }
      vue_pv.asignerTitreVue(titreVue)

      // insérer les catégories de tables
      let fragCategories = elementsCategoriesTables()
      document.querySelector('#tables-categories').innerHTML = fragCategories
      translate('#tables-categories')

      // insérer la liste de tables ('visualiserCommandes' = afficher les tables dans le but de viualiser les commandes)
      let fragListeTables = elementsListeTables(mode)
      document.querySelector('#tables-liste').innerHTML = fragListeTables

      // footer, fond menu catégories et fond contenu
      let fragFooter = ''
      if (mode === 'assignerTable') {
        fragFooter = `<div id="table-footer-contenu" class="fond-normal l100p h100p BF-ligne">  
          <div class="BF-ligne fond-normal l50p h100p curseur-action test-check-carte" onclick="vue_pv.check_carte()">
            <i class="footer-bt-icon fas fa-money-check-alt md4px"></i>
            <div class="BF-col-deb footer-bt-text mg4px">
              <div data-i8n="check,uppercase">CHECK</div>
              <div data-i8n="card,uppercase">CARTE</div>
            </div>
          </div>
          <div class="BF-ligne fond-coul1 l50p h100p curseur-action test-service-direct" onclick="restau.lancerVenteDirecte()">
            <i class="footer-bt-icon fas fa-cash-register md4px"></i>
            <div class="BF-col footer-bt-text mg4px">
              <div data-i8n="directService,uppercase">SERVICE DIRECT</div>
            </div>
          </div>
        <div>`

        document.querySelector('#tables-footer').innerHTML = fragFooter
        translate('#tables-footer')

        document.querySelector('#tables-contenu').setAttribute('style', 'background-color:#18252f')
        document.querySelector('#tables-categories').setAttribute('style', 'background-color:#24303a')
      } else {
        // mode = visualiserCommandes
        document.querySelector('#tables-contenu').setAttribute('style', 'height:100%;background-color:#0f2e45')
        document.querySelector('#tables-categories').setAttribute('style', 'background-color:#0f3350')
      }

    } else {
      console.log('status.code =', status.code)
      vue_pv.afficher_message_erreur_requete(retour, status)
    }
  })
}
