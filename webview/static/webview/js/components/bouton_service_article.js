
function getTemplate(ctx){
  // sys.logJson('ctx = ', ctx)

  let template = `
    <style>
      @font-face {
        font-family: 'Source Sans';
        src: url('/static/webview/css/googlefonts/SourceSansPro-Regular.ttf') format("truetype");
      }
      :host {
        box-sizing: border-box;
        width: 120px;
        height: 120px;
        cursor: pointer;
        overflow: hidden;
        border-radius: 15px;
        background-color: ${ ctx.couleurFond };
        margin: 20px 0 0 20px;
        float: left;
      }

      .ele-conteneur {
        position: relative;
        font-family: 'Source Sans', sans-serif;
        box-sizing: border-box;
        width: 100%;
        height: 100%;
        border-radius: 15px;
      }

      .ele-nom {
        position: absolute;
        left: 8px;
        top: 6px;
        font-weight: bold;
        max-height: 60px;
        font-size: 20px;
        margin-top: 0;
        margin-bottom: 1rem;
        color: ${ ctx.couleurTexte };
        overflow: hidden;
      }

      .ele-img {
        position: absolute;
        left: 0;
        top: 0;
        width: 100%;
        height: 100%;
        overflow: hidden;
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

      .article-statut {
         position: absolute;
         width: 21px;
         height: 21px;
         right: 4px;
         bottom: 34px;
         color: #FFFFFF;
         border-radius: 50%;
      }

      .ele-icon {
        flex-basis: 25%;
        color: ${ ctx.couleurTexte };
      }

      .ele-prix {
        flex-basis: 45%;
        color: ${ ctx.couleurTexte };
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
        left: 0px;
        top: 0px;
        width: 100%;
        height: 100%;
        border-radius: 15px;
        background-color: #2a2828;
        opacity: 0.5;
        cursor: default;
        display: none;
      }

      /* largeur maxi 600 pixels */
      @media only screen and (min-width: 599px){
        :host {
          width: 140px;
        }
      }

      /* largeur maxi 1024 pixels */
      @media only screen and (min-width: 1023px) {
        :host {
          width: 100px;
          height: 100px;
        }
        .ele.img {
          width: 100px;
          height: 100px;
        }
        .ele-nom {
          font-size: 16px;
        }
        .ele-prix {
          flex-basis: 40%;
        }
      }

    </style>
    <link rel="stylesheet" href="/static/webview/css/all_fontawesome-free-5-11-2.css">
    <div class="ele-conteneur">
      ${ ctx.afficherImage() }
      <div class="ele-nom">
        ${ ctx.nom }
      </div>
      <div class="article-pdp BF-ligne-g">
        <div class="ele-icon">${ ctx.infoIcon }</div>
        ${ ctx.afficherPrix() }
        <div class="ele-nombre BF-ligne">
          <span id="rep-reste-a-servir${ ctx.articleUuid }" class="badge">${ ctx.resteAservir }</span>
        </div>
      </div>
      <div id="bt-rideau"></div>
    </div>
  `
  return template
}

export default class BoutonCommandeArticle extends HTMLElement {
  static get observedAttributes() {
    return ['nb-commande'];
  }

  connectedCallback() {
    let data = this.getAttribute('data')
    let article = JSON.parse(unescape(data))
    // sys.logJson('article -> ',article);
    // console.log('-----------------------------------------------')

    this.idTable = article.idTable
    this.articleUuid = article.uuid
    this.prix = article.prix
    this.nom = article.name
    this.img = article.urlImage
    this.nomModule = article.nomModule
    this.commandes = article.commandes
    this.resteAservir = article.resteAservir

    // couleur de fond de la categorie
    // par défaut
    this.couleurFond = '#189ac8'
    // icon
    this.infoIcon = ''
    if (article.categorie !== undefined && article.categorie !== null){
      // affiche ou pas le fond
      this.couleurFond = article.categorie.couleur_backgr
      // couleur du texte par défaut
      this.infoIcon = '  <i class="fas '+article.categorie.icon+'"></i>'
      this.couleurTexte = article.categorie.couleurTexte
    }

    // couleur du texte de l'article prioritaire pour mieux resortir sur l'image
    if (article.couleurTexte !== null) this.couleurTexte = article.couleurTexte
    if (this.couleurTexte === undefined || this.couleurTexte === null) this.couleurTexte = '#FFFFFF'

    this.setAttribute('reste-a-servir', this.resteAservir)

    this.attachShadow({mode: 'open'}).innerHTML = getTemplate(this)

    this.addEventListener('click', this.decrementer, false)

    this.removeAttribute('data')
  }


  afficherPrix () {
    return `
       <div class="ele-prix BF-ligne-g">
          ${ this.prix } €
       </div>
    `
  }

  /**
   * Affiche une image dans le bouton article
   * @returns {string} template div contenant une image
   */
  afficherImage () {
    if (typeof this.img === 'string') {
      return `
          <div class="ele-img BF-ligne">
            <img src="${this.img}">
          </div>
     `
    }
    return ''
  }

  decrementer() {
    console.log('-> bouton service article décrémente !')
    /*
    if (this.resteAservir > 0) {
      this.setAttribute('reste-a-servir', this.resteAservir--)
    }
     */
  }

  attributeChangedCallback(name, oldValue, newValue) {
    if (name === 'reste-a-servir') {
      this.resteAservir = this.getAttribute('reste-a-servir')
      if (this.shadowRoot !== null) {
        // maj nombre article
        this.shadowRoot.querySelector(`#rep-reste-a-servir${this.articleUuid}`).innerHTML = this.resteAservir
      }

      // cache l'élément
      if (this.nbCommande === '0') {
        console.log('article servi !!')
      } else {
        console.log('article non servi !!')
      }
    }
  }
}