from pathlib import Path
ROOT=Path('/opt/zbrano'); MAIN=ROOT/'app/main.py'; INDEX=ROOT/'app/static/index.html'
def require(t,m,l):
    if m not in t: raise RuntimeError(f'ZBRANO v0.11.17 patch missing: {l}')
def patch_main():
    t=MAIN.read_text(); t=t.replace('version="0.11.16"','version="0.11.17"').replace('"version": "0.11.16"','"version": "0.11.17"'); MAIN.write_text(t)
def patch_index():
    t=INDEX.read_text()
    reps=[('<title>ZBRANO Workshop Assistant</title>','<title>ZBRANO Workshop Assistant</title>'),('content: "SYS/ZBRANO_WORKSHOP"','content: "SYS/ZBRANO_WORKSHOP"'),('<h1>ZBRANO</h1>','<h1>ZBRANO</h1>'),('ZBRANO intelligence core online.','ZBRANO intelligence core online.'),('aria-label="Stop ZBRANO response"','aria-label="Stop ZBRANO response"'),('Elegant ZBRANO glass','Elegant ZBRANO glass'),('every new ZBRANO response','every new ZBRANO response'),('ZBRANO saves only explicit requests.','ZBRANO saves only explicit requests.'),('During quiet hours ZBRANO still replies','During quiet hours ZBRANO still replies'),('ZBRANO voice systems online. How may I assist?','ZBRANO voice systems online. How may I assist?'),('saved ZBRANO conversation','saved ZBRANO conversation'),('Include this entity in ZBRANO policy','Include this entity in ZBRANO policy'),('save immediately to ZBRANO runtime policy','save immediately to ZBRANO runtime policy'),('generated_by: "ZBRANO"','generated_by: "ZBRANO"'),('project: "ZBRANO Workshop Assistant"','project: "ZBRANO Workshop Assistant"'),('Check the ZBRANO app log.','Check the ZBRANO app log.')]
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
