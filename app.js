




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


// ===== ARTICLE DETAIL =====
function showArticle(id) {
  var a = articles[id];
  if(!a) return;
  var badges = a.badges.map(function(b,i){ return '<span class="badge '+b+'">'+a.badgeLabels[i]+'</span>'; }).join(' ');
  document.getElementById('article-content').innerHTML =
    '<a class="article-back" data-nav="blog">← Retour a la veille</a>' +
    '<div class="article-header">' +
      '<div class="article-top">'+badges+'</div>' +
      '<h1>'+a.title+'</h1>' +
      '<div class="article-meta"><span>📅 '+a.date+'</span><span>⏱ '+a.readTime+'</span><span>Source : '+a.source+'</span></div>' +
    '</div>' +
    '<p class="article-intro">'+a.intro+'</p>' +
    '<div class="article-body">'+a.body+'</div>';
  showPage('article');
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
  a1:{badges:["b-cdp","b-new"],badgeLabels:["CDP","Nouveau"],
    title:"Avril 2026 - CDP et Education signent une convention de protection des donnees",
    date:"Avril 2026",readTime:"4 min",source:"OSIRIS / Pressafrik",
    intro:"Le ministere de l'Education et la CDP ont signe le 9 avril 2026 un accord pour proteger les donnees des eleves, enseignants et personnel administratif dans le systeme educatif senegalais.",
    body:"<h2>Un accord historique pour le numerique educatif</h2><p>Le 9 avril 2026, le ministere de l'Education Nationale et la CDP ont signe une convention definissant les modalites de collaboration pour une gestion securisee des donnees dans les ecoles et administrations. Cette initiative renforce la protection de la vie privee des eleves et enseignants, conformement a la Loi 2008-12.</p><div class='source-box'><strong>Source :</strong> OSIRIS Senegal / Pressafrik, Avril 2026</div>"},
  a2:{badges:["b-rgpd","b-new"],badgeLabels:["RGPD","Nouveau"],
    title:"CNIL 2026 : Free sanctionne a 42M euros, France Travail a 5M euros",
    date:"Janvier 2026",readTime:"6 min",source:"CNIL / DPO Partage",
    intro:"Debut 2026, la CNIL sanctionne Free Mobile (27M) et Free (15M) pour faille de securite, puis France Travail a 5M euros pour violation de donnees de demandeurs d'emploi.",
    body:"<h2>Sanctions CNIL debut 2026</h2><p>Le 13 janvier 2026, la CNIL a sanctionne Free Mobile (27 millions euros) et Free (15 millions euros) suite a une intrusion ayant compromis les donnees de millions d'abonnes. Le 22 janvier 2026, France Travail a ete condamne a 5 millions euros pour manque de securite. Ces decisions s'adressent aussi aux entreprises senegalaises exportant vers l'Europe : la conformite RGPD Art. 32 est obligatoire.</p><div class='source-box'><strong>Source :</strong> CNIL / DPO Partage, Janvier 2026</div>"},
  a3:{badges:["b-cdp"],badgeLabels:["CDP"],
    title:"Janvier 2026 - CDP, ISOC et ESP s'allient pour former des experts en protection des donnees",
    date:"Janvier 2026",readTime:"4 min",source:"Cybersecurity Mag Africa",
    intro:"La CDP du Senegal annonce le 27 janvier 2026 une collaboration avec l'ISOC et l'ESP Dakar pour developper des formations et certifications en protection des donnees personnelles.",
    body:"<h2>Vers une formation certifiante au Senegal</h2><p>Le 27 janvier 2026, M. Ousmane Thiongane, President de la CDP, a annonce une collaboration avec l'ISOC-Chapitre Senegal et l'ESP Dakar. Cette alliance vise a developper des formations professionnelles certifiantes en protection des donnees, repondant a un besoin croissant de DPO qualifies dans les organisations senegalaises.</p><div class='source-box'><strong>Source :</strong> Cybersecurity Mag Africa, Janvier 2026</div>"},
  a4:{badges:["b-rgpd"],badgeLabels:["RGPD"],
    title:"Bilan RGPD 2025 : 487 millions euros d'amendes CNIL, record absolu",
    date:"Decembre 2025",readTime:"7 min",source:"RGPD Kit / DPO Partage",
    intro:"La CNIL a prononce 83 sanctions en 2025 pour 487 millions euros, contre 55 millions en 2024. Google (325M) et Shein (150M) dominent le palmaresn des amendes.",
    body:"<h2>Une annee record pour la CNIL</h2><p>En 2025, la CNIL a prononce 83 sanctions pour 486,8 millions euros, multiplication par neuf vs 2024. Google sanctionne a 325 millions euros et Shein a 150 millions euros le 3 septembre 2025 pour non-conformite sur les cookies. A l'echelle europeenne : 1,15 milliard euros d'amendes. Les PME ne sont plus epargnees : 32% des entreprises controlees etaient des TPE/PME.</p><div class='source-box'><strong>Source :</strong> RGPD Kit / DPO Partage, 2026</div>"},
  a5:{badges:["b-tech"],badgeLabels:["IA Act"],
    title:"IA Act 2026 : la CNIL lance le projet PANAME pour auditer les modeles d'IA",
    date:"Mars 2026",readTime:"5 min",source:"Legiscope / CNIL",
    intro:"La CNIL place l'IA au coeur de ses priorites 2026 avec le projet PANAME d'audit des modeles. Les systemes a haut risque sont sous surveillance accrue en Europe.",
    body:"<h2>L'IA sous surveillance en 2026</h2><p>Depuis aout 2025, la CNIL est autorite de regulation de l'IA en France au titre de l'IA Act. En 2026, elle lance PANAME, programme d'audit des modeles d'IA dans les secteurs RH, sante, education et finance. Pour les entreprises senegalaises exportant des services IA vers l'UE, la conformite a l'IA Act s'impose desormais en complement du RGPD.</p><div class='source-box'><strong>Source :</strong> Legiscope / CNIL, Mars 2026</div>"},
  a6:{badges:["b-loi"],badgeLabels:["Legislation"],
    title:"Senegal 2026 : reforme de la Loi 2008-12 et DPO bientot obligatoire",
    date:"Fevrier 2026",readTime:"5 min",source:"Monde Business / AITN",
    intro:"En 2026, le Senegal finalise la modernisation de la Loi 2008-12 avec un DPO obligatoire pour les grandes structures et des sanctions renforcees.",
    body:"<h2>Une reforme legislative en profondeur</h2><p>En 2026, le Senegal modernise la Loi 2008-12 : DPO obligatoire pour les grandes structures des secteurs sante, telecoms et finance, sanctions renforcees, et introduction du droit a la portabilite des donnees. Ces evolutions alignent le Senegal sur les standards RGPD et renforcent son attractivite pour les partenaires internationaux.</p><div class='source-box'><strong>Source :</strong> Monde Business / AITN, Fevrier 2026</div>"}
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
  if(t) { var prenom=document.getElementById('nl-prenom'); var nlEmail=document.getElementById('nl-email'); if(!prenom||!prenom.value.trim()||!nlEmail||!nlEmail.value.trim()){showToast('Entrez votre prenom et email.');return;} t.textContent='Envoi...'; t.disabled=true; fetch('/api/newsletter',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prenom:prenom.value.trim(),email:nlEmail.value.trim()})}).then(function(r){return r.json();}).then(function(data){t.textContent=data.success?'Inscription confirmee !':'Email deja inscrit';t.style.background=data.success?'#b8e6c8':'#f5c842';if(data.success){prenom.value='';nlEmail.value='';}setTimeout(function(){t.textContent='Sabonner';t.style.background='';t.disabled=false;},3000);}).catch(function(){t.textContent='Sabonner';t.disabled=false;}); return; }
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
