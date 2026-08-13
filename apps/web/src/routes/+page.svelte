<script lang="ts">
  import { api, type ExtractedDocument, type Founder, type Prefill, type Program, type Screening, type Startup } from '$lib/api/client';

  type Stage = 'startup' | 'evidence' | 'results';
  let stage = $state<Stage>('startup');
  let programs = $state<Program[]>([]);
  let docs = $state<ExtractedDocument[]>([]);
  let loading = $state(false);
  let error = $state('');
  let result = $state<Screening | null>(null);
  let prefill = $state<Prefill | null>(null);
  let geographyText = $state('Nigeria, Global');
  let technicalAssetsText = $state('FastAPI backend\nSvelteKit frontend\nRepository analysis');
  let repoSignalsText = $state('Repository is deployable\nCore service has automated tests');

  let startup = $state<Startup>({
    name:'', one_liner:'', problem:'', solution:'', customer:'', industry:'', geography:['Nigeria','Global'], stage:'prototype',
    business_model:'', pricing:'', market_evidence:'', differentiation:'', unfair_advantage:'', traction:'', revenue_monthly_usd:0,
    active_users:0, paying_customers:0, pilots:0, monthly_growth_percent:0, months_building:0, funding_raised_usd:0, product_url:'',
    founders:[{name:'',role:'Founder',bio:'',technical:true,domain_years:0,prior_builds:0,prior_startups:0,notable_outcomes:[]}],
    technical_assets:[], repository_signals:[], application_answers:{}, evidence_document_ids:[], target_program_ids:[]
  });

  function toggleProgram(id:string){
    startup.target_program_ids = startup.target_program_ids.includes(id) ? startup.target_program_ids.filter(x=>x!==id) : [...startup.target_program_ids,id];
  }
  function addFounder(){ startup.founders=[...startup.founders,{name:'',role:'',bio:'',technical:false,domain_years:0,prior_builds:0,prior_startups:0,notable_outcomes:[]}]; }
  function removeFounder(i:number){ if(startup.founders.length>1) startup.founders=startup.founders.filter((_,idx)=>idx!==i); }
  function updateFounder(i:number,key:keyof Founder,value:any){ startup.founders=startup.founders.map((f,idx)=>idx===i?{...f,[key]:value}:f); }

  async function uploadEvidence(event:Event){
    const input=event.currentTarget as HTMLInputElement; const file=input.files?.[0]; if(!file) return;
    loading=true; error='';
    try { const doc=await api.upload(file); docs=[...docs,doc]; startup.evidence_document_ids=[...startup.evidence_document_ids,doc.document_id]; prefill=await api.prefill(startup.evidence_document_ids); stage='evidence'; }
    catch(e){ error=e instanceof Error?e.message:'Upload failed'; }
    finally{ loading=false; input.value=''; }
  }

  function applyPrefill(){
    if(!prefill) return;
    const keepIds=startup.evidence_document_ids; const keepPrograms=startup.target_program_ids; const keepFounders=startup.founders;
    startup={...startup,...prefill.startup_patch,evidence_document_ids:keepIds,target_program_ids:keepPrograms,founders:keepFounders};
    if(Array.isArray(prefill.startup_patch.geography)) geographyText=(prefill.startup_patch.geography as string[]).join(', ');
    stage='startup';
  }

  async function screen(){
    loading=true; error='';
    startup.geography=geographyText.split(',').map(x=>x.trim()).filter(Boolean);
    startup.technical_assets=technicalAssetsText.split('\n').map(x=>x.trim()).filter(Boolean);
    startup.repository_signals=repoSignalsText.split('\n').map(x=>x.trim()).filter(Boolean);
    try { result=await api.screen(startup); stage='results'; }
    catch(e){ error=e instanceof Error?e.message:'Screening failed'; }
    finally{ loading=false; }
  }

  function demo(){
    startup={...startup,
      name:'ContractGuard',
      one_liner:'Detect API changes and prepare tested migrations for affected customer repositories.',
      problem:'API vendors ship breaking changes that create downtime, emergency engineering work, and integration risk for customer teams.',
      solution:'Normalize API contracts, identify affected usages in connected repositories, generate migrations, and validate them before opening a PR.',
      customer:'API providers and engineering teams maintaining production integrations', industry:'Developer tools / API infrastructure',
      business_model:'B2B SaaS priced per connected repository and API provider', pricing:'$299/month pilot tier with enterprise pricing',
      market_evidence:'Engineering teams already buy observability, CI, dependency management, and API infrastructure. Initial validation targets API vendors with many downstream integrations.',
      differentiation:'Provider-aware contract diff plus repository blast-radius analysis and evidence-backed migration validation.',
      unfair_advantage:'Accumulated API-change-to-code-fix traces improve future migration routing and validation.',
      traction:'Three design partners are testing repository scans; one paid pilot is under negotiation.', active_users:9,pilots:3,monthly_growth_percent:12,months_building:4,
      founders:[{name:'Founder',role:'Founder / Engineer',bio:'Builds developer tooling and API systems.',technical:true,domain_years:4,prior_builds:5,prior_startups:0,notable_outcomes:['Deployed production APIs']}],
      target_program_ids:['yc_f2026','techstars_general_2026','antler_residency_2026']
    };
    geographyText='Nigeria, Global'; technicalAssetsText='OpenAPI parser\nRepository analyzer\nContract diff engine\nTest runner'; repoSignalsText='FastAPI service\nSvelteKit client\nAutomated tests';
  }

  $effect(()=>{ api.programs().then(x=>programs=x).catch(()=>{}); });
</script>

<svelte:head><title>Venture Screening Intelligence</title></svelte:head>

<main class="app">
  <aside class="rail">
    <div class="brand"><span>V</span><div><strong>VentureScreen</strong><small>evidence-grounded diligence</small></div></div>
    <nav>
      <button class:active={stage==='startup'} onclick={()=>stage='startup'}>01 · Startup</button>
      <button class:active={stage==='evidence'} onclick={()=>stage='evidence'}>02 · Evidence</button>
      <button class:active={stage==='results'} disabled={!result} onclick={()=>stage='results'}>03 · Screening</button>
    </nav>
    <div class="policy"><strong>No fake acceptance probabilities.</strong><span>Program readiness is versioned, criterion-level decision support.</span></div>
  </aside>

  <section class="workspace">
    <header class="hero">
      <div><p>Venture diligence + accelerator readiness</p><h1>Screen the company before you optimize the application.</h1><span>Founder · problem · market · traction · differentiation · technical execution · program fit</span></div>
      <div class="hero-actions"><button class="ghost" onclick={demo}>Load demo</button><button class="primary" onclick={screen} disabled={loading || !startup.name || !startup.problem || !startup.solution}>{loading?'Screening…':'Run screening'}</button></div>
    </header>
    {#if error}<p class="error">{error}</p>{/if}

    {#if stage==='startup'}
      <section class="columns">
        <div class="stack">
          <article class="panel form">
            <div class="panel-title"><div><span>Company thesis</span><h2>What are you building?</h2></div><b>Required</b></div>
            <div class="two"><label>Name<input bind:value={startup.name} placeholder="Company name" /></label><label>Stage<select bind:value={startup.stage}><option value="idea">Idea</option><option value="prototype">Prototype</option><option value="pre_revenue">Pre-revenue</option><option value="early_revenue">Early revenue</option><option value="growth">Growth</option><option value="later">Later</option></select></label></div>
            <label>One-liner<input bind:value={startup.one_liner} placeholder="Concrete description without buzzwords" /></label>
            <label>Problem<textarea bind:value={startup.problem} placeholder="Who has the problem, what happens today, and why is it painful?"></textarea></label>
            <label>Solution<textarea bind:value={startup.solution} placeholder="What does the product actually do?"></textarea></label>
            <div class="two"><label>Customer<input bind:value={startup.customer} /></label><label>Industry<input bind:value={startup.industry} /></label></div>
            <label>Geographies<input bind:value={geographyText} placeholder="Nigeria, United States, Global" /></label>
          </article>

          <article class="panel form">
            <div class="panel-title"><div><span>Venture evidence</span><h2>Economics, market and differentiation</h2></div></div>
            <div class="two"><label>Business model<textarea bind:value={startup.business_model}></textarea></label><label>Pricing<textarea bind:value={startup.pricing}></textarea></label></div>
            <label>Market evidence<textarea bind:value={startup.market_evidence} placeholder="Prefer bottom-up sizing, buyer spend, interviews and observed budgets."></textarea></label>
            <div class="two"><label>Differentiation<textarea bind:value={startup.differentiation}></textarea></label><label>Unfair advantage<textarea bind:value={startup.unfair_advantage}></textarea></label></div>
            <label>Traction narrative<textarea bind:value={startup.traction}></textarea></label>
            <div class="metrics"><label>MRR (USD)<input type="number" bind:value={startup.revenue_monthly_usd}/></label><label>Active users<input type="number" bind:value={startup.active_users}/></label><label>Paying customers<input type="number" bind:value={startup.paying_customers}/></label><label>Pilots<input type="number" bind:value={startup.pilots}/></label><label>MoM growth %<input type="number" bind:value={startup.monthly_growth_percent}/></label><label>Months building<input type="number" bind:value={startup.months_building}/></label></div>
          </article>
        </div>

        <aside class="stack">
          <article class="panel form">
            <div class="panel-title"><div><span>Review targets</span><h2>Program adapters</h2></div></div>
            <p class="muted">No selection means screen against all currently registered adapters.</p>
            {#each programs as program}
              <button class="program" class:selected={startup.target_program_ids.includes(program.id)} onclick={()=>toggleProgram(program.id)}><i></i><div><strong>{program.name}</strong><small>{program.status.replaceAll('_',' ')} · snapshot {program.version}</small></div></button>
            {/each}
          </article>

          <article class="panel form">
            <div class="panel-title"><div><span>Founders</span><h2>Execution capability</h2></div><button class="mini" onclick={addFounder}>+ Add</button></div>
            {#each startup.founders as founder,i}
              <div class="founder">
                <div class="founder-head"><strong>Founder {i+1}</strong>{#if startup.founders.length>1}<button onclick={()=>removeFounder(i)}>Remove</button>{/if}</div>
                <div class="two"><input value={founder.name} oninput={(e)=>updateFounder(i,'name',(e.currentTarget as HTMLInputElement).value)} placeholder="Name"/><input value={founder.role} oninput={(e)=>updateFounder(i,'role',(e.currentTarget as HTMLInputElement).value)} placeholder="Role"/></div>
                <textarea value={founder.bio} oninput={(e)=>updateFounder(i,'bio',(e.currentTarget as HTMLTextAreaElement).value)} placeholder="Relevant background, earned insight, prior outcomes"></textarea>
                <div class="two"><label>Domain years<input type="number" value={founder.domain_years} oninput={(e)=>updateFounder(i,'domain_years',+(e.currentTarget as HTMLInputElement).value)}/></label><label>Prior builds<input type="number" value={founder.prior_builds} oninput={(e)=>updateFounder(i,'prior_builds',+(e.currentTarget as HTMLInputElement).value)}/></label></div>
                <label class="check"><input type="checkbox" checked={founder.technical} onchange={(e)=>updateFounder(i,'technical',(e.currentTarget as HTMLInputElement).checked)}/> Technical founder</label>
              </div>
            {/each}
          </article>
        </aside>
      </section>
    {/if}

    {#if stage==='evidence'}
      <section class="columns">
        <article class="panel form">
          <div class="panel-title"><div><span>Evidence ledger</span><h2>Upload supporting material</h2></div></div>
          <div class="drop"><div><strong>Pitch deck, business plan, PDF/DOCX, notes or repository ZIP</strong><p>Repository ZIPs are bounded and only safe text/code files are extracted. Image-only PDF OCR is intentionally not performed.</p></div><label for="evidence">Choose file</label><input id="evidence" type="file" accept=".pdf,.docx,.txt,.md,.zip,.json,.csv" onchange={uploadEvidence}/></div>
          <div class="doc-list">
            {#each docs as doc}<article><div><strong>{doc.filename}</strong><small>{doc.chars.toLocaleString()} chars · {doc.sha256.slice(0,12)}</small></div><span>{doc.warnings.length?`${doc.warnings.length} warning(s)`:'ready'}</span></article>{/each}
            {#if docs.length===0}<p class="empty">No supporting documents uploaded. Screening can still run from structured evidence, but evidence confidence may be lower.</p>{/if}
          </div>
          {#if prefill}<div class="prefill"><div class="panel-title"><div><span>Document extraction</span><h2>{prefill.fields.length} reviewable startup fields detected</h2></div><button class="mini" onclick={applyPrefill}>Apply to startup form</button></div><div class="prefill-fields">{#each prefill.fields.slice(0,12) as field}<article><div><strong>{field.field.replaceAll('_',' ')}</strong><small>{field.source_filename} · {field.method}</small></div><b class={field.confidence}>{field.confidence}</b><p>{field.evidence_excerpt}</p></article>{/each}</div>{#if prefill.missing_required_fields.length}<p class="muted">Still needs founder input: {prefill.missing_required_fields.join(', ')}</p>{/if}</div>{/if}
        </article>
        <aside class="stack">
          <article class="panel form"><div class="panel-title"><div><span>Technical evidence</span><h2>Assets and repository signals</h2></div></div><label>Technical assets<textarea bind:value={technicalAssetsText}></textarea></label><label>Repository signals<textarea bind:value={repoSignalsText}></textarea></label></article>
          <article class="panel callout"><strong>Decision boundary</strong><p>The system scores what is evidenced. Missing data becomes a validation workflow; it is not silently guessed.</p><button class="primary wide" onclick={screen} disabled={loading || !startup.name}>{loading?'Screening…':'Run evidence-grounded screening'}</button></article>
        </aside>
      </section>
    {/if}

    {#if stage==='results' && result}
      <section class="results">
        <article class="verdict panel"><div><span>Screening verdict</span><h2>{result.verdict.replaceAll('_',' ')}</h2><p>{result.verdict_rationale}</p></div><div class="score"><strong>{result.overall_quality_score.toFixed(0)}</strong><span>quality</span><small>{result.evidence_confidence} evidence confidence</small></div></article>
        {#if result.contradictions.length}<article class="panel warn"><strong>Contradictions detected</strong>{#each result.contradictions as c}<p><b>{c.severity}</b> · {c.explanation}</p>{/each}</article>{/if}

        <section class="result-grid">
          <div class="stack">
            <article class="panel"><div class="panel-title"><div><span>Reviewer committee</span><h2>Dimension scores</h2></div></div><div class="dimensions">{#each result.dimensions as d}<div><div class="dim-head"><strong>{d.label}</strong><b>{d.score.toFixed(0)}</b></div><div class="bar"><i style={`width:${d.score}%`}></i></div><p>{d.rationale}</p>{#if d.gaps[0]}<small>{d.gaps[0]}</small>{/if}</div>{/each}</div></article>
            <article class="panel"><div class="panel-title"><div><span>Commercial redundancy</span><h2>Closest indexed companies</h2></div><small>catalog: {String(result.metadata.company_catalog_size)}</small></div><div class="matches">{#each result.competitors.slice(0,6) as c}<article><div><strong>{c.name}</strong><small>{c.source}</small></div><b>{Math.round(c.overall_similarity*100)}%</b><p>{c.explanation}</p></article>{/each}</div></article>
          </div>

          <aside class="stack">
            <article class="panel"><div class="panel-title"><div><span>Accelerator adapters</span><h2>Program readiness</h2></div></div>{#each result.program_assessments as p}<article class="assessment"><div><strong>{p.program_name}</strong><small>{p.eligible?'profile eligible':'hard rule failed'} · {p.evidence_confidence} evidence</small></div><span class={`readiness ${p.readiness}`}>{p.readiness}</span><b>{p.weighted_score.toFixed(0)}</b>{#each p.eligibility.filter(x=>!x.passed) as rule}<p>{rule.severity}: {rule.message}</p>{/each}</article>{/each}</article>
            <article class="panel"><div class="panel-title"><div><span>Current problem calls</span><h2>Opportunity matches</h2></div></div>{#each result.opportunities as o}<article class="opportunity"><strong>{o.title}</strong><div><span>idea {Math.round(o.similarity*100)}%</span><span>capability {Math.round(o.capability_fit*100)}%</span></div><p>{o.rationale}</p></article>{/each}</article>
          </aside>
        </section>

        <article class="panel"><div class="panel-title"><div><span>Remediation engine</span><h2>Evidence-producing validation workflows</h2></div></div><div class="workflows">{#each result.validation_workflows as wf}<article><header><div><span>{wf.priority}</span><strong>{wf.objective}</strong></div><small>{wf.rescore_dimensions.join(', ')}</small></header><p>{wf.finding}</p><ol>{#each wf.steps as step}<li><strong>{step.title}</strong><span>{step.instruction}</span><small>Gate: {step.gate} → {step.evidence_output}</small></li>{/each}</ol></article>{/each}</div></article>
      </section>
    {/if}
  </section>
</main>

<style>
:global(body){margin:0;background:#f2f3ed;color:#101511;font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;font-size:14px}.app{min-height:100vh;display:grid;grid-template-columns:240px minmax(0,1fr)}.rail{position:sticky;top:0;height:100vh;box-sizing:border-box;background:#0d1712;color:#f1f6ef;padding:22px 16px;display:flex;flex-direction:column;gap:28px}.brand{display:flex;gap:11px;align-items:center}.brand>span{width:34px;height:34px;display:grid;place-items:center;border-radius:11px;background:#b7f36b;color:#13200f;font-weight:900}.brand div{display:grid}.brand small{color:#8fa195;font-size:10px;margin-top:2px}nav{display:grid;gap:6px}nav button{border:0;text-align:left;background:transparent;color:#96aa9d;border-radius:12px;padding:10px 11px;cursor:pointer}nav button.active,nav button:hover{background:#18251e;color:white}nav button:disabled{opacity:.35}.policy{margin-top:auto;border:1px solid #28392f;background:#142019;border-radius:17px;padding:14px;display:grid;gap:7px}.policy strong{font-size:12px}.policy span{font-size:11px;line-height:1.45;color:#93a49a}.workspace{padding:25px 30px 50px;min-width:0}.hero{display:flex;justify-content:space-between;align-items:flex-start;gap:24px;margin-bottom:22px}.hero p,.panel-title span,.verdict>div>span{margin:0 0 7px;color:#527a3b;letter-spacing:.13em;text-transform:uppercase;font-size:10px;font-weight:800}.hero h1{margin:0;font-size:32px;line-height:1.02;letter-spacing:-.05em;max-width:760px}.hero>div>span{display:block;margin-top:10px;color:#6f786f;font-size:12px}.hero-actions{display:flex;gap:8px}.primary,.ghost,.mini,.founder-head button{border:0;border-radius:999px;padding:10px 14px;cursor:pointer;font:inherit}.primary{background:#a9e85f;color:#10200b;font-weight:800}.ghost{background:#fff;border:1px solid #d9ddd2;color:#26302a}.primary:disabled{opacity:.4}.columns,.result-grid{display:grid;grid-template-columns:minmax(0,1.4fr) minmax(340px,.75fr);gap:16px}.stack{display:grid;gap:16px;align-content:start}.panel{background:#fbfcf8;border:1px solid #dce1d6;border-radius:22px;padding:18px;box-shadow:0 18px 60px rgba(32,52,38,.045)}.form{display:grid;gap:13px}.panel-title{display:flex;justify-content:space-between;align-items:flex-start;gap:14px}.panel-title h2{margin:0;font-size:16px;letter-spacing:-.025em}.panel-title b{background:#eef7e4;color:#4d6e3c;border-radius:999px;padding:5px 8px;font-size:9px;text-transform:uppercase;letter-spacing:.08em}.panel-title small{color:#788178;font-size:10px}.two{display:grid;grid-template-columns:1fr 1fr;gap:10px}.metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:9px}label{display:grid;gap:6px;font-size:11px;color:#69736b}input,textarea,select{box-sizing:border-box;width:100%;border:1px solid #d8ddd4;background:white;border-radius:12px;padding:10px 11px;font:inherit;color:#121713}textarea{min-height:92px;resize:vertical;line-height:1.45}.program{display:flex;width:100%;gap:10px;align-items:center;text-align:left;border:1px solid #dde3d8;background:white;border-radius:14px;padding:11px;cursor:pointer;color:#162019}.program i{width:13px;height:13px;border-radius:4px;border:1px solid #a9b4a9}.program.selected{background:#152119;color:#eff6ed;border-color:#152119}.program.selected i{background:#b7f36b;border-color:#b7f36b}.program div{display:grid;gap:3px}.program strong{font-size:12px}.program small{font-size:10px;color:#7b867d}.program.selected small{color:#9bae9f}.muted,.empty{font-size:11px;line-height:1.5;color:#7b847d;margin:0}.mini{padding:6px 9px;background:#edf4e7;color:#314128;font-size:11px}.founder{display:grid;gap:9px;border-top:1px solid #e5e9e1;padding-top:12px}.founder:first-of-type{border-top:0}.founder-head{display:flex;justify-content:space-between}.founder-head button{padding:3px 7px;background:#f5ebe7;color:#8b3d29;font-size:10px}.check{display:flex;align-items:center;gap:7px}.check input{width:auto}.drop{border:1px dashed #b8c6b2;background:#f6faf2;border-radius:18px;padding:18px;display:flex;justify-content:space-between;gap:20px;align-items:center}.drop p{margin:5px 0 0;max-width:640px;color:#718071;font-size:11px;line-height:1.5}.drop label{display:inline-flex;background:#142019;color:white;border-radius:999px;padding:9px 12px;cursor:pointer}.drop input{position:absolute;opacity:0;pointer-events:none;width:1px}.doc-list{display:grid;gap:8px}.doc-list article{display:flex;justify-content:space-between;gap:15px;align-items:center;border:1px solid #e0e5dc;background:white;border-radius:14px;padding:11px}.doc-list article div{display:grid}.doc-list small{font-size:10px;color:#7a847b}.doc-list span{font-size:10px;color:#567845}.callout{background:#16211a;color:white;border-color:#16211a}.callout p{color:#aab7ad;line-height:1.5}.wide{width:100%}.error{border:1px solid #e8b9a8;background:#fff0e9;color:#913618;border-radius:14px;padding:10px 12px}.results{display:grid;gap:16px}.verdict{display:flex;justify-content:space-between;align-items:center;gap:25px;background:#132018;color:white;border-color:#132018}.verdict h2{font-size:28px;margin:0 0 8px;letter-spacing:-.04em}.verdict p{margin:0;max-width:800px;color:#b0bdb3;line-height:1.5}.score{min-width:130px;text-align:center;border-left:1px solid #2e4035;padding-left:24px;display:grid}.score strong{font-size:46px;color:#b7f36b;line-height:1}.score span{font-size:10px;text-transform:uppercase;letter-spacing:.12em}.score small{margin-top:5px;color:#8fa194;font-size:9px}.warn{border-color:#e3c49c;background:#fff8ee}.warn>strong{color:#80551b}.warn p{margin:8px 0 0;font-size:11px}.dimensions{display:grid;gap:16px}.dim-head{display:flex;justify-content:space-between}.dim-head b{font-variant-numeric:tabular-nums}.bar{height:6px;border-radius:99px;background:#e7ebe4;margin:7px 0}.bar i{display:block;height:100%;background:#82ba47;border-radius:99px}.dimensions p{margin:0;color:#657068;font-size:11px;line-height:1.45}.dimensions small{display:block;margin-top:5px;color:#986633;font-size:10px}.matches{display:grid;gap:8px}.matches article{display:grid;grid-template-columns:1fr auto;gap:5px 12px;border-top:1px solid #e5e9e2;padding-top:10px}.matches article:first-child{border-top:0}.matches div{display:grid}.matches small{color:#879087;font-size:9px}.matches b{font-size:18px;color:#527a3b}.matches p{grid-column:1/-1;margin:0;font-size:10px;color:#717a73}.assessment{display:grid;grid-template-columns:1fr auto auto;gap:8px 10px;align-items:center;border-top:1px solid #e4e8e0;padding:12px 0}.assessment:first-of-type{border-top:0}.assessment>div{display:grid}.assessment small{font-size:9px;color:#7b867e}.assessment>b{font-size:17px}.assessment p{grid-column:1/-1;margin:0;font-size:10px;color:#8b5e2a}.readiness{font-size:9px;text-transform:uppercase;border-radius:999px;padding:5px 7px;background:#eef1eb}.readiness.strong{background:#e5f6d2;color:#456f2b}.readiness.ineligible{background:#f6e5df;color:#934127}.opportunity{border-top:1px solid #e4e8e0;padding:11px 0}.opportunity:first-of-type{border-top:0}.opportunity>div{display:flex;gap:6px;margin:7px 0}.opportunity span{background:#edf3e8;border-radius:999px;padding:4px 6px;font-size:9px}.opportunity p{margin:0;font-size:10px;line-height:1.4;color:#69746b}.workflows{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:12px}.workflows>article{border:1px solid #dfe4db;background:white;border-radius:18px;padding:14px}.workflows header{display:flex;justify-content:space-between;gap:12px}.workflows header div{display:grid;gap:4px}.workflows header span{font-size:9px;color:#9a642a;text-transform:uppercase}.workflows header small{font-size:9px;color:#7b857d}.workflows>article>p{font-size:10px;color:#7b624b}.workflows ol{padding-left:20px;margin:10px 0 0;display:grid;gap:9px}.workflows li{font-size:10px}.workflows li strong,.workflows li span,.workflows li small{display:block}.workflows li span{color:#5f6961;line-height:1.4;margin:2px 0}.workflows li small{color:#879188}.prefill{margin-top:14px;border-top:1px solid #e4e8e5;padding-top:14px}.prefill-fields{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.prefill-fields article{display:grid;grid-template-columns:1fr auto;gap:4px 10px;background:#f8faf8;border:1px solid #e0e7e1;border-radius:12px;padding:9px}.prefill-fields div{display:grid}.prefill-fields strong{font-size:10px;text-transform:capitalize}.prefill-fields small{font-size:8px;color:#7b887e}.prefill-fields b{font-size:8px;text-transform:uppercase;border-radius:999px;background:#e9eeea;padding:4px 6px;align-self:start}.prefill-fields b.high{background:#e1f4e7;color:#39734b}.prefill-fields p{grid-column:1/-1;margin:2px 0 0;font-size:9px;line-height:1.4;color:#626e64;max-height:40px;overflow:hidden}@media(max-width:1120px){.app{grid-template-columns:1fr}.rail{position:static;height:auto}.columns,.result-grid{grid-template-columns:1fr}.hero{display:grid}.metrics{grid-template-columns:repeat(2,1fr)}.prefill-fields{grid-template-columns:1fr}}@media(max-width:650px){.workspace{padding:18px}.two,.metrics{grid-template-columns:1fr}.verdict{display:grid}.score{border-left:0;border-top:1px solid #2e4035;padding:15px 0 0}.hero-actions{width:100%}.hero-actions button{flex:1}}
</style>
