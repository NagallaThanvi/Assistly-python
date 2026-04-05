document.addEventListener("DOMContentLoaded", () => {
    const root = document.documentElement;
    const body = document.body;
    const themeToggle = document.getElementById("themeToggle");
    const a11yToggle = document.getElementById("a11yToggle");
    const topbar = document.querySelector(".app-topbar");
    const storedTheme = localStorage.getItem("assistly-theme");
    const storedA11y = localStorage.getItem("assistly-accessibility");
    const prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
    const initialTheme = storedTheme || (prefersDark ? "dark" : "light");
    const initialA11y = storedA11y || "default";

    function applyTheme(theme) {
        root.setAttribute("data-theme", theme);
        if (themeToggle) {
            const icon = themeToggle.querySelector("i");
            const label = themeToggle.querySelector("span");
            if (icon) {
                icon.className = theme === "dark" ? "bi bi-moon-stars-fill" : "bi bi-sun-fill";
            }
            if (label) {
                label.textContent = theme === "dark" ? "Dark" : "Light";
            }
        }
        window.dispatchEvent(new CustomEvent("assistly:theme-changed", { detail: { theme } }));
    }

    applyTheme(initialTheme);

    function applyAccessibility(mode) {
        body.classList.remove("a11y-default", "a11y-large-text", "a11y-high-contrast");
        body.classList.add(`a11y-${mode}`);
        if (a11yToggle) {
            const label = a11yToggle.querySelector("span");
            if (label) {
                const text = mode === "large-text" ? "Large Text" : mode === "high-contrast" ? "High Contrast" : "Accessibility";
                label.textContent = text;
            }
        }
        window.dispatchEvent(new CustomEvent("assistly:accessibility-changed", { detail: { mode } }));
    }

    applyAccessibility(initialA11y);

    function syncTopbarState() {
        if (!topbar) return;
        topbar.classList.toggle("scrolled", window.scrollY > 6);
    }

    syncTopbarState();
    window.addEventListener("scroll", syncTopbarState, { passive: true });

    const revealTargets = document.querySelectorAll(
        ".hero-box, .hero-panel, .section-card, .request-card, .stats-card, .kpi-card, .compact-list-item, .table-responsive"
    );
    revealTargets.forEach((node) => node.classList.add("reveal-item"));

    if ("IntersectionObserver" in window) {
        const observer = new IntersectionObserver(
            (entries) => {
                for (const entry of entries) {
                    if (entry.isIntersecting) {
                        entry.target.classList.add("revealed");
                        observer.unobserve(entry.target);
                    }
                }
            },
            { threshold: 0.08, rootMargin: "0px 0px -8% 0px" }
        );
        revealTargets.forEach((node) => observer.observe(node));
    } else {
        revealTargets.forEach((node) => node.classList.add("revealed"));
    }

    const tiltTargets = document.querySelectorAll(".request-card, .section-card, .stats-card");
    const prefersReducedMotion =
        window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    if (!prefersReducedMotion) {
        tiltTargets.forEach((el) => {
            el.classList.add("tilt-card");

            el.addEventListener("pointermove", (event) => {
                if (window.innerWidth < 992) return;
                const rect = el.getBoundingClientRect();
                const px = (event.clientX - rect.left) / rect.width;
                const py = (event.clientY - rect.top) / rect.height;
                const rotateX = (0.5 - py) * 2.2;
                const rotateY = (px - 0.5) * 2.2;
                el.style.transform = `perspective(900px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateY(-3px)`;
            });

            el.addEventListener("pointerleave", () => {
                el.style.transform = "";
            });
        });
    }

    const buttons = document.querySelectorAll(".btn");
    buttons.forEach((btn) => {
        btn.addEventListener("pointerdown", (event) => {
            const rect = btn.getBoundingClientRect();
            const x = ((event.clientX - rect.left) / rect.width) * 100;
            const y = ((event.clientY - rect.top) / rect.height) * 100;
            btn.style.setProperty("--ripple-x", `${x}%`);
            btn.style.setProperty("--ripple-y", `${y}%`);
            btn.classList.remove("ripple");
            window.requestAnimationFrame(() => btn.classList.add("ripple"));
        });

        btn.addEventListener("animationend", () => {
            btn.classList.remove("ripple");
        });
    });

    if (body) {
        body.classList.add("motion-ready");
    }

    const counterNodes = document.querySelectorAll(".kpi-value, .metric");
    const prefersLiteMotion =
        window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    function runCounter(node) {
        const source = (node.textContent || "").trim();
        const matched = source.match(/-?\d+(?:\.\d+)?/);
        if (!matched) {
            node.classList.add("counter-ready");
            return;
        }

        const value = Number(matched[0]);
        if (Number.isNaN(value)) {
            node.classList.add("counter-ready");
            return;
        }

        const hasPercent = source.includes("%");
        const hasStar = source.includes("★");
        const prefix = source.slice(0, matched.index || 0);
        const suffix = source.slice((matched.index || 0) + matched[0].length);
        const duration = Math.min(1100, 500 + Math.abs(value) * 22);
        const start = performance.now();

        function frame(now) {
            const progress = Math.min((now - start) / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            const current = Math.round(value * eased);
            let out = `${prefix}${current}${suffix}`;
            if (hasPercent && !out.includes("%")) out = `${prefix}${current}%`;
            if (hasStar && !out.includes("★")) out = `${prefix}${current}★`;
            node.textContent = out;
            if (progress < 1) {
                requestAnimationFrame(frame);
            } else {
                node.textContent = source;
                node.classList.add("counter-ready");
            }
        }

        requestAnimationFrame(frame);
    }

    if (prefersLiteMotion) {
        counterNodes.forEach((node) => node.classList.add("counter-ready"));
    } else {
        counterNodes.forEach((node, idx) => {
            setTimeout(() => runCounter(node), idx * 80);
        });
    }

    if (themeToggle) {
        themeToggle.addEventListener("click", () => {
            const nextTheme = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
            localStorage.setItem("assistly-theme", nextTheme);
            applyTheme(nextTheme);
        });
    }

    if (a11yToggle) {
        a11yToggle.addEventListener("click", () => {
            const current = localStorage.getItem("assistly-accessibility") || "default";
            const next = current === "default" ? "large-text" : current === "large-text" ? "high-contrast" : "default";
            localStorage.setItem("assistly-accessibility", next);
            applyAccessibility(next);
        });
    }

    const modeSelector = document.getElementById("modeSelector");
    if (modeSelector) {
        modeSelector.addEventListener("change", async (event) => {
            modeSelector.disabled = true;
            modeSelector.classList.add("is-loading");
            const mode = event.target.value;
            const response = await fetch("/dashboard/mode", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ mode }),
            });
            if (response.ok) {
                window.location.reload();
            } else {
                modeSelector.disabled = false;
                modeSelector.classList.remove("is-loading");
            }
        });
    }

    const mapEl = document.getElementById("map");
    if (mapEl && window.L) {
        const map = L.map("map", { zoomControl: false }).setView([12.9716, 77.5946], 11);
        L.control.zoom({ position: "bottomright" }).addTo(map);

        const mapTiles = {
            light: "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
            dark: "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
        };
        let activeTileLayer = null;

        function applyMapTheme(theme) {
            const resolved = theme === "dark" ? "dark" : "light";
            if (activeTileLayer) {
                map.removeLayer(activeTileLayer);
            }
            activeTileLayer = L.tileLayer(mapTiles[resolved], {
                maxZoom: 20,
                attribution: "&copy; OpenStreetMap contributors &copy; CARTO",
            });
            activeTileLayer.addTo(map);
        }

        applyMapTheme(root.getAttribute("data-theme") || "light");
        window.addEventListener("assistly:theme-changed", (event) => {
            const nextTheme = event?.detail?.theme || (root.getAttribute("data-theme") || "light");
            applyMapTheme(nextTheme);
        });

        const latField = document.getElementById("latField");
        const lngField = document.getElementById("lngField");
        const detectBtn = document.getElementById("detectLocationBtn");
        const focusMineBtn = document.getElementById("focusMineBtn");
        const focusOpenBtn = document.getElementById("focusOpenBtn");
        const fitAllBtn = document.getElementById("fitAllBtn");

        const mineLayer = L.layerGroup().addTo(map);
        const openLayer = L.layerGroup().addTo(map);
        const progressLayer = L.layerGroup().addTo(map);
        const completedLayer = L.layerGroup().addTo(map);

        let userMarker = null;
        let allMarkers = [];

        function statusStyle(marker) {
            if (marker.is_mine) return { color: "#245fcd", fill: true, fillOpacity: 0.9, fillColor: "#245fcd", radius: 8, weight: 2 };
            if (marker.status === "Open") return { color: "#c17b10", fill: true, fillOpacity: 0.88, fillColor: "#c17b10", radius: 7, weight: 2 };
            if (marker.status === "In Progress") return { color: "#7f5a1b", fill: true, fillOpacity: 0.88, fillColor: "#7f5a1b", radius: 7, weight: 2 };
            return { color: "#1b8756", fill: true, fillOpacity: 0.88, fillColor: "#1b8756", radius: 7, weight: 2 };
        }

        function renderRequestMarkers(markers) {
            mineLayer.clearLayers();
            openLayer.clearLayers();
            progressLayer.clearLayers();
            completedLayer.clearLayers();
            allMarkers = [];

            markers.forEach((item) => {
                const circle = L.circleMarker([item.lat, item.lng], statusStyle(item));
                circle.bindPopup(
                    `<div class="map-popup">`
                        + `<strong>${item.title}</strong><br>`
                        + `<span class="small">${item.category} | ${item.status}</span>`
                        + `</div>`
                );

                if (item.is_mine) {
                    circle.addTo(mineLayer);
                } else if (item.status === "Open") {
                    circle.addTo(openLayer);
                } else if (item.status === "In Progress") {
                    circle.addTo(progressLayer);
                } else {
                    circle.addTo(completedLayer);
                }
                allMarkers.push(circle);
            });
        }

        function setUserMarker(lat, lng) {
            if (userMarker) {
                userMarker.setLatLng([lat, lng]);
            } else {
                userMarker = L.circleMarker([lat, lng], {
                    color: "#0e1f34",
                    fillColor: "#3ea883",
                    fillOpacity: 1,
                    radius: 9,
                    weight: 3,
                }).addTo(map);
                userMarker.bindTooltip("Your location", { direction: "top" });
            }

            if (latField) latField.value = String(lat);
            if (lngField) lngField.value = String(lng);
        }

        async function persistLocation(lat, lng) {
            await fetch("/dashboard/location", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ lat: String(lat), lng: String(lng) }),
            });
        }

        async function loadMapData() {
            try {
                const response = await fetch("/dashboard/map/data");
                if (!response.ok) return;
                const data = await response.json();
                if (!data.success) return;

                renderRequestMarkers(Array.isArray(data.markers) ? data.markers : []);

                if (data.user_location && Number.isFinite(data.user_location.lat) && Number.isFinite(data.user_location.lng)) {
                    setUserMarker(data.user_location.lat, data.user_location.lng);
                }

                if (allMarkers.length > 0) {
                    const group = L.featureGroup(allMarkers);
                    map.fitBounds(group.getBounds().pad(0.2));
                }
            } catch (err) {
                // Ignore map data failures to keep dashboard interactive.
            }
        }

        map.on("click", async (event) => {
            const lat = Number(event.latlng.lat.toFixed(6));
            const lng = Number(event.latlng.lng.toFixed(6));
            setUserMarker(lat, lng);
            await persistLocation(lat, lng);
        });

        if (detectBtn) {
            detectBtn.addEventListener("click", () => {
                if (!navigator.geolocation) return;
                navigator.geolocation.getCurrentPosition(async (position) => {
                    const lat = Number(position.coords.latitude.toFixed(6));
                    const lng = Number(position.coords.longitude.toFixed(6));
                    map.setView([lat, lng], 14);
                    setUserMarker(lat, lng);
                    await persistLocation(lat, lng);
                });
            });
        }

        if (focusMineBtn) {
            focusMineBtn.addEventListener("click", () => {
                const mineMarkers = [];
                mineLayer.eachLayer((layer) => mineMarkers.push(layer));
                if (mineMarkers.length) {
                    map.fitBounds(L.featureGroup(mineMarkers).getBounds().pad(0.25));
                }
            });
        }

        if (focusOpenBtn) {
            focusOpenBtn.addEventListener("click", () => {
                const openMarkers = [];
                openLayer.eachLayer((layer) => openMarkers.push(layer));
                if (openMarkers.length) {
                    map.fitBounds(L.featureGroup(openMarkers).getBounds().pad(0.25));
                }
            });
        }

        if (fitAllBtn) {
            fitAllBtn.addEventListener("click", () => {
                if (allMarkers.length) {
                    map.fitBounds(L.featureGroup(allMarkers).getBounds().pad(0.2));
                } else if (userMarker) {
                    map.setView(userMarker.getLatLng(), 14);
                }
            });
        }

        loadMapData();
    }

    const assistantToggle = document.getElementById("assistantToggle");
    if (assistantToggle) {
        const panel = document.getElementById("assistantPanel");
        const closeBtn = document.getElementById("assistantClose");
        const messagesEl = document.getElementById("assistantMessages");
        const inputEl = document.getElementById("assistantInput");
        const sendBtn = document.getElementById("assistantSendBtn");
        const micBtn = document.getElementById("assistantMicBtn");
        const speakToggle = document.getElementById("assistantSpeakToggle");
        const suggestionsEl = document.getElementById("assistantSuggestions");
        const stateEl = document.getElementById("assistantState");

        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        let recognition = null;
        let voiceOutputEnabled = true;

        function setAssistantState(text) {
            if (stateEl) stateEl.textContent = text;
        }

        function addMessage(kind, text) {
            if (!messagesEl || !text) return;
            const node = document.createElement("article");
            node.className = `assistant-msg ${kind === "user" ? "assistant-msg-user" : "assistant-msg-bot"}`;
            node.textContent = text;
            messagesEl.appendChild(node);
            messagesEl.scrollTop = messagesEl.scrollHeight;
        }

        function speak(text) {
            if (!voiceOutputEnabled || !window.speechSynthesis || !text) return;
            window.speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.rate = 1;
            utterance.pitch = 1;
            window.speechSynthesis.speak(utterance);
        }

        function setSuggestions(items) {
            if (!suggestionsEl) return;
            suggestionsEl.innerHTML = "";
            if (!Array.isArray(items) || items.length === 0) return;

            items.slice(0, 4).forEach((item) => {
                const btn = document.createElement("button");
                btn.type = "button";
                btn.className = "btn btn-sm btn-outline-secondary";
                btn.textContent = item;
                btn.addEventListener("click", () => {
                    if (inputEl) {
                        inputEl.value = item;
                        inputEl.focus();
                    }
                });
                suggestionsEl.appendChild(btn);
            });
        }

        function openPanel() {
            if (!panel) return;
            panel.hidden = false;
            assistantToggle.setAttribute("aria-expanded", "true");
            setAssistantState("Ready");
            if (inputEl) inputEl.focus();
        }

        function closePanel() {
            if (!panel) return;
            panel.hidden = true;
            assistantToggle.setAttribute("aria-expanded", "false");
            setAssistantState("Closed");
        }

        async function sendAssistantMessage() {
            if (!inputEl) return;
            const message = inputEl.value.trim();
            if (!message) return;

            addMessage("user", message);
            inputEl.value = "";
            setAssistantState("Thinking...");

            try {
                const response = await fetch("/assistant/chat", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ message }),
                });
                const data = await response.json();
                if (!response.ok || !data.success) {
                    addMessage("bot", "I could not process that request right now.");
                    setAssistantState("Unavailable");
                    return;
                }

                addMessage("bot", data.reply || "Done.");
                setSuggestions(data.suggestions || []);
                speak(data.reply || "");
                setAssistantState("Ready");

                if (data.action && data.action.type === "navigate" && data.action.url) {
                    const quickGo = document.createElement("button");
                    quickGo.type = "button";
                    quickGo.className = "btn btn-sm btn-primary";
                    quickGo.textContent = "Open";
                    quickGo.addEventListener("click", () => {
                        window.location.href = data.action.url;
                    });
                    if (suggestionsEl) suggestionsEl.appendChild(quickGo);
                }
            } catch (err) {
                addMessage("bot", "Network issue detected. Please try again.");
                setAssistantState("Offline");
            }
        }

        assistantToggle.addEventListener("click", () => {
            if (panel && panel.hidden) openPanel();
            else closePanel();
        });

        if (closeBtn) {
            closeBtn.addEventListener("click", closePanel);
        }

        if (sendBtn) {
            sendBtn.addEventListener("click", sendAssistantMessage);
        }

        if (inputEl) {
            inputEl.addEventListener("keydown", (event) => {
                if (event.key === "Enter") {
                    event.preventDefault();
                    sendAssistantMessage();
                }
            });
        }

        if (speakToggle) {
            speakToggle.addEventListener("click", () => {
                voiceOutputEnabled = !voiceOutputEnabled;
                speakToggle.textContent = voiceOutputEnabled ? "Voice On" : "Voice Off";
            });
        }

        if (SpeechRecognition && micBtn) {
            recognition = new SpeechRecognition();
            recognition.lang = "en-IN";
            recognition.interimResults = false;
            recognition.maxAlternatives = 1;

            recognition.onstart = () => {
                micBtn.classList.add("is-listening");
                setAssistantState("Listening...");
            };

            recognition.onresult = (event) => {
                const transcript = event.results?.[0]?.[0]?.transcript || "";
                if (inputEl) inputEl.value = transcript;
                setAssistantState("Voice captured");
            };

            recognition.onerror = () => {
                setAssistantState("Voice unavailable");
                micBtn.classList.remove("is-listening");
            };

            recognition.onend = () => {
                micBtn.classList.remove("is-listening");
            };

            micBtn.addEventListener("click", () => {
                try {
                    recognition.start();
                } catch (err) {
                    setAssistantState("Voice unavailable");
                }
            });
        } else if (micBtn) {
            micBtn.disabled = true;
            micBtn.title = "Voice input not supported in this browser";
        }
    }

    const notificationBadge = document.getElementById("notificationBadge");
    if (notificationBadge) {
        setInterval(async () => {
            try {
                const response = await fetch("/notifications");
                if (!response.ok) return;
                const data = await response.json();
                notificationBadge.textContent = `${data.accepted_count} accepted | ${data.completed_count} completed`;
            } catch (err) {
                // Ignore network hiccups for non-blocking polling.
            }
        }, 12000);
    }

    const progressBars = document.querySelectorAll(".progress-bar[data-progress]");
    progressBars.forEach((bar) => {
        const value = Number(bar.getAttribute("data-progress") || "0");
        const safeValue = Math.max(0, Math.min(100, value));
        bar.style.width = `${safeValue}%`;
    });
});
