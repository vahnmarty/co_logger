
import re

CHARACTERS = ["Dubu", "KimDahyun"]

def detect_death(line):
    for character in CHARACTERS:
        pattern = (
            rf"\b{re.escape(character)}\s+"
            rf"was\s+killed\s+by\s+([A-Za-z0-9_]+)"
        )

        match = re.search(pattern, line, re.IGNORECASE)

        if match:
            return {
                "character": character,
                "killer": match.group(1),
                "message": line.strip()
            }

    return None


# Test using actual OCR output
test_messages = [
    '(S7S" Dubu was killed by RedDevilL117!',
    'Sys KimDahyun was killed by Player123!',
    'Dubu speaks to All: hello',
    'KingNomaD won SouthofCloud'
]

for message in test_messages:
    result = detect_death(message)

    if result:
        print(
            f"DEATH DETECTED: {result['character']} "
            f"was killed by {result['killer']}"
        )
