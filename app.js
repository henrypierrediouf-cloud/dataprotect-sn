




// ===== NAVIGATION =====
function showPage(id) {
  var target = document.getElementById('page-' + id);
  if (!target) return;
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  target.classList.add('active');
  document.querySelectorAll('.nav-links a').forEach(a => a.classList.remove('active'));
  const navEl = document.getElementById('nav-' + id);
  if(navEl) navEl.classList.add('active');
  window.scrollTo(0, 0);
  if(id === 'guide' && !quizInitialized) { quizInitialized = true; selectQuizCat('all'); initQuizCats(); }
  // Ferme le menu mobile si ouvert
  var mm=document.getElementById('mobileMenu'); if(mm) mm.classList.remove('open');
  var hb=document.getElementById('hamburger'); if(hb) hb.classList.remove('open');
}

// ===== MOBILE MENU =====
function toggleMenu() {
  const m = document.getElementById('mobileMenu');
  const h = document.getElementById('hamburger');
  m.classList.toggle('open');
  h.classList.toggle('open');
}

// ===== ACCORDION GUIDE =====
function toggleStep(header) {
  const step = header.parentElement;
  step.classList.toggle('open');
}

// ===== RESSOURCES FILTER =====
function filterRes(cat, btn) {
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  document.querySelectorAll('.res-card').forEach(card => {
    card.style.display = (cat === 'all' || card.dataset.cat === cat) ? '' : 'none';
  });
}

// ===== ARTICLES =====
const articles = {
  a1:{
    badges:["b-cdp","b-new"],badgeLabels:["CDP","Avril 2026"],
    title:"Bilan Q1 2026 - CDP Senegal : controles renforces sur les fintechs",
    date:"Avril 2026",readTime:"6 min",source:"CDP Senegal / Seneweb",
    intro:"La CDP a traite 112 dossiers au Q1 2026, un record. Les fintechs sont dans le viseur avec 3 mises en demeure simultanees.",
    body:"<h2>Intensification des controles</h2><p>La CDP a traite 112 dossiers au Q1 2026. Wave, Orange Money et Free Money ont recu des courriers de verification concernant leurs politiques de partage de donnees (Art. 18 Loi 2008-12).</p><h2>3 mises en demeure officielles</h2><p>Pour la premiere fois, la CDP a emis 3 mises en demeure simultanees : absence de registre des traitements, collecte excessive de donnees biometriques sans base legale, transferts vers pays tiers sans notification.</p><div class=\"source-box\"><strong>Source :</strong> CDP Senegal / Seneweb</div>"
  },
  a2:{
    badges:["b-rgpd","b-new"],badgeLabels:["RGPD","Mars 2026"],
    title:"RGPD : Meta condamne a 1,2 milliard euros - record mondial",
    date:"Mars 2026",readTime:"5 min",source:"DPC Irlande / CNIL",
    intro:"La DPC irlandaise inflige une amende historique de 1,2 milliard euros a Meta pour transfert illegal de donnees europeennes vers les USA.",
    body:"<h2>Amende record RGPD</h2><p>La DPC irlandaise a confirme en mars 2026 une amende de 1,2 milliard euros contre Meta pour transfert de donnees vers les USA en violation des Art. 44-49 RGPD.</p><h2>Impact pour les entreprises africaines</h2><p>Toute entreprise mondiale traitant des donnees de residents europeens doit respecter le RGPD sur les transferts. Une startup senegalaise sans Clauses Contractuelles Types (CCT) est exposee aux memes risques.</p><div class=\"source-box\"><strong>Source :</strong> DPC Irlande / CNIL France</div>"
  },
  a3:{
    badges:["b-tech","b-new"],badgeLabels:["IA Act","Fevrier 2026"],
    title:"IA Act : les premieres interdictions en vigueur depuis fevrier 2026",
    date:"Fevrier 2026",readTime:"7 min",source:"Commission europeenne / CNIL",
    intro:"Depuis le 2 fevrier 2026, les systemes IA interdits par le reglement europeen sont bannis en Europe. Impact direct pour les entreprises africaines exportant vers UE.",
    body:"<h2>Ce qui est interdit depuis fevrier 2026</h2><p>Sont desormais interdits dans UE : systemes de scoring social gouvernemental, IA de manipulation comportementale, reconnaissance faciale en temps reel dans espaces publics.</p><h2>Impact pour les entreprises senegalaises</h2><p>Toute entreprise senegalaise fournissant un systeme IA utilise dans UE est soumise au reglement (portee extraterritoriale Art. 2). Cela inclut startups IA, editeurs RH, plateformes de scoring.</p><div class=\"source-box\"><strong>Source :</strong> Commission europeenne / CNIL / EUR-Lex</div>"
  },
  a4:{
    badges:["b-loi","b-new"],badgeLabels:["Reforme","Janvier 2026"],
    title:"Reforme Loi 2008-12 : projet depose a Assemblee nationale senegalaise",
    date:"Janvier 2026",readTime:"6 min",source:"Assemblee Nationale SN",
    intro:"Le gouvernement senegalais a depose en janvier 2026 un projet de reforme de la Loi 2008-12 : portabilite, sanctions jusqu a 50M FCFA, DPO obligatoire.",
    body:"<h2>Grands changements du projet</h2><p>Le projet de reforme introduit : droit a la portabilite des donnees, obligation de nommer un DPO pour organisations traitant plus de 5000 personnes, sanctions pouvant atteindre 50 millions FCFA (contre 10M actuellement).</p><h2>Droit a effacement renforce</h2><p>Droit a oubli numerique pour les mineurs et droit a explication des decisions automatisees, inspires des Art. 17 et 22 RGPD.</p><div class=\"source-box\"><strong>Source :</strong> Assemblee Nationale SN / Ministere du Numerique</div>"
  },
  a5:{
    badges:["b-afrique","b-new"],badgeLabels:["Afrique","Decembre 2025"],
    title:"Nigeria NDPA 2025 : les premieres amendes tombent",
    date:"Decembre 2025",readTime:"5 min",source:"NDPC Nigeria",
    intro:"La Commission nigeriane de protection des donnees a prononce ses premieres amendes en 2025. 12 entreprises sanctionnees dont deux multinationales.",
    body:"<h2>Nigeria pionnier africain</h2><p>La NDPC nigeriane a prononce 12 amendes en 2025 : une banque internationale (890M NGN) et une plateforme e-commerce (320M NGN). Motifs : absence de politique de confidentialite, collecte sans consentement, transferts non encadres.</p><h2>Ce que le Senegal peut apprendre</h2><p>Le Senegal dispose de la CDP creee en 2008. La reforme en cours devrait renforcer ses pouvoirs. Les entreprises ont interet a se conformer des maintenant plutot que subir les premieres sanctions.</p><div class=\"source-box\"><strong>Source :</strong> NDPC Nigeria / Business Day / RAPDP</div>"
  },
  a6:{
    badges:["b-cdp"],badgeLabels:["CDP","Novembre 2025"],
    title:"CDP Senegal : premier guide sectoriel pour etablissements de sante",
    date:"Novembre 2025",readTime:"4 min",source:"CDP Senegal",
    intro:"La CDP a publie en novembre 2025 son premier guide sectoriel dedie aux etablissements de sante. Hopitaux et cliniques ont desormais un referentiel clair.",
    body:"<h2>Un guide tres attendu</h2><p>La CDP a publie un guide de 48 pages pour hopitaux, cliniques, laboratoires et pharmacies sur le traitement des donnees de sante (categorie speciale Art. 46 Loi 2008-12).</p><h2>Obligations specifiques sante</h2><p>Les donnees de sante necessitent une autorisation prealable de la CDP. Conservation minimale : 10 ans pour dossiers medicaux. Mesures de securite renforcees obligatoires pour dossiers numeriques.</p><div class=\"source-box\"><strong>Source :</strong> CDP Senegal - cdp.sn</div>"
  }
};

const quizAllData = [
  // Loi 2008-12
  {cat:'loi',q:"Numero et date de la loi senegalaise sur la protection des donnees ?",options:["Loi 2004-05","Loi 2008-12 du 25 janvier 2008","Loi 2011-01","Loi 2016-29"],correct:1,explanation:"La Loi 2008-12 du 25 janvier 2008 est le texte fondateur de la protection des donnees au Senegal. Elle a cree la CDP."},
  {cat:'loi',q:"Quelle autorite controle la protection des donnees au Senegal ?",options:["La CNIL","L'ARTP","La CDP","Le Ministere de la Justice"],correct:2,explanation:"La CDP (Commission des Donnees Personnelles) est l'autorite independante creee par la Loi 2008-12 pour veiller au respect de la vie privee."},
  {cat:'loi',q:"Quelle formalite est obligatoire avant de traiter des donnees personnelles ?",options:["Aucune formalite","Envoyer un email a la CDP","Une declaration prealable a la CDP","Un simple enregistrement commercial"],correct:2,explanation:"Art. 18 Loi 2008-12 : toute mise en oeuvre d'un traitement de donnees personnelles necessite une declaration prealable aupres de la CDP."},
  {cat:'loi',q:"Sanction pecuniaire maximale que peut prononcer la CDP ?",options:["1 million FCFA","5 millions FCFA","10 millions FCFA","50 millions FCFA"],correct:2,explanation:"La CDP peut prononcer des sanctions jusqu'a 10 millions de FCFA. Le projet de reforme 2026 envisage de porter ce plafond a 50 millions FCFA."},
  {cat:'loi',q:"Quelles donnees sont considerees sensibles selon la Loi 2008-12 ?",options:["Noms et prenoms","Donnees de sante, biometriques et opinions politiques/religieuses","Adresses email","Numeros de telephone"],correct:1,explanation:"Art. 46 Loi 2008-12 : sont sensibles les donnees de sante, biometriques, opinions politiques, convictions religieuses et origine ethnique ou raciale."},
  {cat:'loi',q:"Quel droit permet a un citoyen de demander la copie de ses donnees ?",options:["Droit d'opposition","Droit a l'oubli","Droit d'acces","Droit de portabilite"],correct:2,explanation:"Le droit d'acces (Art. 48 decret d'application) permet a toute personne d'obtenir communication des donnees la concernant detenues par un organisme."},
  {cat:'loi',q:"Devant quelle juridiction peut-on contester une decision de la CDP ?",options:["Tribunal de grande instance de Dakar","Conseil d'Etat","Cour d'appel de Dakar","Cour supreme"],correct:2,explanation:"Art. 39 Loi 2008-12 : les decisions de la CDP peuvent faire l'objet d'un recours devant la Cour d'appel de Dakar dans un delai de deux mois."},
  {cat:'loi',q:"Quelle nouveaute introduit le projet de reforme 2026 de la Loi 2008-12 ?",options:["Suppression de la CDP","Obligation de nommer un DPO pour les grandes organisations","Autorisation de vendre des donnees","Suppression du droit d'acces"],correct:1,explanation:"Le projet de reforme 2026 prevoit l'obligation de nommer un DPO (Delegue a la Protection des Donnees) pour les organisations traitant plus de 5000 personnes."},
  // RGPD
  {cat:'rgpd',q:"Depuis quand le RGPD est applicable en Europe ?",options:["25 mai 2016","25 mai 2018","25 janvier 2020","1er janvier 2021"],correct:1,explanation:"Le RGPD (Reglement General sur la Protection des Donnees) est entre en application le 25 mai 2018, deux ans apres sa publication au Journal officiel de l'UE."},
  {cat:'rgpd',q:"Amende maximale du RGPD pour les violations graves ?",options:["100 000 euros","1 million euros","20 millions euros ou 4% du CA mondial","50 millions euros"],correct:2,explanation:"Art. 83.5 RGPD : les violations les plus graves peuvent entrainer des amendes allant jusqu'a 20 millions d'euros ou 4% du chiffre d'affaires annuel mondial."},
  {cat:'rgpd',q:"Le RGPD s'applique-t-il aux entreprises senegalaises traitant des donnees de residents europeens ?",options:["Non, jamais","Oui, portee extraterritoriale (Art. 3)","Seulement si elles ont un bureau en Europe","Seulement pour les entreprises de plus de 50 employes"],correct:1,explanation:"Art. 3 RGPD : le reglement s'applique a toute organisation dans le monde qui traite des donnees de residents de l'UE, peu importe ou elle est etablie."},
  {cat:'rgpd',q:"Quel droit du RGPD n'existe pas dans la Loi 2008-12 actuelle ?",options:["Droit d'acces","Droit de rectification","Droit a la portabilite","Droit d'opposition"],correct:2,explanation:"Le droit a la portabilite (Art. 20 RGPD) permet d'obtenir ses donnees dans un format lisible par machine pour les transferer. Il n'existe pas encore dans la Loi 2008-12."},
  {cat:'rgpd',q:"Qu'est-ce qu'une AIPD (Analyse d'Impact sur la Protection des Donnees) ?",options:["Un rapport annuel obligatoire","Une evaluation prealable des risques avant tout traitement a fort impact","Un formulaire d'inscription a la CDP","Un audit financier annuel"],correct:1,explanation:"Art. 35 RGPD : l'AIPD est obligatoire avant tout traitement susceptible d'engendrer un risque eleve pour les droits des personnes (reconnaissance faciale, scoring, etc.)."},
  {cat:'rgpd',q:"Quelle amende historique a recu Meta en 2023 ?",options:["150 millions euros","530 millions euros","1,2 milliard euros","800 millions euros"],correct:2,explanation:"En mai 2023, la DPC irlandaise a inflige a Meta une amende record de 1,2 milliard euros pour transfert illegal de donnees europeennes vers les Etats-Unis."},
  {cat:'rgpd',q:"En quoi consiste le droit a l'effacement (droit a l'oubli) du RGPD ?",options:["Supprimer son compte email","Demander la suppression de ses donnees lorsque leur conservation n'est plus justifiee","Effacer ses photos des reseaux sociaux","Annuler une commande en ligne"],correct:1,explanation:"Art. 17 RGPD : le droit a l'effacement permet d'obtenir la suppression de ses donnees quand elles ne sont plus necessaires, quand le consentement est retire ou en cas de traitement illicite."},
  // IA Act
  {cat:'ia',q:"Depuis quand les premieres interdictions de l'IA Act sont-elles en vigueur dans l'UE ?",options:["Aout 2024","Fevrier 2025","Aout 2025","Fevrier 2026"],correct:3,explanation:"Les interdictions absolues de l'IA Act (scoring social, IA manipulatrice, reconnaissance faciale en temps reel dans les espaces publics) sont entrees en vigueur le 2 fevrier 2026."},
  {cat:'ia',q:"Quelle autorite francaise regule desormais l'IA en France ?",options:["Le CSA","L'ARCEP","La CNIL","L'AMF"],correct:2,explanation:"Depuis aout 2025, la CNIL est officiellement l'autorite nationale de supervision de l'intelligence artificielle en France au titre de l'IA Act europeen."},
  {cat:'ia',q:"L'IA Act s'applique-t-il aux entreprises senegalaises exportant des systemes IA vers l'UE ?",options:["Non, jamais","Oui, portee extraterritoriale comme le RGPD","Seulement si elles ont un partenaire europeen","Seulement pour les systemes d'IA a haut risque"],correct:1,explanation:"Art. 2 IA Act : le reglement s'applique a toute organisation mondiale fournissant des systemes d'IA utilises dans l'UE. Une startup senegalaise vendant une solution IA en Europe est concernee."},
];

const quizCategories = [
  {key:'all', label:'Tout ('+quizAllData.length+' questions)'},
  {key:'loi', label:'Loi 2008-12'},
  {key:'rgpd', label:'RGPD'},
  {key:'ia', label:'IA Act'},
];

let quizData = [], currentQ = 0, score = 0, answered = false, quizInitialized = false;
let quizWrong = [], quizTimerInterval = null, quizTimeLeft = 30, activeCategory = 'all';

function shuffleArray(arr) {
  var a = arr.slice();
  for(var i = a.length - 1; i > 0; i--) { var j = Math.floor(Math.random()*(i+1)); var t=a[i]; a[i]=a[j]; a[j]=t; }
  return a;
}

function initQuizCats() {
  var el = document.getElementById('quizCats');
  if(!el) return;
  el.innerHTML = quizCategories.map(function(c) {
    return '<button class="quiz-cat-btn'+(c.key===activeCategory?' active':'')+'" onclick="selectQuizCat(\''+c.key+'\')">'+c.label+'</button>';
  }).join('');
}

function selectQuizCat(cat) {
  activeCategory = cat;
  quizData = shuffleArray(cat==='all' ? quizAllData : quizAllData.filter(function(q){return q.cat===cat;}));
  currentQ = 0; score = 0; quizWrong = [];
  initQuizCats();
  clearQuizTimer();
  renderQuiz();
}

function startQuizTimer() {
  clearQuizTimer();
  quizTimeLeft = 30;
  updateTimerDisplay();
  quizTimerInterval = setInterval(function() {
    quizTimeLeft--;
    updateTimerDisplay();
    if(quizTimeLeft <= 0) { clearQuizTimer(); if(!answered) answerQuiz(-1); }
  }, 1000);
}

function clearQuizTimer() {
  if(quizTimerInterval) { clearInterval(quizTimerInterval); quizTimerInterval = null; }
}

function updateTimerDisplay() {
  var t = document.getElementById('quizTimer');
  var f = document.getElementById('quizTimerFill');
  if(!t) return;
  t.textContent = quizTimeLeft;
  t.className = 'quiz-timer' + (quizTimeLeft <= 8 ? ' urgent' : '');
  if(f) { f.style.width = (quizTimeLeft/30*100)+'%'; f.className = 'quiz-timer-fill'+(quizTimeLeft<=8?' urgent':''); }
}

function renderQuiz() {
  var counterEl = document.getElementById('quizCounter');
  var okEl = document.getElementById('qlOk');
  var koEl = document.getElementById('qlKo');
  if(counterEl) counterEl.textContent = quizData.length ? 'Question '+(currentQ+1)+' / '+quizData.length : '';
  if(okEl) okEl.textContent = '✓ '+score;
  if(koEl) koEl.textContent = '✗ '+(currentQ - score - (answered?0:0));
  if(currentQ >= quizData.length && quizData.length > 0) {
    clearQuizTimer();
    showQuizResult();
    return;
  }
  if(!quizData.length) {
    document.getElementById('quizCard').innerHTML = '<div style="text-align:center;padding:2rem;color:var(--muted)">Selectionnez une categorie pour commencer.</div>';
    document.getElementById('quizBar').style.width = '0%';
    return;
  }
  var q = quizData[currentQ];
  document.getElementById('quizBar').style.width = (currentQ/quizData.length*100)+'%';
  answered = false;
  document.getElementById('quizCard').innerHTML =
    '<div class="quiz-q">'+q.q+'</div>'+
    '<div class="quiz-options">'+
    q.options.map(function(o,i){ return '<button class="quiz-option" data-answer="'+i+'">'+o+'</button>'; }).join('')+
    '</div>'+
    '<div id="quizExp" style="display:none" class="quiz-explanation"></div>'+
    '<div class="quiz-nav" id="quizNav" style="display:none">'+
    '<span style="font-size:.82rem;color:var(--muted)">'+score+' correcte(s) sur '+(currentQ+(answered?1:0))+'</span>'+
    '<button class="btn-gold" data-quiz-next="1">'+(currentQ < quizData.length-1 ? 'Suivant →' : 'Voir mon score →')+'</button>'+
    '</div>';
  startQuizTimer();
}

function answerQuiz(idx) {
  if(answered) return;
  answered = true;
  clearQuizTimer();
  var q = quizData[currentQ];
  var opts = document.querySelectorAll('.quiz-option');
  opts.forEach(function(o){ o.disabled = true; });
  if(idx >= 0) opts[idx].classList.add(idx===q.correct?'correct':'wrong');
  if(idx !== q.correct) opts[q.correct].classList.add('correct');
  if(idx === q.correct) { score++; }
  else { quizWrong.push({q:q.q, correct:q.options[q.correct], explanation:q.explanation}); }
  var expEl = document.getElementById('quizExp');
  if(expEl) { expEl.style.display='block'; expEl.textContent = (idx<0?'⏱ Temps ecoule ! ':'')+q.explanation; }
  var navEl = document.getElementById('quizNav');
  if(navEl) {
    navEl.style.display='flex';
    var scoreSpan = navEl.querySelector('span');
    if(scoreSpan) scoreSpan.textContent = score+' correcte(s) sur '+(currentQ+1);
  }
  var okEl = document.getElementById('qlOk'); if(okEl) okEl.textContent='✓ '+score;
  var koEl = document.getElementById('qlKo'); if(koEl) koEl.textContent='✗ '+quizWrong.length;
}

function showQuizResult() {
  var pct = Math.round((score/quizData.length)*100);
  var medal = pct>=90?'🥇':pct>=70?'🥈':pct>=50?'🥉':'📚';
  var msg = pct>=90?'Excellent ! Vous maîtrisez parfaitement la protection des donnees.':
            pct>=70?'Bon resultat ! Quelques points a approfondir.':
            pct>=50?'Pas mal ! Continuez a explorer nos ressources.':
            'Continuez a vous former — nos ressources sont la pour vous aider !';
  var reviewHtml = '';
  if(quizWrong.length) {
    reviewHtml = '<div class="quiz-review">'+
      '<div class="quiz-review-title">Questions ratees ('+quizWrong.length+')</div>'+
      quizWrong.map(function(w){
        return '<div class="quiz-review-item ko">'+
          '<strong>Q : </strong>'+w.q+'<br>'+
          '<strong>Reponse : </strong>'+w.correct+'<br>'+
          '<span style="font-size:.8rem;opacity:.8">'+w.explanation+'</span></div>';
      }).join('')+'</div>';
  }
  document.getElementById('quizBar').style.width='100%';
  document.getElementById('quizCard').innerHTML =
    '<div class="quiz-result">'+
    '<span class="quiz-medal">'+medal+'</span>'+
    '<div class="quiz-score">'+score+'/'+quizData.length+'</div>'+
    '<div class="quiz-pct">'+pct+'% de bonnes reponses</div>'+
    '<div class="quiz-result-msg">'+msg+'</div>'+
    '<div class="quiz-result-btns">'+
    '<button class="btn-gold" data-quiz-restart="1">🔄 Recommencer</button>'+
    '<button class="btn-ghost-w" style="background:var(--green);color:#fff;border:none;padding:.65rem 1.5rem;border-radius:100px;cursor:pointer;font-size:.88rem" data-nav="ressources">📚 Voir les ressources</button>'+
    '</div>'+reviewHtml+'</div>';
  var counterEl = document.getElementById('quizCounter'); if(counterEl) counterEl.textContent='';
  var t = document.getElementById('quizTimer'); if(t) t.textContent='';
  var f = document.getElementById('quizTimerFill'); if(f) f.style.width='0';
}

// Quiz initialized when guide page is first shown

// Toast notification for resource downloads
function showToast(msg) {
  let t = document.getElementById('toast');
  if(!t) {
    t = document.createElement('div');
    t.id = 'toast';
    t.style.cssText = 'position:fixed;bottom:2rem;left:50%;transform:translateX(-50%);background:#1a2744;color:#fff;padding:.75rem 1.5rem;border-radius:100px;font-size:.88rem;z-index:999;opacity:0;transition:opacity .3s;pointer-events:none;font-family:DM Sans,sans-serif';
    document.body.appendChild(t);
  }
  t.textContent = msg;
  t.style.opacity = '1';
  setTimeout(() => t.style.opacity = '0', 3000);
}

// Attach toast to all download spans
document.addEventListener('DOMContentLoaded', () => {
  showPage('home');
  loadDbArticles();
  if (!localStorage.getItem('ck_consent')) {
    setTimeout(() => {
      var banner = document.getElementById('cookie-banner');
      if (banner) banner.classList.add('show');
    }, 1500);
  }
});


var dbArticles = {};

function loadDbArticles() {
  fetch('/api/articles').then(function(r){ return r.json(); }).then(function(data) {
    var list = document.querySelector('.blog-list');
    if (!list) return;
    data.forEach(function(a) {
      var key = 'db-' + a.id;
      dbArticles[key] = a;
      if (document.querySelector('[data-article="' + key + '"]')) return;
      var badgeClass = a.badge || 'b-cdp';
      var badgeLabel = a.categorie || 'Actualité';
      var card = document.createElement('div');
      card.className = 'article-card';
      card.setAttribute('data-article', key);
      card.innerHTML = '<div class="article-top"><span class="badge ' + badgeClass + '">' + badgeLabel + '</span></div>' +
        '<div class="article-title">' + (a.titre || '') + '</div>' +
        '<div class="article-excerpt">' + (a.extrait || '') + '</div>' +
        '<div class="article-meta"><span>📅 ' + (a.date_publication ? a.date_publication.slice(0,10) : '') + '</span>' +
        (a.source ? '<span>Source : ' + a.source + '</span>' : '') + '</div>' +
        '<span class="read-more">Lire l\'article →</span>';
      list.appendChild(card);
    });
  }).catch(function(){});
}

function showArticle(id) {
  var art = articles[id] ? {
    title: articles[id].title, date: articles[id].date,
    readTime: articles[id].readTime, source: articles[id].source,
    badges: articles[id].badges, badgeLabels: articles[id].badgeLabels,
    intro: articles[id].intro, body: articles[id].body
  } : null;
  if (!art && dbArticles[id]) {
    var d = dbArticles[id];
    art = {
      title: d.titre, date: d.date_publication ? d.date_publication.slice(0,10) : '',
      readTime: '', source: d.source || '',
      badges: [d.badge || 'b-cdp'], badgeLabels: [d.categorie || 'Actualité'],
      intro: d.extrait || '', body: d.contenu || d.extrait || ''
    };
  }
  if (!art) return;
  showPage('article');
  var container = document.getElementById('article-content');
  if (!container) return;
  container.innerHTML = 
    '<div style="max-width:800px;margin:0 auto;padding:2rem 1.5rem">' +
    '<a data-nav="blog" style="cursor:pointer;color:var(--green);font-size:.88rem;display:inline-flex;align-items:center;gap:.35rem;margin-bottom:1.5rem;font-weight:500">' +
    '&larr; Retour a la veille</a>' +
    '<div style="display:flex;gap:.5rem;flex-wrap:wrap;margin-bottom:1rem">' +
    (art.badges || []).map(function(b,i){ 
      return '<span class="badge ' + b + '">' + (art.badgeLabels || [])[i] + '</span>'; 
    }).join('') +
    '</div>' +
    '<h1 style="font-size:clamp(1.4rem,3.5vw,2rem);font-weight:800;color:var(--text);line-height:1.25;margin:0 0 1rem;letter-spacing:-.02em">' + art.title + '</h1>' +
    '<div style="display:flex;gap:1.5rem;flex-wrap:wrap;font-size:.82rem;color:var(--muted);margin-bottom:2rem;padding-bottom:1.25rem;border-bottom:1px solid var(--border)">' +
    '<span>&#128197; ' + (art.date || '') + '</span>' +
    '<span>&#9201; ' + (art.readTime || '') + '</span>' +
    '<span>&#128196; ' + (art.source || '') + '</span>' +
    '</div>' +
    '<div style="background:var(--green-light);border-left:4px solid var(--green);border-radius:0 10px 10px 0;padding:1rem 1.25rem;margin-bottom:1.75rem;font-size:.92rem;line-height:1.7;color:var(--text)">' +
    (art.intro || '') + '</div>' +
    '<div class="article-body" style="line-height:1.85;font-size:.93rem;color:var(--text-secondary)">' +
    (art.body || '') + '</div>' +
    '</div>';
}

// LISTENER PRINCIPAL
document.addEventListener('click', function(e) {
  var t;
  t = e.target.closest ? e.target.closest('[data-nav]') : null;
  if(t && t.dataset && t.dataset.nav) { e.preventDefault(); showPage(t.dataset.nav); return; }
  t = e.target.closest ? e.target.closest('[data-toggle-menu]') : null;
  if(t) { var mm=document.getElementById('mobileMenu'); var hb=document.getElementById('hamburger'); if(mm)mm.classList.toggle('open'); if(hb)hb.classList.toggle('open'); return; }
  t = e.target.closest ? e.target.closest('[data-article]') : null;
  if(t && t.dataset.article) { showArticle(t.dataset.article); return; }
  t = e.target.closest ? e.target.closest('[data-reg]') : null;
  if(t && t.dataset.reg) { document.querySelectorAll('#reg-tabs .filter-btn').forEach(function(b){b.classList.remove('active');}); t.classList.add('active'); currentReg=t.dataset.reg; renderReg(currentReg); return; }
  t = e.target.closest ? e.target.closest('[data-accordion]') : null;
  if(t) { t.parentElement.classList.toggle('open'); return; }
  t = e.target.closest ? e.target.closest('[data-filter]') : null;
  if(t && t.dataset.filter) { var cat=t.dataset.filter; document.querySelectorAll('.filter-btn').forEach(function(b){b.classList.remove('active');}); t.classList.add('active'); document.querySelectorAll('.res-card').forEach(function(c){c.style.display=(cat==='all'||c.dataset.cat===cat)?'':'none';}); return; }
  t = e.target.closest ? e.target.closest('[data-faq]') : null;
  if(t) { var item=t.parentElement; var wasOpen=item.classList.contains('open'); document.querySelectorAll('.faq-item').forEach(function(i){i.classList.remove('open');}); if(!wasOpen)item.classList.add('open'); return; }
  t = e.target.closest ? e.target.closest('[data-letter]') : null;
  if(t && t.dataset.letter) { document.querySelectorAll('.alpha-btn').forEach(function(b){b.classList.remove('active');}); t.classList.add('active'); currentLetter=t.dataset.letter; var s=document.getElementById('glossaireSearch'); renderGlossaire(currentLetter, s?s.value:''); return; }
  if(e.target.id==='darkToggle') { var isDark=document.documentElement.getAttribute('data-theme')==='dark'; applyTheme(!isDark); return; }
  t = e.target.closest ? e.target.closest('[data-nl-btn]') : null;
  if(t) { var prenom=document.getElementById('nl-prenom')||document.getElementById('nl-prenom-blog');
    var nlEmail=document.getElementById('nl-email')||document.getElementById('nl-email-blog');
    if(!prenom||!prenom.value.trim()||!nlEmail||!nlEmail.value.trim()){showToast('Entrez votre prenom et email.');return;} t.textContent='Envoi...'; t.disabled=true; fetch('/api/newsletter',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prenom:prenom.value.trim(),email:nlEmail.value.trim()})}).then(function(r){return r.json();}).then(function(data){t.textContent=data.success?'Inscription confirmee !':'Email deja inscrit';t.style.background=data.success?'#fff3ec':'#f5c842';if(data.success){prenom.value='';nlEmail.value='';}setTimeout(function(){t.textContent="S'abonner";t.style.background='';t.disabled=false;},3000);}).catch(function(){t.textContent="S'abonner";t.disabled=false;}); return; }
  t = e.target.closest ? e.target.closest('[data-contact-btn]') : null;
  if(t) { var nom=document.getElementById('c-nom'); var email=document.getElementById('c-email'); var org=document.getElementById('c-org'); var besoin=document.getElementById('c-besoin'); var msg=document.getElementById('c-message'); if(!nom||!nom.value.trim()||!email||!email.value.trim()||!msg||!msg.value.trim()){showToast('Remplissez nom, email et message.');return;} t.textContent='Envoi...'; t.disabled=true; fetch('/api/contact',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({nom:nom.value.trim(),email:email.value.trim(),organisation:org?org.value:'',type_besoin:besoin?besoin.value:'',message:msg.value.trim()})}).then(function(r){return r.json();}).then(function(data){t.textContent='Message envoye !';t.style.background='#2d8a52';if(nom)nom.value='';if(email)email.value='';if(org)org.value='';if(besoin)besoin.value='';if(msg)msg.value='';setTimeout(function(){t.textContent='Envoyer';t.style.background='';t.disabled=false;},4000);}).catch(function(){t.textContent='Envoyer';t.disabled=false;showToast('Erreur serveur.');}); return; }
  t = e.target.closest ? e.target.closest('[data-answer]') : null;
  if(t && t.dataset.answer !== undefined) { answerQuiz(parseInt(t.dataset.answer)); return; }
  t = e.target.closest ? e.target.closest('[data-quiz-next]') : null;
  if(t) { currentQ++; renderQuiz(); return; }
  t = e.target.closest ? e.target.closest('[data-quiz-restart]') : null;
  if(t) { currentQ=0; score=0; answered=false; renderQuiz(); return; }
  t = e.target.closest ? e.target.closest('.res-dl') : null;
  if(t) { if(!t.getAttribute('href')) { showToast('Document disponible prochainement !'); return; } else { return; } }
  if(e.target.closest && e.target.closest('#chatbot-btn') && !e.target.closest('#chatbot-window')) { var cw=document.getElementById('chatbot-window'); if(cw){chatOpen=!chatOpen;cw.classList.toggle('open',chatOpen);if(chatOpen){var ci=document.getElementById('chatInput');if(ci)ci.focus();}} return; }
  if(e.target.id==='chatClose'){chatOpen=false;var cw2=document.getElementById('chatbot-window');if(cw2)cw2.classList.remove('open');return;}
  if(e.target.id==='chatSend'){sendChat();return;}
  t = e.target.closest ? e.target.closest('[data-sug]') : null;
  if(t){var ci2=document.getElementById('chatInput');if(ci2){ci2.value=t.dataset.sug;sendChat();}return;}
  if(e.target.id==='ck-accept'||e.target.id==='ck-modal-accept'){savePref(true,true);return;}
  if(e.target.id==='ck-refuse'||e.target.id==='ck-modal-refuse'){savePref(false,false);return;}
  if(e.target.id==='ck-custom'||e.target.id==='ck-manage-btn'){showCkModal();return;}
  if(e.target.id==='ck-modal-save'){var a2=document.getElementById('ck-analytics');var p2=document.getElementById('ck-perso');savePref(a2&&a2.checked,p2&&p2.checked);return;}
  if(e.target===document.getElementById('cookie-modal')){hideCkModal();return;}
});
document.addEventListener('keydown',function(e){if(e.key==='Enter'&&document.activeElement&&document.activeElement.id==='chatInput')sendChat();});
function applyTheme(dark){document.documentElement.setAttribute('data-theme',dark?'dark':'');try{localStorage.setItem('theme',dark?'dark':'light');}catch(er){}var btn=document.getElementById('darkToggle');if(btn)btn.innerHTML=dark?'Jour':'Nuit';}
try{if(localStorage.getItem('theme')==='dark')applyTheme(true);}catch(er){}
var chatHistory=[],chatOpen=false;
function addChatMsg(text,role){var msgs=document.getElementById('chatMessages');if(!msgs)return;var d=document.createElement('div');d.className='chat-msg '+role;d.innerHTML=text.replace(/\n/g,'<br>');msgs.appendChild(d);msgs.scrollTop=msgs.scrollHeight;}
function showTyping(){var msgs=document.getElementById('chatMessages');if(!msgs)return;var d=document.createElement('div');d.className='chat-msg typing';d.id='typingDot';d.innerHTML='<div class="typing-dots"><span></span><span></span><span></span></div>';msgs.appendChild(d);msgs.scrollTop=msgs.scrollHeight;}
function removeTyping(){var t=document.getElementById('typingDot');if(t)t.remove();}
async function sendChat(){var inp=document.getElementById('chatInput');if(!inp)return;var text=inp.value.trim();if(!text)return;inp.value='';var sugs=document.getElementById('chatSugs');if(sugs)sugs.style.display='none';addChatMsg(text,'user');chatHistory.push({role:'user',content:text});showTyping();try{var res=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({messages:chatHistory.slice(-6)})});var data=await res.json();removeTyping();var reply=data.reply||data.detail||'Desole, une erreur.';chatHistory.push({role:'assistant',content:reply});addChatMsg(reply,'bot');}catch(err){removeTyping();addChatMsg('Erreur de connexion.','bot');}}
function setCookie(n,v,d){var e=new Date();e.setTime(e.getTime()+(d*864e5));document.cookie=n+'='+v+';expires='+e.toUTCString()+';path=/;SameSite=Lax';}
function getCookie(n){var a=document.cookie.split(';');for(var i=0;i<a.length;i++){var c=a[i].trim();if(c.startsWith(n+'='))return c.substring(n.length+1);}return null;}
function showCkBanner(){var b=document.getElementById('cookie-banner');if(b)b.classList.add('show');}
function hideCkBanner(){var b=document.getElementById('cookie-banner');if(b)b.classList.remove('show');}
function showCkModal(){var m=document.getElementById('cookie-modal');if(m)m.classList.add('show');}
function hideCkModal(){var m=document.getElementById('cookie-modal');if(m)m.classList.remove('show');}
function savePref(a,p){setCookie('dp_consent',JSON.stringify({n:true,a:a,p:p}),365);hideCkBanner();hideCkModal();showToast('Preferences cookies enregistrees !');}
if(!getCookie('dp_consent')){setTimeout(showCkBanner,1500);}
function showToast(msg){var t=document.getElementById('toast');if(!t){t=document.createElement('div');t.id='toast';t.style.cssText='position:fixed;bottom:2rem;left:50%;transform:translateX(-50%);background:#1a2744;color:#fff;padding:.7rem 1.4rem;border-radius:100px;font-size:.86rem;z-index:9999;opacity:0;transition:opacity .3s;pointer-events:none';document.body.appendChild(t);}t.textContent=msg;t.style.opacity='1';setTimeout(function(){t.style.opacity='0';},3000);}
