"use strict";

(() => {
  const supported = Object.freeze({en: "English", el: "Greek", it: "Italian", fr: "French"});
  const rows = {
    "About": ["Σχετικά", "Informazioni", "À propos"],
    "About ZBRANO": ["Σχετικά με το ZBRANO", "Informazioni su ZBRANO", "À propos de ZBRANO"],
    "Access": ["Πρόσβαση", "Accesso", "Accès"],
    "All": ["Όλα", "Tutto", "Tout"],
    "All categories": ["Όλες οι κατηγορίες", "Tutte le categorie", "Toutes les catégories"],
    "All domains": ["Όλοι οι τομείς", "Tutti i domini", "Tous les domaines"],
    "All settings": ["Όλες οι ρυθμίσεις", "Tutte le impostazioni", "Tous les paramètres"],
    "Appearance": ["Εμφάνιση", "Aspetto", "Apparence"],
    "Assistant": ["Βοηθός", "Assistente", "Assistant"],
    "Attach": ["Επισύναψη", "Allega", "Joindre"],
    "Attach selected to chat": ["Επισύναψη επιλεγμένων στη συνομιλία", "Allega selezionati alla chat", "Joindre la sélection à la discussion"],
    "Attach to this chat": ["Επισύναψη σε αυτή τη συνομιλία", "Allega a questa chat", "Joindre à cette discussion"],
    "Auto": ["Αυτόματα", "Auto", "Auto"],
    "Automations": ["Αυτοματισμοί", "Automazioni", "Automatisations"],
    "Back": ["Πίσω", "Indietro", "Retour"],
    "Balanced": ["Ισορροπημένη", "Bilanciata", "Équilibrée"],
    "Brief": ["Σύντομη", "Breve", "Brève"],
    "Browse Plugins": ["Περιήγηση προσθηκών", "Sfoglia plugin", "Parcourir les plugins"],
    "Calendar": ["Ημερολόγιο", "Calendario", "Calendrier"],
    "Cancel": ["Ακύρωση", "Annulla", "Annuler"],
    "Chat": ["Συνομιλία", "Chat", "Discussion"],
    "Check": ["Έλεγχος", "Verifica", "Vérifier"],
    "Checking…": ["Έλεγχος…", "Verifica…", "Vérification…"],
    "Clear": ["Εκκαθάριση", "Cancella", "Effacer"],
    "Configure": ["Ρύθμιση", "Configura", "Configurer"],
    "Configure ZBRANO": ["Ρύθμιση ZBRANO", "Configura ZBRANO", "Configurer ZBRANO"],
    "Connections & data": ["Συνδέσεις και δεδομένα", "Connessioni e dati", "Connexions et données"],
    "Contacts": ["Επαφές", "Contatti", "Contacts"],
    "Continue": ["Συνέχεια", "Continua", "Continuer"],
    "CONVERSATIONS": ["ΣΥΝΟΜΙΛΙΕΣ", "CONVERSAZIONI", "DISCUSSIONS"],
    "Control device": ["Συσκευή ελέγχου", "Dispositivo di controllo", "Appareil contrôlable"],
    "Current value": ["Τρέχουσα τιμή", "Valore attuale", "Valeur actuelle"],
    "Dark": ["Σκούρο", "Scuro", "Sombre"],
    "Data": ["Δεδομένα", "Dati", "Données"],
    "Delete selected": ["Διαγραφή επιλεγμένων", "Elimina selezionati", "Supprimer la sélection"],
    "Descending": ["Φθίνουσα", "Decrescente", "Décroissant"],
    "Detailed": ["Αναλυτική", "Dettagliata", "Détaillée"],
    "Developer": ["Προγραμματιστής", "Sviluppatore", "Développeur"],
    "Device access": ["Πρόσβαση συσκευών", "Accesso ai dispositivi", "Accès aux appareils"],
    "Do not allow": ["Να μην επιτρέπεται", "Non consentire", "Ne pas autoriser"],
    "Entities": ["Οντότητες", "Entità", "Entités"],
    "Entity ID": ["Αναγνωριστικό οντότητας", "ID entità", "ID d’entité"],
    "Entity Inventory": ["Κατάλογος οντοτήτων", "Inventario entità", "Inventaire des entités"],
    "Export Backup": ["Εξαγωγή αντιγράφου", "Esporta backup", "Exporter la sauvegarde"],
    "Export JSON": ["Εξαγωγή JSON", "Esporta JSON", "Exporter JSON"],
    "General": ["Γενικά", "Generale", "Général"],
    "History & Event Timeline": ["Ιστορικό και χρονολόγιο συμβάντων", "Cronologia ed eventi", "Historique et chronologie des événements"],
    "Home Assistant": ["Home Assistant", "Home Assistant", "Home Assistant"],
    "Installed Plugins": ["Εγκατεστημένες προσθήκες", "Plugin installati", "Plugins installés"],
    "Intelligence": ["Νοημοσύνη", "Intelligenza", "Intelligence"],
    "Interface and reply language": ["Γλώσσα διεπαφής και απαντήσεων", "Lingua dell’interfaccia e delle risposte", "Langue de l’interface et des réponses"],
    "Light": ["Φωτεινό", "Chiaro", "Clair"],
    "Loading…": ["Φόρτωση…", "Caricamento…", "Chargement…"],
    "Loading chats…": ["Φόρτωση συνομιλιών…", "Caricamento chat…", "Chargement des discussions…"],
    "Mark all read": ["Σήμανση όλων ως αναγνωσμένων", "Segna tutto come letto", "Tout marquer comme lu"],
    "Memory": ["Μνήμη", "Memoria", "Mémoire"],
    "Message ZBRANO": ["Μήνυμα στο ZBRANO", "Messaggio a ZBRANO", "Envoyer un message à ZBRANO"],
    "Needs attention": ["Χρειάζεται προσοχή", "Richiede attenzione", "Nécessite une attention"],
    "New automation": ["Νέος αυτοματισμός", "Nuova automazione", "Nouvelle automatisation"],
    "No notifications yet.": ["Δεν υπάρχουν ακόμη ειδοποιήσεις.", "Nessuna notifica.", "Aucune notification pour le moment."],
    "Notifications": ["Ειδοποιήσεις", "Notifiche", "Notifications"],
    "Notifications and autonomy": ["Ειδοποιήσεις και αυτονομία", "Notifiche e autonomia", "Notifications et autonomie"],
    "Off": ["Ανενεργό", "Disattivato", "Désactivé"],
    "On": ["Ενεργό", "Attivato", "Activé"],
    "Open Calendar": ["Άνοιγμα ημερολογίου", "Apri calendario", "Ouvrir le calendrier"],
    "Open Notification Center": ["Άνοιγμα κέντρου ειδοποιήσεων", "Apri centro notifiche", "Ouvrir le centre de notifications"],
    "Open notifications": ["Άνοιγμα ειδοποιήσεων", "Apri notifiche", "Ouvrir les notifications"],
    "Plugins": ["Προσθήκες", "Plugin", "Plugins"],
    "Provider": ["Πάροχος", "Fornitore", "Fournisseur"],
    "Ready": ["Έτοιμο", "Pronto", "Prêt"],
    "Refresh": ["Ανανέωση", "Aggiorna", "Actualiser"],
    "Response detail": ["Λεπτομέρεια απάντησης", "Dettaglio risposta", "Niveau de détail de la réponse"],
    "Restore Backup": ["Επαναφορά αντιγράφου", "Ripristina backup", "Restaurer la sauvegarde"],
    "Review": ["Επισκόπηση", "Rivedi", "Consulter"],
    "Save All Settings": ["Αποθήκευση όλων των ρυθμίσεων", "Salva tutte le impostazioni", "Enregistrer tous les paramètres"],
    "Send": ["Αποστολή", "Invia", "Envoyer"],
    "Sensor device": ["Συσκευή αισθητήρα", "Dispositivo sensore", "Appareil capteur"],
    "Settings": ["Ρυθμίσεις", "Impostazioni", "Paramètres"],
    "Setup": ["Αρχική ρύθμιση", "Configurazione", "Configuration"],
    "Shared Files": ["Κοινόχρηστα αρχεία", "File condivisi", "Fichiers partagés"],
    "Show Approved": ["Εμφάνιση εγκεκριμένων", "Mostra approvati", "Afficher les autorisés"],
    "Speak replies": ["Εκφώνηση απαντήσεων", "Leggi le risposte", "Lire les réponses"],
    "Start a conversation": ["Έναρξη συνομιλίας", "Avvia una conversazione", "Démarrer une discussion"],
    "Start microphone": ["Έναρξη μικροφώνου", "Avvia microfono", "Activer le microphone"],
    "Start new chat": ["Νέα συνομιλία", "Avvia nuova chat", "Nouvelle discussion"],
    "Stop": ["Διακοπή", "Interrompi", "Arrêter"],
    "Stop ZBRANO response": ["Διακοπή απάντησης ZBRANO", "Interrompi la risposta di ZBRANO", "Arrêter la réponse de ZBRANO"],
    "Talk": ["Μίλησε", "Parla", "Parler"],
    "Thinking": ["Σκέψη", "Elaborazione", "Réflexion"],
    "Try it safely": ["Ασφαλής δοκιμή", "Prova in sicurezza", "Tester en toute sécurité"],
    "Voice": ["Φωνή", "Voce", "Voix"],
    "Voice and wake word": ["Φωνή και λέξη αφύπνισης", "Voce e parola di attivazione", "Voix et mot d’activation"],
    "Web": ["Ιστός", "Web", "Web"],
    "ZBRANO IS LISTENING": ["ΤΟ ZBRANO ΑΚΟΥΕΙ", "ZBRANO STA ASCOLTANDO", "ZBRANO ÉCOUTE"],
    "ZBRANO is ready": ["Το ZBRANO είναι έτοιμο", "ZBRANO è pronto", "ZBRANO est prêt"],
    "Speak your command…": ["Πείτε την εντολή σας…", "Pronuncia il comando…", "Dites votre commande…"],
    "Enter command…": ["Πληκτρολογήστε εντολή…", "Inserisci un comando…", "Saisissez une commande…"],
    "Changes the ZBRANO interface, AI replies, and browser voice recognition. English remains the fallback.": ["Αλλάζει τη διεπαφή ZBRANO, τις απαντήσεις AI και τη φωνητική αναγνώριση του προγράμματος περιήγησης. Τα Αγγλικά παραμένουν η εφεδρική γλώσσα.", "Cambia l’interfaccia ZBRANO, le risposte AI e il riconoscimento vocale del browser. L’inglese rimane la lingua di riserva.", "Modifie l’interface ZBRANO, les réponses de l’IA et la reconnaissance vocale du navigateur. L’anglais reste la langue de secours."],
    "Core setup is complete. You can start chatting now and add optional capabilities whenever you need them.": ["Η βασική ρύθμιση ολοκληρώθηκε. Μπορείτε να ξεκινήσετε συνομιλία και να προσθέσετε προαιρετικές δυνατότητες όποτε τις χρειαστείτε.", "La configurazione principale è completa. Puoi iniziare a chattare e aggiungere funzioni opzionali quando servono.", "La configuration principale est terminée. Vous pouvez discuter maintenant et ajouter des fonctions facultatives quand vous le souhaitez."],
    "Review setup": ["Έλεγχος ρύθμισης", "Rivedi configurazione", "Vérifier la configuration"],
    "Review connections": ["Έλεγχος συνδέσεων", "Rivedi connessioni", "Vérifier les connexions"],
    "Start chatting": ["Έναρξη συνομιλίας", "Inizia a chattare", "Commencer à discuter"]
  };

  const catalogs = {el: {}, it: {}, fr: {}};
  for (const [english, translations] of Object.entries(rows)) {
    catalogs.el[english] = translations[0];
    catalogs.it[english] = translations[1];
    catalogs.fr[english] = translations[2];
  }
  const aliases = {English: "en", Greek: "el", Italian: "it", French: "fr"};
  const protectedSelector = "script,style,textarea,#messages,#chat-list,#entity-rows,[data-i18n-ignore]";
  const originals = new WeakMap();
  const rendered = new WeakMap();
  const attributeOriginals = new WeakMap();
  let preference = "auto";
  let locale = "en";

  function browserLocale() {
    for (const value of navigator.languages || [navigator.language || "en"]) {
      const candidate = String(value).toLowerCase().split("-")[0];
      if (supported[candidate]) return candidate;
    }
    return "en";
  }
  function resolveLocale(value) {
    const clean = String(value || "auto").trim();
    if (!clean || clean.toLowerCase() === "auto") return browserLocale();
    const candidate = aliases[clean] || clean.toLowerCase().split("-")[0];
    return supported[candidate] ? candidate : "en";
  }
  function translate(value) {
    const source = String(value || "");
    return locale === "en" ? source : catalogs[locale]?.[source] || source;
  }
  function isProtected(node) {
    const parent = node.nodeType === Node.ELEMENT_NODE ? node : node.parentElement;
    return !parent || Boolean(parent.closest(protectedSelector));
  }
  function translateText(node) {
    if (isProtected(node) || !node.data.trim()) return;
    const current = node.data;
    if (!originals.has(node) || (rendered.has(node) && current !== rendered.get(node))) originals.set(node, current);
    const source = originals.get(node);
    const leading = source.match(/^\s*/)?.[0] || "";
    const trailing = source.match(/\s*$/)?.[0] || "";
    const next = `${leading}${translate(source.trim())}${trailing}`;
    rendered.set(node, next);
    if (current !== next) node.data = next;
  }
  function translateAttributes(element) {
    if (isProtected(element)) return;
    let saved = attributeOriginals.get(element);
    if (!saved) { saved = {}; attributeOriginals.set(element, saved); }
    for (const name of ["aria-label", "title", "placeholder"]) {
      if (!element.hasAttribute(name)) continue;
      if (!(name in saved)) saved[name] = element.getAttribute(name);
      const next = translate(saved[name]);
      if (element.getAttribute(name) !== next) element.setAttribute(name, next);
    }
  }
  function apply(root = document) {
    document.documentElement.lang = locale;
    if (root.nodeType === Node.TEXT_NODE) translateText(root);
    if (root.nodeType === Node.ELEMENT_NODE) translateAttributes(root);
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
      if (walker.currentNode.nodeType === Node.TEXT_NODE) translateText(walker.currentNode);
      else translateAttributes(walker.currentNode);
    }
    window.dispatchEvent(new CustomEvent("zbrano:language-applied", {detail: {locale, preference}}));
  }
  function setPreference(value) {
    preference = String(value || "auto");
    locale = resolveLocale(preference);
    try { localStorage.setItem("zbrano_interface_language_v1", preference); } catch {}
    apply(document);
  }

  try { preference = localStorage.getItem("zbrano_interface_language_v1") || "auto"; } catch {}
  locale = resolveLocale(preference);
  apply(document);
  new MutationObserver(records => {
    for (const record of records) {
      if (record.type === "characterData") translateText(record.target);
      for (const node of record.addedNodes) apply(node);
    }
  }).observe(document.body, {childList: true, characterData: true, subtree: true});
  window.ZbranoI18n = Object.freeze({apply, setPreference, t: translate, get locale() { return locale; }, supported});
})();
