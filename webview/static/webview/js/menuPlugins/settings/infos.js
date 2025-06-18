/**
 * Show setting infos UI
 */
window.settingsShowInfos = function () {
  // changer titre
  vue_pv.asignerTitreVue(`<span data-i8n="settings,capitalize">Paramètres</span> - <span data-i8n="infos",capitalize">Infos</span>`)

  const style = `
  <style>
    .settings-info-line {
      width: 99%;
      min-height: 80px;
      border-bottom: 1px solid var(--gris04);
      margin-bottom: 16px;
    }
  </style>`

  const template = `
  <div class="BF-col-deb l100p h100p" style="font-size: 1.5rem">
    <div class="BF-col settings-info-line">
      <label class="md16px">Server</label>
      <div>${glob.appConfig.current_server}</div>
    </div>
    <div class="BF-col settings-info-line">
      <label class="md16px">User</label>
      <div>${glob.appConfig.client.username}</div>
    </div>
    <div class="BF-col settings-info-line">
      <label class="md16px">LaBoutik Ip</label>
      <div>${glob.appConfig.ip}</div>
    </div>
    <div class="BF-col settings-info-line">
      <label class="md16px">LaBoutik version</label>
      <div>${glob.appConfig.versionApk}</div>
    </div>
  </div>`

  document.querySelector('.content-settings').innerHTML = style + template
}
