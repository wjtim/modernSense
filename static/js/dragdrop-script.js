const dragArea = document.getElementById("drag-area");
const fileInput = document.getElementById("file-input");
const dragText = document.getElementById("drag-text");

// Handle drag over event
dragArea.addEventListener("dragover", (e) => {
    e.preventDefault();
    dragArea.classList.add("dragover");
    dragText.textContent = "You're almost there! Drop to upload your file.";
});

dragArea.addEventListener("dragleave", () => {
    dragArea.classList.remove("dragover");
    dragText.textContent = "Drop your file here or click below to select. Let’s analyze some data together!";
});

// Handle file drop event
dragArea.addEventListener("drop", (e) => {
    e.preventDefault();
    dragArea.classList.remove("dragover");

    const files = e.dataTransfer.files;
    if (files.length) {
        fileInput.files = files;  // Set the file input with the dropped files
        dragArea.classList.add("file-selected"); // Add file-selected styling
        dragText.textContent = `Great choice! Ready to analyze: ${files[0].name}`;
    }
});

// Handle file selection through the button
fileInput.addEventListener("change", (e) => {
    const file = fileInput.files[0];
    if (file) {
        dragText.textContent = `File selected: ${file.name}`;
        dragArea.classList.add("file-selected"); // Add file-selected styling
    }
});