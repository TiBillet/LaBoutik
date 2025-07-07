const rfid = new Nfc()
let totalAmount = 0;

function goBack() {
  window.history.back();
}

function selectAmount(amount) {
  totalAmount += amount;
  document.getElementById("totalAmount").textContent = `${totalAmount}`;
}

function validateAmount() {
  if (totalAmount > 0) {
    localStorage.setItem("selectedAmount", totalAmount);
    return true;
  } else {
    alert("Veuillez sélectionner un montant.");
    return false;
  }
}

function selectPaymentMethod(method) {
  localStorage.setItem("paymentMethod", method);

  if (method === "Carte bancaire") {
    window.location.href = "confirmationCB.html";
  } else if (method === "Espèces") {
    window.location.href = "confirmationCash.html";
  }
}

function clearAmount() {
  totalAmount = 0;
  document.getElementById("totalAmount").textContent = `${totalAmount}`;
  localStorage.removeItem("selectedAmount");
}

document.addEventListener("DOMContentLoaded", function () {
  const selectedAmount = localStorage.getItem("selectedAmount");
  const paymentMethod = localStorage.getItem("paymentMethod");

  if (selectedAmount && paymentMethod) {
    document.getElementById("selectedAmount").textContent = selectedAmount;
    document.getElementById("paymentMethod").textContent = paymentMethod;
  }
});

function updateDarkModeButton() {
  const button = document.getElementById("toggleDarkModeBtn");
  if (document.body.classList.contains("dark-mode")) {
    button.innerHTML = 'Mode Jour <i class="fas fa-sun"></i>';
  } else {
    button.innerHTML = 'Mode Nuit <i class="fas fa-moon"></i>';
  }
}

function toggleDarkMode() {
  document.body.classList.toggle("dark-mode");
  const elements = document.querySelectorAll(
    ".logo-header, .logo-footer, .main-center, .card-panel, .card-panel-blink, .card-panel-currentAmount, .btn-cbcash, .btn-validate, .btn-large, .btn-back, .btn-clear"
  );
  elements.forEach((el) => el.classList.toggle("dark-mode"));

  if (document.body.classList.contains("dark-mode")) {
    localStorage.setItem("theme", "dark");
  } else {
    localStorage.setItem("theme", "light");
  }
  updateDarkModeButton();
}

document.addEventListener("DOMContentLoaded", function () {
  const theme = localStorage.getItem("theme");
  if (theme === "dark") {
    document.body.classList.add("dark-mode");
    const elements = document.querySelectorAll(
      ".logo-header, .logo-footer, .main-center, .card-panel, .card-panel-blink, .card-panel-currentAmount, .btn-cbcash, .btn-validate, .btn-large, .btn-back, .btn-clear"
    );
    elements.forEach((el) => el.classList.add("dark-mode"));
  }
  updateDarkModeButton();
});

function sendTagId(data) {
  console.log('-> sendTagId, data =', data)
}

function readNfc() {
  console.log('-> readNfc totalAmount =', totalAmount, '  --  DEMO =', window.DEMO)
  if (totalAmount > 0) {
    Swal.fire({
      title: "Vous avez selectionné " + totalAmount + "€",
      html: "<p>Merci de scanner votre carte TiBillet sur le lecteur Sunmi.</p><p>⬆️⬆️⬆️⬆️⬆️⬆️⬆️</p><p>Le lecteur de carte est juste au dessus de cet écran</p>",
      timer: 30000,
      timerProgressBar: true,
      // after the popup has been shown on screen
      didOpen: () => {
        Swal.showLoading()
        rfid.initModeLectureNfc()
        rfid.muteEtat('message','')
        rfid.muteEtat('callbackOk', sendTagId)
        rfid.muteEtat('tagIdIdentite', 'cm')
        rfid.lireTagId()

      },
      // uns when the popup closes by user
      willClose: () => {
      }
    }).then((result) => {
      // Read more about handling dismissals below 
      if (result.dismiss === Swal.DismissReason.timer) {
        clearAmount();
        console.log("I was closed by the timer");
      } else {
        console.log("I was closed");
        if (window.DEMO !== undefined) { }
        this.tagId = "{{ DEMO_TAGID_CLIENT1 }}"
        console.log(this.tagId)
        htmx.trigger(this, `confirmed`);
      }
    })
  }
}