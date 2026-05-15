let apiReady = false;
let lastScrapeResult = null;

function addLog(m){ const el = document.getElementById("log"); if(el){ el.innerText += m + "\n"; el.scrollTop = el.scrollHeight; } }

window.addEventListener('pywebviewready', () => {
  apiReady = true;
});

function val(id){ return (document.getElementById(id)?.value || "").trim(); }

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatNumber(value) {
  return new Intl.NumberFormat().format(value ?? 0);
}

function metric(label, value) {
  return `
    <div class="metric">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
    </div>
  `;
}

function renderBars(containerId, items, valueKey, labelKey) {
  const container = document.getElementById(containerId);
  if (!container) return;

  if (!items || items.length === 0) {
    container.innerHTML = `<p class="empty-state">No post data to chart.</p>`;
    return;
  }

  const max = Math.max(...items.map((item) => Number(item[valueKey]) || 0), 1);
  container.innerHTML = items.map((item) => {
    const value = Number(item[valueKey]) || 0;
    const width = Math.max(3, Math.round((value / max) * 100));
    const label = item[labelKey] || "Untitled";

    return `
      <div class="bar-row">
        <div class="bar-label" title="${escapeHtml(label)}">${escapeHtml(label)}</div>
        <div class="bar-track">
          <div class="bar-fill" style="width: ${width}%"></div>
        </div>
        <div class="bar-value">${formatNumber(value)}</div>
      </div>
    `;
  }).join("");
}

function renderAnalytics(result) {
  if (!result?.ok) {
    addLog("❌ " + (result?.error || "Scrape failed."));
    return;
  }

  lastScrapeResult = result;
  const analytics = result.analytics || {};
  const section = document.getElementById("analytics_section");
  const target = document.getElementById("analytics_target");
  const metricsGrid = document.getElementById("metrics_grid");
  const highestPost = document.getElementById("highest_post");

  section?.classList.remove("hidden");
  if (target) {
    target.innerText = `${result.kind === "subreddit" ? "r/" : "u/"}${result.target}`;
  }

  const metrics = [
    metric("Total posts", formatNumber(analytics.total_posts)),
    metric("Total comments", formatNumber(analytics.total_comments)),
    metric("Average score", analytics.average_score ?? 0),
    metric("Median score", analytics.median_score ?? 0),
    metric("Average comments per post", analytics.average_comments_per_post ?? 0)
  ];

  if (analytics.scraped_user_comments !== undefined) {
    metrics.push(metric("User comments scraped", formatNumber(analytics.scraped_user_comments)));
  }

  metricsGrid.innerHTML = metrics.join("");

  const topPost = analytics.highest_scoring_post;
  if (topPost) {
    highestPost.innerHTML = `
      <span>Highest scoring post</span>
      <strong>${escapeHtml(topPost.Title)}</strong>
      <a href="${escapeHtml(topPost.Permalink || topPost.URL)}" target="_blank">${formatNumber(topPost.score)} score</a>
    `;
  } else {
    highestPost.innerHTML = `<span>No highest scoring post yet</span>`;
  }

  renderBars(
    "top_posts_chart",
    (analytics.top_posts || []).map((post) => ({ label: post.Title, value: post.score })),
    "value",
    "label"
  );
  renderBars("frequency_day_chart", analytics.frequency?.day || [], "count", "label");
  renderBars("frequency_week_chart", analytics.frequency?.week || [], "count", "label");
  renderBars("frequency_month_chart", analytics.frequency?.month || [], "count", "label");
  renderDataTables(result);

  section?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderDataTables(result) {
  const posts = result.posts || [];
  const comments = result.comments || [];
  const postsBody = document.getElementById("posts_table_body");
  const commentsBody = document.getElementById("comments_table_body");
  const postCount = document.getElementById("post_count_label");
  const commentCount = document.getElementById("comment_count_label");
  const commentsBlock = document.getElementById("comments_data_block");
  const dataTables = document.getElementById("data_tables");
  const toggleButton = document.getElementById("toggle_posts_button");

  if (postCount) postCount.innerText = `${formatNumber(posts.length)} posts`;
  if (commentCount) commentCount.innerText = `${formatNumber(comments.length)} comments`;

  if (postsBody) {
    postsBody.innerHTML = posts.map((post) => `
      <tr>
        <td>${escapeHtml(post.Title)}</td>
        <td>${formatNumber(post.score)}</td>
        <td>${formatNumber(post.num_comments)}</td>
        <td>${escapeHtml(post.Created || "")}</td>
        <td><a href="${escapeHtml(post.Permalink || post.URL)}" target="_blank">Open</a></td>
      </tr>
    `).join("");
  }

  if (commentsBlock) {
    commentsBlock.classList.toggle("hidden", comments.length === 0);
  }

  if (commentsBody) {
    commentsBody.innerHTML = comments.map((comment) => `
      <tr>
        <td>${escapeHtml(comment["Comment Body"])}</td>
        <td>${escapeHtml(comment.Subreddit)}</td>
        <td>${formatNumber(comment.Score)}</td>
        <td><a href="${escapeHtml(comment["Comment URL"])}" target="_blank">Open</a></td>
      </tr>
    `).join("");
  }

  dataTables?.classList.add("hidden");
  if (toggleButton) toggleButton.innerText = comments.length ? "Show all posts/comments" : "Show all posts";
}

function toggleDataTables() {
  const dataTables = document.getElementById("data_tables");
  const toggleButton = document.getElementById("toggle_posts_button");
  if (!dataTables || !toggleButton) return;

  const willShow = dataTables.classList.contains("hidden");
  dataTables.classList.toggle("hidden", !willShow);
  toggleButton.innerText = willShow ? "Hide data" : (lastScrapeResult?.comments?.length ? "Show all posts/comments" : "Show all posts");
}

async function downloadResults() {
  const button = document.getElementById("download_button");
  if (!lastScrapeResult) {
    addLog("❌ Run a scrape before downloading.");
    return;
  }

  try {
    if (button) {
      button.disabled = true;
      button.innerText = "Downloading...";
    }
    const result = await pywebview.api.download_last_scrape();
    if (result?.ok) {
      addLog("✅ Download finished.");
    } else {
      addLog("❌ " + (result?.error || "Download failed."));
    }
  } catch (e) {
    addLog("❌ download failed: " + (e?.message || e));
  } finally {
    if (button) {
      button.disabled = false;
      button.innerText = "Download";
    }
  }
}

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
  const result = await pywebview.api.scrape_user(
    val("user_target"),
    parseInt(val("user_limit"), 10) || 25
  );
  renderAnalytics(result);
  if (result?.ok) addLog("✅ User scrape complete.");
}

async function scrapeSubreddit() {
  addLog("Scraping subreddit...");
  const result = await pywebview.api.scrape_subreddit(
    val("subreddit"),
    parseInt(val("sub_limit"), 10) || 25,
    val("time_filter")
  );
  renderAnalytics(result);
  if (result?.ok) addLog("✅ Subreddit scrape complete.");
}

async function checkUpdates() {
  const res = await pywebview.api.check_updates();
  if (res.update) {
    addLog("Update available: " + res.latest);
    addLog("Opening download page…");
    await pywebview.api.open_url(res.url);
  } else {
    addLog("You’re up to date.");
  }
}
