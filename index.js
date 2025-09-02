let apiReady = false;

function addLog(m){ const el = document.getElementById("log"); if(el){ el.innerText += m + "\n"; el.scrollTop = el.scrollHeight; } }

window.addEventListener('pywebviewready', () => {
  apiReady = true;
  addLog('pywebview ready');
});

function val(id){ return (document.getElementById(id)?.value || "").trim(); }

async function checkCredentials() {
  const client_id     = val("client_id");
  const client_secret = val("client_secret");
  const username      = val("username");

  if (!client_id || !client_secret || !username) {
    addLog("❌ Please fill in Client ID, Client Secret, and Username.");
    document.getElementById("result").innerText = "❌ Missing required fields";
    return;
  }

  try {
    addLog("Checking credentials…");
    const res = await pywebview.api.check_credentials(client_id, client_secret, username);
    const ok = typeof res === "boolean" ? res : !!res?.ok;

    if (ok) {
      document.getElementById("result").innerText = "✅ Valid credentials";
      document.getElementById("credentials_section").classList.add("hidden");
      document.getElementById("mode_section").classList.remove("hidden");
      addLog("Credentials valid. Mode selector shown.");
    } else {
      const msg = (res && res.error) ? res.error : "Invalid credentials";
      document.getElementById("result").innerText = "❌ " + msg;
      addLog("❌ " + msg);
    }
  } catch (e) {
    addLog("❌ check_credentials failed: " + (e?.message || e));
  }
}



function showUser() {
  document.getElementById("mode_section").classList.add("hidden");
  document.getElementById("user_section").classList.remove("hidden");
  addLog("User mode selected.");
}

function showSubreddit() {
  document.getElementById("mode_section").classList.add("hidden");
  document.getElementById("subreddit_section").classList.remove("hidden");
  addLog("Subreddit mode selected.");
}

function goBack() {
  document.getElementById("user_section").classList.add("hidden");
  document.getElementById("subreddit_section").classList.add("hidden");
  document.getElementById("mode_section").classList.remove("hidden");
  addLog("Went back to mode selection.");
}

async function scrapeUser() {
  addLog("Scraping user...");
  await pywebview.api.scrape_user(
    document.getElementById("user_target").value,
    parseInt(document.getElementById("user_limit").value)
  );
  addLog("✅ User scrape complete.");
}

async function scrapeSubreddit() {
  addLog("Scraping subreddit...");
  await pywebview.api.scrape_subreddit(
    document.getElementById("subreddit").value,
    parseInt(document.getElementById("sub_limit").value),
    document.getElementById("time_filter").value
  );
  addLog("✅ Subreddit scrape complete.");
}
