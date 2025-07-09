const rfid = new NfcReader() //TODO: import dynamic cordova 
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
    button.innerHTML = 'Mode Jour';
    button.setAttribute('aria-label', 'Activer le mode jour');
  } else {
    button.innerHTML = 'Mode Nuit';
    button.setAttribute('aria-label', 'Activer le mode nuit');
  }
}

function toggleDarkMode() {
  document.body.classList.toggle("dark-mode");
  const elements = document.querySelectorAll(
    ".main-center, .card, .btn-amount, .btn-validate, .btn-clear, .btn-cancel, .btn-toggle-dark-mode"
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
      ".main-center, .card, .btn-amount, .btn-validate, .btn-clear, .btn-cancel, .btn-toggle-dark-mode"
    );
    elements.forEach((el) => el.classList.add("dark-mode"));
  }
  updateDarkModeButton();
});


function readNfc() {
  // listen function for 'nfcResult' message
  function listenTagId(event) {
    console.log('-> event.detail =', event.detail)
    // confirm popup
    Swal.clickConfirm()
    // send tag id
    htmx.ajax('POST', '/htmx/kiosk/refill_with_wisepos/', {
      target: "#tb-kiosque",
      swap: "outerHTML",
      values: { totalAmount, tag_id: event.detail }
    })
  }
  // launch listen for 'nfcResult' message
  document.body.addEventListener('nfcResult', listenTagId)

  if (totalAmount > 0 && window?.DEMO === undefined) {
    Swal.fire({
      title: "Vous avez selectionné " + totalAmount + "€",
      html: "<p>Merci de scanner votre carte TiBillet sur le lecteur Sunmi.</p><p>⬆️⬆️⬆️⬆️⬆️⬆️⬆️</p><p>Le lecteur de carte est juste au dessus de cet écran</p>",
      timer: 30000,
      timerProgressBar: true,
      // after the popup has been shown on screen
      didOpen: () => {
        Swal.showLoading()
        rfid.startLecture()
      },
      // when the popup closes by user
      willClose: () => {
        rfid.stopLecture()
        document.body.removeEventListener('nfcResult', listenTagId)
      }
    })
  }

  if (totalAmount > 0 && window?.DEMO !== undefined) {
    rfid.startLecture({ simulation: true })
  }
}
