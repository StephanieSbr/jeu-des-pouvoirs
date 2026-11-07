const csrf = document.querySelector('meta[name="csrf-token"]').content;
const lobby = document.getElementById("lobby");
const gameRoot = document.getElementById("game");
const content = document.getElementById("content");
const roomHeader = document.getElementById("room-header");
const notice = document.getElementById("notice");
let lastState = "";
let selectedCard = null;
let privateNotice = "";
let polling = null;
let inRoom = false;

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

function cardOptions(scores) {
  return scores.map((score) => ({ value: score, label: `Carte ${score}` }));
}

function renderLobby() {
  gameRoot.classList.add("hidden");
  lobby.classList.remove("hidden");
}

function renderRoomHeader(state) {
  roomHeader.replaceChildren();
  const left = document.createElement("div");
  left.append(node("div", "eyebrow", "SALON PRIVÉ"));
  const codeLine = node("div", "room-code", state.code);
  const copy = node("button", "ghost", "Copier");
  copy.type = "button";
  copy.addEventListener("click", async () => {
    await navigator.clipboard.writeText(state.code);
    showNotice("Code copié. Envoie-le aux autres joueurs.");
  });
  codeLine.append(copy);
  left.append(codeLine, node("p", "room-caption", `Tu joues sous le nom de ${state.vous}`));
  roomHeader.append(left);
  roomHeader.append(node("span", "phase-label", phaseTitle(state.phase)));
  const leave = node("button", "secondary", "Quitter le jeu");
  leave.type = "button";
  leave.addEventListener("click", leaveRoom);
  roomHeader.append(leave);
}

function phaseTitle(phase) {
  return ({
    attente: "En attente des joueurs",
    tirage: "Tirage des équipes",
    active: "Partie en cours",
    choix_13: "Résolution de la carte 13",
    entre_parties: "Fin de la partie",
    match_termine: "Fin du match",
  })[phase] || phase;
}

function renderPlayers(state, showTeams = true) {
  const list = node("ul", "player-list");
  for (const player of state.joueurs) {
    const item = node("li", "player-item");
    item.append(node("strong", "", player.nom));
    let detail = "";
    if (showTeams && player.equipe) detail = player.equipe;
    else if (player.a_tire) detail = "Carte tirée";
    else if (state.phase === "attente") detail = "Dans le salon";
    if (!player.connecte) detail = "Déconnecté — en attente de son retour";
    if (player.cartes_en_main !== undefined) {
      detail = `${player.cartes_en_main} carte${player.cartes_en_main === 1 ? "" : "s"} en main`;
      if (showTeams && player.equipe) detail += ` · ${player.equipe}`;
      if (player.victoires !== undefined) detail += ` · ${player.victoires} victoire(s)`;
    }
    if (player.a_joue) detail += " · a joué";
    item.append(node("span", "", detail));
    list.append(item);
  }
  return list;
}

function renderWaiting(state) {
  const panel = section("Les joueurs", `${state.joueurs.length}/${state.nombre_joueurs}`);
  panel.append(node("p", "muted", "Partage le code du salon. N'importe quel joueur peut démarrer lorsque le groupe est complet et connecté."));
  if (state.joueurs_deconnectes.length) {
    panel.append(node("p", "notice", `En attente du retour de : ${state.joueurs_deconnectes.join(", ")}.`));
  }
  panel.append(renderPlayers(state, false));
  if (state.peut_commencer) {
    const button = node("button", "", "Démarrer le match");
    button.addEventListener("click", () => runAction(() => post("/api/demarrer")));
    panel.append(button);
  }
  content.append(panel);
}

function renderDraft(state) {
  const panel = section("Tirage des équipes", `${state.tirages_valides}/${state.nombre_joueurs} tirages`);
  panel.append(node("p", "muted", "Chaque joueur tire une carte absolue. La plus forte et la plus faible formeront une équipe."));
  if (state.tirage_personnel !== null && state.tirage_personnel !== undefined) {
    const preview = node("div", "drawn-card");
    const image = document.createElement("img");
    image.src = `/cartes/${state.tirage_personnel}.png`;
    image.alt = `Carte ${state.tirage_personnel}`;
    preview.append(
      image,
      node("p", "notice", `Tu as tiré la carte ${state.tirage_personnel}. Elle reste dans ta main pour cette première partie.`),
    );
    panel.append(preview);
  } else {
    const button = node("button", "", "Piocher ma carte absolue");
    button.addEventListener("click", () => runAction(() => post("/api/tirer")));
    panel.append(button);
  }
  panel.append(renderPlayers(state, false));
  content.append(panel);
}

function renderScoreboard(state) {
  const board = node("div", "scoreboard");
  if (state.individuel) {
    for (const [name, wins] of Object.entries(state.scores_joueurs)) {
      board.append(node("span", "score-chip", `${name} : ${wins} victoire(s)`));
    }
  } else {
    for (const [team, wins] of Object.entries(state.scores_equipes)) {
      board.append(node("span", "score-chip", `${team} : ${wins} victoire(s)`));
    }
  }
  return board;
}

function renderBoard(state) {
  const panel = section("Cartes en jeu", `Tour ${state.numero_tour}`);
  panel.append(node("p", "muted small", `Pioche : ${state.pioche_restante} · Défausse : ${state.defausse.length}`));
  if (state.direction_15) panel.append(node("p", "notice", `Contrainte active : jouer ${state.direction_15}.`));
  const grid = node("div", "board-grid");
  for (const player of state.joueurs) {
    const slot = node("div", "board-slot");
    slot.append(node("strong", "", player.nom));
    if (player.carte_devant !== null) {
      const img = document.createElement("img");
      img.src = `/cartes/${player.carte_devant}.png`;
      img.alt = `Carte ${player.carte_devant}`;
      slot.append(img, node("span", "small muted", `Carte ${player.carte_devant}`));
    } else {
      slot.append(node("div", "empty-card", "＋"), node("span", "small muted", "Pas encore joué"));
    }
    grid.append(slot);
  }
  panel.append(grid);
  content.append(panel);
}

function renderHand(state) {
  const panel = section("Ta main", `${state.main.length} carte(s)`);
  panel.append(node("p", "muted small", state.joueur_courant === state.vous
    ? "C'est ton tour. Choisis une carte."
    : `C'est au tour de ${state.joueur_courant || "un autre joueur"}.`));
  const cards = node("div", "hand");
  for (const card of state.main) {
    const button = node("button", `hand-card${selectedCard === card.score ? " selected" : ""}`);
    button.type = "button";
    button.disabled = state.joueur_courant !== state.vous || !!state.action_en_attente;
    const img = document.createElement("img");
    img.src = card.image;
    img.alt = `Carte ${card.score}`;
    button.append(img, node("span", "score", String(card.score)), node("span", "power", card.pouvoir));
    button.addEventListener("click", () => {
      selectedCard = card.score;
      render(state, true);
    });
    cards.append(button);
  }
  panel.append(cards);
  if (selectedCard !== null && state.joueur_courant === state.vous && !state.action_en_attente) {
    renderPlayControls(panel, state, selectedCard);
  }
  content.append(panel);
}

function renderPlayControls(panel, state, score) {
  const controls = node("div", "controls");
  controls.append(node("h3", "", `Jouer la carte ${score}`));
  const form = document.createElement("form");
  const fields = {};
  const occupiedSlots = state.cartes_en_jeu.map((card) => ({
    value: card.devant,
    label: `${card.devant} — carte ${card.score}`,
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
      fields.score_main = addSelect(controls, "Ta carte à échanger", cardOptions(state.main.filter((card) => card.score !== score).map((card) => card.score)), "score_main", "Choisir…");
    }
  } else if (score === 24) {
    fields.joueur_cible = addSelect(controls, "Autre joueur", otherPlayers, "joueur_cible", "Choisir…");
    fields.mode_24 = addSelect(controls, "Action", [
      { value: "montrer une carte de ma main", label: "Je montre une carte de ma main" },
      { value: "demander une carte choisie par l'autre joueur", label: "L'autre joueur choisit une carte à me montrer" },
    ], "mode_24", "Choisir…");
    fields.score_main = addSelect(controls, "Carte que tu montres", cardOptions(state.main.filter((card) => card.score !== score).map((card) => card.score)), "score_main", "Choisir…");
    fields.score_main.disabled = true;
    fields.mode_24.addEventListener("change", () => { fields.score_main.disabled = fields.mode_24.value !== "montrer une carte de ma main"; });
  } else if (score >= 30 && score <= 35) {
    const ownOptions = state.main.filter((card) => card.score !== score).map((card) => card.score);
    const lastCardDraw = state.main.length === 1 && state.pioche_restante > 0;
    if (ownOptions.length) {
      fields.score_main = addSelect(controls, "Ta carte à échanger", cardOptions(ownOptions), "score_main", "Choisir…");
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
  const panel = section("Pouvoir en attente");
  if (!action.est_cible) {
    panel.append(node("p", "muted", `Tu attends la réponse de ${action.cible}.`));
    content.append(panel);
    return;
  }
  const text = action.type === "21"
    ? `${action.acteur} t'impose de poser une carte devant lui.`
    : action.type === "24"
      ? `${action.acteur} te demande de choisir une carte à lui montrer.`
      : action.type === "28"
        ? `${action.acteur} renvoie la carte ${action.carte_a_remplacer} dans ta main. Choisis une autre carte à poser devant ${action.emplacement}.`
        : `${action.acteur} échange une carte avec toi. Choisis la carte de ta main à échanger.`;
  panel.append(node("p", "", text));
  const form = document.createElement("form");
  const select = addSelect(panel, "Choisis une carte de ta main", cardOptions(state.main.map((card) => card.score)), "score", "Choisir…");
  const button = node("button", "", "Envoyer mon choix");
  button.type = "submit";
  form.append(button);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    if (!select.value) return showNotice("Choisis une carte.", true);
    runAction(() => post("/api/repondre", { score: Number(select.value) }));
  });
  panel.append(form);
  content.append(panel);
}

function renderChoose13(state) {
  const panel = section("Effet de la carte 13");
  if (!state.doit_choisir_13) {
    panel.append(node("p", "muted", "Un autre joueur doit choisir une carte à défausser."));
    content.append(panel);
    return;
  }
  panel.append(node("p", "", "Ta carte 13 a été défaussée. Choisis une carte de ta main à défausser en plus (sauf la 14)."));
  const form = document.createElement("form");
  const select = addSelect(panel, "Carte supplémentaire", cardOptions(state.cartes_choix_13), "score", "Choisir…");
  const button = node("button", "", "Défausser cette carte");
  button.type = "submit";
  form.append(button);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    if (!select.value) return showNotice("Choisis une carte.", true);
    runAction(() => post("/api/choisir-13", { score: Number(select.value) }));
  });
  panel.append(form);
  content.append(panel);
}

function render(state, force = false) {
  const signature = JSON.stringify(state);
  if (!force && signature === lastState) return;
  lastState = signature;
  if (state.messages_prives) privateNotice = state.messages_prives;
  lobby.classList.add("hidden");
  gameRoot.classList.remove("hidden");
  inRoom = true;
  if (polling === null) polling = window.setInterval(refresh, 2000);
  renderRoomHeader(state);
  content.replaceChildren();
  if (privateNotice) {
    const message = node("div", "private-message", privateNotice);
    content.append(message);
  }
  if (state.joueurs_deconnectes.length && state.phase !== "attente") {
    const paused = section("Partie en pause");
    paused.append(node(
      "p",
      "muted",
      `En attente du retour de ${state.joueurs_deconnectes.join(", ")}. La partie reprendra lorsqu'il ou elle aura rejoint le salon avec le même nom et le même code.`,
    ));
    content.append(paused);
    return;
  }
  if (state.phase === "attente") renderWaiting(state);
  else if (state.phase === "tirage") renderDraft(state);
  else if (state.phase === "entre_parties") {
    const panel = section("Partie terminée", `${state.parties_jouees}/3`);
    panel.append(renderScoreboard(state));
    if (state.peut_commencer) {
      const button = node("button", "", "Distribuer la partie suivante");
      button.addEventListener("click", () => runAction(() => post("/api/prochaine-partie")));
      panel.append(button);
    } else panel.append(node("p", "muted", "Un joueur peut démarrer la prochaine partie."));
    content.append(panel);
  } else if (state.phase === "match_termine") {
    const panel = section("Fin du match");
    panel.append(node("p", "", state.equipe_gagnante_match || state.joueur_gagnant_match
      ? `${state.equipe_gagnante_match || state.joueur_gagnant_match} remporte le match !`
      : "Le match se termine sur une égalité après trois parties."));
    panel.append(renderScoreboard(state));
    if (state.peut_nouveau_match) {
      const button = node("button", "", "Rejouer un match");
      button.addEventListener("click", () => runAction(() => post("/api/nouveau-match")));
      panel.append(button);
    }
    content.append(panel);
  } else {
    const summary = section("Match", `Partie ${state.numero_partie}/3`);
    summary.append(renderScoreboard(state));
    content.append(summary);
    if (state.phase === "active" || state.phase === "choix_13") {
      content.append(renderPlayers(state, true));
      renderBoard(state);
      if (state.phase === "choix_13") renderChoose13(state);
      else if (state.action_en_attente) renderPending(state);
      else renderHand(state);
    }
  }
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
    nombre_joueurs: Number(form.get("nombre_joueurs")),
  }));
});

document.getElementById("join-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  runAction(() => post("/api/rejoindre", {
    nom: form.get("nom"),
    code: form.get("code"),
  }));
});

if (document.querySelector('meta[name="has-room"]').content === "true") refresh();

window.addEventListener("pagehide", () => {
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
