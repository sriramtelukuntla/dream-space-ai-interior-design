// ============================================================
// Dream Space – AI Interior Designer  |  main.js  (v6)
// ============================================================

// ── State ────────────────────────────────────────────────────
let uploadedImage      = null;
let segmentedData      = null;
let generatedImage     = null;
let generatedImagePath = null;
let parsedRequirements = null;
let costData           = null;
let allTierData        = null;
let _activeRoomCard    = null;   // tracks which room card is selected

// ── Helpers ──────────────────────────────────────────────────
const $  = id  => document.getElementById(id);
const $$ = sel => document.querySelectorAll(sel);
function fmtINR(n) { return Number(n).toLocaleString('en-IN', { maximumFractionDigits: 0 }); }
function setText(id, txt) { const e=$(id); if(e) e.textContent=txt; }
function setHTML(id, html){ const e=$(id); if(e) e.innerHTML=html;  }
function show(id){ const e=$(id); if(e) e.style.display='block'; }
function hide(id){ const e=$(id); if(e) e.style.display='none';  }
function showLoading(on, msg='Working…'){
    const s=$('loadingSpinner'); if(!s) return;
    s.style.display=on?'block':'none';
    if(on) setText('loadingText', msg);
}
function showToast(msg, type='success'){
    const t=$('toast'); if(!t) return;
    t.textContent=msg; t.className=`toast ${type} show`;
    setTimeout(()=>t.classList.remove('show'), 3500);
}

// ══════════════════════════════════════════════════════════════
//  ROOM EXAMPLE PROMPTS  (one per room type)
// ══════════════════════════════════════════════════════════════
const ROOM_PROMPTS = {
    bedroom: {
        icon: '🛏️', label: 'Bedroom',
        roomTypeValue: 'bedroom',
        prompt: `Design a modern bedroom with dimensions 12 ft × 10 ft. The north wall should be light blue, south wall white, east wall grey, and west wall cream. Include a queen-size bed, two nightstands, a wardrobe, study table with chair, and floor-length curtains. Style should be minimalist and contemporary with natural lighting.`,
    },
    kitchen: {
        icon: '🍳', label: 'Kitchen',
        roomTypeValue: 'kitchen',
        prompt: `Design a contemporary kitchen with dimensions 14 ft × 10 ft. North wall should be white subway tile, remaining walls light grey. Include an island counter with bar stools, overhead pendant lights, built-in cabinetry, open shelves for crockery, a gas hob with chimney, and a large refrigerator. Style should be modern Scandinavian with warm under-cabinet lighting.`,
    },
    bathroom: {
        icon: '🚿', label: 'Bathroom',
        roomTypeValue: 'bathroom',
        prompt: `Design a luxury bathroom with dimensions 10 ft × 8 ft. Walls should be white and light marble. Include a freestanding bathtub, walk-in rainfall shower, double vanity with mirror cabinet, heated towel rail, and indoor plant. Floor should be large-format grey porcelain tile. Style should be spa-like and serene with soft warm lighting.`,
    },
    'living room': {
        icon: '🛋️', label: 'Living Room',
        roomTypeValue: 'living room',
        prompt: `Design a cozy living room with dimensions 16 ft × 14 ft. North wall should be sage green, remaining walls off-white. Include a large L-shaped sofa, coffee table, TV unit with floating shelves, two armchairs, floor lamp, and indoor plants. Floor should be light oak hardwood with a large rug. Style should be bohemian mid-century with warm ambient lighting.`,
    },
    office: {
        icon: '💼', label: 'Office',
        roomTypeValue: 'office',
        prompt: `Design a productive home office with dimensions 12 ft × 10 ft. Walls should be light grey with a navy blue accent wall. Include a large standing desk, ergonomic chair, dual-monitor setup with monitor arm, built-in bookshelf, filing cabinet, small sofa for breaks, and a whiteboard. Style should be modern industrial with cool daylight lighting.`,
    },
    lab: {
        icon: '🔬', label: 'Laboratory',
        roomTypeValue: 'lab',
        prompt: `Design a clean research laboratory with dimensions 20 ft × 15 ft. All walls should be white. Include stainless steel workbenches, overhead ventilation hoods, built-in storage cabinets, lab stools, safety eyewash station, and a clean zone partition. Flooring should be anti-static grey tile. Style should be clinical and functional with bright cool white lighting.`,
    },
    classroom: {
        icon: '🏫', label: 'Classroom',
        roomTypeValue: 'classroom',
        prompt: `Design a modern classroom with dimensions 30 ft × 25 ft. Front wall should be light green chalkboard, remaining walls pale yellow. Include 30 student desks with chairs arranged in rows, a teacher's desk and whiteboard at the front, large windows on the east wall, overhead projector screen, and bookshelves along the back wall. Style should be bright and encouraging with natural and fluorescent lighting.`,
    },
    auditorium: {
        icon: '🎭', label: 'Auditorium',
        roomTypeValue: 'auditorium',
        prompt: `Design a college auditorium with seating capacity of 200. Side walls should be deep burgundy, back wall charcoal, and ceiling dark with recessed lighting. Include tiered seating with upholstered seats, a raised stage with podium and curtains, professional stage lighting rigs, a large projection screen, and acoustic wall panels. Style should be dramatic and professional with dramatic accent lighting.`,
    },
    hall: {
        icon: '🏛️', label: 'Hall / Foyer',
        roomTypeValue: 'hall',
        prompt: `Design a grand entrance hall with dimensions 18 ft × 12 ft. Walls should be warm ivory with wainscoting panels. Include a statement chandelier, console table with decorative mirror, umbrella stand, coat hooks, a bench with storage, and a large indoor plant. Floor should be black and white chequerboard marble tile. Style should be classic and elegant with warm ambient lighting.`,
    },
};

// ── Tab switching ─────────────────────────────────────────────
function switchTab(nameOrEvt){
    const name = typeof nameOrEvt==='string' ? nameOrEvt : nameOrEvt.currentTarget.dataset.tab;
    $$('.tab-btn').forEach(b=>b.classList.remove('active'));
    $$('.tab-panel').forEach(p=>p.classList.remove('active'));
    const btn=document.querySelector(`.tab-btn[data-tab="${name}"]`);
    const panel=$(name);
    if(btn)   btn.classList.add('active');
    if(panel) panel.classList.add('active');
}
const switchToTab = name => switchTab(name);

// ── Init ─────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', ()=>{
    setupListeners();
    loadRoomTypes();
    _buildRoomSelectorCards();
    _buildRoomEditorPanel();
});

function setupListeners(){
    $('uploadArea').addEventListener('click',     ()=>$('imageInput').click());
    $('imageInput').addEventListener('change',    e =>handleImageUpload(e));
    $('removeImage').addEventListener('click',    clearUploadedImage);
    $('uploadArea').addEventListener('dragover',  e =>{ e.preventDefault(); $('uploadArea').classList.add('dragover'); });
    $('uploadArea').addEventListener('dragleave', e =>{ e.preventDefault(); $('uploadArea').classList.remove('dragover'); });
    $('uploadArea').addEventListener('drop',      handleDrop);
    $('designPrompt').addEventListener('input', ()=>{
        const n=$('designPrompt').value.length;
        setText('charCount', n);
        $('charCount').style.color = n>1000?'#ff6b6b':'#888';
    });
    $('segmentBtn').addEventListener('click',  segmentImage);
    $('generateBtn').addEventListener('click', generateDesign);
    $('analyzeBtn').addEventListener('click',  analyzePrompt);
    $('clearBtn').addEventListener('click',    clearAll);
    $('downloadBtn').addEventListener('click', downloadImage);
    $('enhanceBtn').addEventListener('click',  openRoomEditor);
    $('estimateCostBtn').addEventListener('click', estimateCost);
    $$('.tab-btn').forEach(b=>b.addEventListener('click', switchTab));
    safeOn('compareTiersBtn', 'click', compareCostTiers);
    safeOn('downloadCostBtn', 'click', downloadCostReport);
    safeOn('printCostBtn',    'click', printCostReport);
}
function safeOn(id, ev, fn){ const el=$(id); if(el) el.addEventListener(ev, fn); }


// ══════════════════════════════════════════════════════════════
//  ROOM SELECTOR CARDS
// ══════════════════════════════════════════════════════════════

function _buildRoomSelectorCards(){
    const grid = $('roomSelectorGrid'); if(!grid) return;
    grid.innerHTML = '';
    Object.entries(ROOM_PROMPTS).forEach(([key, room])=>{
        const card = document.createElement('div');
        card.className   = 'room-card';
        card.dataset.key = key;
        card.innerHTML   = `
            <span class="room-card-icon">${room.icon}</span>
            <span class="room-card-label">${room.label}</span>`;
        card.addEventListener('click', ()=> _selectRoomCard(key));
        grid.appendChild(card);
    });
    // Select bedroom by default
    _selectRoomCard('bedroom');
}

function _selectRoomCard(key){
    const room = ROOM_PROMPTS[key]; if(!room) return;

    // Update active card styling
    $$('.room-card').forEach(c=> c.classList.remove('active'));
    const card = document.querySelector(`.room-card[data-key="${key}"]`);
    if(card) card.classList.add('active');
    _activeRoomCard = key;

    // Update label
    const label = $('templateRoomLabel');
    if(label) label.textContent = `${room.icon} ${room.label} — Example Prompt`;

    // Update template text with highlighted keywords
    const text = $('templateText');
    if(text){
        const highlighted = _highlightPrompt(room.prompt);
        text.innerHTML = `"${highlighted}"`;
    }

    // Sync the room type dropdown
    const sel = $('roomType');
    if(sel){
        const opt = [...sel.options].find(o=> o.value === room.roomTypeValue);
        if(opt) sel.value = room.roomTypeValue;
    }
}

/** Wrap key design terms in highlight spans */
function _highlightPrompt(text){
    const patterns = [
        /(\d+\s*(?:ft|m)\s*[×x]\s*\d+\s*(?:ft|m))/gi,
        /((?:north|south|east|west)\s+wall[^,\.]*)/gi,
        /((?:queen-size bed|king bed|L-shaped sofa|sofa|island counter|standing desk|wardrobe|nightstand|dining table|bookshelf|armchair|vanity|bathtub|shower|chandelier|console table|whiteboard|projector|bench|floor lamp|coffee table|TV unit|bar stool|pendant light|monitor arm|filing cabinet|ergonomic chair|stainless steel workbench|lab stool|student desk|teacher's desk|podium|upholstered seat|acoustic panel|coat hook)[^,\.]*)(?=[,\.])/gi,
        /(minimalist|contemporary|modern|scandinavian|bohemian|mid-century|industrial|luxury|spa-like|classic|elegant|clinical|dramatic|functional|encouraging)[^,\.]*/gi,
        /(natural lighting|warm ambient lighting|cool white lighting|dramatic accent lighting|soft warm lighting|recessed lighting|fluorescent lighting)/gi,
    ];
    let out = text;
    patterns.forEach(re=>{
        out = out.replace(re, m=> `<span class="highlight">${m}</span>`);
    });
    return out;
}

/** Copy current template text (plain) to clipboard */
function copyTemplate(){
    const key  = _activeRoomCard || 'bedroom';
    const room = ROOM_PROMPTS[key];
    const text = room ? room.prompt : ($('templateText')?.innerText || '');
    navigator.clipboard.writeText(text)
        .then(()=> showToast('Prompt copied!','success'))
        .catch(()=> showToast('Copy failed','error'));
}

/** Paste the current example prompt into the textarea and sync the dropdown */
function useSelectedPrompt(){
    const key  = _activeRoomCard || 'bedroom';
    const room = ROOM_PROMPTS[key]; if(!room) return;
    $('designPrompt').value = room.prompt;
    const n = room.prompt.length;
    setText('charCount', n);
    $('charCount').style.color = n>1000?'#ff6b6b':'#888';
    const sel = $('roomType');
    if(sel){
        const opt = [...sel.options].find(o=> o.value === room.roomTypeValue);
        if(opt) sel.value = room.roomTypeValue;
    }
    $('designPrompt').scrollIntoView({behavior:'smooth', block:'center'});
    $('designPrompt').focus();
    showToast(`${room.icon} ${room.label} prompt loaded!`, 'success');
}

/** Append a phrase to the current textarea content */
function _appendToPrompt(phrase){
    const ta = $('designPrompt');
    const cur = ta.value.trim();
    ta.value = cur ? `${cur}, ${phrase}` : phrase;
    const n = ta.value.length;
    setText('charCount', n);
    $('charCount').style.color = n>1000?'#ff6b6b':'#888';
    ta.focus();
    showToast(`Added: "${phrase}"`, 'success');
}


// ══════════════════════════════════════════════════════════════
//  ROOM EDITOR PANEL
// ══════════════════════════════════════════════════════════════

const FURNITURE_PRESETS = {
    bedroom:   ['Wardrobe','Dressing table','Nightstand','Floor lamp','Bookshelf','Armchair','Ottoman','Plant','Mirror','Study desk'],
    living:    ['Sofa','Coffee table','TV unit','Floor lamp','Bookshelf','Armchair','Side table','Plant','Rug','Curtains'],
    kitchen:   ['Island counter','Bar stools','Pendant lights','Pantry cabinet','Open shelves','Herb garden','Wine rack'],
    bathroom:  ['Vanity cabinet','Freestanding tub','Walk-in shower','Heated towel rail','Plant','Mirror cabinet'],
    office:    ['Standing desk','Ergonomic chair','Bookshelf','Filing cabinet','Whiteboard','Plants','Monitor arm'],
    dining:    ['Dining table','Dining chairs','Sideboard','Pendant lights','Bar cart','Plant','Rug'],
    default:   ['Sofa','Armchair','Coffee table','Bookshelf','Floor lamp','Plant','Mirror','Rug','Side table','Ottoman'],
};
const STYLE_OPTIONS = [
    {v:'modern',l:'Modern'},{v:'minimalist',l:'Minimalist'},{v:'scandinavian',l:'Scandinavian'},
    {v:'industrial',l:'Industrial'},{v:'bohemian',l:'Bohemian'},{v:'mid-century',l:'Mid-Century'},
    {v:'contemporary',l:'Contemporary'},{v:'traditional',l:'Traditional'},{v:'rustic',l:'Rustic'},
    {v:'coastal',l:'Coastal'},{v:'luxury',l:'Luxury'},{v:'art deco',l:'Art Deco'},
    {v:'japandi',l:'Japandi'},{v:'french country',l:'French Country'},
];
const LIGHTING_OPTIONS = [
    {v:'warm ambient',l:'Warm Ambient'},{v:'cool daylight',l:'Cool Daylight'},
    {v:'soft diffused',l:'Soft Diffused'},{v:'dramatic accent',l:'Dramatic Accent'},
    {v:'natural sunlight',l:'Natural Sunlight'},{v:'recessed ceiling',l:'Recessed Ceiling'},
    {v:'pendant lights',l:'Pendant Lights'},{v:'fairy lights',l:'Fairy Lights'},
];
const MOOD_OPTIONS = [
    {v:'cozy',l:'Cozy 🛋️'},{v:'luxurious',l:'Luxurious ✨'},{v:'minimalist',l:'Minimal 🤍'},
    {v:'romantic',l:'Romantic 🕯️'},{v:'energetic',l:'Energetic ⚡'},{v:'serene',l:'Serene 🌿'},
    {v:'playful',l:'Playful 🎨'},{v:'sophisticated',l:'Sophisticated 🎩'},
];
const WALL_COLORS = [
    {v:'white',l:'White',hex:'#FFFFFF'},{v:'off white',l:'Off White',hex:'#F5F0E8'},
    {v:'light grey',l:'Lt Grey',hex:'#D5D5D5'},{v:'dark grey',l:'Dk Grey',hex:'#555555'},
    {v:'beige',l:'Beige',hex:'#C8B89A'},{v:'taupe',l:'Taupe',hex:'#A89880'},
    {v:'sage green',l:'Sage',hex:'#8FAF8A'},{v:'forest green',l:'Forest',hex:'#3A5A40'},
    {v:'navy blue',l:'Navy',hex:'#1B3A5C'},{v:'sky blue',l:'Sky Blue',hex:'#7DB8D8'},
    {v:'terracotta',l:'Terracotta',hex:'#C5693A'},{v:'blush pink',l:'Blush',hex:'#E8A0A0'},
    {v:'dusty rose',l:'Dusty Rose',hex:'#C88080'},{v:'charcoal',l:'Charcoal',hex:'#333333'},
    {v:'warm yellow',l:'Warm Yel',hex:'#E8D080'},{v:'lavender',l:'Lavender',hex:'#B0A0D0'},
];
const FLOOR_OPTIONS = [
    {v:'light oak hardwood',l:'Light Oak',hex:'#C8A87A'},{v:'dark walnut hardwood',l:'Dark Walnut',hex:'#6A4020'},
    {v:'white marble',l:'White Marble',hex:'#F0EDEA'},{v:'grey concrete',l:'Concrete',hex:'#909090'},
    {v:'warm beige tile',l:'Beige Tile',hex:'#D4C4A8'},{v:'black tile',l:'Black Tile',hex:'#303030'},
    {v:'herringbone wood',l:'Herringbone',hex:'#B89060'},{v:'plush grey carpet',l:'Grey Carpet',hex:'#B0B0B0'},
    {v:'bamboo flooring',l:'Bamboo',hex:'#C8B070'},{v:'terracotta tile',l:'Terracotta',hex:'#C07040'},
    {v:'white washed wood',l:'Whitewashed',hex:'#E0D8C8'},{v:'chevron parquet',l:'Chevron',hex:'#A07840'},
];

function _buildRoomEditorPanel(){
    if($('roomEditorPanel')) return;
    const panel = document.createElement('div');
    panel.id = 'roomEditorPanel';
    panel.style.cssText = `display:none;position:fixed;top:0;right:0;bottom:0;width:min(420px,100vw);background:#fff;box-shadow:-4px 0 32px rgba(0,0,0,.18);z-index:9000;overflow-y:auto;font-family:inherit;transition:transform .3s ease;transform:translateX(100%);`;
    panel.innerHTML = `
    <div style="position:sticky;top:0;z-index:10;background:linear-gradient(135deg,#667eea,#764ba2);padding:18px 20px 14px;display:flex;align-items:center;justify-content:space-between;">
        <div><div style="color:#fff;font-size:1.1rem;font-weight:700;">✏️ Room Editor</div>
        <div style="color:rgba(255,255,255,.75);font-size:.78rem;margin-top:2px;">Modify &amp; regenerate your design</div></div>
        <button id="roomEditorClose" style="background:rgba(255,255,255,.2);border:none;color:#fff;width:32px;height:32px;border-radius:50%;cursor:pointer;font-size:1.1rem;display:flex;align-items:center;justify-content:center;">✕</button>
    </div>
    <div style="padding:18px 18px 100px;">
        <div id="editorCurrentSummary" style="background:#f8f7ff;border:1px solid #e0ddf5;border-radius:10px;padding:12px 14px;margin-bottom:18px;font-size:.82rem;color:#555;">
            <strong style="color:#667eea;">Current design:</strong> <span id="editorSummaryText">—</span>
        </div>
        <div class="editor-section"><div class="editor-section-title">🛋️ Add Furniture</div>
            <div id="furniturePresetChips" style="display:flex;flex-wrap:wrap;gap:7px;margin-bottom:10px;"></div>
            <input id="customFurnitureInput" type="text" placeholder="Type custom item, press Enter…" style="width:100%;box-sizing:border-box;padding:9px 12px;border:1.5px solid #ddd;border-radius:8px;font-size:.85rem;outline:none;"/>
            <div id="furnitureToAddList" style="display:flex;flex-wrap:wrap;gap:6px;margin-top:8px;min-height:0;"></div>
        </div>
        <div class="editor-section"><div class="editor-section-title">🗑️ Remove Furniture</div>
            <div id="existingFurnitureChips" style="display:flex;flex-wrap:wrap;gap:7px;"><span style="color:#aaa;font-size:.82rem;font-style:italic;">Generate a design first to see current furniture</span></div>
        </div>
        <div class="editor-section"><div class="editor-section-title">🎨 Wall Color</div>
            <div id="wallColorSwatches" style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:8px;"></div>
            <input id="customWallColor" type="text" placeholder="Custom color (e.g. dusty mauve)…" style="width:100%;box-sizing:border-box;padding:8px 12px;border:1.5px solid #ddd;border-radius:8px;font-size:.85rem;outline:none;"/>
        </div>
        <div class="editor-section"><div class="editor-section-title">🪵 Floor Material</div>
            <div id="floorSwatches" style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:8px;"></div>
            <input id="customFloor" type="text" placeholder="Custom floor (e.g. patterned cement tile)…" style="width:100%;box-sizing:border-box;padding:8px 12px;border:1.5px solid #ddd;border-radius:8px;font-size:.85rem;outline:none;"/>
        </div>
        <div class="editor-section"><div class="editor-section-title">🏠 Interior Style</div><div id="styleChips" style="display:flex;flex-wrap:wrap;gap:7px;"></div></div>
        <div class="editor-section"><div class="editor-section-title">💡 Lighting</div><div id="lightingChips" style="display:flex;flex-wrap:wrap;gap:7px;"></div></div>
        <div class="editor-section"><div class="editor-section-title">🌟 Mood / Atmosphere</div><div id="moodChips" style="display:flex;flex-wrap:wrap;gap:7px;"></div></div>
        <div class="editor-section"><div class="editor-section-title">📝 Extra Instructions</div>
            <textarea id="extraNoteInput" rows="3" placeholder="e.g. add more plants, make it brighter, larger windows…" style="width:100%;box-sizing:border-box;padding:10px 12px;border:1.5px solid #ddd;border-radius:8px;font-size:.85rem;resize:vertical;outline:none;font-family:inherit;"></textarea>
        </div>
        <div id="editorChangesPreview" style="background:#fffbf0;border:1px solid #ffe58f;border-radius:10px;padding:11px 14px;margin-top:4px;display:none;">
            <strong style="color:#b8860b;font-size:.82rem;">📋 Pending changes:</strong>
            <div id="editorChangesText" style="font-size:.8rem;color:#666;margin-top:5px;line-height:1.6;"></div>
        </div>
    </div>
    <div style="position:sticky;bottom:0;background:#fff;padding:14px 18px;border-top:1px solid #eee;display:flex;gap:10px;">
        <button id="editorResetBtn" style="flex:0 0 auto;padding:11px 18px;border-radius:9px;border:1.5px solid #ddd;background:#fff;cursor:pointer;font-size:.88rem;color:#666;">↺ Reset</button>
        <button id="editorApplyBtn" style="flex:1;padding:11px 0;border-radius:9px;border:none;background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;cursor:pointer;font-size:.95rem;font-weight:700;letter-spacing:.3px;">✨ Regenerate Design</button>
    </div>`;

    const style = document.createElement('style');
    style.textContent = `
    .editor-section{margin-bottom:20px;padding-bottom:18px;border-bottom:1px solid #f0eff7;}
    .editor-section:last-of-type{border-bottom:none;}
    .editor-section-title{font-weight:700;font-size:.88rem;color:#444;margin-bottom:10px;letter-spacing:.2px;}
    .editor-chip{padding:6px 13px;border-radius:20px;border:1.5px solid #ddd;background:#f7f7f9;cursor:pointer;font-size:.8rem;color:#555;transition:all .18s;user-select:none;white-space:nowrap;}
    .editor-chip:hover{border-color:#a89ef0;color:#667eea;}
    .editor-chip.active{background:linear-gradient(135deg,#667eea,#764ba2);border-color:#667eea;color:#fff;font-weight:600;}
    .editor-chip.to-remove{background:#fff0f0;border-color:#ffb3b3;color:#cc4444;text-decoration:line-through;}
    .color-swatch{width:44px;height:44px;border-radius:8px;cursor:pointer;border:2.5px solid transparent;transition:all .18s;position:relative;display:flex;align-items:flex-end;justify-content:center;overflow:hidden;flex-shrink:0;}
    .color-swatch:hover{transform:scale(1.08);}
    .color-swatch.active{border-color:#667eea !important;box-shadow:0 0 0 3px rgba(102,126,234,.3);}
    .color-swatch-label{font-size:9px;color:#fff;background:rgba(0,0,0,.45);width:100%;text-align:center;padding:2px 0;line-height:1.2;}
    .furniture-tag{display:inline-flex;align-items:center;gap:5px;padding:4px 10px 4px 12px;background:#eef2ff;border-radius:20px;font-size:.8rem;color:#667eea;border:1px solid #c7d0f8;}
    .furniture-tag button{background:none;border:none;cursor:pointer;color:#9aa5d8;font-size:.85rem;padding:0;line-height:1;}
    .furniture-tag button:hover{color:#cc4444;}`;
    document.head.appendChild(style);
    document.body.appendChild(panel);

    $('roomEditorClose').addEventListener('click', closeRoomEditor);
    panel.addEventListener('click', e=>{ if(e.target===panel) closeRoomEditor(); });
    $('editorResetBtn').addEventListener('click', _resetEditorState);
    $('editorApplyBtn').addEventListener('click', _applyRoomEdits);
    $('customFurnitureInput').addEventListener('keydown', e=>{
        if(e.key==='Enter'){ const val=$('customFurnitureInput').value.trim(); if(val){ _addFurnitureItem(val); $('customFurnitureInput').value=''; } }
    });
    $('customWallColor').addEventListener('input', ()=>{ _clearSwatchActive('wallColorSwatches'); _updateChangesPreview(); });
    $('customFloor').addEventListener('input', ()=>{ _clearSwatchActive('floorSwatches'); _updateChangesPreview(); });
    $('extraNoteInput').addEventListener('input', _updateChangesPreview);
    _buildChips('styleChips', STYLE_OPTIONS, 'style', true);
    _buildChips('lightingChips', LIGHTING_OPTIONS, 'lighting', true);
    _buildChips('moodChips', MOOD_OPTIONS, 'mood', true);
    _buildColorSwatches('wallColorSwatches', WALL_COLORS, 'wallColor', $('customWallColor'));
    _buildColorSwatches('floorSwatches', FLOOR_OPTIONS, 'floorColor', $('customFloor'));
}

const _editorState = { furnitureToAdd:[], furnitureToRemove:new Set(), wallColor:null, floorColor:null, style:null, lighting:null, mood:null };

function _resetEditorState(){
    _editorState.furnitureToAdd=[]; _editorState.furnitureToRemove=new Set();
    _editorState.wallColor=null; _editorState.floorColor=null;
    _editorState.style=null; _editorState.lighting=null; _editorState.mood=null;
    $$('.editor-chip').forEach(c=>c.classList.remove('active','to-remove'));
    $$('.color-swatch').forEach(s=>s.classList.remove('active'));
    $('customWallColor').value=''; $('customFloor').value='';
    $('extraNoteInput').value=''; $('customFurnitureInput').value='';
    setHTML('furnitureToAddList',''); _updateChangesPreview();
    showToast('Editor reset','success');
}
function _buildChips(containerId, options, stateKey, singleSelect=true){
    const container=$(containerId); if(!container) return; container.innerHTML='';
    options.forEach(opt=>{
        const btn=document.createElement('button'); btn.className='editor-chip'; btn.textContent=opt.l; btn.dataset.value=opt.v;
        btn.addEventListener('click', ()=>{
            if(singleSelect){ const isActive=btn.classList.contains('active'); container.querySelectorAll('.editor-chip').forEach(c=>c.classList.remove('active')); if(!isActive){ btn.classList.add('active'); _editorState[stateKey]=opt.v; } else{ _editorState[stateKey]=null; } }
            _updateChangesPreview();
        });
        container.appendChild(btn);
    });
}
function _buildColorSwatches(containerId, colors, stateKey, textInput){
    const container=$(containerId); if(!container) return; container.innerHTML='';
    colors.forEach(col=>{
        const sw=document.createElement('div'); sw.className='color-swatch'; sw.dataset.value=col.v;
        sw.style.background=col.hex; sw.style.borderColor=col.hex==='#FFFFFF'?'#ddd':col.hex;
        sw.innerHTML=`<div class="color-swatch-label">${col.l}</div>`;
        sw.addEventListener('click', ()=>{ container.querySelectorAll('.color-swatch').forEach(s=>s.classList.remove('active')); sw.classList.add('active'); _editorState[stateKey]=col.v; if(textInput) textInput.value=''; _updateChangesPreview(); });
        container.appendChild(sw);
    });
}
function _clearSwatchActive(containerId){ $(containerId)?.querySelectorAll('.color-swatch').forEach(s=>s.classList.remove('active')); }
function _addFurnitureItem(name){ if(_editorState.furnitureToAdd.includes(name)) return; _editorState.furnitureToAdd.push(name); _renderFurnitureToAdd(); _updateChangesPreview(); }
function _removeFurnitureAddItem(name){ _editorState.furnitureToAdd=_editorState.furnitureToAdd.filter(f=>f!==name); _renderFurnitureToAdd(); _updateChangesPreview(); }
function _renderFurnitureToAdd(){
    const list=$('furnitureToAddList'); if(!list) return;
    if(!_editorState.furnitureToAdd.length){ list.innerHTML=''; return; }
    list.innerHTML=_editorState.furnitureToAdd.map(f=>`<span class="furniture-tag">${f}<button onclick="_removeFurnitureAddItem('${f.replace(/'/g,"\\'")}')">×</button></span>`).join('');
}
function _populateExistingFurniture(){
    const container=$('existingFurnitureChips'); if(!container) return;
    const furniture=parsedRequirements?.furniture;
    if(!furniture||!furniture.length){ container.innerHTML='<span style="color:#aaa;font-size:.82rem;font-style:italic;">No furniture data</span>'; return; }
    container.innerHTML='';
    furniture.forEach(item=>{
        const btn=document.createElement('button'); btn.className='editor-chip'; btn.textContent=item; btn.dataset.value=item;
        btn.addEventListener('click', ()=>{ const isRemoving=_editorState.furnitureToRemove.has(item); if(isRemoving){ _editorState.furnitureToRemove.delete(item); btn.classList.remove('to-remove'); } else{ _editorState.furnitureToRemove.add(item); btn.classList.add('to-remove'); } _updateChangesPreview(); });
        container.appendChild(btn);
    });
}
function _populateFurniturePresets(){
    const container=$('furniturePresetChips'); if(!container) return;
    const roomType=(parsedRequirements?.room_type||'default').toLowerCase();
    const key=Object.keys(FURNITURE_PRESETS).find(k=>roomType.includes(k))||'default';
    container.innerHTML='';
    FURNITURE_PRESETS[key].forEach(item=>{
        const already=(parsedRequirements?.furniture||[]).map(f=>f.toLowerCase()).includes(item.toLowerCase());
        const btn=document.createElement('button'); btn.className='editor-chip'+(already?' active':''); btn.textContent=item+(already?' ✓':''); btn.dataset.value=item; btn.dataset.already=already?'1':'0';
        btn.addEventListener('click', ()=>{ if(btn.dataset.already==='1'){ showToast(`${item} already in design`,'warning'); return; } _addFurnitureItem(item); btn.classList.add('active'); btn.textContent=item+' ✓'; btn.dataset.already='1'; });
        container.appendChild(btn);
    });
}
function _updateEditorSummary(){
    if(!parsedRequirements){ setText('editorSummaryText','—'); return; }
    const p=parsedRequirements; const fCount=(p.furniture||[]).length;
    setText('editorSummaryText',`${p.style||'modern'} ${p.room_type||'room'} · ${fCount} furniture item${fCount!==1?'s':''}`);
}
function _updateChangesPreview(){
    const changes=[];
    if(_editorState.furnitureToAdd.length) changes.push(`+ Add: ${_editorState.furnitureToAdd.join(', ')}`);
    if(_editorState.furnitureToRemove.size) changes.push(`- Remove: ${[..._editorState.furnitureToRemove].join(', ')}`);
    const wc=_getWallColor(); if(wc) changes.push(`🎨 Wall: ${wc}`);
    const fc=_getFloorColor(); if(fc) changes.push(`🪵 Floor: ${fc}`);
    if(_editorState.style)    changes.push(`🏠 Style: ${_editorState.style}`);
    if(_editorState.lighting) changes.push(`💡 Lighting: ${_editorState.lighting}`);
    if(_editorState.mood)     changes.push(`🌟 Mood: ${_editorState.mood}`);
    const note=$('extraNoteInput')?.value?.trim(); if(note) changes.push(`📝 Note: ${note.slice(0,60)}${note.length>60?'…':''}`);
    const preview=$('editorChangesPreview'); if(!preview) return;
    if(changes.length){ $('editorChangesText').innerHTML=changes.map(c=>`<div>${c}</div>`).join(''); preview.style.display='block'; }
    else{ preview.style.display='none'; }
}
function _getWallColor(){ return $('customWallColor')?.value?.trim()||_editorState.wallColor||null; }
function _getFloorColor(){ return $('customFloor')?.value?.trim()||_editorState.floorColor||null; }

function openRoomEditor(){
    if(!generatedImage){ showToast('Generate a design first','warning'); return; }
    const panel=$('roomEditorPanel'); panel.style.display='block';
    requestAnimationFrame(()=>{ panel.style.transform='translateX(0)'; });
    _resetEditorState(); _updateEditorSummary(); _populateFurniturePresets(); _populateExistingFurniture();
}
function closeRoomEditor(){ const panel=$('roomEditorPanel'); panel.style.transform='translateX(100%)'; setTimeout(()=>{ panel.style.display='none'; },300); }

async function _applyRoomEdits(){
    if(!parsedRequirements){ showToast('No design to edit','warning'); return; }
    const edits={};
    if(_editorState.furnitureToAdd.length)   edits.add_furniture=[..._editorState.furnitureToAdd];
    if(_editorState.furnitureToRemove.size)  edits.remove_furniture=[..._editorState.furnitureToRemove];
    const wc=_getWallColor(); const fc=_getFloorColor();
    if(wc) edits.wall_color=wc; if(fc) edits.floor_color=fc;
    if(_editorState.style)    edits.style=_editorState.style;
    if(_editorState.lighting) edits.lighting=_editorState.lighting;
    if(_editorState.mood)     edits.mood=_editorState.mood;
    const note=$('extraNoteInput')?.value?.trim(); if(note) edits.extra_note=note;
    if(!Object.keys(edits).length){ showToast('Make at least one change first','warning'); return; }
    closeRoomEditor();
    const editLabels=[];
    if(edits.add_furniture)    editLabels.push(`adding ${edits.add_furniture.join(', ')}`);
    if(edits.remove_furniture) editLabels.push(`removing ${edits.remove_furniture.join(', ')}`);
    if(edits.wall_color)       editLabels.push(`${edits.wall_color} walls`);
    if(edits.floor_color)      editLabels.push(`${edits.floor_color} floor`);
    if(edits.style)            editLabels.push(`${edits.style} style`);
    if(edits.lighting)         editLabels.push(`${edits.lighting} lighting`);
    if(edits.mood)             editLabels.push(`${edits.mood} mood`);
    showLoading(true,`Regenerating: ${editLabels.slice(0,3).join(', ')}${editLabels.length>3?'…':''}…`);
    try{
        const res=await fetch('/api/edit-room',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({parsed_requirements:parsedRequirements,edits})});
        let data; try{ data=await res.json(); } catch{ throw new Error(`Server error (status ${res.status})`); }
        if(!res.ok||!data.success) throw new Error(data.error||`Edit failed (HTTP ${res.status})`);
        generatedImage=data.image_base64; generatedImagePath=data.image_path; parsedRequirements=data.parsed_requirements;
        if(data.cost_breakdown) costData=data.cost_breakdown;
        $('outputImage').src=data.image_url; switchToTab('generated');
        showToast(`✅ Regenerated with ${(editLabels.slice(0,2).join(', '))||'changes'}!`,'success');
    } catch(err){ console.error('Room edit error:',err); showToast('Edit failed: '+err.message,'error'); }
    finally{ showLoading(false); }
}
function enhanceDesign(){ openRoomEditor(); }
function openEnhanceModal(){ openRoomEditor(); }


// ── Upload ────────────────────────────────────────────────────
function handleDrop(e){ e.preventDefault(); $('uploadArea').classList.remove('dragover'); const f=e.dataTransfer.files[0]; if(f&&f.type.startsWith('image/')) processImageFile(f); else showToast('Please drop an image file','error'); }
function handleImageUpload(e){ const f=e.target.files[0]; if(f) processImageFile(f); }
function processImageFile(file){
    if(file.size>16*1024*1024){ showToast('Max 16 MB','error'); return; }
    const reader=new FileReader();
    reader.onload=ev=>{ uploadedImage=file; const prev=$('previewImage'); prev.src=ev.target.result; prev.style.display='block'; document.querySelector('.upload-placeholder').style.display='none'; $('removeImage').style.display='block'; $('segmentBtn').disabled=false; };
    reader.readAsDataURL(file);
}
function clearUploadedImage(e){
    if(e&&e.stopPropagation) e.stopPropagation();
    uploadedImage=null; segmentedData=null;
    $('previewImage').style.display='none'; $('previewImage').src='';
    document.querySelector('.upload-placeholder').style.display='block';
    $('removeImage').style.display='none'; $('segmentBtn').disabled=true; $('imageInput').value='';
}
async function loadRoomTypes(){ try{ await (await fetch('/api/room-types')).json(); } catch(_){} }

// ── Segmentation ──────────────────────────────────────────────
async function segmentImage(){
    if(!uploadedImage){ showToast('Upload an image first','warning'); return; }
    const fd=new FormData(); fd.append('image',uploadedImage);
    showLoading(true,'Segmenting image…');
    try{ const res=await fetch('/api/segment',{method:'POST',body:fd}); const data=await res.json(); if(data.success){ segmentedData=data; displaySegmentedImage(data); switchToTab('segmented'); showToast('Image segmented!','success'); } else showToast(data.error||'Segmentation failed','error'); }
    catch{ showToast('Error segmenting image','error'); } finally{ showLoading(false); }
}
function displaySegmentedImage(data){
    $('segmentedImage').src=data.segmented_image;
    let html=`<h4>Segmentation Results</h4><p><strong>Objects Detected:</strong> ${data.num_objects}</p><p><strong>Labels:</strong> ${data.detected_objects.join(', ')}</p><h5 style="margin-top:12px">Room Structure</h5><p><strong>Ceiling:</strong> RGB(${data.room_structure.ceiling_color.join(', ')})</p><p><strong>Floor:</strong> RGB(${data.room_structure.floor_color.join(', ')})</p><h5 style="margin-top:8px">Wall Colours</h5>`;
    for(const [dir,col] of Object.entries(data.room_structure.walls)) html+=`<p><strong>${dir[0].toUpperCase()+dir.slice(1)}:</strong> RGB(${col.join(', ')})</p>`;
    setHTML('segmentationInfo',html); show('segmentedContainer');
}

// ── Prompt analysis ───────────────────────────────────────────
async function analyzePrompt(){
    const prompt=$('designPrompt').value.trim(); if(!prompt){ showToast('Enter a design description','warning'); return; }
    showLoading(true,'Analysing prompt…');
    try{ const res=await fetch('/api/analyze-prompt',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt,room_type:$('roomType').value})}); const data=await res.json();
        if(data.success){ parsedRequirements=data.parsed_requirements; displayAnalysis(data.parsed_requirements); switchToTab('analysis'); showToast('Prompt analysed!','success'); }
        else{ const miss=data.missing_elements?`Missing: ${data.missing_elements.join(', ')}. `:''; showToast(miss+(data.suggestion||data.error||'Analysis failed'),'warning'); }
    } catch{ showToast('Error analysing prompt','error'); } finally{ showLoading(false); }
}
function displayAnalysis(d){
    let roomHTML=`<p><strong>Type:</strong> ${d.room_type||'—'}</p>`; if(d.dimensions&&(d.dimensions.width||d.dimensions.length)) roomHTML+=`<p><strong>Dimensions:</strong> ${d.dimensions.width}×${d.dimensions.length} ${d.dimensions.unit||'ft'}</p>`; setHTML('roomInfo',roomHTML);
    let colHTML=''; if(d.colors){ for(const dir of ['north','south','east','west']) if(d.colors[dir]) colHTML+=`<p><strong>${dir[0].toUpperCase()+dir.slice(1)} Wall:</strong> ${d.colors[dir]}</p>`; if(d.colors.overall?.length) colHTML+=`<p><strong>Palette:</strong> ${d.colors.overall.join(', ')}</p>`; }
    setHTML('colorInfo',colHTML||'<p>No specific colours mentioned</p>');
    setHTML('furnitureInfo',d.furniture?.length?`<ul>${d.furniture.map(i=>`<li>${i}</li>`).join('')}</ul>`:'<p>No specific furniture mentioned</p>');
    let stHTML=`<p>${d.style||'modern'}</p>`; if(d.special_requirements?.length) stHTML+=`<ul>${d.special_requirements.map(r=>`<li>${r}</li>`).join('')}</ul>`; setHTML('styleInfo',stHTML); show('analysisContainer');
}

// ── Design generation ─────────────────────────────────────────
async function generateDesign(){
    const prompt=$('designPrompt').value.trim(); const mode=document.querySelector('input[name="mode"]:checked')?.value||'fast';
    if(!prompt){ showToast('Enter a design description','warning'); return; }
    showLoading(true,`Generating design [${mode} mode] …`); switchToTab('generated');
    try{
        await fetch('/api/switch-mode',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mode})});
        const res=await fetch('/api/generate-design',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt,room_type:$('roomType').value})});
        const data=await res.json();
        if(data.success){ generatedImage=data.image_base64; generatedImagePath=data.image_path; parsedRequirements=data.parsed_requirements; $('outputImage').src=data.image_url; hide('outputPlaceholder'); show('outputImageContainer'); if(data.cost_breakdown) costData=data.cost_breakdown; showToast('Design generated! Use ✏️ Edit Room to customise it.','success'); }
        else showToast(data.error||'Generation failed','error');
    } catch{ showToast('Error generating design','error'); } finally{ showLoading(false); }
}

// ── Cost estimation ───────────────────────────────────────────
async function estimateCost(){
    if(costData&&parsedRequirements){ displayCostEstimate(costData); switchToTab('cost'); showToast('Cost breakdown ready!','success'); return; }
    if(!parsedRequirements){ if(!$('designPrompt').value.trim()){ showToast('Enter a design description first','warning'); return; } await analyzePrompt(); if(!parsedRequirements){ showToast('Could not parse requirements','error'); return; } }
    showLoading(true,'Calculating detailed cost breakdown…');
    try{ const res=await fetch('/api/estimate-cost',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({parsed_data:parsedRequirements})}); const data=await res.json(); if(data.success){ costData=data.cost_breakdown; displayCostEstimate(data.cost_breakdown); switchToTab('cost'); showToast('Cost breakdown ready!','success'); } else showToast(data.error||'Cost estimation failed','error'); }
    catch(err){ showToast('Error estimating cost: '+err.message,'error'); } finally{ showLoading(false); }
}
function displayCostEstimate(bd){
    // Keep _activeTier in sync with whatever tier is being displayed
    const tierFromData = bd?.room_details?.quality_tier?.toLowerCase();
    if(tierFromData) _activeTier = tierFromData;
    const rd=bd.room_details||{}; const cb=bd.cost_breakdown||{};
    setText('costTotal',`₹${fmtINR(bd.total_cost)}`); setText('costRange',`Range: ₹${fmtINR(bd.cost_range.minimum)} – ₹${fmtINR(bd.cost_range.maximum)}`); setText('costTier',`Quality: ${rd.quality_tier||'STANDARD'}`);
    setHTML('roomDetails',`<p><strong>Room Type:</strong> ${rd.room_type||'—'}</p><p><strong>Area:</strong> ${Number(rd.area_sqft||150).toFixed(0)} sq ft ${rd.dimensions_specified?'':'<small style="color:#e07d7d"> (default)</small>'}</p><p><strong>Style:</strong> ${rd.style||'—'}</p><p><strong>Furniture items:</strong> ${rd.furniture_count??0}</p><p><strong>Materials listed:</strong> ${rd.material_count??0}</p>`);
    const order=['base_construction','furniture','materials','lighting','labour','additional']; let html='';
    for(const key of order){ const item=cb[key]; if(!item) continue; html+=`<div class="cost-breakdown-item"><strong>${item.icon||''} ${item.label||key}</strong><span>₹${fmtINR(item.amount)}</span></div><div style="padding:2px 16px 8px;color:#888;font-size:.84rem">${item.description||''}</div>`; if(item.items?.length){ for(const sub of item.items){ const name=sub.name||sub.material||'—'; const amt=sub.amount||0; let extra=''; if(sub.unit_cost) extra=` <small>@ ₹${fmtINR(sub.unit_cost)}/pc</small>`; else if(sub.rate_per_sqft) extra=` <small>@ ₹${fmtINR(sub.rate_per_sqft)}/sq ft × ${sub.coverage_sqft} sq ft</small>`; html+=`<div class="cost-breakdown-item sub-item"><span>↳ ${name}${extra}</span><span style="color:#999">₹${fmtINR(amt)}</span></div>`; } } }
    html+=`<div class="cost-breakdown-item totals-row"><strong>Subtotal</strong><span>₹${fmtINR(bd.subtotal)}</span></div><div class="cost-breakdown-item"><strong>Designer Fee (10%)</strong><span>₹${fmtINR(bd.designer_fee)}</span></div><div class="cost-breakdown-item"><strong>GST (18%)</strong><span>₹${fmtINR(bd.gst_18_percent)}</span></div><div class="cost-breakdown-item grand-total"><strong>TOTAL</strong><span>₹${fmtINR(bd.total_cost)}</span></div>`;
    setHTML('costBreakdown',html);
    if(bd.notes?.length) setHTML('costNotes',`<ul>${bd.notes.map(n=>`<li>${n}</li>`).join('')}</ul>`);
    const ts=bd.ui_metadata?.generated_at; if(ts) setText('costTimestamp',`Generated: ${new Date(ts).toLocaleString()}`);
    hide('costPlaceholder'); show('costContainer');
}

// ── Tier comparison ───────────────────────────────────────────

// Canonical display order for tiers
const TIER_ORDER  = ['basic', 'standard', 'premium', 'luxury'];
const TIER_ICONS  = { basic:'🪑', standard:'🛋️', premium:'✨', luxury:'👑' };
const TIER_COLORS = { basic:'#6c757d', standard:'#0d6efd', premium:'#7c3aed', luxury:'#b8860b' };

// Track which tier is currently displayed in the cost panel
let _activeTier = null;

async function compareCostTiers(){
    if(!parsedRequirements){ showToast('Generate a design first','warning'); return; }
    showLoading(true,'Comparing quality tiers…');
    try{
        const res  = await fetch('/api/cost-comparison',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt:$('designPrompt').value.trim(),room_type:$('roomType').value})});
        const data = await res.json();
        if(data.success){
            allTierData = data.comparisons;
            // Sync _activeTier with whatever is currently showing
            if(!_activeTier) _activeTier = costData?.room_details?.quality_tier?.toLowerCase() || 'standard';
            _renderTierCards();
            showToast('Click a tier card to see its full breakdown!','success');
        } else showToast(data.error||'Comparison failed','error');
    } catch{ showToast('Error comparing tiers','error'); }
    finally{ showLoading(false); }
}

function _renderTierCards(){
    if(!allTierData) return;
    let html='<div class="tier-cards">';
    // Always render in canonical order: basic → standard → premium → luxury
    for(const tier of TIER_ORDER){
        const bd = allTierData[tier];
        if(!bd) continue;
        const isActive = (tier === _activeTier);
        const icon  = TIER_ICONS[tier]  || '🏠';
        const color = TIER_COLORS[tier] || '#6c757d';
        html += `
        <div class="tier-card ${isActive?'active':''}" data-tier="${tier}"
             onclick="switchTier('${tier}')"
             style="--tier-color:${color};">
            <div class="tier-card-icon">${icon}</div>
            <h5>${tier.toUpperCase()}</h5>
            <div class="price">₹${fmtINR(bd.total_cost)}</div>
            <small class="tier-range">₹${fmtINR(bd.cost_range.minimum)} – ₹${fmtINR(bd.cost_range.maximum)}</small>
            <div class="tier-click-hint">${isActive ? '✓ Current' : 'Click to apply'}</div>
        </div>`;
    }
    html += '</div>';
    setHTML('tierComparison', html);
}

function switchTier(tier){
    if(!allTierData?.[tier]){ showToast('Tier data not available','warning'); return; }
    _activeTier = tier;
    costData    = allTierData[tier];
    displayCostEstimate(costData);
    _renderTierCards();   // re-render cards AFTER costData is updated so active state is correct
    showToast(`Switched to ${tier.toUpperCase()} tier!`, 'success');
}

// ── Download helpers ──────────────────────────────────────────
function dlLink(href,filename){ const a=document.createElement('a'); a.href=href; a.download=filename; a.click(); }
function downloadImage(){ const img=$('outputImage'); if(!img?.src){ showToast('No image','warning'); return; } dlLink(img.src,`dreamspace-design-${Date.now()}.png`); showToast('Image downloaded!','success'); }
function downloadCostReport(){
    if(!costData){ showToast('No cost data','warning'); return; }
    const rd=costData.room_details||{}; const cb=costData.cost_breakdown||{};
    let txt='═'.repeat(58)+'\n    INTERIOR DESIGN COST ESTIMATE REPORT\n'+'═'.repeat(58)+'\n\n';
    txt+=`Room Type    : ${rd.room_type}\nArea         : ${Number(rd.area_sqft).toFixed(0)} sq ft\nQuality Tier : ${rd.quality_tier}\nStyle        : ${rd.style}\n\n`+'─'.repeat(58)+'\n';
    for(const [,item] of Object.entries(cb)){ txt+=`${(item.label||'').padEnd(28)} ₹${fmtINR(item.amount)}\n`; for(const sub of (item.items||[])) txt+=`   ↳ ${((sub.name||sub.material||'')).padEnd(24)} ₹${fmtINR(sub.amount)}\n`; }
    txt+='─'.repeat(58)+'\n'+`${'Subtotal'.padEnd(28)} ₹${fmtINR(costData.subtotal)}\n${'Designer Fee (10%)'.padEnd(28)} ₹${fmtINR(costData.designer_fee)}\n${'GST (18%)'.padEnd(28)} ₹${fmtINR(costData.gst_18_percent)}\n`+'═'.repeat(58)+'\n'+`${'TOTAL'.padEnd(28)} ₹${fmtINR(costData.total_cost)}\n`+'═'.repeat(58)+'\n\n';
    txt+=`Range: ₹${fmtINR(costData.cost_range.minimum)} – ₹${fmtINR(costData.cost_range.maximum)}\n\nNOTES:\n`; (costData.notes||[]).forEach(n=>txt+=`  • ${n}\n`); txt+=`\nGenerated: ${new Date().toLocaleString()}\n`;
    dlLink(URL.createObjectURL(new Blob([txt],{type:'text/plain'})),`cost-estimate-${Date.now()}.txt`); showToast('Report downloaded!','success');
}
function printCostReport(){
    if(!costData){ showToast('No cost data','warning'); return; }
    const rd=costData.room_details||{}; const cb=costData.cost_breakdown||{}; let rows='';
    for(const [,item] of Object.entries(cb)){ rows+=`<tr><td>${item.icon||''} ${item.label||''}</td><td>₹${fmtINR(item.amount)}</td></tr>`; for(const sub of (item.items||[])) rows+=`<tr style="color:#888;font-size:.85rem"><td>&nbsp;&nbsp;↳ ${sub.name||sub.material}</td><td>₹${fmtINR(sub.amount)}</td></tr>`; }
    const w=window.open('','_blank'); w.document.write(`<!DOCTYPE html><html><head><title>Cost Estimate</title><style>body{font-family:Arial,sans-serif;padding:30px}h1{color:#667eea;border-bottom:2px solid #667eea;padding-bottom:10px}table{width:100%;border-collapse:collapse;margin:20px 0}td{padding:10px;border-bottom:1px solid #eee}td:last-child{text-align:right;font-weight:600;color:#667eea}.total-row td{background:#667eea;color:white;font-size:1.3rem;font-weight:bold}</style></head><body><h1>🏠 Interior Design Cost Estimate</h1><p><strong>Room:</strong> ${rd.room_type} | <strong>Area:</strong> ${Number(rd.area_sqft).toFixed(0)} sq ft | <strong>Tier:</strong> ${rd.quality_tier}</p><table>${rows}<tr><td>Subtotal</td><td>₹${fmtINR(costData.subtotal)}</td></tr><tr><td>Designer Fee (10%)</td><td>₹${fmtINR(costData.designer_fee)}</td></tr><tr><td>GST (18%)</td><td>₹${fmtINR(costData.gst_18_percent)}</td></tr><tr class="total-row"><td>TOTAL</td><td>₹${fmtINR(costData.total_cost)}</td></tr></table><p><em>Range: ₹${fmtINR(costData.cost_range.minimum)} – ₹${fmtINR(costData.cost_range.maximum)}</em></p><ul>${(costData.notes||[]).forEach(n=>`<li>${n}</li>`).join('')}</ul></body></html>`);
    w.document.close(); w.print();
}

// ── Clear all ─────────────────────────────────────────────────
function clearAll(){
    if(!confirm('Clear all inputs?')) return;
    $('designPrompt').value=''; $('roomType').value=''; setText('charCount','0');
    clearUploadedImage({stopPropagation:()=>{}});
    show('outputPlaceholder'); hide('outputImageContainer'); show('costPlaceholder'); hide('costContainer'); hide('segmentedContainer'); hide('analysisContainer');
    generatedImage=null; generatedImagePath=null; parsedRequirements=null; costData=null; allTierData=null; _activeTier=null;
    switchToTab('generated'); showToast('All cleared!','success');
}