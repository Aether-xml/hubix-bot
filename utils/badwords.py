"""
Nexify AutoMod — Built-in Protection Database
Comprehensive lists for multi-language profanity, scam links, and more.
"""

# ═══════════════════════════════════════════════════════════════
#  ENGLISH PROFANITY
# ═══════════════════════════════════════════════════════════════

ENGLISH_BAD_WORDS = [
    # Heavy profanity
    "fuck", "fucking", "fucked", "fucker", "fuckers", "fucks",
    "motherfucker", "motherfucking", "motherfuckers",
    "mf", "mfs", "mfer",
    "shit", "shitty", "shitting", "bullshit", "horseshit", "dipshit", "shithead",
    "bitch", "bitches", "bitchass", "bitching", "sonofabitch",
    "ass", "asshole", "assholes", "dumbass", "fatass", "jackass", "smartass",
    "badass", "kickass", "asshat", "assclown", "arsehole",
    "dick", "dickhead", "dickheads", "dickwad", "dickface",
    "cunt", "cunts",
    "bastard", "bastards",
    "damn", "goddamn", "damnit",
    "piss", "pissed", "pissoff", "pissing",
    "crap", "crappy",
    "hell", "hellhole",
    "douche", "douchebag", "douchebags",
    "wanker", "wankers", "tosser", "twat", "twats",
    "bollocks", "bugger", "bloody",
    "arse", "git", "pillock", "plonker", "prat", "sod",
    "knobhead", "bellend", "minger", "numpty",

    # Sexual slurs
    "whore", "whores", "slut", "sluts", "slutty",
    "hoe", "hoes", "skank", "skanks", "tramp",
    "hooker", "prostitute",
    "cock", "cocks", "cocksucker", "cocksuckers",
    "penis", "vagina", "pussy", "pussies",
    "cum", "cumshot", "cumming", "creampie",
    "blowjob", "handjob", "rimjob",
    "dildo", "vibrator",
    "tits", "titties", "boobs", "boobies",
    "jizz", "spunk", "semen",
    "orgasm", "orgy", "gangbang",
    "masturbate", "masturbation", "fap", "fapping",
    "erection", "boner",
    "deepthroat", "throatfuck",
    "anal", "anus", "butthole", "buttplug",
    "queef",

    # Racial / hate slurs
    "nigga", "niggas", "nigger", "niggers", "negro", "negroes",
    "cracker", "crackers",
    "chink", "chinks", "gook", "gooks",
    "spic", "spics", "wetback", "wetbacks", "beaner", "beaners",
    "kike", "kikes",
    "paki", "pakis",
    "wop", "wops", "dago", "dagos",
    "jap", "japs",
    "coon", "coons", "darkie", "darkies",
    "honky", "honkey",
    "redneck", "hillbilly",
    "redskin", "redskins",
    "sandnigger", "towelhead", "camel jockey",
    "zipperhead",

    # Homophobic / transphobic
    "fag", "fags", "faggot", "faggots", "faggy",
    "dyke", "dykes",
    "tranny", "trannies", "shemale", "shemales",
    "ladyboy", "he-she", "heshe",
    "homo", "homos",
    "queer",  # context dependent but blocked by default

    # Ableist
    "retard", "retarded", "retards", "tard", "tards",
    "spastic", "spaz", "spazzy",
    "cripple", "crippled",
    "mongoloid",

    # Violence / threats
    "kys", "killyourself", "kill yourself",
    "neck yourself", "go die", "drink bleach",
    "rope yourself", "end yourself",
    "slit your wrists", "cut yourself",

    # Misc offensive
    "nazi", "nazis", "hitler", "heil", "sieg heil",
    "kkk", "ku klux", "white power", "white supremacy",
    "genocide",
    "rape", "raping", "rapist", "rapists", "raped",
    "molest", "molester", "molestation",
    "pedo", "pedophile", "pedophiles", "paedophile",
    "predator",
    "incest",

    # NSFW keywords
    "porn", "porno", "pornography", "pornhub",
    "hentai", "xxx", "nsfw",
    "xvideos", "xnxx", "xhamster",
    "brazzers", "onlyfans", "chaturbate",
    "rule34", "r34", "e621",
    "yiff", "furporn",
    "loli", "lolicon", "shotacon", "shota",
    "ahegao",
    "milf", "gilf", "dilf",
    "camgirl", "camboy",
    "sexting", "nudes", "dickpic", "dickpics",

    # Common evasions
    "f u c k", "f.u.c.k", "f_u_c_k", "fvck", "phuck", "phuk",
    "fuk", "fuq", "fck", "fcking", "fcked",
    "sh1t", "sh!t", "s.h.i.t",
    "b1tch", "b!tch", "bi+ch",
    "a$$", "a$$hole", "@ss", "@sshole",
    "d1ck", "d!ck",
    "c0ck", "c.o.c.k",
    "p0rn", "pr0n",
    "n1gga", "n1gger", "nigg3r", "n!gga", "niqqer", "niqqa",
    "r3tard", "r*tard",
    "stfu", "gtfo", "lmfao", "lmao",
    "wtf", "wth",
    "fml", "smfh",
]

# ═══════════════════════════════════════════════════════════════
#  TURKISH PROFANITY
# ═══════════════════════════════════════════════════════════════

TURKISH_BAD_WORDS = [
    # Heavy profanity
    "amk", "amq", "aq", "amına", "amina", "amınakoyim", "aminakoyim",
    "amınakoyayım", "aminakoyayim", "amınakoduğum", "aminakodugum",
    "amınakoyduğum", "aminakoydugum", "amk oğlu", "amkoglu",
    "ananı", "anani", "ananın", "ananin", "anasını", "anasini",
    "ananısikeyim", "ananisikim", "anasınısikeyim",
    "orospu", "orospuçocuğu", "orospucocugu", "orospuçocukları",
    "orosbucocu", "oç", "oc", "oçlar", "oclar",
    "sik", "sikik", "siktir", "sikerim", "sikeyim", "sikim", "sikimi",
    "sikicem", "siktirgit", "siktiğimin", "siktigimin", "sikmek",
    "siken", "sikici", "siktimin", "siktiriboktan",
    "yarrak", "yarak", "yarrağ", "yarrağı", "yarrağım", "yarramı",
    "göt", "got", "götün", "gotun", "götüne", "gotune",
    "götveren", "gotveren", "götlek", "gotlek",
    "piç", "pic", "piçkurusu", "pickurusu", "piçler",
    "pezevenk", "pezevenkler",
    "kodumun", "kodumunun", "kodumunçocuğu",

    # Sexual
    "ibne", "ıbne", "ibneler",
    "gavat", "gavatlar",
    "kaltak", "kaltaklar",
    "fahişe", "fahise",
    "döl", "dol", "dölü",
    "meme", "memeler",
    "am", "amcık", "amcik", "amcıklar",
    "taşak", "tasak", "daşşak", "dassak", "taşşak",
    "çük", "cuk", "çüük",
    "sikişmek", "sikismek",
    "otuzbir", "31",

    # Insults
    "şerefsiz", "serefsiz", "şerefsizler",
    "haysiyetsiz",
    "dangalak", "dangalaklar",
    "gerizekalı", "gerizekali", "gerizekalılar",
    "aptal", "aptallar",
    "salak", "salaklar",
    "mal", "mallar",
    "ezik", "ezikler",
    "yavşak", "yavsak", "yavşaklar",
    "kahpe", "kahpeler",
    "puşt", "pust", "puştlar",
    "hıyar", "hiyar",
    "sürtük", "surtuk", "sürtükler",
    "dönek", "donek",
    "kepaze",
    "alçak", "alcak",
    "namussuz",
    "adi", "adisiniz",
    "ahlaksız", "ahlaksiz",
    "hayvan", "hayvanlar",
    "it", "itoğlu", "itoglu",
    "köpek", "kopek",

    # Vulgar
    "bok", "boktan", "boklu",
    "hassiktir", "hsktr", "hass",
    "zıkkım", "zikkim",
    "sıçmak", "sicmak",
    "osur", "osurmak",

    # Common evasions
    "a.m.k", "a-m-k", "amq", "a m k",
    "s1k", "s.i.k", "s-k",
    "p1ç", "p.i.ç",
    "o.ç", "o-ç", "0ç",
    "0r0spu", "0rospu",
    "s!kt!r", "s1kt1r",
    "y4rr4k", "y.a.r.r.a.k",
    "g.ö.t", "g0t",
]

# ═══════════════════════════════════════════════════════════════
#  GERMAN PROFANITY
# ═══════════════════════════════════════════════════════════════

GERMAN_BAD_WORDS = [
    "scheiße", "scheisse", "scheiß", "scheiss",
    "fick", "ficken", "ficker", "gefickt",
    "arschloch", "arsch",
    "hurensohn", "hure", "huren",
    "wichser", "wichsen",
    "fotze", "fotzen",
    "schwanz",
    "missgeburt", "misgeburt",
    "bastard",
    "vollidiot", "idiot",
    "drecksau", "dreckig",
    "penner",
    "spast", "spasti",
    "behindert",
    "schwuchtel", "schwul",
    "kanake",
    "nazi", "nazischwein",
]

# ═══════════════════════════════════════════════════════════════
#  SPANISH PROFANITY
# ═══════════════════════════════════════════════════════════════

SPANISH_BAD_WORDS = [
    "puta", "putas", "putamadre", "hijo de puta",
    "mierda", "mierdas",
    "joder", "jodido", "jodete",
    "coño", "cono",
    "pendejo", "pendejos", "pendeja",
    "cabron", "cabrón", "cabrones",
    "chinga", "chingada", "chingado", "chingar",
    "verga", "vergudo",
    "culo",
    "marica", "maricon", "maricón",
    "perra", "perras",
    "zorra", "zorras",
    "gonorrea",
    "malparido", "malparida",
    "hijueputa",
    "mamón", "mamon",
    "idiota",
    "estúpido", "estupido",
    "imbécil", "imbecil",
]

# ═══════════════════════════════════════════════════════════════
#  FRENCH PROFANITY
# ═══════════════════════════════════════════════════════════════

FRENCH_BAD_WORDS = [
    "merde", "putain", "pute", "putes",
    "connard", "connards", "connasse", "connasses",
    "enculé", "encule", "enculer",
    "salaud", "salauds", "salope", "salopes",
    "bordel",
    "foutre", "je m'en fous",
    "baiser",
    "nique", "niquer", "nique ta mère", "niquetamere", "ntm",
    "fils de pute", "fdp",
    "bâtard", "batard",
    "con", "conne",
    "couilles",
    "bite",
    "chatte",
    "branleur", "branler",
    "pd", "pédé", "pede",
    "trou du cul", "trouduc",
]

# ═══════════════════════════════════════════════════════════════
#  RUSSIAN PROFANITY (Transliterated)
# ═══════════════════════════════════════════════════════════════

RUSSIAN_BAD_WORDS = [
    "blyad", "blyat", "blyadi", "cyka", "suka",
    "pizdec", "pizda", "pizdets",
    "nahui", "nahuy", "nahuj",
    "ebat", "eblan", "ebal",
    "huy", "hui", "huesos",
    "mudak", "mudilo",
    "gandon",
    "zalupa",
    "debil",
    "ueban",
    "pidor", "pidoras",
    "svoloch",
    "dolboeb", "dolboyob",
    "idi nahui", "poshel nahui",
    "yob tvoyu mat",
]

# ═══════════════════════════════════════════════════════════════
#  PORTUGUESE PROFANITY
# ═══════════════════════════════════════════════════════════════

PORTUGUESE_BAD_WORDS = [
    "porra", "caralho", "foda", "foder", "fodido", "fodase",
    "merda", "bosta",
    "puta", "putaria", "filho da puta", "fdp",
    "cu", "cuzão", "cuzao",
    "vai se foder", "vai tomar no cu",
    "viado", "veado",
    "arrombado", "arrombada",
    "desgraçado", "desgracado", "desgraça",
    "otário", "otario",
    "babaca",
    "buceta", "xoxota", "xereca",
    "piroca", "rola", "pau",
    "punheta", "punheteiro",
    "corno",
]

# ═══════════════════════════════════════════════════════════════
#  SCAM / PHISHING / NSFW / MALICIOUS LINKS
# ═══════════════════════════════════════════════════════════════

BLOCKED_LINKS = [
    # ─── Discord Phishing ────────────────────────────────
    "discord.gift", "discordgift.com",
    "dlscord.com", "dlscord.org", "dlscord.gg",
    "discordi.com", "discorcl.com", "disc0rd.com",
    "discord-nitro.com", "discordnitro.com",
    "discord-app.com", "discordapp.co", "discordapp.net",
    "dis-cord.com", "dis.cord.com",
    "dlscord-app.com", "dlscordapp.com",
    "discrod.com", "dicsord.com", "disocrd.com",
    "discord-give.com", "discord-airdrop.com",
    "discordsteam.com", "discord-hypesquad.com",
    "discord-partner.com",
    "discordgiveaway.com", "discord-drop.com",
    "discordappgift.com",
    "nitro-gift.com", "nitro-drop.com",
    "free-nitro.com", "freenitro.com",
    "claim-nitro.com", "nitrodiscord.com",
    "gift-discord.com", "claimdiscord.com",
    "discord-claim.com",

    # ─── Steam Phishing ──────────────────────────────────
    "steamcommunlty.com", "steamcommunlty.ru",
    "steancommunity.com", "steamcommunity.ru",
    "steamcommunitv.com", "steamcornmunity.com",
    "steamcomrnunity.com", "steammcommunity.com",
    "store-steampowered.com", "steampowored.com",
    "steampowerd.com", "stearnpowered.com",
    "steamtrade.me", "steamtrading.org",
    "csgo-skins.com", "csgo-drop.com",
    "csgofree.com", "skinsfree.com",
    "steamgifts.pro", "steam-gifts.com",

    # ─── General Phishing / Scam ─────────────────────────
    "free-robux.com", "freerobux.gg",
    "vbucks-free.com", "freevbucks.com",
    "roblox-free.com",
    "fortnite-free.com",
    "minecraft-free.com",
    "gift-cards-free.com",
    "amazon-gift.com",

    # ─── IP Loggers / Grabbers ───────────────────────────
    "grabify.link", "iplogger.com", "iplogger.org",
    "2no.co", "ipgrabber.ru", "iplis.ru",
    "02telecom.eu", "blasze.tk", "yip.su",
    "bfrfrg.info", "youramonkey.com",
    "protonpage.com", "lovebird.guru",
    "trfrg.info", "shrekis.life",
    "headshot.monster", "gaming-at-my.best",
    "progaming.monster", "yourmy.monster",
    "imagons.com", "iplogger.co",
    "ezstat.ru", "whatstheirip.com",
    "hfrfrg.info", "myiptest.com",
    "ipsnoop.com",

    # ─── Malware / RAT Hosting ───────────────────────────
    "anonfiles.com",
    "mediafire.com",
    "mega.nz",
    "gofile.io",
    "file.io",
    "anonymousfiles.io",
    "transfer.sh",
    "fileditch.com",
    "bayfiles.com",

    # ─── NSFW / Adult Content ────────────────────────────
    "pornhub.com", "xvideos.com", "xnxx.com",
    "xhamster.com", "redtube.com", "youporn.com",
    "brazzers.com", "onlyfans.com", "fansly.com",
    "chaturbate.com", "stripchat.com", "cam4.com",
    "bongacams.com", "livejasmin.com", "myfreecams.com",
    "rule34.xxx", "rule34.paheal.net",
    "e621.net", "e926.net",
    "nhentai.net", "nhentai.to",
    "hanime.tv", "hentaihaven.xxx",
    "gelbooru.com", "danbooru.donmai.us",
    "sankakucomplex.com",
    "fapello.com", "thothub.tv",
    "erome.com", "noodlemagazine.com",
    "spankbang.com", "tnaflix.com",
    "tube8.com", "beeg.com",
    "motherless.com", "efukt.com",

    # ─── URL Shorteners (often used for scams) ──────────
    "bit.ly", "tinyurl.com", "shorturl.at",
    "t.co", "goo.gl", "is.gd", "v.gd",
    "rb.gy", "cutt.ly", "ow.ly",
    "adf.ly", "ouo.io", "bc.vc",
    "exe.io", "za.gl", "shrink.pe",
    "short.io", "clck.ru",
    "linktr.ee",
    "rebrand.ly", "bl.ink",
    "smarturl.it",

    # ─── Crypto Scam ─────────────────────────────────────
    "freecrypto.com", "freebitcoin.io",
    "crypto-airdrop.com", "btc-drop.com",
    "ethereum-giveaway.com",
    "elon-crypto.com",

    # ─── Token Grabbers / Webhook Exploits ───────────────
    "discordtokengrabber.com",
    "webhook.site",
    "hookbin.com",
    "requestbin.com",
    "pipedream.com",
]

# ═══════════════════════════════════════════════════════════════
#  ALLOWED DOMAINS (bypass anti-link)
# ═══════════════════════════════════════════════════════════════

ALLOWED_DOMAINS = [
    # Discord
    "discord.com", "discord.gg", "discordapp.com",
    "cdn.discordapp.com", "media.discordapp.net",
    # Google
    "google.com", "google.co", "googleapis.com",
    "youtube.com", "youtu.be", "googledrive.com",
    "docs.google.com", "drive.google.com",
    # Social Media
    "twitter.com", "x.com", "t.co",
    "instagram.com", "facebook.com", "fb.com",
    "tiktok.com", "vm.tiktok.com",
    "reddit.com", "old.reddit.com",
    "pinterest.com", "linkedin.com",
    "snapchat.com", "threads.net",
    "bsky.app", "mastodon.social",
    # Streaming
    "twitch.tv", "clips.twitch.tv",
    "spotify.com", "open.spotify.com",
    "soundcloud.com", "music.apple.com",
    "deezer.com", "tidal.com",
    # Gaming
    "steam.com", "steampowered.com", "steamcommunity.com",
    "epicgames.com", "store.epicgames.com",
    "roblox.com", "minecraft.net",
    "ea.com", "ubisoft.com",
    "xbox.com", "playstation.com",
    "riot.com", "leagueoflegends.com",
    "blizzard.com", "battle.net",
    # Dev
    "github.com", "gist.github.com",
    "gitlab.com", "bitbucket.org",
    "stackoverflow.com", "stackexchange.com",
    "npmjs.com", "pypi.org",
    "replit.com", "codepen.io",
    "vercel.app", "netlify.app",
    # Media / Images
    "imgur.com", "i.imgur.com",
    "tenor.com", "giphy.com", "gfycat.com",
    "prnt.sc", "lightshot.com",
    "flickr.com", "unsplash.com",
    # Reference
    "wikipedia.org", "wikimedia.org",
    "fandom.com",
    "archive.org",
    # News
    "bbc.com", "cnn.com", "reuters.com",
    "theguardian.com", "nytimes.com",
    # Misc trusted
    "paypal.com", "patreon.com",
    "ko-fi.com", "buymeacoffee.com",
    "amazon.com", "ebay.com",
    "notion.so", "notion.site",
    "canva.com", "figma.com",
    "trello.com", "asana.com",
]

# ═══════════════════════════════════════════════════════════════
#  ZALGO / UNICODE ABUSE RANGES
# ═══════════════════════════════════════════════════════════════

ZALGO_CHARS = (
    "\u0300-\u036f"   # Combining Diacritical Marks
    "\u0489"          # Combining Cyrillic
    "\u1dc0-\u1dff"   # Combining Diacritical Marks Supplement
    "\u20d0-\u20ff"   # Combining Diacritical Marks for Symbols
    "\ufe20-\ufe2f"   # Combining Half Marks
)

# ═══════════════════════════════════════════════════════════════
#  HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def get_all_bad_words() -> list[str]:
    """Get all built-in bad words from all languages."""
    combined = (
        ENGLISH_BAD_WORDS +
        TURKISH_BAD_WORDS +
        GERMAN_BAD_WORDS +
        SPANISH_BAD_WORDS +
        FRENCH_BAD_WORDS +
        RUSSIAN_BAD_WORDS +
        PORTUGUESE_BAD_WORDS
    )
    return list(set(w.lower() for w in combined))


def get_all_blocked_links() -> list[str]:
    """Get all blocked domains."""
    return list(set(d.lower() for d in BLOCKED_LINKS))


def get_allowed_domains() -> list[str]:
    """Get all allowed domains."""
    return list(set(d.lower() for d in ALLOWED_DOMAINS))


def get_bad_words_by_language(lang: str) -> list[str]:
    """Get bad words for a specific language."""
    mapping = {
        "english": ENGLISH_BAD_WORDS,
        "turkish": TURKISH_BAD_WORDS,
        "german": GERMAN_BAD_WORDS,
        "spanish": SPANISH_BAD_WORDS,
        "french": FRENCH_BAD_WORDS,
        "russian": RUSSIAN_BAD_WORDS,
        "portuguese": PORTUGUESE_BAD_WORDS,
    }
    return mapping.get(lang.lower(), [])


def get_blocked_links_by_category() -> dict[str, list[str]]:
    """Get blocked links organized by category."""
    return {
        "Discord Phishing": [l for l in BLOCKED_LINKS if "disc" in l or "nitro" in l or "dlsc" in l],
        "Steam Phishing": [l for l in BLOCKED_LINKS if "steam" in l or "csgo" in l],
        "IP Loggers": [l for l in BLOCKED_LINKS if any(x in l for x in ["grab", "iplog", "ipgrab", "2no", "ezstat", "yip.su", "blasze", "hookbin", "webhook"])],
        "NSFW": [l for l in BLOCKED_LINKS if any(x in l for x in ["porn", "xxx", "xvideo", "xnxx", "xhamster", "brazzers", "onlyfans", "hentai", "nhentai", "rule34", "e621", "chaturbate", "strip", "cam4", "bonga", "livejasmin", "fap", "spank", "tube8", "beeg", "mother", "erome", "noodle", "thothub", "fansly"])],
        "URL Shorteners": [l for l in BLOCKED_LINKS if any(x in l for x in ["bit.ly", "tinyurl", "shorturl", "goo.gl", "is.gd", "v.gd", "rb.gy", "cutt.ly", "ow.ly", "adf.ly", "ouo", "bc.vc", "exe.io", "za.gl", "shrink", "short.io", "clck", "rebrand", "bl.ink", "smart"])],
        "Malware Hosting": [l for l in BLOCKED_LINKS if any(x in l for x in ["anonfiles", "mediafire", "mega.nz", "gofile", "file.io", "anonym", "transfer.sh", "fileditch", "bayfiles"])],
        "Crypto Scam": [l for l in BLOCKED_LINKS if any(x in l for x in ["crypto", "bitcoin", "btc", "ethereum", "elon"])],
    }


def get_stats() -> dict:
    """Get statistics about the built-in database."""
    all_words = get_all_bad_words()
    all_links = get_all_blocked_links()
    return {
        "total_words": len(all_words),
        "total_links": len(all_links),
        "total_allowed": len(get_allowed_domains()),
        "languages": {
            "English": len(ENGLISH_BAD_WORDS),
            "Turkish": len(TURKISH_BAD_WORDS),
            "German": len(GERMAN_BAD_WORDS),
            "Spanish": len(SPANISH_BAD_WORDS),
            "French": len(FRENCH_BAD_WORDS),
            "Russian": len(RUSSIAN_BAD_WORDS),
            "Portuguese": len(PORTUGUESE_BAD_WORDS),
        },
        "link_categories": {k: len(v) for k, v in get_blocked_links_by_category().items()},
    }