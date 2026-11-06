import json,sys,os
P="/Applications/DeepSeek Harness.app/Contents/Resources/app.asar"
f=open(P,"rb")
import struct
h1,h2,l1,l2=struct.unpack("<IIII", f.read(16))
f.seek(16); hdr=json.loads(f.read(l2).decode("utf8"))
DATA=8+h2
print(f"# data offset {DATA}", file=sys.stderr)
def walk(node,prefix=""):
    for k,v in node.get("files",{}).items():
        p=prefix+"/"+k
        if "files" in v: yield from walk(v,p)
        else: yield p,v
def get(path):
    node=hdr
    for part in path.strip("/").split("/"):
        node=node["files"][part]
    if "files" in node: return None
    off=DATA+int(node["offset"]); size=node["size"]
    f.seek(off); return f.read(size)
if __name__=="__main__":
    cmd=sys.argv[1]
    if cmd=="ls":
        pref=sys.argv[2] if len(sys.argv)>2 else ""
        for p,v in walk(hdr):
            if p.startswith(pref): print(p, v.get("size"))
    elif cmd=="get":
        data=get(sys.argv[2]); sys.stdout.buffer.write(data)
    elif cmd=="find":
        sub=sys.argv[2]
        for p,v in walk(hdr):
            if sub in p: print(p, v.get("size"))
