(function () {
  "use strict";

  const root = document.querySelector("[data-global-chat]");
  if (!root) {
    return;
  }

  const thread = root.querySelector("#global-chat-thread");
  const status = root.querySelector("[data-chat-poll-status]");
  const messagesUrl = root.dataset.messagesUrl;
  let cursor = root.dataset.chatCursor;
  let timer = null;
  let requestInFlight = false;
  let stopped = false;
  let retryDelay = 2000;
  const MAX_RENDERED_MESSAGES = 200;

  const knownMessageIds = new Set();
  thread.querySelectorAll("[data-chat-message-id]").forEach(function (node) {
    knownMessageIds.add(node.dataset.chatMessageId);
  });

  function setStatus(message) {
    status.textContent = message;
  }

  function schedule(delay) {
    if (stopped || document.hidden) {
      return;
    }
    if (timer !== null) {
      window.clearTimeout(timer);
    }
    timer = window.setTimeout(poll, delay);
  }

  function appendMessage(message) {
    const id = String(message.id);
    if (!Number.isSafeInteger(message.id) || message.id < 1 || knownMessageIds.has(id)) {
      return;
    }
    if (
      typeof message.sender !== "string" ||
      typeof message.body !== "string" ||
      typeof message.created_at !== "string" ||
      typeof message.display_time !== "string" ||
      typeof message.is_own !== "boolean"
    ) {
      return;
    }

    const empty = thread.querySelector("[data-chat-empty]");
    if (empty) {
      empty.remove();
    }

    const row = document.createElement("article");
    row.className = message.is_own ? "message-row message-own" : "message-row";
    row.dataset.chatMessageId = id;

    const avatar = document.createElement("span");
    avatar.className = "message-avatar";
    avatar.setAttribute("aria-hidden", "true");
    avatar.textContent = message.sender.slice(0, 1).toUpperCase();

    const block = document.createElement("div");
    block.className = "message-block";

    const sender = document.createElement("span");
    sender.className = "message-sender";
    sender.textContent = message.is_own ? "나" : message.sender;

    const body = document.createElement("p");
    body.textContent = message.body;

    const time = document.createElement("time");
    time.dateTime = message.created_at;
    time.textContent = message.display_time;

    block.append(sender, body, time);
    row.append(avatar, block);
    thread.append(row);
    knownMessageIds.add(id);

    const rows = thread.querySelectorAll("[data-chat-message-id]");
    const excess = rows.length - MAX_RENDERED_MESSAGES;
    for (let index = 0; index < excess; index += 1) {
      knownMessageIds.delete(rows[index].dataset.chatMessageId);
      rows[index].remove();
    }
  }

  async function poll() {
    timer = null;
    if (stopped || document.hidden) {
      return;
    }
    if (requestInFlight) {
      schedule(2000);
      return;
    }

    requestInFlight = true;
    let nextDelay = 2000;
    try {
      const url = new URL(messagesUrl, window.location.origin);
      url.searchParams.set("cursor", cursor);
      url.searchParams.set("limit", "50");
      const response = await window.fetch(url.toString(), {
        method: "GET",
        credentials: "same-origin",
        cache: "no-store",
        headers: { Accept: "application/json" },
      });

      if (response.redirected || response.status === 401 || response.status === 403) {
        stopped = true;
        setStatus("로그인 상태를 확인한 뒤 페이지를 새로고침해 주세요.");
        return;
      }
      if (response.status === 429) {
        const retryAfter = Number.parseInt(response.headers.get("Retry-After"), 10);
        retryDelay = Number.isFinite(retryAfter)
          ? Math.max(2000, retryAfter * 1000)
          : Math.min(Math.max(retryDelay * 2, 4000), 30000);
        setStatus("요청이 많아 자동 갱신을 잠시 늦춥니다.");
        nextDelay = retryDelay;
        return;
      }
      if (!response.ok) {
        throw new Error("chat polling failed");
      }

      const payload = await response.json();
      if (
        !payload ||
        !Array.isArray(payload.messages) ||
        typeof payload.next_cursor !== "string" ||
        typeof payload.has_more !== "boolean"
      ) {
        throw new Error("invalid chat payload");
      }

      payload.messages.forEach(appendMessage);
      cursor = payload.next_cursor;
      root.dataset.chatCursor = cursor;
      retryDelay = 2000;
      nextDelay = payload.has_more ? 750 : 2000;
      setStatus(payload.messages.length > 0 ? "새 메시지를 불러왔습니다." : "");
      if (payload.messages.length > 0) {
        thread.scrollTop = thread.scrollHeight;
      }
    } catch (error) {
      retryDelay = Math.min(Math.max(retryDelay * 2, 4000), 30000);
      nextDelay = retryDelay;
      setStatus("네트워크 연결을 확인하고 있습니다. 자동으로 다시 시도합니다.");
    } finally {
      requestInFlight = false;
      schedule(nextDelay);
    }
  }

  document.addEventListener("visibilitychange", function () {
    if (document.hidden) {
      if (timer !== null) {
        window.clearTimeout(timer);
        timer = null;
      }
      return;
    }
    retryDelay = 2000;
    schedule(0);
  });

  schedule(2000);
})();
