export function paymentBt({ width, height, backgroundColor, textColor, icon, methods, currency, total, cssClass, addHtmlContent, paymentBtForceHeight}) {
  try {
    // console.log('-> btBasique')
    // change height value
    height = paymentBtForceHeight !== undefined ? paymentBtForceHeight : height
    const commonStyle = `<style id="payment-bt-common-style">
      .paiement-bt-container {
        width: ${width}px;
        height:  ${height}px;
        display: flex;
        flex-direction: row;
        background: ${backgroundColor};
        color: ${textColor};
        cursor: pointer;
        overflow: hidden;
        font-size: 2rem;
        margin-top: 16px;
      }
      .paiement-bt-icon {
        width: 80px;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
      }
      .paiement-bt-icon i {
        width: 46px;
        height: auto;
      }
      .paiement-bt-text {
        width: calc(100% - 80px);
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        font-weight: bold;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
      }
      .paiement-bt-total {
        font-size: 1.5rem;
      }
      /* pour une largeur supérieure ou égale à 599 pixels */
      @media only screen and (min-width: 599px) {
      .paiement-bt-container {
        width: ${width * 1.42}px;
        height:  ${height * 1.34}px;
      }
      /* pour une largeur supérieure ou égale à 1023 pixels */
      @media only screen and (min-width: 1023px) {
        .paiement-bt-container  {
          width: ${width * 1.4}px;
          height: ${height}px;
        }
      }
    </style>`

    let curencyContent = ''
    if (Array.isArray(currency)) {
      currency.forEach(item => {
        curencyContent += item.tradIndex !== undefined ? (getTranslate(item.tradIndex, item.tradOption) + ' ') : (item.name + ' ')
      })
    } else {
      // traduction ou pas de traduction
      curencyContent = currency.tradIndex !== undefined ? getTranslate(currency.tradIndex, currency.tradOption) : currency.name
    }

    const fonctions = methods.join(';')
    const addClassCss = 'paiement-bt-container ' + cssClass.join(' ')

    // add html or not
    const html = addHtmlContent !== undefined ? addHtmlContent : ''

    return `${commonStyle}
    <div class="${addClassCss}" onclick="${fonctions}">
      <div class="paiement-bt-icon">
        <i class="fas ${icon}"></i>
      </div>
      <div class="paiement-bt-text">
        <div>${curencyContent}</div>
        ${html}
        <div class="paiement-bt-total">${getTranslate('total', 'uppercase')} ${total} ${getTranslate('currencySymbol', null, 'methodCurrency')}</div>
      </div>
    </div>`

  } catch (error) {
    console.log('-> paymentBt ${currency},', error)

  }
}