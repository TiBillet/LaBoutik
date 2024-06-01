function listen_card() {
    const inputElement = document.getElementById('given_card');
    // Create a new div element to display the input value
    const displayDiv = document.createElement('div');
    displayDiv.textContent = inputElement.value;
    // Append the new div to the body of the document
    document.body.appendChild(displayDiv);
}