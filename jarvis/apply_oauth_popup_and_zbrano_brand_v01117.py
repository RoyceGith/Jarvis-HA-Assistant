from pathlib import Path
ROOT=Path('/opt/jarvis'); MAIN=ROOT/'app/main.py'; INDEX=ROOT/'app/static/index.html'
def require(t,m,l):
    if m not in t: raise RuntimeError(f'Jarvis v0.11.17 patch missing: {l}')
def patch_main():
    t=MAIN.read_text(); t=t.replace('version="0.11.16"','version="0.11.17"').replace('"version": "0.11.16"','"version": "0.11.17"'); MAIN.write_text(t)
def patch_index():
    t=INDEX.read_text()
    reps=[('<title>Jarvis Workshop Assistant</title>','<title>ZBRANO Workshop Assistant</title>'),('content: "SYS/JARVIS_WORKSHOP"','content: "SYS/ZBRANO_WORKSHOP"'),('<h1>Jarvis</h1>','<h1>ZBRANO</h1>'),('Jarvis intelligence core online.','ZBRANO intelligence core online.'),('aria-label="Stop Jarvis response"','aria-label="Stop ZBRANO response"'),('Elegant Jarvis glass','Elegant ZBRANO glass'),('every new Jarvis response','every new ZBRANO response'),('Jarvis saves only explicit requests.','ZBRANO saves only explicit requests.'),('During quiet hours Jarvis still replies','During quiet hours ZBRANO still replies'),('Jarvis voice systems online. How may I assist?','ZBRANO voice systems online. How may I assist?'),('saved Jarvis conversation','saved ZBRANO conversation'),('Include this entity in Jarvis policy','Include this entity in ZBRANO policy'),('save immediately to Jarvis runtime policy','save immediately to ZBRANO runtime policy'),('generated_by: "Jarvis"','generated_by: "ZBRANO"'),('project: "Jarvis Workshop Assistant"','project: "ZBRANO Workshop Assistant"'),('Check the Jarvis app log.','Check the ZBRANO app log.')]
    for o,n in reps: require(t,o,o); t=t.replace(o,n)
    o='authWindow = window.open("about:blank", "_blank", "noopener");'; require(t,o,'popup'); t=t.replace(o,'authWindow = window.open("https://github.com/login/device", "_blank");\n      if (authWindow) { try { authWindow.opener = null; } catch (_) {} }',1)
    o='if (authWindow) authWindow.location = start.verification_uri;'; require(t,o,'popup nav'); t=t.replace(o,'if (authWindow && start.verification_uri) {\n        try { authWindow.location.replace(start.verification_uri); }\n        catch (_) { authWindow.location.href = start.verification_uri; }\n      }',1)
    t=t.replace('HUD 0.11.16','HUD 0.11.17')
    INDEX.write_text(t)
def verify():
    m=MAIN.read_text(); i=INDEX.read_text();
    for x in ['version="0.11.17"','<h1>ZBRANO</h1>','content: "ZBRANO"','SYS/ZBRANO_WORKSHOP','window.open("https://github.com/login/device", "_blank")','HUD 0.11.17']:
        if x not in m and x not in i: raise RuntimeError('missing '+x)
if __name__=='__main__': patch_main(); patch_index(); verify()
