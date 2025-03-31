/**
 *  An `object` called `currencyObject`
 *
 * @typedef {Object} currencyObject
 * @property {String} name The currency name
 * @property {String} symbol The currency symbol
 * @property {String} country The country name
 * @property {String} htmlEntity html entity
 */

const currencysList = [
  {
    name: 'euro',
    symbol: '€',
    country: [
      "Union européenne",
      "Allemagne",
      "Autriche",
      "Belgique",
      "Chypre",
      "Croatie",
      "Espagne",
      "Finlande",
      "France",
      "Grèce",
      "Irlande",
      "Italie",
    ],
    htmlContent: '&#8364;'
  },
  {
    name: 'lek',
    symbol: 'L',
    country: 'Albania',
    htmlContent: '&#76;'
  },
  {
    name: 'dirham',
    symbol: 'MAD',
    country: 'Morocco',
    // htmlContent: '&#77;&#65;&#68;'
    // htmlContent: 'DH<span itemprop="priceCurrency" content="MAD"></span>'
    // htmlContent: '<span style="margin-left:2px;font-weight:bold;">&#x62f;&#x2e;&#x625;</span>'
    htmlContent: '&#x62f;&#x2e;&#x625;'
  },
  {
    name: 'dollar',
    symbol: '$',
    country: 'America',
    htmlContent: '&#36;'
  },
  {
    name: 'British Pound Sterling',
    symbol: '£',
    country: 'England',
    htmlContent: '&#163;'
  },
]

/**
 * Métode pour bypasser la traduction
 * Retourne un string représentant la monnaie d'un pays
 * @param {String} option - option de traduction : capitalize, uppercase
 * @returns {String} - resultat de la traduction
 */
window.methodCurrency = (option) => {
  let result = ''
  const currency = glob.currencyData
  if (currency.htmlContent !== undefined) {
    result = currency.htmlContent
  } else {
    result = currency.symbol
  }
  // option exist
  if (option !== undefined && option !== null && typeof (option) === 'string') {

    if (option.includes('capitalize')) {
      result = result.charAt(0).toUpperCase() + result.slice(1)
    }

    if (option.includes('uppercase')) {
      result = result.toUpperCase()
    }
  }
  return result
}

/**
 * Retourne un object(name/symbol/country/htmlEntity) en fonction d'un pays donné
 * @param {Object} data - pays sélectionné
 * @param {String} data.name - nom de la monnaie
 * @param {String} data.country - nom du pays
 * @returns {currencyObject}
 */
export function getCurrentCurrency(data) {
  // console.log('getCurrentCurrency, data=', data)
  const result = currencysList.find(item => {
    const countryChoice = data.country.toLowerCase()
    // lower case
    if (typeof (item.country) === 'string') {
      item.country = item.country.toLowerCase()
    } else {
      item.country.forEach((country, index) => {
        item.country[index] = country.toLowerCase()
      })
    }
    if (item.country === countryChoice || item.country.includes(countryChoice)) {
      return item
    }
  })
  return result
}