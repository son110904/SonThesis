# -*- coding: utf-8 -*-
import re

_RE_SYMBOL_NOISE = re.compile(
    r"(?:^|(?<=\s))["
    r"\U00002000-\U000020FF"
    r"\U00000080-\U000000FF"
    r"\U0001F000-\U0001FAFF"
    r"\U0001F600-\U0001F64F"
    r"\U0001F300-\U0001F5FF"
    r"\U00002600-\U000027BF"
    r"\U0000E00-\U0000E7F"
    r"\U00003000-\U0000303F"
    r"\U0001B80-\U0001BFF"
    r"\U0000F00-\U0000FFF"
    r"\U0000E80-\U0000EFF"
    r"\U0001A00-\U0001A1F"
    r"]+?(?=\s|$)"
)

def clean(t):
    prev = None
    c = t
    while prev != c:
        prev = c
        c = _RE_SYMBOL_NOISE.sub(" ", c)
    return re.sub(r"\s{2,}", " ", c).strip()

tests = [
    ("Noise only", "  ♔ ♔ ๋İ ๋Ï ๋Ì ๋Í ๋Î ๋Ğ ๋π ๋å ๋Â ๋Ë ๋Ê "),
    ("Skills normal", "Skills: Python, Java, SQL."),
    ("Vietnamese", "Đây là CV tiếng Việt có dấu"),
    ("Tech names", "CI/CD, Node.js, React.js"),
    ("English", "I speak English and Vietnamese"),
    ("Korean mixed", "뽀나♔ ♔ ๋İ ๋Ï ๋Ì"),
    ("Full CV snippet", "Skills: Python, SQL, Figma. Experience: BA intern at FPT."),
    ("Noisy start", "♔ ♔ LE PHAN ANH Business Analyst"),
]

for label, t in tests:
    c = clean(t)
    has_noise = any(ch in c for ch in "♔๋İ๋Ï๋Ì๋Í๋Î๋Ğ๋π๋å๋Â๋Ë๋Ê뽀나")
    status = "STRIPPED" if not c else ("CLEAN" if not has_noise else "STILL_NOISE")
    print(f"[{status}] {label}")
    print(f"  IN : {repr(t)}")
    print(f"  OUT: {repr(c)}")
    print()
