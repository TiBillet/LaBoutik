/**
 * Obtenir une couleur plus claire ou plus sombre
 *@param {string} hex = couleur en hexadécimal
 *@param {float} lum = positif => claire, négatif => sombre
 *@return {string} rgb = coluleur format rgb
 * by Craig Buckler
 */
function colorLuminance(hex, lum) {
  // validate hex string
  hex = String(hex).replace(/[^0-9a-f]/gi, '')
  if (hex.length < 6) {
    hex = hex[0] + hex[0] + hex[1] + hex[1] + hex[2] + hex[2]
  }
  lum = lum || 0

  // convert to decimal and change luminosity
  let rgb = '#', c, i
  for (i = 0; i < 3; i++) {
    // c = parseInt(hex.substr(i*2,2), 16);
    c = parseInt(hex.substring(i * 2, (i * 2 + 2)), 16)
    c = Math.round(Math.min(Math.max(0, c + (c * lum)), 255)).toString(16)
    rgb += ('00' + c).substring(c.length)
  }
  return rgb
}

// TODO: les hauteurs du bouton article doivent être en pourcentage du conteneur principal
function get_template(ctx) {
  // console.log('couleur_texte = '+ctx.couleur_texte + '  --  type = ' + typeof ctx.couleur_texte+ '  --  nom = '+ctx.nom);
  let template = `
    <style>
      :host {
        box-sizing: border-box;
        width: 120px;
        height: 120px;
        cursor: pointer;
        overflow: hidden;
        border-radius: 15px;
        background-color: ${ctx.couleur_fond};
        margin: 20px 0 0 20px;
        float: left;
      }

      .ele-conteneur {
        position: relative;
        font-family: "Luciole-regular";
        box-sizing: border-box;
        width: 100%;
        height: 100%;
        border-radius: 15px;
      }

      .ele-nom {
        position: absolute;
        left: 4px;
        top: 6px;
        font-weight: bold;
        height: 78px;
        width: calc(100% - 8px);
        font-size: 18px;
        margin: 0;
        padding: 0;
        color: ${ctx.couleur_texte};
        overflow: hidden;
        text-shadow: 2px 2px 3px ${colorLuminance(ctx.couleur_fond, -0.5)};
        text-align: center;
      }

      .ele-img {
        position: absolute;
        left: 0;
        top: 0;
        width: 100%;
        height: 100%;
        overflow: hidden;
      }

      .bouton-article-image {
        opacity: 0.7;
      }
      
      .BF-ligne {
        align-items: center;
        display: flex;
        flex-direction: row;
        justify-content: center;
      }

      .BF-ligne-g{
        align-items: center;
        display: flex;
        flex-direction: row;
        justify-content: flex-start;
        width: 100%;
      }

      .article-pdp {
        position: absolute;
        left: 8px;
        bottom: 8px;
      }

      .ele-icon {
        flex-basis: 25%;
        color: ${ctx.couleur_texte};
      }

      .ele-prix {
        flex-basis: 45%;
        color: ${ctx.couleur_texte};
      }

      .ele-nombre {
        flex-basis: 25%;
      }

      .badge {
        color: #212529;
        background-color: #f8f9fa;
        display: inline-block;
        padding: .25em .4em;
        font-weight: bold;
        line-height: 1;
        text-align: center;
        white-space: nowrap;
        vertical-align: baseline;
        border-radius: .25rem;
        transition: color .15s ease-in-out,background-color .15s ease-in-out,border-color .15s ease-in-out,box-shadow .15s ease-in-out;
      }

      #bt-rideau{
        position: absolute;
        left: 0;
        top: 0;
        width: 100%;
        height: 100%;
        border-radius: 15px;
        background-color: #2a2828;
        opacity: 0.5;
        cursor: default;
        display: none;
      }

      /* pour une largeur supérieure ou égale à 599 pixels */
      @media only screen and (min-width: 599px){
        :host {
          width: 140px;
        }
      }

      /* pour une largeur supérieure ou égale à 1023 pixels */
      @media only screen and (min-width: 1023px) {
        :host {
          width: 100px;
          height: 100px;
        }
        .article-pdp {
          font-size: 0.8rem;
        }
        .ele.img {
          width: 100px;
          height: 100px;
        }
        .ele-nom {
          font-size: 16px;
        }
        .ele-icon {
          flex-basis: 20%;
        }
      }
    
      /* sunmi d3mini -- pour une largeur supérieure ou égale à 1279 pixels */
      @media only screen and (min-width: 1279px) { 
        :host {
          width: 160px;
          height: 160px;
        }
        .ele-nom {
          font-size: 1.5rem;
        }
        .article-pdp {
          width: 95%;
          left: 4px;
          font-size: 1.4rem;
        }
        .ele-icon {
          flex-basis: 20%;
        }
        .ele-prix {
          flex-basis: 55%;
          overflow-wrap: break-word;
        }
        .ele-nombre {
          flex-basis: 25%;
        }
      }

    </style>
    <link rel="stylesheet" href="/static/webview/css/all_fontawesome-free-5-11-2.css">
    <div class="ele-conteneur">
      ${ctx.afficher_image()}
      <div class="ele-nom">
        ${ctx.nom.replace(/\\n/g, '<br>')}
      </div>
      <div class="article-pdp BF-ligne-g">
        <div class="ele-icon">${ctx.info_icon}</div>
        ${ctx.afficher_prix()}
        <div class="ele-nombre BF-ligne">
          <span id="rep-nb-article${ctx.uuid}" class="badge">0</span>
        </div>
      </div>
      <div id="bt-rideau"></div>
    </div>
  `
  return template
}

export default class BoutonArticle extends HTMLElement {
  static get observedAttributes() {
    return ['nb-commande']
  }

  connectedCallback() {
    this.classList.add('bouton-article')

    let data = this.getAttribute('data')
    let article = JSON.parse(unescape(data))
    // sys.log_json('data -> ',article);
    // this.nb_commande  = article.nb_commande;
    this.uuid = article.id
    // retour consigne en absolut
    // this.prix = article.methode_name !== "RetourConsigne" ? article.prix : Math.abs(article.prix)
    this.prix = article.prix
    this.afficher_les_prix = article.afficher_les_prix
    this.largeur = article.largeur
    this.hauteur = article.hauteur
    this.nom = article.name
    this.img = article.url_image
    this.presence_prix = article.presence_prix
    this.nom_module = article.nom_module
    this.nb_commande = 0
    this.nb_commande_max = article.bt_groupement.nb_commande_max
    this.bt_groupement = article.bt_groupement
    this.groupe = article.bt_groupement.groupe
    this.methode = article.methode_name

    // couleur de fond de la categorie
    // par défaut
    this.couleur_fond = '#189ac8'
    // affiche ou pas le fond
    if (article.categorie !== null && article.categorie.couleur_backgr !== null) {
      this.couleur_fond = article.categorie.couleur_backgr
    }

    // console.log('couleur_fond =', this.couleur_fond)

    // icon
    this.info_icon = ''
    // couleur du texte par défaut
    if (article.categorie !== null) {
      this.info_icon = '  <i class="fas ' + article.categorie.icon + '"></i>'
      if (article.categorie.couleur_texte !== null) {
        this.couleur_texte = article.categorie.couleur_texte
      } else {
        this.couleur_texte = '#FFFFFF'
      }
    }
    // couleur du texte de l'article prioritaire pour mieux resortir sur l'image
    if (article.couleur_texte !== null) this.couleur_texte = article.couleur_texte
    if (this.couleur_texte === undefined || this.couleur_texte === null) this.couleur_texte = '#FFFFFF'

    // initialisation des attributs [target=_blank]
    this.setAttribute('nb-commande', 0)
    this.setAttribute('prix', article.prix)
    this.setAttribute('nom', article.name)
    this.setAttribute('uuid', article.id)
    this.setAttribute('groupe', this.groupe)
    this.setAttribute('groupe-actif', '')
    this.setAttribute('methode', article.methode_name)
    this.setAttribute('moyens-paiement', article.bt_groupement.moyens_paiement)
    this.setAttribute('uuid-pv', article.pv)

    // sys.log_json('article = ',article);
    // console.log('-------------------------------------------------------');

    this.attachShadow({ mode: 'open' }).innerHTML = get_template(this)
    this.addEventListener('click', this.increment, false)
    if (article.class_categorie !== undefined) this.classList.add(article.class_categorie)

    this.removeAttribute('data')
  }

  afficher_prix() {
    if (this.afficher_les_prix === true) {
      return `
        <div class="ele-prix BF-ligne-g">
          ${this.prix} ${getTranslate('currencySymbol', null, 'methodCurrency')}
        </div>
      `
    }
    return ''
  }

  /**
   * Affiche une image dans le bouton article
   * @returns {string} template div contenant une image
   */
  afficher_image() {
    if (typeof this.img === 'string') {
      return `
          <div class="ele-img BF-ligne">
            <img src="${this.img}" class="bouton-article-image" loading="lazy" alt='' onerror="this.style.display='none'">
          </div>
     `
    }
    return ''
  }

  set_groupe_actif(groupe_actif) {
    // met le nombre d'article commander de tous les articles à 0
    let eles = document.querySelectorAll('.bouton-article')
    for (let i = 0; i < eles.length; i++) {
      let ele = eles[i]
      ele.setAttribute('groupe-actif', groupe_actif)
      let groupe = ele.getAttribute('groupe')
      if (groupe !== groupe_actif) {
        ele.shadowRoot.querySelector('#bt-rideau').style.display = 'block'
      }
    }
  }

  // incrémente les commandes
  increment() {
    // console.log(`-> fonction increment de 'bouton-article.js'`)
    // gère l'activation d'un groupe de bouton
    let groupe_actif = this.getAttribute('groupe-actif')
    if (groupe_actif === '') {
      this.set_groupe_actif(this.groupe)
      groupe_actif = this.groupe
    }

    if (this.groupe === groupe_actif && this.nb_commande < this.nb_commande_max) {
      document.querySelector('#article-infos-divers').setAttribute('achat-possible', 1)
      this.nb_commande++

      // maj attribut nb-commande du bouton
      this.setAttribute('nb-commande', this.nb_commande)
      // maj du prix affiché sur le bouton
      this.shadowRoot.querySelector('#rep-nb-article' + this.uuid).innerHTML = this.nb_commande

      // obtenir l'enregistrement de la variable "total" du DOM
      let total = new Big(parseFloat(document.querySelector('#article-infos-divers').getAttribute('data-total')))
      // ajouter le prix de l'article sélectionné
      total = total.plus(this.prix)
      // enregistre la nouvelle valeur dans le DOM
      document.querySelector('#article-infos-divers').setAttribute('data-total', total)

      // active achat (achat possible)
      document.querySelector('#article-infos-divers').setAttribute('achat-possible', 1)

      // renseigne le bouton "VALIDER" contenant l'information du total des achats
      document.querySelector('#bt-valider-total').innerHTML = `TOTAL ${total} ${getTranslate('currencySymbol', null, 'methodCurrency')}`

      // renseigne/peuple la liste
      let liste = document.querySelector('#achats-liste')
      if (document.querySelector('#achats-liste-ligne' + this.uuid)) {
        // article déjà dans la liste
        document.querySelector('#achats-liste-ligne-nb' + this.uuid).innerHTML = this.nb_commande
      } else {
        let frag = `
        <div id="achats-liste-ligne${this.uuid}" class="BF-ligne-deb l100p achats-ligne">
          <div class="achats-col-bt">
            <i class="fas fa-minus-square" onclick="${this.nom_module}.decrementer_nombre_produit('${this.uuid}');" title="Enlever un article !"></i>
          </div>
          <div id="achats-liste-ligne-nb${this.uuid}" class="achats-col-qte">${this.nb_commande}</div>
          <div class="achats-col-produit">
            <div class="achats-ligne-produit-contenu">${this.nom}</div>
          </div>
          <div class="achats-col-prix">
            <div class="achats-col-prix-contenu">
              ${this.prix}${getTranslate('currencySymbol', null, 'methodCurrency')}
            </div>
          </div> 
        </div>
      `
        liste.insertAdjacentHTML('beforeend', frag)
      }
    }

  }

  attributeChangedCallback(name, oldValue, newValue) {
    if (name === 'nb-commande') {
      // console.log('nb-command change, oldValue =', oldValue, '  --  newValue =', newValue)
      this.nb_commande = this.getAttribute('nb-commande')
    }
  }
}