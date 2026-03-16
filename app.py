"""
app.py – Dream Space: AI-Powered Interior Designer  (v5 – cost fix + prompt fidelity)
"""

import os
import cv2
import math
import traceback
import numpy as np
from datetime import datetime

from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

from models.segmentation import RoomSegmenter

try:
    from utils.nlp_processor import PromptAnalyzer
    _ANALYZER_AVAILABLE = True
except ImportError:
    _ANALYZER_AVAILABLE = False
    print("⚠️  WARNING: utils/nlp_processor.py missing or no PromptAnalyzer.")

try:
    from utils.image_generator import InteriorDesignGenerator, assemble_final_prompt
    _ASSEMBLE_FROM_MODULE = True
except ImportError:
    from utils.image_generator import InteriorDesignGenerator
    _ASSEMBLE_FROM_MODULE = False

from cost_estimator import CostEstimator
load_dotenv()


# ── Local prompt assembler fallback ───────────────────────────
def _local_assemble_final_prompt(parsed: dict, analyzer=None) -> str:
    def _to_list(val):
        if not val: return []
        if isinstance(val, str): return [val]
        try: return list(val)
        except TypeError: return []

    room_type  = parsed.get("room_type") or "room"
    style      = parsed.get("style") or "modern"
    dims       = parsed.get("dimensions") or {}
    colors     = parsed.get("colors") or {}
    furniture  = _to_list(parsed.get("furniture"))
    materials  = _to_list(parsed.get("materials"))
    mood       = _to_list(parsed.get("mood"))
    lighting   = _to_list(parsed.get("lighting"))
    view       = parsed.get("view_direction") or ""
    extra_note = parsed.get("extra_note") or ""

    parts = [f"a {style} {room_type}"]

    # ── Dimensions ────────────────────────────────────────────
    if dims.get("width") and dims.get("length"):
        unit = dims.get("unit", "ft")
        parts.append(f"{dims['width']} {unit} by {dims['length']} {unit} room")

    # ── View ──────────────────────────────────────────────────
    if view:
        parts.append(f"{view} view")

    # ── Wall colours — compass directions first, then overall ─
    if isinstance(colors, dict):
        wall_parts = []
        for direction in ["north", "south", "east", "west"]:
            c = colors.get(direction)
            if c:
                wall_parts.append(f"{direction} wall {c}")
        if wall_parts:
            parts.append("walls: " + ", ".join(wall_parts))
        overall = _to_list(colors.get("overall"))
        if overall:
            parts.append(f"color palette: {', '.join(overall[:4])}")
    elif colors:
        parts.append(f"color palette: {', '.join(_to_list(colors)[:4])}")

    # ── Furniture — every item listed ────────────────────────
    if furniture:
        parts.append(f"containing {', '.join(furniture)}")

    # ── Materials / floor ────────────────────────────────────
    if materials:
        parts.append(f"with {', '.join(materials[:4])} finishes")

    # ── Mood & lighting ───────────────────────────────────────
    if mood:
        parts.append(f"{', '.join(mood[:3])} atmosphere")
    if lighting:
        parts.append(f"{', '.join(lighting[:2])} lighting")

    # ── Extra free-text note ─────────────────────────────────
    if extra_note:
        parts.append(extra_note)

    # ── Quality suffixes ──────────────────────────────────────
    parts += [
        "professional interior photography",
        "photorealistic",
        "8K resolution",
        "perfect lighting",
        "highly detailed",
    ]

    return ", ".join(parts)[:900]

_assemble = assemble_final_prompt if _ASSEMBLE_FROM_MODULE else _local_assemble_final_prompt


# ── App setup ──────────────────────────────────────────────────
app = Flask(__name__)
app.config.update(
    SECRET_KEY         = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key'),
    UPLOAD_FOLDER      = 'uploads',
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_FILE_SIZE', 16 * 1024 * 1024)),
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'},
)
for d in ['uploads', 'outputs', 'static/generated']:
    os.makedirs(d, exist_ok=True)

_segmenter = _nlp_analyzer = _image_generator = _cost_estimator = None

def get_segmenter():
    global _segmenter
    if _segmenter is None: _segmenter = RoomSegmenter()
    return _segmenter

def get_nlp_analyzer():
    global _nlp_analyzer
    if not _ANALYZER_AVAILABLE:
        raise RuntimeError("PromptAnalyzer unavailable. Fix utils/nlp_processor.py.")
    if _nlp_analyzer is None: _nlp_analyzer = PromptAnalyzer()
    return _nlp_analyzer

def get_image_generator():
    global _image_generator
    if _image_generator is None: _image_generator = InteriorDesignGenerator(mode="fast")
    return _image_generator

def get_cost_estimator():
    global _cost_estimator
    if _cost_estimator is None: _cost_estimator = CostEstimator()
    return _cost_estimator

def allowed_file(fn):
    return '.' in fn and fn.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def ts():
    return datetime.now().strftime('%Y%m%d_%H%M%S')


# ══════════════════════════════════════════════════════════════
# TOP-VIEW RENDERER  (unchanged)
# ══════════════════════════════════════════════════════════════
def _dominant_colors(img_np, n=8):
    px = img_np.reshape(-1, 3).astype(np.float32)
    _, labels, centers = cv2.kmeans(px, n, None,
        (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0),
        5, cv2.KMEANS_RANDOM_CENTERS)
    counts = np.bincount(labels.flatten())
    order  = np.argsort(-counts)
    return [tuple(int(v) for v in centers[i]) for i in order]

def _assign_colors(palette):
    bright = sorted(palette, key=lambda c: sum(c), reverse=True)
    dark   = sorted(palette, key=lambda c: sum(c))
    mid    = sorted(palette, key=lambda c: abs(sum(c) - 390))
    def clamp(c): return tuple(min(255, max(0, int(v))) for v in c)
    wall   = clamp((min(255,bright[0][0]+12), min(255,bright[0][1]+8), min(255,bright[0][2]+4)))
    furn   = clamp(mid[0])
    acc_b  = dark[1] if len(dark) > 1 else dark[0]
    accent = clamp((max(60,acc_b[0]), max(55,acc_b[1]), max(50,acc_b[2])))
    return {"wall": wall, "furn": furn, "accent": accent}

def _get_font(size):
    for path in [
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "C:/Windows/Fonts/arialbd.ttf",
    ]:
        try: return ImageFont.truetype(path, size)
        except Exception: pass
    return ImageFont.load_default()

def _drop_shadow(draw, cx, cy, w, h, r=10, offset=(6,6), alpha=80):
    ox, oy = offset
    for i in range(r, 0, -1):
        a = int(alpha*(1-i/r))
        draw.rounded_rectangle([cx-w//2+ox-i//2,cy-h//2+oy-i//2,cx+w//2+ox+i//2,cy+h//2+oy+i//2],
            radius=6, outline=(36,28,20,a), width=2)

def _draw_plant(draw, cx, cy, size=38):
    base_g=(65,128,68); dark_g=(42,98,48)
    draw.ellipse([cx-size//4,cy-size//4,cx+size//4,cy+size//4], fill=(158,128,98))
    for i in range(6):
        angle=i*60*math.pi/180
        lx=int(cx+math.cos(angle)*size*0.56); ly=int(cy+math.sin(angle)*size*0.56); lr=size//3
        draw.ellipse([lx-lr,ly-lr,lx+lr,ly+lr], fill=base_g if i%2==0 else dark_g)
    draw.ellipse([cx-size//5,cy-size//5,cx+size//5,cy+size//5], fill=(88,152,82))

def render_top_view(image_path: str, output_path: str) -> str:
    W=H=800
    raw=Image.open(image_path).convert("RGB").resize((W,H),Image.LANCZOS)
    img_np=np.array(raw)
    colors=_assign_colors(_dominant_colors(img_np,n=8))
    sc=colors["furn"]; ac=colors["accent"]
    canvas=Image.new("RGB",(W,H),(215,200,180))
    PAD=int(W*0.06); x1,y1,x2,y2=PAD,PAD,W-PAD,H-PAD; rw,rh=x2-x1,y2-y1
    floor=np.full((rh,rw,3),(195,170,140),dtype=np.float32)
    for gx in range(0,rw,30):
        floor[:,gx:gx+2]*=0.87
        mid=gx+15
        if mid<rw: floor[:,mid:mid+1]*=0.93
    for gy in range(0,rh,3):
        if gy%9==0: floor[gy:gy+1,:]*=0.96
    Yg,Xg=np.ogrid[:rh,:rw]
    glow=1.0+0.24*np.exp(-((Xg)**2+(Yg)**2)/(rw*rh*0.10))
    for c in range(3): floor[:,:,c]=np.clip(floor[:,:,c]*glow,0,255)
    canvas.paste(Image.fromarray(floor.astype(np.uint8)),(x1,y1))
    win_cy=y1+int(rh*0.31)
    Yg2,Xg2=np.mgrid[:H,:W]; dist=np.sqrt((Xg2-x1)**2*0.25+(Yg2-win_cy)**2)
    glow2=np.clip(1-dist/(rw*0.48),0,1)*0.18
    arr=np.array(canvas).astype(np.float32)
    arr[:,:,0]=np.clip(arr[:,:,0]+glow2*60,0,255); arr[:,:,1]=np.clip(arr[:,:,1]+glow2*46,0,255); arr[:,:,2]=np.clip(arr[:,:,2]+glow2*28,0,255)
    canvas=Image.fromarray(arr.astype(np.uint8))
    draw=ImageDraw.Draw(canvas,"RGBA")
    for i in range(22,0,-1):
        a=int(50*(1-i/22)); draw.rectangle([x1+i,y1+i,x2-i,y2-i],outline=(28,20,12,a),width=1)
    draw.rectangle([x1,y1,x2,y2],outline=(65,52,40),width=4)
    draw.rectangle([x1-3,y1-3,x2+3,y2+3],outline=(52,42,32),width=3)
    draw.rectangle([x1-6,y1-6,x2+6,y2+6],outline=(42,33,25),width=2)
    pw=10
    for cx_p,cy_p in [(x1-pw,y1-pw),(x2,y1-pw),(x1-pw,y2),(x2,y2)]:
        draw.rectangle([cx_p,cy_p,cx_p+pw+6,cy_p+pw+6],fill=(30,22,16))
    win_y1=y1+int(rh*0.18); win_y2=y1+int(rh*0.44); wh=win_y2-win_y1
    draw.rectangle([x1-5,win_y1,x1+7,win_y2],fill=(205,222,238))
    draw.rectangle([x1-5,win_y1,x1+7,win_y2],outline=(130,165,198),width=2)
    for d in [wh//3,2*wh//3]: draw.line([(x1-3,win_y1+d),(x1+6,win_y1+d)],fill=(130,165,198),width=1)
    door_x=x1+int(rw*0.36); door_w=55
    draw.rectangle([door_x,y2-2,door_x+door_w,y2+10],fill=(215,200,180))
    draw.arc([door_x,y2-door_w,door_x+door_w*2,y2+door_w],start=90,end=180,fill=(70,58,46),width=2)
    rug_cx=x1+int(rw*0.47); rug_cy=y1+int(rh*0.50); rug_w=int(rw*0.37); rug_h=int(rh*0.27)
    _drop_shadow(draw,rug_cx,rug_cy,rug_w,rug_h,r=10,offset=(6,6))
    draw.rounded_rectangle([rug_cx-rug_w//2,rug_cy-rug_h//2,rug_cx+rug_w//2,rug_cy+rug_h//2],radius=7,fill=(162,145,126,225),outline=(138,122,104,235),width=2)
    for i in [7,14]: draw.rounded_rectangle([rug_cx-rug_w//2+i,rug_cy-rug_h//2+i,rug_cx+rug_w//2-i,rug_cy+rug_h//2-i],radius=5,outline=(135,118,100,150),width=1)
    s_cx=x1+int(rw*0.45); s_y=y1+int(rh*0.09); s_w=int(rw*0.52); s_d=int(rh*0.14)
    back_h=int(s_d*0.34); arm_w=int(s_d*0.22)
    _drop_shadow(draw,s_cx,s_y+s_d//2,s_w+arm_w*2,s_d,r=12,offset=(7,7))
    draw.rounded_rectangle([s_cx-s_w//2,s_y,s_cx+s_w//2,s_y+back_h],radius=5,fill=(*sc,255))
    seat_y=s_y+back_h+2; cw3=(s_w-6)//3
    for i in range(3):
        cx_i=s_cx-s_w//2+i*(cw3+3)+2
        draw.rounded_rectangle([cx_i,seat_y,cx_i+cw3,s_y+s_d],radius=5,fill=(*sc,255),outline=(*tuple(max(0,v-18) for v in sc),255),width=1)
    for ax_i in [s_cx-s_w//2-arm_w,s_cx+s_w//2]:
        draw.rounded_rectangle([ax_i,s_y,ax_i+arm_w,s_y+s_d],radius=4,fill=(*tuple(max(0,v-22) for v in sc),255))
    ac_cx=x1+int(rw*0.19); ac_cy=y1+int(rh*0.72); ac_s=int(rw*0.16)
    _drop_shadow(draw,ac_cx,ac_cy,ac_s,ac_s,r=10,offset=(6,6))
    draw.rounded_rectangle([ac_cx-ac_s//2,ac_cy-ac_s//2,ac_cx+ac_s//2,ac_cy+ac_s//2],radius=8,fill=(*sc,255))
    draw.rounded_rectangle([ac_cx-ac_s//2,ac_cy-ac_s//2,ac_cx+ac_s//2,ac_cy-ac_s//2+int(ac_s*0.30)],radius=5,fill=(*tuple(max(0,v-22) for v in sc),255))
    t_cx=x1+int(rw*0.47); t_cy=y1+int(rh*0.42); t_w=int(rw*0.25); t_h=int(rh*0.12)
    t_col=(232,222,208)
    _drop_shadow(draw,t_cx,t_cy,t_w,t_h,r=8,offset=(5,5))
    draw.rounded_rectangle([t_cx-t_w//2,t_cy-t_h//2,t_cx+t_w//2,t_cy+t_h//2],radius=6,fill=(*t_col,255),outline=(175,160,142,255),width=2)
    draw.rounded_rectangle([t_cx-t_w//2+5,t_cy-t_h//2+5,t_cx+t_w//2-5,t_cy-t_h//2+t_h//3],radius=4,fill=(248,242,232,110))
    st_x=x2-int(rw*0.14); st_y1=y1+int(rh*0.11); st_y2=y1+int(rh*0.62); st_w=int(rw*0.11)
    _drop_shadow(draw,st_x+st_w//2,(st_y1+st_y2)//2,st_w,st_y2-st_y1,r=10,offset=(5,5))
    draw.rounded_rectangle([st_x,st_y1,st_x+st_w,st_y2],radius=4,fill=(*ac,255),outline=(*tuple(max(0,v-24) for v in ac),255),width=2)
    dh3=(st_y2-st_y1)//3
    for i in [1,2]: draw.line([(st_x+3,st_y1+i*dh3),(st_x+st_w-3,st_y1+i*dh3)],fill=(*tuple(max(0,v-30) for v in ac),200),width=1)
    tv_cx=x1+int(rw*0.47); tv_y=y2-int(rh*0.07); tv_w=int(rw*0.38); tv_d=int(rh*0.045); tv_col=(50,46,44)
    _drop_shadow(draw,tv_cx,tv_y-tv_d//2,tv_w,tv_d,r=6,offset=(4,3))
    draw.rounded_rectangle([tv_cx-tv_w//2,tv_y-tv_d,tv_cx+tv_w//2,tv_y],radius=3,fill=(*tv_col,255))
    draw.rounded_rectangle([tv_cx-tv_w//2+5,tv_y-tv_d+3,tv_cx+tv_w//2-5,tv_y-3],radius=2,fill=(68,65,70,255))
    pm=int(PAD*0.55)
    for px_p,py_p,ps in [(x1+pm,y1+pm,40),(x2-pm,y1+pm,35),(x2-pm,y2-pm,32),(x1+pm,y2-pm,34)]:
        _draw_plant(draw,px_p,py_p,ps)
    ccx,ccy=W-PAD+16,PAD-16
    draw.ellipse([ccx-16,ccy-16,ccx+16,ccy+16],fill=(242,238,232,230),outline=(78,66,54,200),width=1)
    draw.polygon([(ccx,ccy-14),(ccx-4,ccy+2),(ccx+4,ccy+2)],fill=(28,22,16))
    draw.polygon([(ccx,ccy+14),(ccx-4,ccy-2),(ccx+4,ccy-2)],fill=(158,145,132))
    fsm=_get_font(12)
    draw.text((ccx,ccy-16),"N",fill=(28,22,16),font=fsm,anchor="mb")
    dy_d=y1-8; draw.line([(x1,dy_d),(x2,dy_d)],fill=(100,88,76,200),width=1)
    for ex in [x1,x2]: draw.line([(ex,dy_d-4),(ex,dy_d+4)],fill=(100,88,76,200),width=1)
    draw.text(((x1+x2)//2,dy_d-2),"approx. 4.5 m",fill=(85,74,62,220),font=fsm,anchor="mb")
    dx_d=x1-8; draw.line([(dx_d,y1),(dx_d,y2)],fill=(100,88,76,200),width=1)
    for ey in [y1,y2]: draw.line([(dx_d-4,ey),(dx_d+4,ey)],fill=(100,88,76,200),width=1)
    draw.text((dx_d-3,(y1+y2)//2),"approx. 4.0 m",fill=(85,74,62,220),font=fsm,anchor="rm")
    ax,ay=x1+rw//2,y2-24; lbl="Room  (~18 m\u00b2)"
    bb=draw.textbbox((0,0),lbl,font=_get_font(13)); lw=bb[2]-bb[0]
    draw.rounded_rectangle([ax-lw//2-11,ay-10,ax+lw//2+11,ay+10],radius=5,fill=(10,8,6,212))
    draw.text((ax,ay),lbl,fill=(238,234,228),font=_get_font(13),anchor="mm")
    f_big=_get_font(20); txt="\u2299  TOP VIEW"
    bb2=draw.textbbox((0,0),txt,font=f_big); tw2,th2=bb2[2]-bb2[0],bb2[3]-bb2[1]
    tx2,ty2=(W-tw2)//2,H-th2-13
    draw.rounded_rectangle([tx2-12,ty2-7,tx2+tw2+12,ty2+th2+7],radius=6,fill=(14,12,10,218))
    draw.text((tx2,ty2),txt,fill=(255,255,255,255),font=f_big)
    canvas=ImageEnhance.Contrast(canvas).enhance(1.06)
    canvas=ImageEnhance.Color(canvas).enhance(1.10)
    canvas.save(output_path,"PNG")
    return output_path


# ══════════════════════════════════════════════════════════════
# PAGES
# ══════════════════════════════════════════════════════════════
@app.route('/')
def index(): return render_template('index.html')


# ══════════════════════════════════════════════════════════════
# SEGMENTATION
# ══════════════════════════════════════════════════════════════
@app.route('/api/segment', methods=['POST'])
def segment_image():
    try:
        if 'image' not in request.files: return jsonify({'error': 'No image file'}), 400
        f = request.files['image']
        if f.filename == '' or not allowed_file(f.filename): return jsonify({'error': 'Invalid file'}), 400
        fname = f"{ts()}_{secure_filename(f.filename)}"
        fpath = os.path.join(app.config['UPLOAD_FOLDER'], fname)
        f.save(fpath)
        seg  = get_segmenter(); data = seg.segment_room(fpath)
        overlay  = seg.create_mask_overlay(data['original_image'], data['masks'])
        out_name = f"segmented_{fname}"; out_path = os.path.join('static/generated', out_name)
        cv2.imwrite(out_path, cv2.cvtColor(overlay, cv2.COLOR_RGB2BGR))
        return jsonify({'success': True, 'original_image': f'/uploads/{fname}',
            'segmented_image': f'/static/generated/{out_name}', 'num_objects': len(data['labels']),
            'detected_objects': data['labels'],
            'room_structure': {
                'ceiling_color': data['room_structure']['ceiling']['dominant_color'],
                'floor_color':   data['room_structure']['floor']['dominant_color'],
                'walls': {d: info['dominant_color'] for d, info in data['room_structure']['walls'].items()},
            }})
    except Exception as e: traceback.print_exc(); return jsonify({'error': str(e)}), 500


# ══════════════════════════════════════════════════════════════
# PROMPT ANALYSIS
# ══════════════════════════════════════════════════════════════
@app.route('/api/analyze-prompt', methods=['POST'])
def analyze_prompt():
    try:
        try: analyzer = get_nlp_analyzer()
        except RuntimeError as e: return jsonify({'error': str(e)}), 503
        data = request.get_json(); prompt = data.get('prompt', '').strip(); room_type = data.get('room_type')
        if not prompt: return jsonify({'error': 'No prompt'}), 400
        validation = analyzer.validate_prompt(prompt)
        if not all(validation.values()):
            missing = [k.replace('has_','').replace('_',' ') for k, v in validation.items() if not v]
            return jsonify({'error': 'Incomplete prompt', 'missing_elements': missing,
                'suggestion': 'Include room type, colours, and style/furniture.'}), 400
        parsed = analyzer.analyze_prompt(prompt, room_type)
        gen_prompt = _assemble(parsed, analyzer)
        return jsonify({'success': True, 'parsed_requirements': parsed,
            'generation_prompt': gen_prompt, 'object_placements': parsed.get('object_placements', []),
            'view_direction': parsed.get('view_direction')})
    except Exception as e: traceback.print_exc(); return jsonify({'error': str(e)}), 500


# ══════════════════════════════════════════════════════════════
# DESIGN GENERATION
# ══════════════════════════════════════════════════════════════
@app.route('/api/generate-design', methods=['POST'])
def generate_design():
    try:
        try: analyzer = get_nlp_analyzer()
        except RuntimeError as e: return jsonify({'error': str(e)}), 503
        data = request.get_json(); prompt = data.get('prompt', '').strip(); room_type = data.get('room_type')
        if not prompt: return jsonify({'error': 'No prompt'}), 400
        generator  = get_image_generator()
        parsed     = analyzer.analyze_prompt(prompt, room_type)
        gen_prompt = _assemble(parsed, analyzer)
        print(f"\n{'='*60}\n🏠 Room: {parsed.get('room_type')}  🎨 Prompt: {gen_prompt[:120]}\n{'='*60}")
        image    = generator.generate_from_prompt(gen_prompt, width=768, height=768)
        out_name = f"design_{ts()}.png"; out_path = os.path.join('static/generated', out_name)
        image.save(out_path)
        try:
            estimator = get_cost_estimator()
            cost_breakdown = estimator.estimate_cost(parsed)
            cost_report    = estimator.format_cost_report(cost_breakdown)
        except Exception as ce:
            print(f"⚠️  Cost failed: {ce}"); cost_breakdown = cost_report = None
        def _jp(p): return {k: (list(v) if isinstance(v, (set,frozenset)) else v) for k,v in p.items()}
        return jsonify({'success': True, 'image_url': f'/static/generated/{out_name}',
            'image_base64': generator.image_to_base64(image), 'image_path': out_path,
            'parsed_requirements': _jp(parsed), 'generation_prompt': gen_prompt,
            'object_placements': list(parsed.get('object_placements') or []),
            'view_direction': parsed.get('view_direction'),
            'cost_breakdown': cost_breakdown, 'cost_report': cost_report})
    except Exception as e: traceback.print_exc(); return jsonify({'error': str(e)}), 500


# ══════════════════════════════════════════════════════════════
# ROOM REDESIGN
# ══════════════════════════════════════════════════════════════
@app.route('/api/redesign-room', methods=['POST'])
def redesign_room():
    try:
        if 'image' not in request.files or 'prompt' not in request.form:
            return jsonify({'error': 'Missing fields'}), 400
        try: analyzer = get_nlp_analyzer()
        except RuntimeError as e: return jsonify({'error': str(e)}), 503
        f = request.files['image']; prompt = request.form['prompt']; stamp = ts()
        img_name = f"{stamp}_base.png"; img_path = os.path.join(app.config['UPLOAD_FOLDER'], img_name)
        f.save(img_path)
        if 'mask' in request.files:
            mf = request.files['mask']; mk_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{stamp}_mask.png")
            mf.save(mk_path)
        else:
            base = Image.open(img_path)
            mask = Image.fromarray(np.ones((base.height, base.width), dtype=np.uint8) * 255)
            mk_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{stamp}_mask.png"); mask.save(mk_path)
        generator = get_image_generator()
        parsed = analyzer.analyze_prompt(prompt); enhanced = _assemble(parsed, analyzer)
        result = generator.redesign_room(img_path, mk_path, enhanced)
        out_name = f"redesign_{stamp}.png"; out_path = os.path.join('static/generated', out_name)
        result.save(out_path)
        return jsonify({'success': True, 'image_url': f'/static/generated/{out_name}',
            'image_base64': generator.image_to_base64(result), 'original_image': f'/uploads/{img_name}'})
    except Exception as e: traceback.print_exc(); return jsonify({'error': str(e)}), 500


# ══════════════════════════════════════════════════════════════
# ROOM EDITOR
# ══════════════════════════════════════════════════════════════

def _safe(val):
    """Convert set/frozenset/tuple/None/str → plain list."""
    if not val: return []
    if isinstance(val, str): return [val]
    try: return list(val)
    except TypeError: return []

def _merge_room_edits(parsed: dict, edits: dict) -> dict:
    """Return a new parsed dict with every requested edit applied."""
    import copy
    p = copy.deepcopy(parsed)

    # ── Furniture ──────────────────────────────────────────────
    furniture = _safe(p.get('furniture'))
    for item in _safe(edits.get('add_furniture')):
        item = item.strip()
        if item and item.lower() not in [f.lower() for f in furniture]:
            furniture.append(item)
    removes = {r.lower().strip() for r in _safe(edits.get('remove_furniture'))}
    furniture = [f for f in furniture if f.lower().strip() not in removes]
    p['furniture'] = furniture

    # ── Wall color ─────────────────────────────────────────────
    if edits.get('wall_color'):
        colors = p.get('colors') or {}
        if isinstance(colors, (set, list)): colors = {'overall': _safe(colors)}
        colors['overall'] = [edits['wall_color'].strip()]
        p['colors'] = colors

    # ── Floor / material ───────────────────────────────────────
    if edits.get('floor_color'):
        materials = _safe(p.get('materials'))
        floor_val = edits['floor_color'].strip()
        floor_keys = {'wood','oak','walnut','pine','tile','marble','vinyl','laminate','carpet','concrete'}
        materials = [m for m in materials if m.lower() not in floor_keys]
        materials.insert(0, floor_val)
        p['materials'] = materials

    # ── Style, lighting, mood ──────────────────────────────────
    if edits.get('style'):    p['style']    = edits['style'].strip()
    if edits.get('lighting'): p['lighting'] = [edits['lighting'].strip()]
    if edits.get('mood'):     p['mood']     = [edits['mood'].strip()]
    if edits.get('extra_note'): p['extra_note'] = edits['extra_note'].strip()

    return p


@app.route('/api/edit-room', methods=['POST'])
def edit_room():
    """Apply targeted edits to an existing design and regenerate the image."""
    try:
        try: analyzer = get_nlp_analyzer()
        except RuntimeError as e: return jsonify({'error': str(e)}), 503

        data = request.get_json()
        if not data: return jsonify({'error': 'No data'}), 400

        parsed_orig = data.get('parsed_requirements')
        edits       = data.get('edits') or {}
        if not parsed_orig: return jsonify({'error': 'parsed_requirements required'}), 400

        parsed_new = _merge_room_edits(parsed_orig, edits)
        gen_prompt = _assemble(parsed_new, analyzer)
        if parsed_new.get('extra_note'):
            gen_prompt = (gen_prompt + f", {parsed_new['extra_note']}")[:900]

        print(f"\n{'='*60}")
        print(f"✏️  Room Edit — edits: {list(edits.keys())}")
        print(f"   Furniture : {parsed_new.get('furniture')}")
        print(f"   Style     : {parsed_new.get('style')}")
        print(f"   Lighting  : {parsed_new.get('lighting')}")
        print(f"🎨 Prompt    : {gen_prompt[:160]}")
        print('='*60)

        generator = get_image_generator()
        image     = generator.generate_from_prompt(gen_prompt, width=768, height=768)
        out_name  = f"edited_{ts()}.png"
        out_path  = os.path.join('static/generated', out_name)
        image.save(out_path)

        try:
            estimator = get_cost_estimator()
            cost_breakdown = estimator.estimate_cost(parsed_new)
            cost_report    = estimator.format_cost_report(cost_breakdown)
        except Exception as ce:
            print(f"⚠️  Cost failed (non-fatal): {ce}"); cost_breakdown = cost_report = None

        def _jp(p): return {k: (list(v) if isinstance(v,(set,frozenset)) else v) for k,v in p.items()}
        return jsonify({'success': True, 'image_url': f'/static/generated/{out_name}',
            'image_base64': generator.image_to_base64(image), 'image_path': out_path,
            'parsed_requirements': _jp(parsed_new), 'generation_prompt': gen_prompt,
            'cost_breakdown': cost_breakdown, 'cost_report': cost_report})
    except Exception as e: traceback.print_exc(); return jsonify({'error': str(e)}), 500


# ── Legacy enhance-design alias ────────────────────────────────
@app.route('/api/enhance-design', methods=['POST'])
def enhance_design():
    return edit_room()


# ══════════════════════════════════════════════════════════════
# TOP-VIEW
# ══════════════════════════════════════════════════════════════
@app.route('/api/generate-top-view', methods=['POST'])
def generate_top_view():
    try:
        data = request.get_json(); image_path = data.get('image_path', '').strip()
        if not image_path: return jsonify({'error': 'No image_path'}), 400
        for candidate in [image_path,
            os.path.join('static/generated', os.path.basename(image_path)),
            os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(image_path))]:
            if os.path.exists(candidate): image_path = candidate; break
        else: return jsonify({'error': f'Image not found: {image_path}'}), 404
        out_name = f"topview_{ts()}.png"; out_path = os.path.join('static/generated', out_name)
        render_top_view(image_path, out_path)
        return jsonify({'success': True, 'image_url': f'/static/generated/{out_name}'})
    except Exception as e: traceback.print_exc(); return jsonify({'error': str(e)}), 500


# ══════════════════════════════════════════════════════════════
# COST ESTIMATION
# ══════════════════════════════════════════════════════════════
@app.route('/api/estimate-cost', methods=['POST'])
def estimate_cost():
    try:
        data = request.get_json()
        if not data: return jsonify({'error': 'No data'}), 400
        estimator = get_cost_estimator()
        if 'parsed_data' in data: parsed = data['parsed_data']
        elif 'prompt' in data:
            try: analyzer = get_nlp_analyzer()
            except RuntimeError as e: return jsonify({'error': str(e)}), 503
            parsed = analyzer.analyze_prompt(data['prompt'], data.get('room_type'))
        else: return jsonify({'error': 'Provide parsed_data or prompt'}), 400
        breakdown = estimator.estimate_cost(parsed); report = estimator.format_cost_report(breakdown)
        return jsonify({'success': True, 'cost_breakdown': breakdown, 'text_report': report})
    except Exception as e: traceback.print_exc(); return jsonify({'error': str(e)}), 500


@app.route('/api/cost-comparison', methods=['POST'])
def cost_comparison():
    """
    Returns cost breakdowns for all four tiers in guaranteed order:
    basic → standard → premium → luxury.

    Uses CostEstimator.compare_tiers() which returns an OrderedDict,
    so the JS front-end always renders tier cards in the correct order.
    """
    try:
        data = request.get_json()
        if not data or 'prompt' not in data:
            return jsonify({'error': 'No prompt'}), 400

        try:
            analyzer = get_nlp_analyzer()
        except RuntimeError as e:
            return jsonify({'error': str(e)}), 503

        estimator   = get_cost_estimator()
        parsed      = analyzer.analyze_prompt(data['prompt'], data.get('room_type'))

        # compare_tiers() returns OrderedDict: basic→standard→premium→luxury
        comparisons = estimator.compare_tiers(parsed)
        area        = estimator._room_area(parsed.get('dimensions', {}))

        return jsonify({
            'success':     True,
            'room_type':   parsed.get('room_type', 'room'),
            'area_sqft':   area,
            'comparisons': comparisons,   # OrderedDict serialises in insertion order ✓
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ══════════════════════════════════════════════════════════════
# MISC
# ══════════════════════════════════════════════════════════════
@app.route('/api/room-types', methods=['GET'])
def get_room_types():
    try: analyzer = get_nlp_analyzer()
    except RuntimeError as e: return jsonify({'error': str(e)}), 503
    return jsonify({'room_types': list(analyzer.room_furniture.keys()),
        'furniture_by_room': analyzer.room_furniture, 'styles': analyzer.styles,
        'color_palettes': analyzer.color_palette})

@app.route('/api/switch-mode', methods=['POST'])
def switch_mode():
    try:
        data = request.get_json(); new_mode = data.get('mode','fast').lower()
        if new_mode not in ('fast','quality'): return jsonify({'error': 'Use "fast" or "quality"'}), 400
        get_image_generator().switch_mode(new_mode)
        return jsonify({'success': True, 'current_mode': new_mode})
    except Exception as e: return jsonify({'error': str(e)}), 500

@app.route('/api/get-mode', methods=['GET'])
def get_current_mode():
    try:
        g = get_image_generator()
        return jsonify({'current_mode': g.mode, 'device': g.device,
            'default_steps': g.default_steps, 'default_size': g.default_size,
            'estimated_time': '30–90 s' if g.mode=='fast' else '10–20 min'})
    except Exception as e: return jsonify({'error': str(e)}), 500

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename))


# ══════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════
if __name__ == '__main__':
    print("\n" + "="*60)
    print("🏠  DREAM SPACE v5 — Cost Fix + Prompt Fidelity")
    print("="*60)
    print(f"  HF Token       : {'✓' if os.getenv('HUGGINGFACE_TOKEN') else '✗ Missing'}")
    print(f"  PromptAnalyzer : {'✓' if _ANALYZER_AVAILABLE else '✗ fix utils/nlp_processor.py'}")
    print(f"  Routes         : /api/edit-room, /api/cost-comparison (ordered)")
    print("="*60 + "\n")
    app.run(debug=os.getenv('FLASK_DEBUG','True')=='True', host='0.0.0.0', port=5000)