// THEME TOGGLE FUNCTIONALITY
document.addEventListener('DOMContentLoaded', () => {
    const toggleButton = document.getElementById('theme-toggle');
    const iconSun = document.getElementById('icon-sun');
    const iconMoon = document.getElementById('icon-moon');
    const body = document.body;

    // Function to switch to dark mode
    const enableDarkMode = () => {
        body.classList.add('light-theme');
        iconSun.style.display = 'block';  // Show sun icon
        iconMoon.style.display = 'none';  // Hide moon icon
        localStorage.setItem('theme', 'dark');  // Store user preference
    };

    // Function to switch to light mode
    const disableDarkMode = () => {
        body.classList.remove('light-theme');
        iconSun.style.display = 'none';  // Hide sun icon
        iconMoon.style.display = 'block';  // Show moon icon
        localStorage.setItem('theme', 'light');  // Store user preference
    };

    // Check user preference on page load
    const currentTheme = localStorage.getItem('theme');
    if (currentTheme === 'dark') {
        enableDarkMode();  // Apply dark mode if user prefers it
    } else {
        disableDarkMode();  // Default to light mode
    }

    // Toggle theme on button click
    toggleButton.addEventListener('click', () => {
        if (body.classList.contains('light-theme')) {
            disableDarkMode();  // Switch to light mode
        } else {
            enableDarkMode();  // Switch to dark mode
        }
    });
});


// Link popup functionality

// Open the popup
function openPopup() {
    const popup = document.getElementById('linksPopup');
    popup.style.display = 'block';
}

// Close the popup
function closePopup() {
    const popup = document.getElementById('linksPopup');
    popup.style.display = 'none';
}

// Make the popup draggable
let isDragging = false;
let offsetX, offsetY;

const popup = document.getElementById('linksPopup');
const popupHeader = popup.querySelector('.popup-header');

popupHeader.addEventListener('mousedown', (e) => {
    isDragging = true;
    offsetX = e.clientX - popup.offsetLeft;
    offsetY = e.clientY - popup.offsetTop;
    popup.classList.add('dragging');
});

document.addEventListener('mousemove', (e) => {
    if (isDragging) {
        popup.style.left = `${e.clientX - offsetX}px`;
        popup.style.top = `${e.clientY - offsetY}px`;
    }
});

document.addEventListener('mouseup', () => {
    isDragging = false;
    popup.classList.remove('dragging');
});



document.addEventListener('DOMContentLoaded', () => {
    // Your existing code here
    // Preload sounds
    const sounds = {
        click: new Audio("/assets/sounds/open.mp3"),
        close: new Audio("/assets/sounds/close.mp3"),
        redirect: new Audio("/assets/sounds/swoosh.mp3"),
        light: new Audio("/assets/sounds/light.mp3"),
        dark: new Audio("/assets/sounds/dark.mp3"),
    };

    // Helper function to play the appropriate sound
    function playSoundForClass(element) {
        if (element.classList.contains("play-click")) {
            sounds.click.play();
        } else if (element.classList.contains("play-close")) {
            sounds.close.play();
        } else if (element.classList.contains("play-redirect")) {
            sounds.redirect.play();
        } else if (element.classList.contains("play-light")) {
            sounds.light.play();
        } else if (element.classList.contains("play-dark")) {
            sounds.dark.play();
        }
    }

    // Add event listener for elements with sound classes
    document.querySelectorAll(".play-click, .play-close, .play-redirect, .play-light, .play-dark").forEach(element => {
        element.addEventListener("click", () => {
            playSoundForClass(element);
        });
    });
});

