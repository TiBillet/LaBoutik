// add the folder name of your new menu plugin, the array index gives the display order
// const listMenuToAdd = ['pettyCash', 'closeAccounts', 'changeLanguage', 'allOrders', 'testLcd']
const listMenuToAdd = ['allOrders', 'settings']
window.menuAddHtmlFragment = ''

window.addPluginFunctionsToMenu = function () {
  return menuAddHtmlFragment
}

listMenuToAdd.forEach(async (plug) => {
  // plugin import
  const { menu } = await import("./" + plug + "/index.js")
  let activateMenu = true

  // ajoute l'item menu si les conditions sont à "true"
  if (menu.conditions !== undefined) {
    // lance la liste de conditions
    for (let i = 0; i < menu.conditions.length; i++) {
      const condition = menu.conditions[i]
      try {
        activateMenu = await window[condition]()
      } catch (error) {
        console.log(`addAllMenuPlugin.js, la fonction condition = "${condition}" n'existe pas !`)
      }
    }
  }

  if (activateMenu === true) {
    let addClass = ''
    if (menu.testClass !== undefined) {
      addClass = ' ' + menu.testClass
    }
    let visual = ''
    if (menu.icon) {
      visual = ` <i class="${menu.icon}"></i>`
    }
    if (menu.icons) {
      visual = `<span class="fa-stack">`
      menu.icons.forEach((data) => {
        let stateInverse = '', color = ''
        const posX = data.posX !== undefined ? data.posX : 0
        const posY = data.posY !== undefined ? data.posY : 0
        if (data.inverse) {
          stateInverse = ' fa-inverse'
        }
        if (data.color) {
          color = `color: ${data.color};`
        }
        const style = `style="${color}position:absolute;left:${posX};top:${posY};font-size:${data.size}rem;"`
        visual += `<i class="${data.icon} ${stateInverse}" ${style}></i>`
      })
      visual += `</span>`
    }

    menuAddHtmlFragment += `<div class="menu-burger-item BF-ligne-deb${addClass}" onclick="${menu.func}();">
   ${visual}
    <div data-i8n="${menu.i8nIndex}"></div>
  </div>`
  }
})