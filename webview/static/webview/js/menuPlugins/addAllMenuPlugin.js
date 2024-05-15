// add the folder name of your new menu plugin, the array index gives the display order
const listMenuToAdd = ['pettyCash', 'closeAccounts', 'changeLanguage']
window.menuAddHtmlFragment = ''

window.addPluginFunctionsToMenu = function () {
  return menuAddHtmlFragment
}

listMenuToAdd.forEach(async (plug) => {
  const { menu } = await import("./" + plug + "/index.js")
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
      console.log('posX =', posX)
      console.log('posY =', posY)
      if (data.inverse) {
        stateInverse = ' fa-inverse'
      }
      if(data.color) {
        color = `color: ${data.color};`
      }
      const style = `style="${color}position:absolute;left:${posX};top:${posY};font-size:${data.size}rem;"`
      console.log('style =', style)
      visual += `<i class="${data.icon} ${stateInverse}" ${style}></i>`
    })
    visual += `</span>`
  }
  
  menuAddHtmlFragment += `<div class="menu-burger-item BF-ligne-deb${addClass}" onclick="${menu.func}();">
   ${visual}
    <div data-i8n="${menu.i8nIndex}"></div>
  </div>`
})