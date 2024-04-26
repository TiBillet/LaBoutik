// add the folder name of your new menu plugin, the array index gives the display order
const listMenuToAdd = ['pettyCash', 'closeAccounts', 'changeLanguage']
window.menuAddHtmlFragment = ''

window.addPluginFunctionsToMenu = function () {
  return menuAddHtmlFragment
}

listMenuToAdd.forEach(async (plug) => {
  const { menu } = await import("./" + plug + "/index.js")
  menuAddHtmlFragment += `<div class="menu-burger-item BF-ligne-deb" onclick="${menu.func}();">
    <i class="${menu.icon}"></i>
    <div data-i8n="${menu.i8nIndex}"></div>
  </div>`
})