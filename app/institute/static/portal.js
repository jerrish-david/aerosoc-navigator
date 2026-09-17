/* Only progressive interface enhancements live here. Authorization is server-side. */
document.querySelectorAll("form[data-loading]").forEach((form) => {
  form.addEventListener("submit", () => {
    if (!form.checkValidity()) return;
    const button = form.querySelector('button[type="submit"]');
    button.disabled = true;
    button.setAttribute("aria-busy", "true");
    document.querySelector(".navigation-status").textContent =
      form.dataset.loading;
  });
});

document.querySelectorAll('a[href^="/institute/"]').forEach((link) => {
  link.addEventListener("click", (event) => {
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey)
      return;
    document.querySelector(".navigation-status").textContent =
      "Opening your portal…";
  });
});

// Clear pending controls after back/forward navigation; reload private BFCache pages
// so a logged-out session cannot redisplay stale course content.
window.addEventListener("pageshow", (event) => {
  if (event.persisted) {
    window.location.reload();
    return;
  }
  document.querySelectorAll("form[data-loading] button").forEach((button) => {
    button.disabled = false;
    button.removeAttribute("aria-busy");
  });
  document.querySelector(".navigation-status").textContent = "";
});

function timestamp(seconds) {
  const value = Math.floor(Number.isFinite(seconds) ? seconds : 0);
  const hours = Math.floor(value / 3600);
  const minutes = Math.floor((value % 3600) / 60);
  const tail = String(value % 60).padStart(2, "0");
  return hours
    ? `${hours}:${String(minutes).padStart(2, "0")}:${tail}`
    : `${minutes}:${tail}`;
}

document.querySelectorAll("[data-audio-player]").forEach((player) => {
  const audio = player.querySelector("audio");
  const play = player.querySelector("[data-play]");
  const seek = player.querySelector("[data-seek]");
  const volume = player.querySelector("[data-volume]");
  const status = player.querySelector("[data-audio-status]");
  // Same-origin media requests are authorized server-side, including seek ranges.
  audio.addEventListener("loadedmetadata", () => {
    if (!Number.isFinite(audio.duration) || audio.duration <= 0) return;
    [play, seek, volume].forEach((control) => {
      control.disabled = false;
    });
    seek.max = audio.duration;
    const duration = player.querySelector("[data-duration]");
    duration.textContent = timestamp(audio.duration);
    duration.removeAttribute("aria-label");
    status.textContent = "Recording ready.";
  });
  play.addEventListener("click", async () => {
    if (audio.paused) {
      try {
        if (!audio.src && audio.dataset.src) audio.src = audio.dataset.src;
        status.textContent = "Loading recording…";
        await audio.play();
      } catch {
        status.textContent =
          "The recording could not be played. Please try again.";
      }
    } else audio.pause();
  });
  ["play", "pause", "ended"].forEach((event) =>
    audio.addEventListener(event, () => {
      play.setAttribute(
        "aria-label",
        audio.paused ? "Play recording" : "Pause recording",
      );
      play.firstElementChild.textContent = audio.paused ? "▶" : "Ⅱ";
    }),
  );
  audio.addEventListener("timeupdate", () => {
    seek.value = audio.currentTime;
    seek.setAttribute("aria-valuetext", timestamp(audio.currentTime));
    player.querySelector("[data-current]").textContent = timestamp(
      audio.currentTime,
    );
  });
  seek.addEventListener("input", () => {
    audio.currentTime = Number(seek.value);
  });
  volume.addEventListener("input", () => {
    audio.volume = Number(volume.value);
  });
  audio.addEventListener("error", () => {
    [play, seek, volume].forEach((control) => {
      control.disabled = true;
    });
    status.textContent = "Audio is temporarily unavailable.";
  });
});
