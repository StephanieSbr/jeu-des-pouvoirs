const csrf = document.querySelector('meta[name="csrf-token"]').content;
const lobby = document.getElementById("lobby");
const gameRoot = document.getElementById("game");
const content = document.getElementById("content");
const roomHeader = document.getElementById("room-header");
const notice = document.getElementById("notice");
const roomList = document.getElementById("room-list");
const roomDirectoryEmpty = document.getElementById("room-directory-empty");
const roomDirectoryCount = document.getElementById("room-directory-count");
const joinRoomName = document.getElementById("join-room-name");
let lastState = "";
let selectedCard = null;
let polling = null;
let lobbyPolling = null;
let inRoom = false;
let revelationTimer = null;
let revelationKey = null;

function showNotice(message, error = false) {
  notice.replaceChildren();
  if (!message) return;
  const box = document.createElement("div");
  box.className = error ? "notice error" : "notice";
  box.textContent = message;
  notice.append(box);
}

async function post(path, body = {}) {
  const response = await fetch(path, {
    method: "POST",
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": csrf,
    },
    body: JSON.stringify(body),
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || "Une erreur est survenue.");
  return result;
}

function node(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function section(title, hint) {
  const panel = node("section", "panel section");
  const header = node("div", "section-heading");
  const h = node("h2", "", title);
  header.append(h);
  if (hint) header.append(node("span", "phase-label", hint));
  panel.append(header);
  return panel;
}

function addSelect(parent, labelText, options, name, placeholder) {
  const label = node("label", "", labelText);
  const select = document.createElement("select");
  select.name = name;
  select.required = true;
  if (placeholder) {
    const first = document.createElement("option");
    first.value = "";
    first.textContent = placeholder;
    first.disabled = true;
    first.selected = true;
    select.append(first);
  }
  for (const option of options) {
    const item = document.createElement("option");
    item.value = String(option.value);
    item.textContent = option.label;
    select.append(item);
  }
  label.append(select);
  parent.append(label);
  return select;
}

function playerOptions(state, exceptSelf = true, onlyUnplayed = false) {
  return state.joueurs
    .filter((player) => (!exceptSelf || player.nom !== state.vous)
      && (!onlyUnplayed || (!player.a_joue && player.carte_devant === null)))
    .map((player) => ({ value: player.nom, label: player.nom }));
}

function addCardPicker(parent, labelText, cards, name) {
  const picker = node("div", "card-picker");
  picker.append(node("span", "picker-label", labelText));
  const input = document.createElement("input");
  input.type = "hidden";
  input.name = name;
  const choices = node("div", "card-choices");
  const buttons = [];

  for (const card of cards) {
    const score = typeof card === "number" ? card : card.score;
    const button = node("button", "card-choice");
    button.type = "button";
    button.setAttribute("aria-label", "Choisir cette carte");
    const image = document.createElement("img");
    image.src = typeof card === "number" ? `/cartes/${score}.png` : card.image;
    image.alt = "Carte";
    button.append(image);
    button.addEventListener("click", () => {
      input.value = String(score);
      for (const choice of buttons) choice.classList.toggle("selected", choice === button);
    });
    buttons.push(button);
    choices.append(button);
  }

  picker.append(input, choices);
  parent.append(picker);
  input.cardButtons = buttons;
  return input;
}

function setCardPickerDisabled(input, disabled) {
  input.disabled = disabled;
  for (const button of input.cardButtons) button.disabled = disabled;
}

function renderLobby() {
  clearRevelationTimer();
  document.body.classList.remove("hand-focus");
  document.body.classList.remove("in-game");
  window.scrollTo(0, 0);
  roomHeader.classList.add("hidden");
  gameRoot.classList.add("hidden");
  lobby.classList.remove("hidden");
  if (lobbyPolling === null) {
    refreshLobby();
    lobbyPolling = window.setInterval(refreshLobby, 5000);
  }
}

function renderRoomHeader(state) {
  roomHeader.replaceChildren();
  const left = document.createElement("div");
  left.append(node("div", "eyebrow", "SALON"));
  const nameLine = node("div", "room-name", state.nom_salon);
  const copy = node("button", "ghost", "Copier");
  copy.type = "button";
  copy.addEventListener("click", async () => {
    await navigator.clipboard.writeText(state.nom_salon);
    showNotice("Nom du salon copié. Envoie-le aux autres joueurs.");
  });
  nameLine.append(copy);
  left.append(nameLine, node("p", "room-caption", `Tu joues sous le nom de ${state.vous}`));
  roomHeader.append(left);
  roomHeader.append(node("span", "phase-label", "En attente"));
  if (state.peut_cloturer) {
    const close = node("button", "danger", "Clôturer le salon");
    close.type = "button";
    close.addEventListener("click", () => closeRoom(state.nom_salon));
    roomHeader.append(close);
  }
  const leave = node("button", "secondary", "Quitter le jeu");
  leave.type = "button";
  leave.addEventListener("click", leaveRoom);
  roomHeader.append(leave);
}

function renderWaiting(state) {
  const panel = section("Les joueurs", `${state.joueurs.length}/${state.nombre_joueurs}`);
  panel.append(node("p", "muted", `Partage le nom « ${state.nom_salon} ». N'importe quel joueur peut démarrer lorsque le groupe est complet et connecté.`));
  if (state.joueurs_deconnectes.length) {
    panel.append(node("p", "notice", `En attente du retour de : ${state.joueurs_deconnectes.join(", ")}.`));
  }
  const players = node("ul", "waiting-players");
  for (const player of state.joueurs) {
    players.append(node("li", "", `${player.nom}${player.connecte ? "" : " — déconnecté"}`));
  }
  panel.append(players);
  if (state.peut_commencer) {
    const button = node("button", "", "Démarrer le match");
    button.addEventListener("click", () => runAction(() => post("/api/demarrer")));
    panel.append(button);
  }
  content.append(panel);
}

function renderDraft(state) {
  const screen = node("div", "game-screen draft-screen");
  const toolbar = node("div", "game-toolbar");
  if (state.peut_cloturer) {
    const close = node("button", "danger", "Clôturer le salon");
    close.type = "button";
    close.addEventListener("click", () => closeRoom(state.nom_salon));
    toolbar.append(close);
  }
  const leave = node("button", "secondary", "Quitter");
  leave.type = "button";
  leave.addEventListener("click", leaveRoom);
  toolbar.append(leave);
  screen.append(toolbar);
  const panel = node("section", "draw-panel");
  const revelationEnCours = state.phase === "revelation";
  panel.append(node(
    "h2",
    "",
    revelationEnCours
      ? "Révélation des cartes absolues"
      : `Tirage ${state.tirages_valides}/${state.nombre_joueurs}`,
  ));
  const tirages = node("div", "absolute-draws");
  for (const tirage of state.tirages_publics) {
    const resultat = node("article", "absolute-draw");
    resultat.append(node("strong", "", tirage.nom));
    const image = document.createElement("img");
    image.src = `/cartes/${tirage.score}.png`;
    image.alt = `Carte absolue tirée par ${tirage.nom}`;
    resultat.append(image);
    tirages.append(resultat);
  }
  if (tirages.childElementCount) {
    panel.append(tirages);
  }
  if (revelationEnCours) {
    if (state.joueurs_deconnectes.length) {
      if (revelationTimer !== null) window.clearTimeout(revelationTimer);
      revelationTimer = null;
      revelationKey = null;
      panel.append(node(
        "p",
        "muted",
        `En attente du retour de ${state.joueurs_deconnectes.join(", ")}.`,
      ));
    } else {
      programmerConfirmationRevelation(state);
    }
  } else {
    const tiragePersonnel = state.tirages_publics.find(
      (tirage) => tirage.nom === state.vous,
    );
    if (tiragePersonnel) {
      panel.append(node(
        "p",
        "muted",
        `Tu as tiré la carte ${tiragePersonnel.score}.`,
      ));
    } else {
      const button = node("button", "", "Piocher ma carte absolue");
      button.addEventListener("click", () => runAction(() => post("/api/tirer")));
      panel.append(button);
    }
  }
  screen.append(panel);
  content.append(screen);
}

function programmerConfirmationRevelation(state) {
  const key = `${state.nom_salon}:${JSON.stringify(state.tirages_publics)}`;
  if (revelationKey === key) return;
  if (revelationTimer !== null) window.clearTimeout(revelationTimer);
  revelationKey = key;
  revelationTimer = window.setTimeout(async () => {
    revelationTimer = null;
    try {
      await post("/api/voir-absolues");
      await refresh();
    } catch (error) {
      revelationKey = null;
      showNotice(error.message, true);
      await refresh();
    }
  }, 2000);
}

function clearRevelationTimer() {
  if (revelationTimer !== null) window.clearTimeout(revelationTimer);
  revelationTimer = null;
  revelationKey = null;
}

function renderTable(state) {
  const table = node("div", "game-table");
  table.append(node("div", "table-ring"));
  const discards = node("aside", "discard-tray");
  discards.setAttribute("aria-label", "Cartes défaussées au tour précédent");
  for (const card of state.dernieres_defausses || []) {
    discards.append(node("span", `discard-chip color-${card.couleur}`, String(card.numero)));
  }
  table.append(discards);
  if (state.resume_tour) {
    const summary = node("section", "turn-summary");
    summary.setAttribute("role", "status");
    summary.setAttribute("aria-live", "polite");
    summary.append(node("h2", "", `Tour remporté par ${state.resume_tour.gagnant}`));
    summary.append(node(
      "p",
      "",
      `Défausse${state.resume_tour.defausseurs.length > 1 ? "s" : ""} : ${
        state.resume_tour.defausseurs.join(", ") || "personne"
      }`,
    ));
    summary.append(node("p", "", `${state.resume_tour.commence} commence le prochain tour`));
    table.append(summary);
  }

  // Ancre la table sur soi ; l'ordre de jeu progresse dans le sens horaire.
  const players = [...state.joueurs];
  const selfIndex = players.findIndex((player) => player.nom === state.vous);
  const clockwise = [
    ...players.slice(selfIndex),
    ...players.slice(0, selfIndex),
  ];
  const positions = {
    4: [[50, 72], [12, 50], [50, 28], [88, 50]],
    5: [[50, 72], [12, 58], [25, 28], [75, 28], [88, 58]],
    6: [[50, 72], [12, 66], [12, 26], [50, 28], [88, 26], [88, 66]],
  }[clockwise.length];
  clockwise.forEach((player, index) => {
    const seat = node("article", "player-seat");
    seat.style.left = `${positions[index][0]}%`;
    seat.style.top = `${positions[index][1]}%`;
    seat.classList.add(player.equipe === "Équipe A"
      ? "team-a"
      : player.equipe === "Équipe B" ? "team-b" : "individual");
    if (player.nom === state.joueur_courant && state.phase === "active") {
      seat.classList.add("current-turn");
    }

    const name = node("strong", "seat-name", player.nom);
    seat.append(name, node("span", "seat-count", String(player.cartes_en_main)));
    if (player.carte_devant !== null) {
      const card = document.createElement("img");
      card.className = "played-card";
      card.src = `/cartes/${player.carte_devant}.png`;
      card.alt = "Carte posée";
      seat.append(card);
    } else {
      seat.append(node("div", "empty-card"));
    }
    table.append(seat);
  });
  return table;
}

function renderHand(state, panel) {
  const cards = node("div", "hand");
  const afficheControles = selectedCard !== null
    && state.joueur_courant === state.vous
    && !state.action_en_attente;
  panel.classList.toggle("controls-open", afficheControles);
  for (const card of state.main) {
    const button = node("button", `hand-card${selectedCard === card.score ? " selected" : ""}`);
    button.type = "button";
    button.disabled = state.joueur_courant !== state.vous || !!state.action_en_attente;
    const img = document.createElement("img");
    img.src = card.image;
    img.alt = "Carte de ta main";
    button.append(img);
    button.addEventListener("click", () => {
      selectedCard = card.score;
      render(state, true);
    });
    cards.append(button);
  }
  panel.append(cards);
  if (afficheControles) {
    renderPlayControls(panel, state, selectedCard);
  }
}

function renderPlayControls(panel, state, score) {
  const controls = node("div", "controls");
  controls.append(node("h3", "", "Jouer cette carte"));
  const form = document.createElement("form");
  const fields = {};
  const occupiedSlots = state.cartes_en_jeu.map((card) => ({
    value: card.devant,
    label: card.devant,
  }));
  const otherPlayers = playerOptions(state);

  if (score === 15) {
    fields.direction_15 = addSelect(controls, "Choisir la contrainte", [
      { value: "au-dessus de 15", label: "Au-dessus de 15" },
      { value: "au-dessous de 15", label: "Au-dessous de 15" },
    ], "direction_15", "Choisir…");
  } else if (score === 21) {
    fields.utiliser_21 = addSelect(controls, "Utiliser le pouvoir ?", [
      { value: "false", label: "Non, poser sans cibler" },
      { value: "true", label: "Oui, imposer une pose" },
    ], "utiliser_21");
    fields.joueur_cible = addSelect(controls, "Joueur qui n'a pas encore joué", playerOptions(state, true, true), "joueur_cible", "Choisir…");
    fields.joueur_cible.disabled = true;
    fields.utiliser_21.addEventListener("change", () => { fields.joueur_cible.disabled = fields.utiliser_21.value !== "true"; });
  } else if ([23, 28, 29].includes(score) && occupiedSlots.length) {
    fields.joueur_cible = addSelect(controls, score === 23
      ? "Joueur devant lequel échanger"
      : "Carte déjà en jeu à cibler", occupiedSlots, "joueur_cible", "Choisir…");
    if (score === 29 && state.main.some((card) => card.score !== score)) {
      fields.score_main = addCardPicker(
        controls,
        "Ta carte à échanger",
        state.main.filter((card) => card.score !== score),
        "score_main",
      );
    }
  } else if (score === 24) {
    fields.joueur_cible = addSelect(controls, "Autre joueur", otherPlayers, "joueur_cible", "Choisir…");
    fields.mode_24 = addSelect(controls, "Action", [
      { value: "montrer une carte de ma main", label: "Je montre une carte de ma main" },
      { value: "demander une carte choisie par l'autre joueur", label: "L'autre joueur choisit une carte à me montrer" },
    ], "mode_24", "Choisir…");
    fields.score_main = addCardPicker(
      controls,
      "Carte que tu montres",
      state.main.filter((card) => card.score !== score),
      "score_main",
    );
    setCardPickerDisabled(fields.score_main, true);
    fields.mode_24.addEventListener("change", () => {
      setCardPickerDisabled(
        fields.score_main,
        fields.mode_24.value !== "montrer une carte de ma main",
      );
    });
  } else if (score >= 30 && score <= 35) {
    const ownOptions = state.main.filter((card) => card.score !== score).map((card) => card.score);
    const lastCardDraw = state.main.length === 1 && state.pioche_restante > 0;
    if (ownOptions.length) {
      fields.score_main = addCardPicker(
        controls,
        "Ta carte à échanger",
        ownOptions,
        "score_main",
      );
    } else if (lastCardDraw) {
      controls.append(node("p", "muted small", "C'est ta dernière carte : tu piocheras une carte à échanger."));
    }
    fields.joueur_cible = addSelect(controls, "Joueur qui choisira sa carte", otherPlayers.filter((player) => {
      const item = state.joueurs.find((candidate) => candidate.nom === player.value);
      return item && item.cartes_en_main > 0;
    }), "joueur_cible", "Choisir…");
  }

  const submit = node("button", "", "Confirmer la pose");
  submit.type = "submit";
  form.append(submit);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const data = { score };
    for (const [name, input] of Object.entries(fields)) {
      if (input.disabled) continue;
      const value = input.value;
      if (!value) {
        showNotice("Complète les choix demandés par ce pouvoir.", true);
        return;
      }
      data[name] = name === "utiliser_21" ? value === "true"
        : ["score_main", "score_main_cible", "score_forcee_21", "score_remplacement_28"].includes(name)
          ? Number(value) : value;
    }
    runAction(() => post("/api/jouer", data));
    selectedCard = null;
  });
  controls.append(form);
  panel.append(controls);
}

function renderPending(state) {
  const action = state.action_en_attente;
  const panel = node("section", "action-panel");
  if (!action.est_cible) {
    panel.append(node("p", "muted", `En attente de ${action.cible}.`));
    return panel;
  }
  const text = action.type === "21"
    ? `${action.acteur} t'impose de poser une carte devant lui.`
    : action.type === "24"
      ? `${action.acteur} te demande de choisir une carte à lui montrer.`
      : action.type === "28"
        ? `${action.acteur} te demande de remplacer ta carte posée devant ${action.emplacement}.`
        : `${action.acteur} échange une carte avec toi. Choisis la carte de ta main à échanger.`;
  panel.append(node("p", "", text));
  const form = document.createElement("form");
  const picker = addCardPicker(panel, "Choisis une carte", state.main, "score");
  const button = node("button", "", "Confirmer");
  button.type = "submit";
  form.append(button);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    if (!picker.value) return showNotice("Choisis une carte.", true);
    runAction(() => post("/api/repondre", { score: Number(picker.value) }));
  });
  panel.append(form);
  return panel;
}

function renderChoose13(state) {
  const panel = node("section", "action-panel");
  if (!state.doit_choisir_13) {
    panel.append(node("p", "muted", "En attente du choix de défausse."));
    return panel;
  }
  panel.append(node("p", "", "Choisis une carte supplémentaire à défausser."));
  const form = document.createElement("form");
  const choices = state.main.filter((card) => state.cartes_choix_13.includes(card.score));
  const picker = addCardPicker(panel, "Choisir une carte", choices, "score");
  const button = node("button", "", "Confirmer");
  button.type = "submit";
  form.append(button);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    if (!picker.value) return showNotice("Choisis une carte.", true);
    runAction(() => post("/api/choisir-13", { score: Number(picker.value) }));
  });
  panel.append(form);
  return panel;
}

function renderMatch(state) {
  const screen = node("div", "game-screen");
  const rulesImage = document.createElement("img");
  rulesImage.className = "rules-image";
  rulesImage.src = "/regles.png";
  rulesImage.alt = "Règles du jeu";
  rulesImage.title = "Règles du jeu";
  screen.append(rulesImage);
  const toolbar = node("div", "game-toolbar");
  const leave = node("button", "secondary", "Quitter");
  leave.type = "button";
  leave.addEventListener("click", leaveRoom);
  if (state.peut_cloturer) {
    const close = node("button", "danger", "Clôturer le salon");
    close.type = "button";
    close.addEventListener("click", closeRoom);
    toolbar.append(close);
  }
  toolbar.append(leave);

  if (state.messages_prives) {
    const reveal = node("div", "private-reveal");
    reveal.append(node("span", "", state.messages_prives.texte));
    const image = document.createElement("img");
    image.src = state.messages_prives.image;
    image.alt = "Carte révélée";
    reveal.append(image);
    toolbar.append(reveal);
  }
  if (state.joueurs_deconnectes.length) {
    toolbar.append(node(
      "div",
      "game-message",
      `En attente du retour de ${state.joueurs_deconnectes.join(", ")}.`,
    ));
    screen.append(toolbar);
    content.append(screen);
    return;
  }
  screen.append(toolbar);
  if (state.phase === "match_termine") {
    const winner = state.equipe_gagnante_match || state.joueur_gagnant_match;
    toolbar.append(node("p", "round-result", winner ? `${winner} remporte le match.` : "Match terminé."));
  }

  screen.append(renderTable(state));
  const bottom = node("div", "game-bottom");
  if (state.phase === "active") {
    if (selectedCard !== null && !state.main.some((card) => card.score === selectedCard)) {
      selectedCard = null;
    }
    if (state.action_en_attente) bottom.append(renderPending(state));
    else renderHand(state, bottom);
  } else if (state.phase === "choix_13") {
    bottom.append(renderChoose13(state));
  } else if (state.phase === "entre_parties" && state.peut_commencer) {
    const button = node("button", "", "Distribuer la prochaine partie");
    button.addEventListener("click", () => runAction(() => post("/api/prochaine-partie")));
    bottom.append(button);
  } else if (state.phase === "match_termine" && state.peut_nouveau_match) {
    const button = node("button", "", "Rejouer");
    button.addEventListener("click", () => runAction(() => post("/api/nouveau-match")));
    bottom.append(button);
  }
  screen.append(bottom);
  content.append(screen);
}

function render(state, force = false) {
  const signature = JSON.stringify(state);
  if (!force && signature === lastState) return;
  const scrollTop = window.scrollY;
  lastState = signature;
  lobby.classList.add("hidden");
  gameRoot.classList.remove("hidden");
  inRoom = true;
  if (polling === null) polling = window.setInterval(refresh, 2000);
  if (lobbyPolling !== null) {
    window.clearInterval(lobbyPolling);
    lobbyPolling = null;
  }

  const isPlaying = state.phase !== "attente";
  document.body.classList.toggle("in-game", isPlaying);
  const handViewAvailable = !["attente", "tirage", "revelation"].includes(state.phase);
  roomHeader.classList.toggle("hidden", isPlaying);
  if (!isPlaying) renderRoomHeader(state);
  content.replaceChildren();

  if (state.phase === "attente") renderWaiting(state);
  else if (state.phase === "tirage" || state.phase === "revelation") renderDraft(state);
  else renderMatch(state);
  window.scrollTo(0, scrollTop);
  updateHandFocus(handViewAvailable);
  if (state.phase !== "revelation") clearRevelationTimer();
}

function updateHandFocus(enabled = true) {
  const maximumScroll = Math.max(
    0,
    document.documentElement.scrollHeight - window.innerHeight,
  );
  const focusThreshold = Math.min(window.innerHeight * 0.58, maximumScroll * 0.65);
  document.body.classList.toggle(
    "hand-focus",
    enabled && maximumScroll > 0 && window.scrollY >= focusThreshold,
  );
}

async function refresh() {
  try {
    const response = await fetch("/api/etat", { credentials: "same-origin" });
    if (response.status === 401) {
      inRoom = false;
      if (polling !== null) {
        window.clearInterval(polling);
        polling = null;
      }
      renderLobby();
      return;
    }
    const state = await response.json();
    if (!response.ok) throw new Error(state.error || "Impossible de charger le salon.");
    render(state);
  } catch (error) {
    showNotice(error.message, true);
  }
}

async function refreshLobby() {
  try {
    const response = await fetch("/api/salons", { credentials: "same-origin" });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Impossible de charger les salons.");
    renderRoomList(result.salons);
  } catch (error) {
    roomDirectoryEmpty.textContent = error.message;
  }
}

function renderRoomList(salons) {
  roomList.replaceChildren();
  roomDirectoryCount.textContent = `${salons.length} salon${salons.length === 1 ? "" : "s"}`;
  roomDirectoryEmpty.classList.toggle("hidden", salons.length > 0);
  if (!salons.length) {
    roomDirectoryEmpty.textContent = "Aucun salon ouvert pour le moment.";
    return;
  }
  const phases = {
    attente: "En attente",
    tirage: "Tirage des équipes",
    revelation: "Révélation des équipes",
    active: "Partie en cours",
    choix_13: "Choix en cours",
    entre_parties: "Entre deux parties",
    match_termine: "Match terminé",
  };
  for (const salon of salons) {
    const item = node("li", "room-list-item");
    const details = node("div", "room-list-details");
    const joinLabel = salon.phase === "attente"
      ? salon.peut_rejoindre ? "Rejoindre" : "Complet"
      : "Retrouver";
    details.append(node("strong", "", salon.nom));
    details.append(node(
      "span",
      "muted",
      `${salon.joueurs}/${salon.nombre_joueurs} joueurs · ${phases[salon.phase] || salon.phase}`,
    ));
    item.append(details);
    const join = node(
      "button",
      salon.phase === "attente" && !salon.peut_rejoindre ? "ghost" : "secondary",
      joinLabel,
    );
    join.type = "button";
    join.disabled = salon.phase === "attente" && !salon.peut_rejoindre;
    join.addEventListener("click", () => {
      joinRoomName.value = salon.nom;
      document.querySelector('#join-form input[name="nom"]').focus();
    });
    item.append(join);
    if (salon.peut_cloturer) {
      const close = node("button", "danger", "Clôturer");
      close.type = "button";
      close.addEventListener("click", () => closeRoom(salon.nom));
      item.append(close);
    }
    roomList.append(item);
  }
}

async function closeRoom(nomSalon) {
  if (!window.confirm(`Clôturer le salon « ${nomSalon || "ce salon"} » ?`)) return;
  try {
    await post("/api/cloturer", { nom_salon: nomSalon });
    if (polling !== null) {
      window.clearInterval(polling);
      polling = null;
    }
    inRoom = false;
    lastState = "";
    renderLobby();
    showNotice("Le salon a été clôturé.");
    await refreshLobby();
  } catch (error) {
    showNotice(error.message, true);
  }
}

async function leaveRoom() {
  try {
    await post("/api/quitter");
    inRoom = false;
    if (polling !== null) {
      window.clearInterval(polling);
      polling = null;
    }
    lastState = "";
    renderLobby();
  } catch (error) {
    showNotice(error.message, true);
  }
}

async function runAction(action) {
  showNotice("");
  try {
    await action();
    lastState = "";
    await refresh();
  } catch (error) {
    showNotice(error.message, true);
    await refresh();
  }
}

document.getElementById("create-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  runAction(() => post("/api/salons", {
    nom: form.get("nom"),
    nom_salon: form.get("nom_salon"),
    nombre_joueurs: Number(form.get("nombre_joueurs")),
  }));
});

document.getElementById("join-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  runAction(() => post("/api/rejoindre", {
    nom: form.get("nom"),
    nom_salon: form.get("nom_salon"),
  }));
});

if (document.querySelector('meta[name="has-room"]').content === "true") refresh();
else renderLobby();

window.addEventListener("scroll", () => updateHandFocus(), { passive: true });
window.addEventListener("resize", () => updateHandFocus(), { passive: true });

window.addEventListener("pagehide", () => {
  if (revelationTimer !== null) window.clearTimeout(revelationTimer);
  if (!inRoom) return;
  const payload = new Blob([JSON.stringify({ csrf })], {
    type: "application/json",
  });
  navigator.sendBeacon("/api/quitter", payload);
  inRoom = false;
});

window.addEventListener("pageshow", (event) => {
  if (event.persisted) refresh();
});
