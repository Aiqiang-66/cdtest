import zipfile, re, os, glob

# Find the docx file
files = glob.glob(r'D:\python\dmx\cdtest\*.docx')
print("Found files:", files)

for path in files:
    if 'TT' in path or '小程序' in path or '雷霆' in path:
        print(f"\n=== Reading: {path} ===")
        with zipfile.ZipFile(path) as z:
            with z.open('word/document.xml') as f:
                content = f.read().decode('utf-8')
                text = re.sub(r'<[^>]+>', ' ', content)
                text = re.sub(r'\s+', ' ', text).strip()
                print(text[:20000])
        break
