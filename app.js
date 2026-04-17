




// ===== NAVIGATION =====
function showPage(id) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.getElementById('page-' + id).classList.add('active');
  document.querySelectorAll('.nav-links a').forEach(a => a.classList.remove('active'));
  const navEl = document.getElementById('nav-' + id);
  if(navEl) navEl.classList.add('active');
  window.scrollTo(0, 0);
  if(id === 'guide' && !quizInitialized) { quizInitialized = true; renderQuiz(); }
  // Ferme le menu mobile si ouvert
  document.getElementById('mobileMenu').classList.remove('open');
  document.getElementById('hamburger').classList.remove('open');
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
    badges:["b-cdp","b-new"],
    badgeLabels:["CDP","Avril 2026"],
    title:"Bilan Q1 2026 : la CDP Senegal durcit les controles sur les fintechs",
    date:"Avril 2026",
    readTime:"6 min",
    source:"CDP Senegal / Seneweb",
    intro:"Au premier trimestre 2026, la CDP a intensifie ses controles sur les operateurs de mobile money et fintechs, avec 3 mises en demeure et un record de 112 dossiers traites.",
    body:"<h2>Intensification des controles fintechs</h2><p>La Commission des Donnees Personnelles du Senegal a traite 112 dossiers au Q1 2026, un record depuis sa creation. Les fintechs et operateurs de mobile money sont dans le viseur : Wave, Orange Money et Free Money ont toutes recu des courriers de verification concernant leurs politiques de partage de donnees avec des tiers.</p><h2>3 mises en demeure officielles</h2><p>Pour la premiere fois, la CDP a emis 3 mises en demeure simultanees contre des acteurs du secteur numerique senegalais. Les motifs : absence de registre des traitements (Art. 18 Loi 2008-12), collecte excessive de donnees biometriques sans base legale, et transfert de donnees vers des pays tiers sans notification.</p><h2>Nouveaux secteurs surveilles en 2026</h2><p>La CDP a annonce l\'extension de sa surveillance aux plateformes d\'e-commerce, aux applications de transport (Yassir, Heetch) et aux etablissements d\'enseignement qui collectent des donnees d\'eleves mineurs. Un guide sectoriel est en preparation.</p><div class=\"source-box\"><strong>Source :</strong> CDP Senegal / Seneweb / RFM Digital</div>"
  },
  a2:{
    badges:["b-rgpd","b-new"],
    badgeLabels:["RGPD","Mars 2026"],
    title:"RGPD : Meta condamne a 1,2 milliard euros - nouveau record mondial",
    date:"Mars 2026",
    readTime:"5 min",
    source:"CNIL / DPC Irlande",
    intro:"La DPC irlandaise inflige une amende historique de 1,2 milliard euros a Meta pour transfert illegal de donnees d\'europeens vers les Etats-Unis. Les implications pour les entreprises africaines exportant vers l\'UE sont majeures.",
    body:"<h2>L\'amende la plus elevee de l\'histoire du RGPD</h2><p>La Data Protection Commission irlandaise (DPC) a confirme en mars 2026 une amende record de 1,2 milliard euros contre Meta Platforms pour le transfert de donnees personnelles de citoyens europeens vers les serveurs americains de Facebook, en violation des regles RGPD sur les transferts internationaux (Art. 44-49).</p><h2>Ce que cela signifie pour les entreprises africaines</h2><p>Cette decision rappelle que toute entreprise dans le monde - y compris au Senegal - qui traite des donnees de residents europeens doit respecter les regles RGPD sur les transferts. Une startup senegalaise qui collecte des emails d\'utilisateurs europeens sans clauses contractuelles types (CCT) s\'expose aux memes risques.</p><h2>Les outils conformes disponibles</h2><p>Pour les entreprises senegalaises concernees : les CCT approuvees par la Commission europeenne en 2021, les regles d\'entreprise contraignantes (BCR), ou encore le recours a des sous-traitants certifies adequats. La CNIL propose un outil gratuit pour generer des CCT.</p><div class=\"source-box\"><strong>Source :</strong> DPC Irlande / CNIL France</div>"
  },
  a3:{
    badges:["b-tech","b-new"],
    badgeLabels:["IA Act","Fevrier 2026"],
    title:"IA Act : les premieres interdictions en vigueur depuis fevrier 2026",
    date:"Fevrier 2026",
    readTime:"7 min",
    source:"Commission europeenne / CNIL",
    intro:"Depuis le 2 fevrier 2026, les systemes IA interdits par l\'IA Act sont bannis en Europe. Scoring social, manipulation comportementale, reconnaissance faciale en temps reel : voici ce qui change concretement.",
    body:"<h2>Ce qui est interdit depuis fevrier 2026</h2><p>L\'IA Act euroeen a franchi une nouvelle etape decisive. Sont desormais totalement interdits dans l\'UE : les systemes de scoring social gouvernemental, les IA de manipulation comportementale exploitant des vulnerabilites, la reconnaissance faciale biometrique en temps reel dans les espaces publics (sauf exceptions securite nationale), et les systemes inferant des emotions en milieu professionnel ou educatif.</p><h2>Impact sur les entreprises senegalaises exportant vers l\'UE</h2><p>Toute entreprise senegalaise qui fournit un systeme IA utilise dans l\'UE est soumise a l\'IA Act (portee extraterritoriale, Art. 2). Cela inclut les startups IA, les editeurs de logiciels RH, les plateformes de scoring de credit et les outils de surveillance.</p><h2>Le calendrier complet de l\'IA Act</h2><p>Aout 2025 : designation des autorites nationales (CNIL pour la France). Fevrier 2026 : interdictions en vigueur. Aout 2026 : regles pour systemes a risque limite. Aout 2027 : obligations completes pour les systemes a risque eleve. Les entreprises ont encore le temps de se preparer.</p><div class=\"source-box\"><strong>Source :</strong> Commission europeenne / CNIL / EUR-Lex</div>"
  },
  a4:{
    badges:["b-loi","b-new"],
    badgeLabels:["Reforme","Janvier 2026"],
    title:"Reforme Loi 2008-12 : le projet de loi depose a l\'Assemblee nationale senegalaise",
    date:"Janvier 2026",
    readTime:"6 min",
    source:"Assemblee Nationale SN / Ministere du Numerique",
    intro:"Le gouvernement senegalais a depose en janvier 2026 un projet de loi de reforme de la Loi 2008-12. Nouveautes majeures : droit a la portabilite, doublement des sanctions, DPO obligatoire pour les grandes organisations.",
    body:"<h2>Les grands changements du projet de loi</h2><p>Le projet de reforme de la Loi 2008-12, depose a l\'Assemblee nationale en janvier 2026, introduit plusieurs nouveautes majeures alignees sur le RGPD europeen : le droit a la portabilite des donnees (inedi en droit senegalais), l\'obligation de nommer un DPO pour les organisations traitant plus de 5000 personnes, et un renforcement des sanctions pouvant atteindre 50 millions de FCFA (contre 10 millions actuellement).</p><h2>Le droit a l\'effacement renforce</h2><p>Le projet prevoit un droit a l\'oubli numerique applicable aux mineurs (toute donnee publiee avant 18 ans peut etre effacee sur demande) et un droit a l\'explication des decisions automatisees. Ces deux avances s\'inspirent directement des Art. 17 et 22 du RGPD.</p><h2>Calendrier prevu</h2><p>Vote prevu au second semestre 2026, entree en vigueur progressive sur 18 mois. Les entreprises senegalaises ont un interet strategique a anticiper ces changements des maintenant : nommer un DPO, tenir un registre des traitements, mettre en place une politique de confidentialite conforme.</p><div class=\"source-box\"><strong>Source :</strong> Assemblee Nationale SN / Ministere du Numerique / APS</div>"
  },
  a5:{
    badges:["b-afrique","b-new"],
    badgeLabels:["Afrique","Decembre 2025"],
    title:"Nigeria NDPA 2025 : les premieres amendes tombent - lecons pour le Senegal",
    date:"Decembre 2025",
    readTime:"5 min",
    source:"NDPC Nigeria / Business Day Nigeria",
    intro:"La Commission nigeriane de protection des donnees (NDPC) a prononce ses premieres amendes significatives en 2025. 12 entreprises sanctionnees, dont deux multinationales. Ce que le Senegal peut apprendre.",
    body:"<h2>Le Nigeria, pionnier africain de l\'application effective</h2><p>La Nigeria Data Protection Commission (NDPC), creee par le Nigeria Data Protection Act de 2023, a prononce en 2025 ses premieres amendes significatives. 12 entreprises ont ete sanctionnees, dont une banque internationale (890 millions NGN, soit environ 550 000 euros) et une plateforme e-commerce (320 millions NGN). Les motifs : absence de politique de confidentialite, collecte de donnees sans consentement, et transferts internationaux non encadres.</p><h2>Le modele nigerian comme reference continentale</h2><p>Avec une NDPC dotee de pouvoirs effectifs d\'enquete et de sanction, le Nigeria s\'impose comme le modele africain de protection des donnees. Son approche : audit sectoriel systematique, guide de conformite par secteur, et programme de certification pour les DPO. Le Rwanda et le Kenya suivent le meme chemin.</p><h2>Ce que le Senegal peut apprendre</h2><p>Le Senegal dispose d\'une CDP creeee en 2008, mais avec des moyens limites. La reforme en cours (voir article precedent) devrait renforcer son independance et ses pouvoirs. Les entreprises senegalaises ont interet a se conformer des maintenant plutot qu\'attendre les premieres sanctions.</p><div class=\"source-box\"><strong>Source :</strong> NDPC Nigeria / Business Day Nigeria / RAPDP</div>"
  },
  a6:{
    badges:["b-cdp"],
    badgeLabels:["CDP","Novembre 2025"],
    title:"CDP Senegal : guide sectoriel pour les etablissements de sante",
    date:"Novembre 2025",
    readTime:"4 min",
    source:"CDP Senegal",
    intro:"La CDP a publie en novembre 2025 son premier guide sectoriel dedie aux etablissements de sante. Hopitaux, cliniques et laboratoires ont desormais un referentiel clair pour proteger les donnees medicales.",
    body:"<h2>Un guide tres attendu par le secteur sante</h2><p>La Commission des Donnees Personnelles du Senegal a publie en novembre 2025 son premier guide sectoriel dedie aux etablissements de sante. Ce document de 48 pages etablit les regles specifiques applicables aux hopitaux, cliniques, laboratoires d\'analyses et pharmacies pour le traitement des donnees de sante (categorie speciale, Art. 46 Loi 2008-12).</p><h2>Les obligations specifiques au secteur sante</h2><p>Le guide rappelle que les donnees de sante necessitent une autorisation prealable de la CDP (et non une simple declaration). Il fixe des durees de conservation specifiques (dossier medical : 10 ans minimum), encadre le partage entre professionnels de sante, et impose des mesures de securite renforcees pour les dossiers numeriques.</p><h2>Demarche de mise en conformite en 5 etapes</h2><p>Le guide propose une demarche pragmatique : 1) cartographier tous les traitements de donnees de sante, 2) obtenir l\'autorisation CDP, 3) nommer un referent protection des donnees, 4) former le personnel medical et administratif, 5) mettre en place un registre des acces aux dossiers patients.</p><div class=\"source-box\"><strong>Source :</strong> CDP Senegal &mdash; cdp.sn</div>"
  }
};

const quizData = [
  {q:"Numero et date de la loi senegalaise sur la protection des donnees ?",options:["Loi 2004-05","Loi 2008-12 du 25 janvier 2008","Loi 2011-01","Loi 2016-29"],correct:1,explanation:"La Loi 2008-12 du 25 janvier 2008 est le texte fondateur. Elle a cree la CDP."},
  {q:"Quelle autorite controle la protection des donnees au Senegal ?",options:["La CNIL","L'ARTP","La CDP","Le Ministere de la Justice"],correct:2,explanation:"La CDP est l'autorite independante creee par la Loi 2008-12."},
  {q:"Quelle formalite avant de traiter des donnees personnelles ?",options:["Aucune","Un email","Une declaration prealable a la CDP","Un enregistrement"],correct:2,explanation:"Art. 18 Loi 2008-12 : declaration prealable obligatoire."},
  {q:"Sanction maximale de la CDP ?",options:["1 million FCFA","5 millions FCFA","10 millions FCFA","50 millions FCFA"],correct:2,explanation:"La CDP peut prononcer des sanctions jusqu'a 10 millions de FCFA."},
  {q:"Quelles donnees sont sensibles selon la Loi 2008-12 ?",options:["Noms","Donnees de sante et biometriques","Emails","Telephones"],correct:1,explanation:"Art. 46 : sante, biometrie, opinions politiques/religieuses."},
  {q:"Depuis quand le RGPD est applicable ?",options:["25 mai 2016","25 mai 2018","25 janvier 2020","1er janvier 2021"],correct:1,explanation:"Le RGPD est entre en application le 25 mai 2018."},
  {q:"Amende maximale RGPD violations graves ?",options:["100 000 euros","1 million euros","20 millions euros ou 4% CA mondial","50 millions euros"],correct:2,explanation:"Art. 83.5 RGPD : jusqu'a 20M euros ou 4% du CA mondial."},
  {q:"Le RGPD s'applique-t-il aux entreprises senegalaises traitant des donnees europeennes ?",options:["Non","Oui, portee extraterritoriale","Seulement avec bureau en Europe","Non, jamais"],correct:1,explanation:"Art. 3 RGPD : s'applique a toute organisation mondiale traitant des donnees de residents UE."},
  {q:"Quel droit existe dans le RGPD mais pas dans la Loi 2008-12 ?",options:["Droit d'acces","Droit de rectification","Droit a la portabilite","Droit d'opposition"],correct:2,explanation:"Le droit a la portabilite (Art. 20 RGPD) n'existe pas encore dans la Loi 2008-12."},
  {q:"Qu'est-ce qu'une AIPD ?",options:["Rapport annuel a la CDP","Evaluation prealable des risques pour traitements a fort impact","Formulaire d'inscription","Audit financier"],correct:1,explanation:"L'AIPD (Art. 35 RGPD) est obligatoire avant tout traitement a risque eleve."}
];

let currentQ = 0, score = 0, answered = false, quizInitialized = false;

function renderQuiz() {
  if(currentQ >= quizData.length) {
    const pct = Math.round((score / quizData.length) * 100);
    document.getElementById('quizCard').innerHTML = `
      <div class="quiz-result">
        <div class="quiz-score">${score}/${quizData.length}</div>
        <div class="quiz-result-msg">${pct >= 80 ? ' Excellent ! Vous maitrisez bien la protection des donnees.' : pct >= 60 ? ' Bon resultat ! Quelques points a approfondir.' : ' Continuez a explorer nos ressources pour progresser.'}</div>
        <button class="btn-gold" onclick="currentQ=0;score=0;answered=false;renderQuiz()">Recommencer le quiz</button>
      </div>`;
    document.getElementById('quizBar').style.width = '100%';
    return;
  }
  const q = quizData[currentQ];
  document.getElementById('quizBar').style.width = ((currentQ / quizData.length) * 100) + '%';
  answered = false;
  document.getElementById('quizCard').innerHTML = `
    <div class="quiz-q">${q.q}</div>
    <div class="quiz-options">
      ${q.options.map((o, i) => `<button class="quiz-option" onclick="answerQuiz(${i})">${o}</button>`).join('')}
    </div>
    <div id="quizExp" style="display:none" class="quiz-explanation"></div>
    <div class="quiz-nav" id="quizNav" style="display:none">
      <button class="btn-gold" onclick="currentQ++;renderQuiz()">${currentQ < quizData.length - 1 ? 'Question suivante ' : 'Voir mon score '}</button>
    </div>`;
}

function answerQuiz(idx) {
  if(answered) return;
  answered = true;
  const q = quizData[currentQ];
  const opts = document.querySelectorAll('.quiz-option');
  opts[idx].classList.add(idx === q.correct ? 'correct' : 'wrong');
  if(idx !== q.correct) opts[q.correct].classList.add('correct');
  if(idx === q.correct) score++;
  document.getElementById('quizExp').style.display = 'block';
  document.getElementById('quizExp').textContent = q.explanation;
  document.getElementById('quizNav').style.display = 'flex';
}

// Quiz initialized when guide page is first shown

// Toast notification for resource downloads
function showToast(msg) {
  let t = document.getElementById('toast');
  if(!t) {
    t = document.createElement('div');
    t.id = 'toast';
    t.style.cssText = 'position:fixed;bottom:2rem;left:50%;transform:translateX(-50%);background:#1a6b3a;color:#fff;padding:.75rem 1.5rem;border-radius:100px;font-size:.88rem;z-index:999;opacity:0;transition:opacity .3s;pointer-events:none;font-family:DM Sans,sans-serif';
    document.body.appendChild(t);
  }
  t.textContent = msg;
  t.style.opacity = '1';
  setTimeout(() => t.style.opacity = '0', 3000);
}

// Attach toast to all download spans
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.res-dl').forEach(el => {
    if(!el.getAttribute('href')) {
      el.addEventListener('click', () => showToast(' Document disponible prochainement - inscrivez-vous a la newsletter !'));
    }
  });
});

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
  if(t) { var prenom=document.getElementById('nl-prenom'); var nlEmail=document.getElementById('nl-email'); if(!prenom||!prenom.value.trim()||!nlEmail||!nlEmail.value.trim()){showToast('Entrez votre prenom et email.');return;} t.textContent='Envoi...'; t.disabled=true; fetch('/api/newsletter',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prenom:prenom.value.trim(),email:nlEmail.value.trim()})}).then(function(r){return r.json();}).then(function(data){t.textContent=data.success?'Inscription confirmee !':'Email deja inscrit';t.style.background=data.success?'#b8e6c8':'#f5c842';if(data.success){prenom.value='';nlEmail.value='';}setTimeout(function(){t.textContent='S''abonner';t.style.background='';t.disabled=false;},3000);}).catch(function(){t.textContent='S''abonner';t.disabled=false;}); return; }
  t = e.target.closest ? e.target.closest('[data-contact-btn]') : null;
  if(t) { var nom=document.getElementById('c-nom'); var email=document.getElementById('c-email'); var org=document.getElementById('c-org'); var besoin=document.getElementById('c-besoin'); var msg=document.getElementById('c-message'); if(!nom||!nom.value.trim()||!email||!email.value.trim()||!msg||!msg.value.trim()){showToast('Remplissez nom, email et message.');return;} t.textContent='Envoi...'; t.disabled=true; fetch('/api/contact',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({nom:nom.value.trim(),email:email.value.trim(),organisation:org?org.value:'',type_besoin:besoin?besoin.value:'',message:msg.value.trim()})}).then(function(r){return r.json();}).then(function(data){t.textContent='Message envoye !';t.style.background='#2d8a52';if(nom)nom.value='';if(email)email.value='';if(org)org.value='';if(besoin)besoin.value='';if(msg)msg.value='';setTimeout(function(){t.textContent='Envoyer';t.style.background='';t.disabled=false;},4000);}).catch(function(){t.textContent='Envoyer';t.disabled=false;showToast('Erreur serveur.');}); return; }
  t = e.target.closest ? e.target.closest('[data-answer]') : null;
  if(t && t.dataset.answer !== undefined) { answerQuiz(parseInt(t.dataset.answer)); return; }
  t = e.target.closest ? e.target.closest('[data-quiz-next]') : null;
  if(t) { currentQ++; renderQuiz(); return; }
  t = e.target.closest ? e.target.closest('[data-quiz-restart]') : null;
  if(t) { currentQ=0; score=0; answered=false; renderQuiz(); return; }
  t = e.target.closest ? e.target.closest('.res-dl') : null;
  if(t && !t.getAttribute('href')) { showToast('Document disponible prochainement !'); return; }
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
function showToast(msg){var t=document.getElementById('toast');if(!t){t=document.createElement('div');t.id='toast';t.style.cssText='position:fixed;bottom:2rem;left:50%;transform:translateX(-50%);background:#1a6b3a;color:#fff;padding:.7rem 1.4rem;border-radius:100px;font-size:.86rem;z-index:9999;opacity:0;transition:opacity .3s;pointer-events:none';document.body.appendChild(t);}t.textContent=msg;t.style.opacity='1';setTimeout(function(){t.style.opacity='0';},3000);}
