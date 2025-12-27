document.addEventListener("DOMContentLoaded", () => {
  const searchInput = document.getElementById("search-input");
  const voiceBtn = document.getElementById("voice-btn");
  const lensBtn = document.getElementById("lens-btn");

  if (!searchInput) return; // Stop if page has no search bar

  // 🎤 Voice Search
  if (voiceBtn && "webkitSpeechRecognition" in window) {
    const recognition = new webkitSpeechRecognition();
    recognition.lang = "en-IN";
    recognition.onresult = (event) => {
      searchInput.value = event.results[0][0].transcript;
      console.log("Voice input:", searchInput.value);
    };
    voiceBtn.addEventListener("click", () => recognition.start());
  }

  // 📷 Lens (demo feature)
  if (lensBtn) {
    lensBtn.addEventListener("click", () => {
      alert("Lens feature: Soon you can upload/scan crop images for disease detection!");
    });
  }
});
