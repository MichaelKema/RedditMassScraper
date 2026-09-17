const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

function setup(generate) {
  const elements = new Map();
  const context = vm.createContext({
    window: { addEventListener: (_, fn) => fn() },
    document: { getElementById: (id) => {
      if (!elements.has(id)) elements.set(id, {
        textContent: "", disabled: false, setAttribute() {},
        set innerHTML(_) { throw new Error("Overview must not render HTML"); }
      });
      return elements.get(id);
    } },
    pywebview: { api: { generate_overview: generate } }
  });
  vm.runInContext(fs.readFileSync(path.join(__dirname, "..", "index.js"), "utf8"), context);
  vm.runInContext('lastScrapeResult = {scrape_id: "one", posts: [{}], comments: []}; resetOverview();', context);
  return { context, elements };
}

test("renders model output only as text and prevents duplicate clicks", async () => {
  let calls = 0;
  const { context, elements } = setup(async (id) => {
    calls++;
    assert.equal(id, "one");
    return { ok: true, overview: '<script>alert("unsafe")</script>', coverage: { sampled_posts: 1, sampled_comments: 0 } };
  });
  await vm.runInContext("generateOverview()", context);
  assert.equal(elements.get("overview_text").textContent, '<script>alert("unsafe")</script>');
  await vm.runInContext("generateOverview()", context);
  assert.equal(calls, 1);
  assert.equal(elements.get("overview_button").disabled, true);
});

test("old responses do not overwrite a new scrape", async () => {
  let finish;
  const { context, elements } = setup(() => new Promise(resolve => { finish = resolve; }));
  const pending = vm.runInContext("generateOverview()", context);
  vm.runInContext('lastScrapeResult = {scrape_id: "two", posts: [{}], comments: []}; resetOverview();', context);
  finish({ ok: true, overview: "Outdated summary", coverage: { sampled_posts: 1, sampled_comments: 0 } });
  await pending;
  assert.equal(elements.get("overview_text").textContent, "");
  assert.equal(elements.get("overview_button").disabled, false);
});

test("failure restores button and does not display raw bridge exception", async () => {
  const { context, elements } = setup(async () => { throw new Error("potential-secret"); });
  await vm.runInContext("generateOverview()", context);
  assert.equal(elements.get("overview_button").disabled, false);
  assert.equal(elements.get("overview_status").textContent.includes("potential-secret"), false);
});

test("empty scrape disables generation", () => {
  const { context, elements } = setup(() => { throw new Error("must not call"); });
  vm.runInContext('lastScrapeResult = {scrape_id: "empty", posts: [], comments: []}; resetOverview();', context);
  assert.equal(elements.get("overview_button").disabled, true);
});

test("subreddit errors appear next to the form and in the log", async () => {
  const { context, elements } = setup(() => {});
  context.pywebview.api.scrape_subreddit = async () => ({ ok: false, error: "Subreddit not found. Check the spelling and try again." });
  await vm.runInContext("scrapeSubreddit()", context);
  assert.match(elements.get("subreddit_error").textContent, /Check the spelling/);
  assert.match(elements.get("log").innerText, /Check the spelling/);
  assert.equal(vm.runInContext("lastScrapeResult.scrape_id", context), "one");
});

test("unexpected subreddit bridge rejection shows a safe error", async () => {
  const { context, elements } = setup(() => {});
  context.pywebview.api.scrape_subreddit = async () => { throw new Error("secret"); };
  await vm.runInContext("scrapeSubreddit()", context);
  assert.match(elements.get("subreddit_error").textContent, /Could not scrape/);
  assert.doesNotMatch(elements.get("log").innerText, /secret/);
});
