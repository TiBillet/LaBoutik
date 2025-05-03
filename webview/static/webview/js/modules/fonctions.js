/**
 * Charge un fichier js gérant la logique d'un template (binôme template/js)
 * @param  {string} nom_module - nom de l'objet possédant les méthodes pour gérer le template
 * @param  {string} fichier    - chemin du fichier js contenat les méthodes pour gérer le template
 * @param  {object} contexte   - objet contenant les données pour la gestion du template
 * @return {Function}          - lance la fonction window[nom_module].main (export Function main)
 */
export function init_rendu(nom_module, fichier, contexte) {
  import(fichier).then((module) => {
    window[nom_module] = module
    // prend les arguments après page
    let args = [nom_module, contexte]
    window[nom_module].main.apply(this, args)
  })
}


/**
 * Evalue le template avec les données 'ctx'
 * Attention : toutes les variables sont contenu dans l'objet ctx,
 * donc préfixer toutes vos variables avec 'ctx.' dans le template html
 * @param  {string}   template - chaînes de caractères multiligne composant une page ou un frament de page
 * @param  {object}   ctx      - données à insérer dans le template
 * @return {Function} fonction
 */
function template_render(template, ctx) {
  // sys.logJson('ctx = ',ctx);
  let fa = new Function('ctx', '"use strict";return `' + template + '`')
  return fa(ctx)
}

/**
 * Charge un fichier template et le rend sur la page
 * contexte = {
 *   id_cible : 'fond_contenu', => obligatoire|où rendre le template dans la page (un id)
 *   action_cible: 'remplacer', => obligatoire|comment rendre le template, remplacer l'élément sibble ou insérer
 *   nom_module : nom_module,   => obligatoire|point d'entrée des fonctions lancées dans le template
 *   divers : {test:"tset",savoir:1,rep:{obj:obj}},
 *   message:'salut la compagnie !',
 *   template_binding :{        => si composant|obligatoire
 *     composant: "VarModule",  => variable/class contenant le module, import * as VarModule from "/static/webview/js/components/VarModule.js";
 *     data: boutons_action     => données à intégrer au composant
 *  }
 * };
 * action_cible : rempacer        = remplace le contenu de l'élémnet ciblé
 * inserer_premier = insère en première position dans l'élément ciblé
 * inserer_dernier = insère en dernière position dans l'élément ciblé
 *@param {string} fichier  - chemin du fichier
 *@param {object} contexte - données du template
 **/
export function template_render_file(fichier, contexte, methods_after_render) {
  let headers = new Headers()
  headers.append("Content-Type", "text/plain")
  let init = {
    method: 'GET',
    headers: headers
  }
  let requete = new Request(fichier, init)
  fetch(requete, init).then((reponse) => { // 1 - charge le template
    return reponse.text()
  }).then((template) => {
    // rendu du template
    let template_eval = template_render(template, contexte) // 2 -complétion du template par les données (contexte)

    // 2 - insère le template dans le DOM (affiche le fragment ou la page html)
    if (contexte.action_cible === 'remplacer') {
      document.querySelector('#' + contexte.id_cible).innerHTML = template_eval
    }

    if (contexte.action_cible === 'inserer_premier') {
      document.querySelector('#' + contexte.id_cible).insertAdjacentHTML('afterbegin', template_eval)
    }

    if (contexte.action_cible === 'inserer_dernier') {
      document.querySelector('#' + contexte.id_cible).insertAdjacentHTML('beforeend', template_eval)
    }

    // 3 - exécution des methodes après rendu
    if (methods_after_render.length > 0) {
      for (const index_methode in methods_after_render) {
        methods_after_render[index_methode].method()
      }
    }

    translate('#' + contexte.id_cible)
  }).catch((err) => {
    console.log('---- template_render_file Error ----')
    console.log('fichier template : ' + fichier)
    console.log('Erreur; : ', err)
  })
}


/**
 * Pour visuliser des données sur la page pour le débeugage
 * Dans le template  insérer '${ var_dump(ctx.data,'300|200|#0000FF') }'
 *@param {object} data = données à visualiser, exemple ctx.data <=> ctx = contexte de la page / data = une des données du contexte
 *@param {string} options = optionel ou '300|200|#0000FF' <=> largeur|hauteur|couleur du text
 @return {string} fragment html
 **/
export function var_dump(data, options) {
  let largeur = 600,
    hauteur = 300,
    couleur = '#FFFFFF'
  if (options !== undefined) {
    let tab = options.split('|')
    if (tab[0] !== undefined) largeur = tab[0]
    if (tab[1] !== undefined) hauteur = tab[1]
    if (tab[2] !== undefined) couleur = tab[2]
  }
  return '<pre style="border-radius:8px;border:1px solid ' + couleur + ';backgroud-color:rgba(0,0,0,1);color:' + couleur + ';width:' + largeur + 'px;height:' + hauteur + 'px;overflow-y:auto">' + JSON.stringify(data, null, '\t') + '</pre>'
}

export function popupAnnuler() {
  sys.supElement('#popup-cashless')
}

// options ={titre:'Choisir votre moyen de paiement ?',message:'',annuler:'oui',boutons:boutons,type:'normal'}
export function popup(options) {
  let type_message = {
    'normal': { coul_fond: '#1a1e25' },
    'danger': { coul_fond: '#722727' },
    'succes': { coul_fond: '#339448' },
    'attent': { coul_fond: '#b85521' },
    'retour': { coul_fond: '#3b567f' }
  }

  // option.annuler si définit affiche le bouton 'annuler' et lance un callback(sa valeur=une méthode) en plus à appeler popup_alluler()
  let titre = '', message = '', action_prope = '', action_prope_style = '', style_curseur = '', style_fond = '', boutons = ''
  if (options.titre !== undefined) titre = options.titre
  if (options.message !== undefined) message = options.message

  if (options.boutons !== undefined) boutons = options.boutons

  style_fond = 'background-color:' + type_message[options.type].coul_fond + ';'

  action_prope_style = ' style="' + style_curseur + style_fond + '"'

  let frag = `
      <div id="popup-cashless" ${action_prope} class="BF-col popup-cashless-conteneur" ${action_prope_style}>
				${titre}
				${message}
        ${boutons}
			</div>
    `

  document.querySelector('#contenu').insertAdjacentHTML('beforeend', frag)
  translate('#contenu')
  let popup = document.querySelector('#popup-cashless')
  
  // process dynamic htmx content
  htmx.process(popup)

  // gestion des boutons non basiques
  // exemple: lance une méthode qui rajoute un bouton à la liste des boutons après une pression donnée sur la souris
  if (options.boutons_spec !== undefined) {
    for (let i = 0; i < options.boutons_spec.length; i++) {
      let data = options.boutons_spec[i]
      // console.log('nom module = ' + data.nom_module + '  --  méthode = ' + data.methode)
      sys.logJson('argument = ', data.argument)
      window[data.nom_module][data.methode](data.argument)
    }
  }
}

export function popupConfirmeAnnuler() {
  sys.supElement('#popup-cashless-confirm')
}

window.validateGivenSum = function (fonction) {
  // console.log('-> validateGivenSum, fonc =', fonction)
  try {
    const fonctions = ['vue_pv.validerEtapeMoyenComplementaire', 'vue_pv.obtenirIdentiteClientSiBesoin']
    let totalAchat
    if (glob.actionAValider === 'addition_liste' || glob.actionAValider === 'addition_fractionnee') {
      totalAchat = parseFloat(document.querySelector('#commandes-table-contenu').getAttribute('data-total-addition-en-cours'))
    } else {
      totalAchat = parseFloat(document.querySelector('#article-infos-divers').getAttribute('data-total'))
    }

    if (fonctions.includes(fonction) === false) {
      throw new Error('Fonction inconnue !')
    }

    const sumString = document.querySelector('#given-sum').value
    let sum = parseFloat(sumString)
    let firstSumFromCashless = 0

    // additional sum from first cashless card
    if (glob.dataCarte1 !== undefined && glob.dataCarte1 !== null) {
      firstSumFromCashless = parseFloat(glob.dataCarte1.retour.carte.total_monnaie)
    }

    let sumMin = false
    if (isNaN(sum)) {
      document.querySelector('#given-sum-msg-erreur').innerHTML = `<span data-i8n="isNotNumber,capitalize" style="color: red;">Ce n'est pas un nombre</span>`
    } else {
      if ((glob.actionAValider === 'prendre_commande' || glob.actionAValider === 'envoyer_preparation_payer' || glob.actionAValider === 'vente_directe' || glob.actionAValider === 'addition_liste') && (sum + firstSumFromCashless) < totalAchat) {
        document.querySelector('#given-sum-msg-erreur').innerHTML = `<span data-i8n="total,uppercase" style="color: red;">total = ${totalAchat} </span>
      <span data-i8n="currencySymbol" style="color: red;"></span>`
        // une somme entrée, inférieure au total bloque la validation
        sumMin = true
      }
    }

    if (sumString.length === 0) {
      sum = 0
    }

    if (sumMin === false) {
      // une somme quelconque
      const sumValue = (new Big(sum)).valueOf()

      fn.popupConfirmeAnnuler()
      fn.popupAnnuler()
      if (fonction === 'vue_pv.validerEtapeMoyenComplementaire') {
        vue_pv.validerEtapeMoyenComplementaire('espece', sumValue)
      }
      if (fonction === 'vue_pv.obtenirIdentiteClientSiBesoin') {
        vue_pv.obtenirIdentiteClientSiBesoin('espece', sumValue)
      }
    }
    /*
    if (isNaN(sum)) {
      document.querySelector('#given-sum-msg-erreur').innerHTML = `<span data-i8n="isNotNumber,capitalize" style="color: red;">Ce n'est pas un nombre</span>`
    } else {
      // console.log('somme =', sum, '  --  type =', typeof(sum))
      // console.log('totalAchat =', totalAchat, '  --  type =', typeof(totalAchat))
      // console.log('glob.actionAValider =', glob.actionAValider)
      // console.log('sum < totalAchat =', sum < totalAchat)
 
      // payer en une seule fois, somme exacte ou supérieure
      if ((glob.actionAValider === 'prendre_commande' || glob.actionAValider === 'envoyer_preparation_payer' || glob.actionAValider === 'vente_directe' || glob.actionAValider === 'addition_liste') && (sum + firstSumFromCashless) < totalAchat) {
        document.querySelector('#given-sum-msg-erreur').innerHTML = `<span data-i8n="total,uppercase" style="color: red;">total = ${totalAchat} </span>
        <span data-i8n="currencySymbol" style="color: red;"></span>`
      } else {
        // une somme quelconque
        const sumValue = (new Big(sum)).valueOf()
        // console.log('sumValue =', sumValue)
        fn.popupConfirmeAnnuler()
        fn.popupAnnuler()
        if (fonction === 'vue_pv.validerEtapeMoyenComplementaire') {
          vue_pv.validerEtapeMoyenComplementaire('espece', sumValue)
        }
        if (fonction === 'vue_pv.obtenirIdentiteClientSiBesoin') {
          vue_pv.obtenirIdentiteClientSiBesoin('espece', sumValue)
        }
      }
    }
      */
  } catch (error) {
    console.log('error', error)
  }
}

export function popupConfirme(moyenPaiement, nom, fonction) {
  // console.log('-> fonc popupConfirme, moyenPaiement =', moyenPaiement, '  --  nom =', nom, '  --  fonction =', fonction)
  let fonctionValider = ''

  // gestion de la somme donnée pour le moyen de paiement "espèce"
  if (moyenPaiement === 'espece') {
    fonctionValider = `keyboard.hide();validateGivenSum('${fonction}')`
  } else {
    fonctionValider = `keyboard.hide();fn.popupConfirmeAnnuler();fn.popupAnnuler();${fonction}('${moyenPaiement}');`
  }

  let frag = `<div id="popup-cashless-confirm" class="BF-col popup-cashless-confirm-conteneur">
    <h1>
      <div class="BF-ligne test-return-confirm-payment" data-i8n="confirmPayment, capitalize">
        Confirmez le paiement
      </div>
      <div class="BF-ligne">
        <span data-i8n="by" style="margin-right:6px;"></span>
        <span class="test-return-payment-method" data-i8n="${orthoPaiement[moyenPaiement]}"></span>
      </div>
    </h1>
    <div id="given-sum-container" class="BF-col">`

  if (moyenPaiement === 'espece') {
    // Sans clavier virtuel pour les autres fronts
    if (glob.appConfig.front_type !== 'FPI') {
      frag += `
          <div  class="popup-msg1" data-i8n="givenSum">Somme donnée</div>
          <input type="number" id="given-sum" class="addition-fractionnee-input">
          <small id="given-sum-msg-erreur"></small>
        `
    } else {
      // Avec clavier virtuel pour raspberry pi
      frag += `
        <div data-i8n="givenSum">Somme donnée</div>
        <input id="given-sum" class="addition-fractionnee-input keyboard-use" keyboard-type="numpad" onclick="keyboard.run(this,{keySize: 90})">
        <small id="given-sum-msg-erreur"></small>
      `
    }
  }

  frag += `</div>
    <div id="confirm-action-container" class="BF-ligne-entre" style="margin-top: 2rem;">
      <bouton-basique id="popup-confirme-retour" traiter-texte="1" i8n="return" texte="RETOUR|2rem|" couleur-fond="#3b567f" icon="fa-undo-alt||2.5rem" width="300px" height="120px"  onclick="keyboard.hide();fn.popupConfirmeAnnuler();" style="margin: 8px"></bouton-basique>
      <bouton-basique id="popup-confirme-valider" traiter-texte="1" i8n="validate" texte="VALIDER|2rem|" couleur-fond="#339448" icon="fa-check-circle||2.5rem" width="300px" height="120px"  onclick="${fonctionValider};" style="margin: 8px;"></bouton-basique>
    </div>
  </div>`

  document.querySelector('#contenu').insertAdjacentHTML('beforeend', frag)
  translate('#contenu')
}